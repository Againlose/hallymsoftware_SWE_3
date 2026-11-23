from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from companion_robot import JsonStore, Robot
from memory_archive import ArchiveError, MemoryArchive


class MemoryArchiveStartupTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = JsonStore(directory.name)
        self.db_path = self.store.data_dir / "memory_archive.sqlite3"

    def test_robot_initializes_new_database_and_registers_profile(self):
        self.assertFalse(self.db_path.exists())
        robot = Robot(self.store)
        self.assertIsInstance(robot.memory_archive, MemoryArchive)
        self.assertIsNone(robot.memory_archive_error)
        actor_id = robot.profile.user_id
        archive_id = robot.memory_archive.create_archive(actor_id, "내 기억")
        self.assertEqual(robot.memory_archive.list_archives(actor_id)[0]["archive_id"], archive_id)

    def test_opening_invalid_database_directly_reports_database_error(self):
        self.db_path.write_bytes(b"not a SQLite database")
        with self.assertRaises(sqlite3.DatabaseError):
            MemoryArchive(self.db_path)

    def test_corrupt_database_does_not_block_core_features(self):
        self.db_path.write_bytes(b"not a SQLite database")
        robot = Robot(self.store)
        self.assertIsNone(robot.memory_archive)
        self.assertIn("가족 기억 DB 초기화 오류", robot.memory_archive_error)
        self.assertEqual(robot.start_conversation("안녕하세요")[1], "greeting")
        robot.medications.add("예시약", "09:00")
        self.assertEqual(len(robot.check_medication(datetime(2026, 11, 23, 9, 2))), 1)
        self.assertEqual(robot.navigator.route("거실", "주방"), ["거실", "주방"])
        self.assertIsInstance(robot.get_gas_status_summary(), str)

    def test_corrupt_sqlite_page_is_detected_and_original_file_is_preserved(self):
        archive = MemoryArchive(self.db_path)
        archive.register_user("user", "사용자")
        archive_id = archive.create_archive("user", "보관함")
        archive.create_memory("user", archive_id, "제목", "본문")
        with closing(sqlite3.connect(self.db_path)) as db:
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            page_number = db.execute(
                "SELECT rootpage FROM sqlite_master WHERE name='memory_revision'"
            ).fetchone()[0]
        original = bytearray(self.db_path.read_bytes())
        original[(page_number - 1) * page_size] = 0
        self.db_path.write_bytes(original)
        file_before = self.db_path.stat()

        for _ in range(2):
            robot = Robot(self.store)
            self.assertIsNone(robot.memory_archive)
            self.assertIsNotNone(robot.memory_archive_error)
        self.assertEqual(self.db_path.read_bytes(), bytes(original))
        file_after = self.db_path.stat()
        self.assertEqual((file_after.st_ino, file_after.st_mtime_ns),
                         (file_before.st_ino, file_before.st_mtime_ns))

    def test_database_failure_during_profile_registration_disables_archive(self):
        archive = MemoryArchive(self.db_path)
        with patch.object(archive, "register_user", side_effect=sqlite3.OperationalError("database is locked")):
            robot = Robot(self.store, memory_archive=archive)
        self.assertIsNone(robot.memory_archive)
        self.assertIsNotNone(robot.memory_archive_error)
        self.assertIsNotNone(Robot(self.store, memory_archive=archive).memory_archive)

    def test_restart_preserves_existing_memory_crud_and_version_conflicts(self):
        initial = Robot(self.store)
        actor_id = initial.profile.user_id
        archive_id = initial.memory_archive.create_archive(actor_id, "내 기억")
        memory_id = initial.memory_archive.create_memory(actor_id, archive_id, "제목", "원래 본문")

        reopened = Robot(self.store).memory_archive
        self.assertEqual(reopened.get_memory(actor_id, memory_id)["content"], "원래 본문")
        self.assertEqual(reopened.update_memory(actor_id, memory_id, 1, "제목", "수정된 본문"), 2)
        with self.assertRaises(ArchiveError) as error:
            initial.memory_archive.update_memory(actor_id, memory_id, 1, "제목", "오래된 수정")
        self.assertEqual(error.exception.code, "CONFLICT")
        restored = Robot(self.store).memory_archive
        self.assertEqual([row["content"] for row in restored.history(actor_id, memory_id)],
                         ["수정된 본문", "원래 본문"])
        restored.delete_memory(actor_id, memory_id, 2)
        self.assertEqual(Robot(self.store).memory_archive.search(actor_id), [])


class MemoryArchiveTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.service = MemoryArchive(self.root / "memory.sqlite3")
        for actor in ("admin", "member", "outsider"):
            self.service.register_user(actor, actor)
        self.family = self.service.create_family("admin", "우리 가족")
        self.member = self.service.add_member("admin", self.family, "가족", user_id="member")
        self.archive = self.service.create_archive("admin", "가족 여행", family_id=self.family)

    def test_persistence_and_partial_date_filters(self):
        memory = self.service.create_memory(
            "admin", self.archive, "봄 여행", "가족과 바다", visibility="FAMILY",
            event_date="2024-02", member_ids=[self.member], tags=["TRIP"],
        )
        reopened = MemoryArchive(self.service.db_path)
        rows = reopened.search("member", "바다", member_id=self.member, tag="trip",
                               start="2024-02-29", end="2024-02-29")
        self.assertEqual([row["memory_id"] for row in rows], [memory])
        self.assertEqual(rows[0]["date_precision"], "MONTH")
        self.assertEqual(reopened.search("member", start="2024-03"), [])

    def test_admin_cannot_read_private_memory(self):
        memory = self.service.create_memory("member", self.archive, "비공개", "일기")
        for actor in ("admin", "outsider"):
            self.assertEqual(self.service.search(actor), [])
            with self.assertRaises(ArchiveError) as error:
                self.service.get_memory(actor, memory)
            self.assertEqual(error.exception.code, "NOT_FOUND")

    def test_family_revocation_preserves_personal_archive(self):
        personal = self.service.create_archive("member", "내 기록")
        private = self.service.create_memory("member", personal, "비공개", "일기")
        shared = self.service.create_memory("admin", self.archive, "공개", "일기", visibility="FAMILY")
        source = self.service.answer_from_memories("member", "공개")["sources"][0]
        self.service.set_member_active("admin", self.family, self.member, False)
        self.assertEqual([row["memory_id"] for row in self.service.search("member")], [private])
        with self.assertRaises(ArchiveError):
            self.service.get_source("member", shared, source["revision_id"])

    def test_revision_conflict_and_deleted_citations(self):
        memory = self.service.create_memory("member", self.archive, "제목", "이전", visibility="FAMILY")
        source = self.service.answer_from_memories("admin", "이전")["sources"][0]
        self.assertEqual(self.service.update_memory("admin", memory, 1, "제목", "최신"), 2)
        with self.assertRaises(ArchiveError) as error:
            self.service.update_memory("member", memory, 1, "제목", "오래된 수정")
        self.assertEqual(error.exception.code, "CONFLICT")
        self.assertEqual([row["version_no"] for row in self.service.history("member", memory)], [2, 1])
        self.assertEqual(self.service.search("admin", "이전"), [])
        with self.assertRaises(ArchiveError):
            self.service.get_source("admin", memory, source["revision_id"])
        self.service.delete_memory("member", memory, 2)
        self.assertEqual(self.service.answer_from_memories("admin", "최신")["sources"], [])

    def test_cross_family_person_rolls_back_creation(self):
        another = self.service.create_family("outsider", "다른 가족")
        person = self.service.add_member("outsider", another, "다른 가족 인물")
        with self.assertRaises(ArchiveError):
            self.service.create_memory("admin", self.archive, "제목", "본문", member_ids=[person])
        self.assertEqual(self.service.search("admin"), [])

    def test_robot_loads_legacy_state_and_persists_archive_separately(self):
        store = JsonStore(self.root / "demo")
        store.save({"profile": {"user_id": "old", "name": "기존"}, "medications": []})
        robot = Robot(store)
        archive = robot.memory_archive.create_archive(robot.profile.user_id, "내 기억")
        robot.save()
        self.assertEqual(Robot(store).memory_archive.list_archives("old")[0]["archive_id"], archive)
        self.assertEqual(store.load()["medications"], [])
