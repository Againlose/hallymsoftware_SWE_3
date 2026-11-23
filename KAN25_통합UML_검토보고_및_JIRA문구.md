# TEAM05 / KAN-25 전체 UML 설계 및 통합 — 검토용 v2.0

> 상태: 1차 설계 대조 완료 / 팀 검토·확정 전. 작성 근거: `AI_Companion_Robot_Prototype_v1/app.py`, `robot_core.py`, `test_robot_core.py`, `TEAM05_Initial_Requirements_MVP_v0.1.pdf`, 기존 KAN-24·KAN-25 UML.

## 1. 이번 수정 내용

- 팀 합의 핵심 확장 기능인 Family Memory Archive, Smart Home Control, Health Monitoring을 우선 범위로 구성함.
- 기존 UML에 있던 Family & Visitor Recognition은 **미확정 선택 기능**이므로 이번 필수 유스케이스/컴포넌트 다이어그램에서 제외함.
- Family Memory의 **로컬 저장·키워드 검색은 현재 구현**으로 수정함. RAG/Memory Graph는 추후 확장으로 구분함.
- Smart Home의 실제 가스 기기 제어와 Health Monitoring의 실제 웨어러블 연동은 구현되지 않았음을 명시함.
- `Command Router`, 독립 서비스 모듈, API/MCP, SQLite/DB, 사용자 계정·권한은 **계획 구조**로 표시함.
- Use Case는 기능별 영역과 반복 액터를 사용하고 Component는 현재/목표 구조를 분리하여 긴 교차 연결을 최소화함.

## 2. 코드 ↔ UML ↔ 요구사항 연결

| UML/기능 | 실제 구현 클래스·메서드 | 요구사항 후보 | 상태 |
|---|---|---|---|
| GUI / 사용자 상호작용 | `CompanionApp`, `RobotCore.set_user_name()` | FR-01 | 로컬 구현 |
| 대화 / 기능 조회 | `RobotCore.respond()` | FR-02 | 규칙 기반 구현, LLM 아님 |
| 가족 기억 | `RobotCore.add_memory()`, `search_memories()` | FR-03 | 키워드 검색 구현, RAG 미구현 |
| 스마트홈 상태 | `gas_state()`, `simulate_gas()` | FR-04 | 가상 ON/OFF 시뮬레이션 |
| 건강 모니터링 | `add_heart_rate()` | FR-05 | 가상 심박수 임계값 경고 |
| 복약 알림 | `add_medication()`, `check_medications()` | FR-06 | 실행 중 시간 확인, 중복 방지 |
| 낙상 이벤트 | `simulate_fall()` | FR-07 | 버튼 시연, 실제 감지 없음 |
| 로컬 저장·복구 | `LocalJsonStore.load()`, `save()` | FR-08 | JSON 오류 시 보존, 원자적 저장 |
| 모듈·공통 계약 | 현재 `RobotCore` 단일 구현 | FR-09 | 후속 분리 예정 |
| 가족 접근 권한 | 없음 | FR-10, NFR-02 | 추후 구현 |
| Memory Graph/RAG/LLM | 없음 | FR-11 | 추후 개발 |
| 실제 API/MCP/웨어러블 | 없음 | FR-12 | 기술·권한 검토 단계 |

### 이전 설계와 실제 Python 클래스의 차이

- 기존 그림의 `동반자로봇`, `대화관리자`, `AI모델`, `음성처리기`, `센서`는 초기 개념 설계 이름임. 현재 v1.0의 코드에는 이와 동일한 이름의 독립 Python 클래스들이 존재하지 않음.
- 실제 코드의 중심 클래스는 **`CompanionApp`**, **`RobotCore`**, **`LocalJsonStore`**임. KAN-24의 Class Diagram은 향후 팀 리뷰를 거쳐 실제 코드형 UML과 목표 클래스 설계로 구분 필요.
- `companion_state.json`은 아직 DB가 아니므로 ERD의 모든 테이블이 구현되었다고 볼 수 없음.

## 3. KAN-26에 전달할 모듈 인터페이스 초안 (팀 합의 필요)

```json
{
  "request_id": "REQ-001",
  "user_id": "DEMO-001",
  "action": "memory.search",
  "payload": {"query": "가족 여행"}
}
```

```json
{
  "success": true,
  "data": {"records": []},
  "error_code": null,
  "source": "local",
  "timestamp": "2026-11-19T13:00:00"
}
```

위 JSON은 **구현 계획안의 계약 예시**이며 현재 `RobotCore.respond()`의 실제 반환 형식은 문자열임.

| `action` 예시 | 담당 모듈 | 현재 구현 대응 |
|---|---|---|
| `memory.search` | FamilyMemoryService | `search_memories(query)` |
| `smarthome.gas_status` | SmartHomeService | `gas_state()` |
| `smarthome.gas_simulate` | SmartHomeService | `simulate_gas(state)`; 실제 기기 제어 아님 |
| `health.add_demo_rate` | HealthService | `add_heart_rate(rate)` |
| `medication.list` | MedicationService | `state["medications"]` 참조, 서비스 메서드 미분리 |
| `safety.simulate_fall` | SafetyService | `simulate_fall()` |

## 4. 검토 체크리스트

- [ ] 핵심 기능 3개 및 기존 생활지원 범위에 대해 팀원 간 합의함
- [ ] `Family & Visitor Recognition`의 선택/제외 여부를 JIRA에 명시함
- [ ] SRS의 FR-01~FR-12와 Use Case·Component를 대조함
- [ ] KAN-24 Class Diagram의 실제 코드/목표 설계 구분과 용어를 정리함
- [ ] 다른 팀원이 맡은 ERD·Sequence Diagram과 필드명, 호출 순서를 일치시킴
- [ ] 실제 외부 API/MCP·LLM·센서는 아직 미구현이라고 표시함
- [ ] 리뷰 의견과 승인자를 JIRA에 기록한 뒤 최종 완료 처리함

## 5. JIRA KAN-25 댓글용 문구

> 기존 Use Case Diagram, Component Diagram과 Python v1.0 코드 및 요구사항 초안을 대조해 통합 UML v2.0을 작성했습니다. 현재 구현(대화, 가족 기억 저장·검색, 복약), 시뮬레이션(가상 가스밸브, 심박수, 낙상), 추후 확장(명령 라우터, RAG/LLM, MCP/실제 API, 사용자 권한)을 구분했습니다. Family & Visitor Recognition은 팀 미확정이므로 필수 범위에서 제외했습니다. 변경된 UML 2종과 코드-요구사항 대응표를 첨부합니다. KAN-24 Class Diagram, SRS, ERD·SD와 명칭 및 관계를 최종 교차 검토한 후 완료하겠습니다.
