# 가족 기억 보관함 구현 문서

설계 기준은 「AI Companion 통합 기획·기능 명세 및 데이터 설계 v1.0」의 KAN-28, 3절, 5절, 부록 B-1·B-2다. 프로토타입의 첫 구현으로 보관함과 가족 구성원, 기억 CRUD, 검색, 버전 이력, 근거 미리보기를 제공한다.

## 실행

`python companion_robot.py`로 실행해 **가족 기억** 탭에서 개인 보관함을 만든다. 제목과 본문을 작성하고 저장한다. 검색어 없이 보관함을 검색하면 열람 가능한 기억을 표시한다. 검색 결과를 선택해 수정·삭제할 수 있다. **근거 미리보기**는 현재 사용자가 열람할 수 있는 모든 보관함에서 검색한다.

새 가족과 가족 보관함은 탭에서도 생성할 수 있다. 기존 가족의 보관함 추가, 계정 구성원·등장 인물 연결과 복합 검색은 아래 Python API로 사용할 수 있다. Tkinter 탭은 실행 중인 로컬 프로필을 사용한다.

## Python API

```python
from companion_robot import JsonStore, Robot

robot = Robot(JsonStore("demo_data"))
archive = robot.memory_archive
actor_id = robot.profile.user_id
family_id = archive.create_family(actor_id, "우리 가족")
archive_id = archive.create_archive(actor_id, "가족 여행", family_id=family_id)
member_id = archive.add_member(actor_id, family_id, "할머니")
memory_id = archive.create_memory(
    actor_id, archive_id, "가족 여행", "할머니와 동해에 갔다.",
    visibility="FAMILY", event_date="2024-02", member_ids=[member_id], tags=["여행"],
)
matches = archive.search(actor_id, "동해", member_id=member_id, start="2024", tag="여행")
answer = archive.answer_from_memories(actor_id, "동해")
citation = answer["sources"][0]
source = archive.get_source(actor_id, citation["memory_id"], citation["revision_id"])
```

| 호출 | 매개변수와 결과 |
| --- | --- |
| `register_user(user_id, display_name)` | 신뢰된 프로필 또는 계정 연동 계층에서 호출. 동일 ID의 반복 등록 허용 |
| `create_family(actor_id, name)` | 생성자를 ADMIN으로 등록하고 `family_id` 반환 |
| `add_member(actor_id, family_id, display_name, user_id=None)` | ADMIN 전용. `user_id`를 생략하면 계정 없는 인물로 등록. `member_id` 반환 |
| `list_members(actor_id, family_id)`, `set_member_active(actor_id, family_id, member_id, active)` | 활성 구성원은 목록 조회 가능. ADMIN은 일반 구성원 및 비계정 인물을 활성화·비활성화 |
| `create_archive(actor_id, name, family_id=None)`, `list_archives(actor_id)` | 보관함 ID 및 접근 가능한 보관함 목록. 가족 보관함 생성은 ADMIN 전용 |
| `create_memory(actor_id, archive_id, title, content, visibility="PRIVATE", event_date=None, member_ids=(), tags=())` | 공개 범위와 인물 관계를 검사하고 `memory_id` 반환 |
| `get_memory(actor_id, memory_id)`, `history(actor_id, memory_id)` | 현재 본문·연결 정보 및 내림차순 본문 변경 이력 |
| `update_memory(actor_id, memory_id, expected_version, title, content, event_date=None, member_ids=(), tags=())` | 날짜·인물·태그를 포함한 전체 새 버전 저장. 새 버전 번호 반환 |
| `delete_memory(actor_id, memory_id, expected_version)` | `deleted_at`으로 논리 삭제. 검색·이력·출처에서 즉시 제외 |
| `search(actor_id, keyword="", archive_id=None, member_id=None, start=None, end=None, tag=None)` | 단어 모두 포함 및 선택 필터 교집합. 기간은 기억 발생 구간과 겹치는 기록 반환 |
| `answer_from_memories(actor_id, keyword)`, `get_source(actor_id, memory_id, revision_id)` | 최신 본문 발췌와 출처 반환. 출처를 다시 열 때 권한과 최신 버전을 검사 |

`actor_id`는 신뢰된 호출 계층이 확정한 사용자 ID다. 앱의 사용자 인증 서버와 HTTP API는 별도 통합 작업이다. 실패는 `ArchiveError.code`로 구분한다. `INVALID_INPUT`은 입력 오류, `FORBIDDEN`은 권한 오류, `NOT_FOUND`는 접근 가능한 대상 없음, `CONFLICT`는 중복 등록 또는 오래된 버전이다.

## 저장과 의존성

- `service.py`의 `MemoryArchive`가 접근 정책과 트랜잭션을 담당한다. `_visible()`이 SQL에서 작성자 또는 활성 가족 구성원 여부, 최신 버전, 삭제 상태를 제한한다. PRIVATE는 작성자만 읽고 수정할 수 있다. FAMILY는 활성 가족 구성원이 읽을 수 있고 작성자 또는 ADMIN이 수정할 수 있다.
- `schema.sql`의 `app_user`, `family`, `family_member`, `archive`, `memory`, `memory_revision`은 ERD 핵심 관계를 구현한다. 인물과 태그는 수정 이력에 대응하도록 `revision_id`에 연결하고, 태그는 소문자화한 정규 값으로 저장한다.
- `current_version`은 현재 본문 번호, `expected_version`은 호출자가 읽은 번호다. 수정과 삭제는 SQLite 쓰기 트랜잭션에서 비교한다. `event_start`와 `event_end`는 일·월·연도 단위의 구간이고 날짜 미상은 NULL이다. 수정·삭제 시각은 UTC ISO 8601로 저장한다.
- `Robot(store, memory_archive=...)`로 서비스를 주입할 수 있다. 기본 경로는 `store.data_dir / "memory_archive.sqlite3"`다. SQLite는 Python 표준 라이브러리에 포함된다. UI 실행에는 기존 Tkinter가 필요하다. 기존 `companion_state.json`에서 프로필 ID를 재사용한다.

## 명세와 검증

| 명세 | 구현 및 검증 |
| --- | --- |
| FMA-01~03, FMA-05, FMA-07 | 보관함·가족·기억 관리, 등록 후 재조회, 교차 가족 인물 연결 차단, 이력, 버전 충돌, 논리 삭제 |
| FMA-06 | 키워드·인물·기간·태그 필터. 의미 검색은 pgvector 연동 단계에서 구현 |
| FMA-09 | 권한이 있는 최신 버전 발췌와 출처 조회. 수정·삭제·가족 권한 회수 후 이전 출처 접근 차단 시험 |
| FMA-04, FMA-08, FMA-10~11 | 파일과 대화 세션, 임베딩·재색인, 내보내기 및 물리 삭제는 후속 구현 |
| CORE-04 | 기존 프로필과 복약 JSON을 읽고 보관함 데이터와 함께 재실행할 수 있는지 시험 |

`python -m unittest -v`로 기존 코어·Smart Home과 보관함 테스트를 한 번에 실행한다. 보관함 테스트는 임시 SQLite 파일을 사용한다. PostgreSQL/pgvector, 인증 세션과 실장치 연동은 통합 설계 단계에 남아 있다.
