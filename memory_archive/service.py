"""Local Family Memory Archive service. Actor IDs come from the trusted caller."""
from calendar import monthrange
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4


class ArchiveError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _required(value):
    if not isinstance(value, str) or not value.strip():
        raise ArchiveError("INVALID_INPUT", "필수 텍스트를 입력하세요.")
    return value.strip()


def _event_date(value):
    if value is None or value == "":
        return None, None, "UNKNOWN"
    try:
        fields = value.split("-")
        if [len(field) for field in fields] == [4]:
            year = int(value)
            return date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat(), "YEAR"
        if [len(field) for field in fields] == [4, 2]:
            year, month = map(int, fields)
            return (date(year, month, 1).isoformat(),
                    date(year, month, monthrange(year, month)[1]).isoformat(), "MONTH")
        day = date.fromisoformat(value)
        if day.isoformat() == value:
            return value, value, "DAY"
    except (ValueError, TypeError, AttributeError):
        pass
    raise ArchiveError("INVALID_INPUT", "발생일은 YYYY, YYYY-MM 또는 YYYY-MM-DD 형식이어야 합니다.")


def _now():
    return datetime.now(timezone.utc).isoformat()


class MemoryArchive:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self._db() as db:
            if db.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("Family memory database failed its integrity check")
            # executescript closes the read transaction. Run all schema changes in one write transaction.
            db.executescript("BEGIN IMMEDIATE;\n" + schema)

    @contextmanager
    def _db(self, *, write=False):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            with db:
                yield db
        finally:
            db.close()

    def register_user(self, user_id, display_name):
        """Register or synchronize a trusted profile display name without altering family nicknames."""
        with self._db(write=True) as db:
            db.execute(
                """INSERT INTO app_user (user_id, display_name) VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET display_name = excluded.display_name""",
                (_required(user_id), _required(display_name)),
            )

    @staticmethod
    def _role(db, actor_id, family_id):
        row = db.execute(
            "SELECT role FROM family_member WHERE family_id=? AND user_id=? AND active=1",
            (family_id, actor_id),
        ).fetchone()
        return row["role"] if row else None

    @staticmethod
    def _require_user(db, actor_id):
        if not db.execute("SELECT 1 FROM app_user WHERE user_id=?", (actor_id,)).fetchone():
            raise ArchiveError("FORBIDDEN", "등록된 사용자만 이용할 수 있습니다.")

    def create_family(self, actor_id, name):
        family_id = str(uuid4())
        with self._db(write=True) as db:
            self._require_user(db, actor_id)
            db.execute("INSERT INTO family VALUES (?, ?)", (family_id, _required(name)))
            db.execute(
                """INSERT INTO family_member (member_id, family_id, user_id, display_name, role)
                   SELECT ?, ?, user_id, display_name, 'ADMIN' FROM app_user WHERE user_id=?""",
                (str(uuid4()), family_id, actor_id),
            )
        return family_id

    def add_member(self, actor_id, family_id, display_name, *, user_id=None):
        member_id = str(uuid4())
        with self._db(write=True) as db:
            if self._role(db, actor_id, family_id) != "ADMIN":
                raise ArchiveError("FORBIDDEN", "가족 관리자만 구성원을 추가할 수 있습니다.")
            if user_id is not None:
                self._require_user(db, user_id)
                if db.execute("SELECT 1 FROM family_member WHERE family_id=? AND user_id=?",
                              (family_id, user_id)).fetchone():
                    raise ArchiveError("CONFLICT", "이미 등록된 가족 계정입니다.")
            db.execute(
                """INSERT INTO family_member (member_id, family_id, user_id, display_name, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (member_id, family_id, user_id, _required(display_name),
                 "MEMBER" if user_id is not None else None),
            )
        return member_id

    def set_member_active(self, actor_id, family_id, member_id, active):
        with self._db(write=True) as db:
            if self._role(db, actor_id, family_id) != "ADMIN":
                raise ArchiveError("FORBIDDEN", "가족 관리자만 구성원 상태를 변경할 수 있습니다.")
            changed = db.execute(
                """UPDATE family_member SET active=? WHERE family_id=? AND member_id=?
                   AND (role IS NULL OR role='MEMBER')""",
                (int(bool(active)), family_id, member_id),
            )
            if not changed.rowcount:
                raise ArchiveError("NOT_FOUND", "변경 가능한 가족 구성원이 없습니다.")

    def list_members(self, actor_id, family_id):
        with self._db() as db:
            if not self._role(db, actor_id, family_id):
                raise ArchiveError("NOT_FOUND", "접근 가능한 가족이 없습니다.")
            return [dict(row) for row in db.execute(
                """SELECT member_id, display_name, role, active FROM family_member
                   WHERE family_id=? ORDER BY display_name, member_id""", (family_id,)
            )]

    def create_archive(self, actor_id, name, *, family_id=None):
        archive_id = str(uuid4())
        with self._db(write=True) as db:
            self._require_user(db, actor_id)
            if family_id is not None and self._role(db, actor_id, family_id) != "ADMIN":
                raise ArchiveError("FORBIDDEN", "가족 관리자만 가족 보관함을 만들 수 있습니다.")
            db.execute("INSERT INTO archive VALUES (?, ?, ?, ?)",
                       (archive_id, _required(name), actor_id if family_id is None else None, family_id))
        return archive_id

    def list_archives(self, actor_id):
        with self._db() as db:
            return [dict(row) for row in db.execute(
                """SELECT * FROM archive WHERE owner_user_id=? OR family_id IN (
                       SELECT family_id FROM family_member WHERE user_id=? AND active=1)
                   ORDER BY name, archive_id""", (actor_id, actor_id),
            )]

    def _append_revision(self, db, actor_id, memory_id, version, family_id,
                         title, content, event_date, member_ids, tags):
        title, content = _required(title), _required(content)
        start, end, precision = _event_date(event_date)
        revision_id = str(uuid4())
        db.execute("INSERT INTO memory_revision VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (revision_id, memory_id, version, title, content, start, end, precision, actor_id, _now()))
        for member_id in dict.fromkeys(member_ids):
            if family_id is None or not db.execute(
                "SELECT 1 FROM family_member WHERE member_id=? AND family_id=? AND active=1",
                (member_id, family_id),
            ).fetchone():
                raise ArchiveError("INVALID_INPUT", "같은 가족의 활성 구성원만 연결할 수 있습니다.")
            db.execute("INSERT INTO memory_person VALUES (?, ?)", (revision_id, member_id))
        normalized_tags = {_required(tag).casefold() for tag in tags}
        db.executemany("INSERT INTO memory_tag VALUES (?, ?)",
                       [(revision_id, tag) for tag in sorted(normalized_tags)])

    def create_memory(self, actor_id, archive_id, title, content, *, visibility="PRIVATE",
                      event_date=None, member_ids=(), tags=()):
        memory_id = str(uuid4())
        with self._db(write=True) as db:
            self._require_user(db, actor_id)
            archive = db.execute("SELECT * FROM archive WHERE archive_id=?", (archive_id,)).fetchone()
            if not archive or (archive["owner_user_id"] != actor_id and
                               not self._role(db, actor_id, archive["family_id"])):
                raise ArchiveError("NOT_FOUND", "접근 가능한 보관함이 없습니다.")
            if visibility != "PRIVATE" and (visibility != "FAMILY" or archive["family_id"] is None):
                raise ArchiveError("INVALID_INPUT", "가족 공개는 가족 보관함에서만 설정할 수 있습니다.")
            db.execute("INSERT INTO memory VALUES (?, ?, ?, ?, 1, NULL)",
                       (memory_id, archive_id, actor_id, visibility))
            self._append_revision(db, actor_id, memory_id, 1, archive["family_id"],
                                  title, content, event_date, member_ids, tags)
        return memory_id

    @staticmethod
    def _visible(db, actor_id, *, where="", params=()):
        return db.execute(
            """SELECT m.*, a.family_id, r.revision_id, r.title, r.content,
                      r.event_start, r.event_end, r.date_precision, r.created_at
               FROM memory m JOIN archive a USING (archive_id)
               JOIN memory_revision r ON r.memory_id=m.memory_id AND r.version_no=m.current_version
               WHERE m.deleted_at IS NULL AND (
                   (m.visibility='PRIVATE' AND m.author_user_id=?) OR
                   (m.visibility='FAMILY' AND EXISTS (
                       SELECT 1 FROM family_member f WHERE f.family_id=a.family_id
                       AND f.user_id=? AND f.active=1)))
            """ + where + " ORDER BY r.created_at DESC, m.memory_id",
            (actor_id, actor_id, *params),
        )

    def _get(self, db, actor_id, memory_id):
        row = self._visible(db, actor_id, where=" AND m.memory_id=?", params=(memory_id,)).fetchone()
        if row is None:
            raise ArchiveError("NOT_FOUND", "접근 가능한 기억이 없습니다.")
        return row

    def get_memory(self, actor_id, memory_id):
        with self._db() as db:
            memory = dict(self._get(db, actor_id, memory_id))
            revision_id = memory["revision_id"]
            memory["member_ids"] = [row[0] for row in db.execute(
                "SELECT member_id FROM memory_person WHERE revision_id=? ORDER BY member_id", (revision_id,)
            )]
            memory["tags"] = [row[0] for row in db.execute(
                "SELECT tag FROM memory_tag WHERE revision_id=? ORDER BY tag", (revision_id,)
            )]
            return memory

    def _check_edit(self, db, actor_id, row, expected_version):
        if row["author_user_id"] != actor_id and self._role(db, actor_id, row["family_id"]) != "ADMIN":
            raise ArchiveError("FORBIDDEN", "기억을 수정하거나 삭제할 권한이 없습니다.")
        if row["current_version"] != expected_version:
            raise ArchiveError("CONFLICT", "기억이 변경되었습니다. 최신 버전을 다시 조회하세요.")

    def update_memory(self, actor_id, memory_id, expected_version, title, content, *,
                      event_date=None, member_ids=(), tags=()):
        with self._db(write=True) as db:
            row = self._get(db, actor_id, memory_id)
            self._check_edit(db, actor_id, row, expected_version)
            version = expected_version + 1
            self._append_revision(db, actor_id, memory_id, version, row["family_id"],
                                  title, content, event_date, member_ids, tags)
            db.execute("UPDATE memory SET current_version=? WHERE memory_id=?", (version, memory_id))
        return version

    def delete_memory(self, actor_id, memory_id, expected_version):
        with self._db(write=True) as db:
            row = self._get(db, actor_id, memory_id)
            self._check_edit(db, actor_id, row, expected_version)
            db.execute("UPDATE memory SET deleted_at=? WHERE memory_id=?", (_now(), memory_id))

    def history(self, actor_id, memory_id):
        with self._db() as db:
            self._get(db, actor_id, memory_id)
            return [dict(row) for row in db.execute(
                "SELECT * FROM memory_revision WHERE memory_id=? ORDER BY version_no DESC", (memory_id,)
            )]

    def search(self, actor_id, keyword="", *, archive_id=None, member_id=None,
               start=None, end=None, tag=None):
        start = _event_date(start)[0]
        end = _event_date(end)[1]
        if start and end and start > end:
            raise ArchiveError("INVALID_INPUT", "검색 시작일은 종료일보다 늦을 수 없습니다.")
        predicates = [
            ("m.archive_id=?", archive_id),
            ("r.event_end>=?", start),
            ("r.event_start<=?", end),
            ("EXISTS (SELECT 1 FROM memory_person p WHERE p.revision_id=r.revision_id AND p.member_id=?)",
             member_id),
            ("EXISTS (SELECT 1 FROM memory_tag t WHERE t.revision_id=r.revision_id AND t.tag=?)",
             _required(tag).casefold() if tag is not None else None),
        ]
        clauses = [clause for clause, value in predicates if value is not None]
        params = [value for _, value in predicates if value is not None]
        words = keyword.casefold().split()
        with self._db() as db:
            return [
                dict(row) for row in self._visible(
                    db, actor_id, where="".join(" AND " + clause for clause in clauses), params=params
                )
                if all(word in f"{row['title']} {row['content']}".casefold() for word in words)
            ]

    def answer_from_memories(self, actor_id, keyword):
        """Return an extractive preview and opaque current-revision citations."""
        matches = self.search(actor_id, _required(keyword))[:3]
        return {
            "text": "\n".join(f"{row['title']}: {row['content'][:240]}" for row in matches)
                    or "관련 기억을 찾지 못했습니다.",
            "sources": [
                {"memory_id": row["memory_id"], "revision_id": row["revision_id"], "title": row["title"]}
                for row in matches
            ],
        }

    def get_source(self, actor_id, memory_id, revision_id):
        """Recheck visibility and the current revision whenever a citation is opened."""
        row = self.get_memory(actor_id, memory_id)
        if row["revision_id"] != revision_id:
            raise ArchiveError("NOT_FOUND", "현재 버전의 출처를 다시 검색하세요.")
        return row
