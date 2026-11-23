CREATE TABLE IF NOT EXISTS app_user (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS family (
    family_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS family_member (
    member_id TEXT PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES family,
    user_id TEXT REFERENCES app_user,
    display_name TEXT NOT NULL,
    role TEXT CHECK (role IN ('ADMIN', 'MEMBER')),
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE (family_id, user_id)
);
CREATE TABLE IF NOT EXISTS archive (
    archive_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_user_id TEXT REFERENCES app_user,
    family_id TEXT REFERENCES family,
    CHECK ((owner_user_id IS NULL) <> (family_id IS NULL))
);
CREATE TABLE IF NOT EXISTS memory (
    memory_id TEXT PRIMARY KEY,
    archive_id TEXT NOT NULL REFERENCES archive,
    author_user_id TEXT NOT NULL REFERENCES app_user,
    visibility TEXT NOT NULL CHECK (visibility IN ('PRIVATE', 'FAMILY')),
    current_version INTEGER NOT NULL,
    deleted_at TEXT
);
CREATE TABLE IF NOT EXISTS memory_revision (
    revision_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memory,
    version_no INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    event_start TEXT,
    event_end TEXT,
    date_precision TEXT NOT NULL,
    editor_user_id TEXT NOT NULL REFERENCES app_user,
    created_at TEXT NOT NULL,
    UNIQUE (memory_id, version_no)
);
CREATE TABLE IF NOT EXISTS memory_person (
    revision_id TEXT NOT NULL REFERENCES memory_revision,
    member_id TEXT NOT NULL REFERENCES family_member,
    PRIMARY KEY (revision_id, member_id)
);
CREATE TABLE IF NOT EXISTS memory_tag (
    revision_id TEXT NOT NULL REFERENCES memory_revision,
    tag TEXT NOT NULL,
    PRIMARY KEY (revision_id, tag)
);
