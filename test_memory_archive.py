from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from companion_robot import JsonStore, Robot
from memory_archive import ArchiveError, MemoryArchive


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
