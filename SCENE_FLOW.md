# 씬(Scene) 구성과 흐름

## 전체 씬 구조

```
BaseScene (추상 클래스)
├── MainMenuScene (메뉴 화면)
├── GameScene (게임 화면)
└── ResultScene (결과 화면)
```

---

## 씬 전환 흐름

```
┌─────────────┐
│  MENU       │ (시작)
│  (메뉴)     │
└──────┬──────┘
       │ SPACE 입력
       ▼
┌─────────────┐
│  GAME       │
│  (게임)     │
│             │
│  ┌────────┐ │
│  │ CALIBRATING │ (캘리브레이션)
│  └───┬────┘ │
│      │ '0' 키 또는 자동 완료
│      ▼      │
│  ┌────────┐ │
│  │ COUNTDOWN │ (카운트다운 3초)
│  └───┬────┘ │
│      │ 3초 경과
│      ▼      │
│  ┌────────┐ │
│  │ PLAYING   │ (게임 플레이)
│  └───┬────┘ │
│      │ 게임 종료
│      ▼      │
│  ┌────────┐ │
│  │ GAME_OVER │ → RESULT 전환
│  └────────┘ │
└─────────────┘
       │
       ▼
┌─────────────┐
│  RESULT     │ (결과 화면)
│  (점수 표시)│
└──────┬──────┘
       │ SPACE 입력
       ▼
   GAME (재시작)
```

---

## 각 씬 상세 설명

### 1. MainMenuScene (메뉴 화면)

**파일**: `scenes/main_menu_scene.py`

**기능**:
- 게임 타이틀 표시 ("BEAT BOXER")
- 시작 안내 텍스트 표시 ("Press 'Space' to Start")

**키 입력**:
- `SPACE`: 게임 시작 → `GAME` 씬으로 전환

**표시 요소**:
- 타이틀 텍스트
- 시작 안내 텍스트 (SPACE 입력 시 색상 변경)

---

### 2. GameScene (게임 화면)

**파일**: `scenes/game_scene.py`

**내부 상태 (scene_state)**:
1. **CALIBRATING** (캘리브레이션)
2. **COUNTDOWN** (카운트다운)
3. **PLAYING** (게임 플레이)
4. **GAME_OVER** (게임 종료)

#### 2.1 CALIBRATING (캘리브레이션)

**기능**:
- 사용자 포즈를 캘리브레이션 타겟에 맞추도록 요청
- 3개의 타겟 원 표시:
  - `head`: 코 위치
  - `left_fist`: 왼손 위치 (실제로는 오른손)
  - `right_fist`: 오른손 위치 (실제로는 왼손)
- 코, 양손의 중앙점을 노란 원으로 표시

**완료 조건**:
- 모든 타겟 원에 랜드마크가 들어가 있음
- 3초간 유지 (HOLD)

**키 입력**:
- `0`: 캘리브레이션 스킵 + **Test Mode 활성화**

**전환**:
- 자동 완료 또는 '0' 키 입력 → `COUNTDOWN`

---

#### 2.2 COUNTDOWN (카운트다운)

**기능**:
- 게임 시작 전 3초 카운트다운 표시
- 화면 중앙에 큰 숫자 표시 (3.0 → 2.0 → 1.0 → 0.0)

**전환**:
- 3초 경과 → `PLAYING`

---

#### 2.3 PLAYING (게임 플레이)

**기능**:
- 비트맵 노트 표시 및 이동
- 포즈 트래킹을 통한 펀치/덕 감지
- 판정 시스템 (PERFECT, GREAT, GOOD, MISS)
- 점수/콤보/통계 표시
- 히트존 및 덕 라인 표시

**모드**:
- **일반 모드** (기본): 공간 + 타이밍 판정
- **Test 모드** ('0' 키 입력 시): 공간 판정만, 디버그 정보 표시

**전환**:
- 게임 종료 (END 마커 도달) → `GAME_OVER` → `RESULT` 씬

---

#### 2.4 GAME_OVER (게임 종료)

**기능**:
- 게임 종료 처리
- 최종 점수를 `persistent_data`에 저장

**전환**:
- 즉시 `RESULT` 씬으로 전환

---

### 3. ResultScene (결과 화면)

**파일**: `scenes/result_scene.py`

**기능**:
- 게임 종료 메시지 표시 ("GAME OVER")
- 최종 점수 표시
- 재시작 안내 텍스트 표시

**키 입력**:
- `SPACE`: 게임 재시작 → `GAME` 씬으로 전환

**표시 요소**:
- "GAME OVER" 텍스트
- "Final Score: XXX" 텍스트
- "Press 'Space' to Restart" 텍스트

---

## 메인 루프 흐름 (main.py)

```
1. 초기화
   ├── Pygame 초기화
   ├── 카메라 초기화
   ├── 설정 파일 로드 (rules.json, difficulty.json, ui.json)
   ├── AudioManager 생성
   └── PoseTracker 생성

2. 씬 생성
   ├── MainMenuScene
   ├── GameScene
   └── ResultScene

3. 메인 루프 (무한 반복)
   ├── 카메라 프레임 읽기
   ├── Pose Tracking (hit_events, landmarks, mask)
   ├── 배경 블러 처리
   ├── 현재 씬 업데이트 (update)
   ├── 현재 씬 그리기 (draw)
   ├── 화면 표시
   ├── 키 입력 처리 (handle_event)
   └── 씬 전환 확인 (next_scene_name)
```

---

## 씬 전환 메커니즘

### BaseScene 클래스

모든 씬의 기본 클래스로 다음 속성을 제공:
- `next_scene_name`: 다음 씬 이름 (None이면 전환 없음)
- `persistent_data`: 씬 간 데이터 전달 딕셔너리

### 씬 전환 프로세스

1. **현재 씬**에서 `next_scene_name` 설정
2. **main.py**에서 `next_scene_name` 확인
3. **현재 씬**의 `cleanup()` 호출 (데이터 수집)
4. **새 씬** 선택
5. **새 씬**의 `startup(persistent_data)` 호출 (데이터 전달)

---

## GameScene 내부 상태 전환

```
startup()
    ↓
CALIBRATING (캘리브레이션)
    │
    ├─ '0' 키 입력 → Test Mode 활성화
    │
    ├─ 자동 완료 (3초 유지)
    │
    └─ COUNTDOWN (카운트다운 3초)
           │
           └─ 3초 경과
                │
                └─ PLAYING (게임 플레이)
                     │
                     └─ 게임 종료 (END 마커)
                          │
                          └─ GAME_OVER → RESULT 씬
```

---

## 주요 기능 분리

### Strategy 패턴 (GameScene)

**GameModeStrategy** (추상 클래스)
- `TestModeStrategy`: 테스트 모드 전용 로직
- `NormalModeStrategy`: 일반 모드 전용 로직

**활성화 조건**:
- **일반 모드**: 기본값 (캘리브레이션 완료 시)
- **Test 모드**: 캘리브레이션 화면에서 '0' 키 입력 시

---

## 키 입력 안내

| 씬 | 키 | 동작 |
|---|---|------|
| **MENU** | SPACE | 게임 시작 |
| **GAME (CALIBRATING)** | 0 | Test Mode 활성화 + 캘리브레이션 스킵 |
| **RESULT** | SPACE | 게임 재시작 |
| **전역** | ESC | 프로그램 종료 |

---

## 데이터 흐름

### 씬 간 데이터 전달

1. **GameScene → ResultScene**
   - `persistent_data["final_score"]`: 최종 점수

2. **ResultScene → GameScene**
   - 재시작 시 `persistent_data`는 빈 딕셔너리

### GameScene 내부 데이터

- `state`: 게임 상태 (score, combo, start_time, game_over)
- `judgement_stats`: 판정 통계 (PERFECT, GREAT, GOOD, MISS)
- `active_notes`: 활성 노트 리스트
- `floating_judgement_logs`: 판정 로그 (테스트 모드용)
- `event_history`: 이벤트 히스토리 (테스트 모드용)
- `debug_remaining_time`: 다음 노트까지 남은 시간 (테스트 모드용)
- `debug_spatial_distance`: 다음 노트까지 공간 거리 (테스트 모드용)

