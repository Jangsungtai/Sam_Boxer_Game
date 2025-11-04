# Scenes 폴더 파일 설명

## 파일 구조

```
scenes/
├── __init__.py                    # Python 패키지 초기화 (비어있음)
├── base_scene.py                  # 모든 씬의 기본 클래스
├── main_menu_scene.py             # 메뉴 화면 씬
├── game_scene.py                  # 게임 화면 씬 (핵심)
├── result_scene.py                # 결과 화면 씬
├── game_mode_strategy.py          # 게임 모드 전략 추상 클래스
├── test_mode_strategy.py          # 테스트 모드 전략 구현
└── normal_mode_strategy.py        # 일반 모드 전략 구현
```

---

## 1. base_scene.py

**역할**: 모든 씬의 부모 클래스 (추상 클래스)

**주요 속성**:
- `screen`: OpenCV 카메라 객체
- `audio_manager`: 오디오 관리자
- `config`: 설정 딕셔너리 (rules, difficulty, ui)
- `pose_tracker`: 포즈 트래커
- `next_scene_name`: 다음 씬으로 전환할 때 사용 (None이면 전환 없음)
- `persistent_data`: 씬 간 데이터 전달 딕셔너리

**주요 메서드** (자식 클래스에서 구현):
- `handle_event(key)`: 키보드 입력 처리
- `update(frame, hit_events, landmarks, now)`: 매 프레임 게임 로직 업데이트
- `draw(frame)`: 화면에 UI 그리기
- `startup(persistent_data)`: 씬 시작 시 호출 (이전 씬 데이터 수신)
- `cleanup()`: 씬 종료 시 호출 (다음 씬에 데이터 전달)

**설계 목적**: 
- 모든 씬이 공통 인터페이스를 가지도록 보장
- 씬 전환 메커니즘 표준화

---

## 2. main_menu_scene.py

**역할**: 게임 시작 메뉴 화면

**주요 기능**:
- 게임 타이틀 표시 ("BEAT BOXER")
- 시작 안내 텍스트 표시 ("Press 'Space' to Start")
- SPACE 키 입력 시 색상 변경 애니메이션

**키 입력**:
- `SPACE`: 게임 시작 → `next_scene_name = "GAME"` 설정

**표시 요소**:
- 타이틀 텍스트 (화면 중앙 상단)
- 시작 안내 텍스트 (화면 중앙 하단, SPACE 입력 시 색상 변경)

**전환 조건**:
- `SPACE` 키 입력 시 `GAME` 씬으로 전환

---

## 3. game_scene.py

**역할**: 게임의 핵심 로직을 담당하는 씬 (가장 복잡한 파일)

**내부 상태 (scene_state)**:
1. `CALIBRATING`: 캘리브레이션 화면
2. `COUNTDOWN`: 카운트다운 화면
3. `PLAYING`: 게임 플레이 화면
4. `GAME_OVER`: 게임 종료 처리

**주요 기능**:

### 초기화 (`__init__`)
- 비트맵 로딩 (beatmap.txt + BPM/division)
- BPM 스케일링 계산 (30~100 BPM 범위 대응)
- 판정 시간 및 스폰 시간 설정
- 캘리브레이션 타겟 설정
- Strategy 패턴: `test_mode`에 따라 `TestModeStrategy` 또는 `NormalModeStrategy` 선택

### 캘리브레이션 (`CALIBRATING`)
- 포즈 캘리브레이션 (3개 타겟 원)
- 코, 양손의 중앙점 표시
- 3초간 유지 또는 '0' 키로 스킵
- '0' 키 입력 시 Test Mode 활성화

### 게임 플레이 (`PLAYING`)
- 노트 스폰 및 관리
- 포즈 트래킹 및 판정
- 점수/콤보 계산
- HUD 그리기 (Strategy 위임)

**주요 메서드**:
- `_check_calib_position()`: 캘리브레이션 위치 확인
- `_hand_inside_hit_zone()`: 손이 히트존 안에 있는지 확인
- `_spawn_notes()`: 노트 생성
- `_handle_hits()`: 히트 이벤트 처리 (Strategy 위임)
- `_check_misses()`: 미스 노트 처리
- `_judge_time()`: 타이밍 판정
- `_add_judgement()`: 판정 결과 추가
- `_draw_hud()`: HUD 그리기 (Strategy 위임)
- `update()`: 게임 로직 업데이트
- `draw()`: 화면 그리기

**Strategy 패턴**:
- `self.mode_strategy`: 현재 모드 전략 (TestModeStrategy 또는 NormalModeStrategy)
- `_update_strategy()`: Strategy 선택/재선택

---

## 4. result_scene.py

**역할**: 게임 종료 후 결과 화면

**주요 기능**:
- 최종 점수 표시
- 게임 오버 메시지 표시
- 재시작 안내

**키 입력**:
- `SPACE`: 게임 재시작 → `next_scene_name = "GAME"` 설정

**표시 요소**:
- "GAME OVER" 텍스트 (빨간색)
- "Final Score: XXX" 텍스트
- "Press 'Space' to Restart" 텍스트 (SPACE 입력 시 색상 변경)

**데이터 수신**:
- `persistent_data["final_score"]`: GameScene에서 전달된 최종 점수

---

## 5. game_mode_strategy.py

**역할**: 게임 모드 전략 추상 클래스 (Strategy 패턴)

**설계 목적**:
- 일반 모드와 테스트 모드의 로직을 분리
- 코드 중복 제거 및 유지보수성 향상

**추상 메서드**:
1. `handle_hits(hit_events, t_game, now)`: 판정 로직
2. `draw_hud(frame)`: HUD 그리기
3. `draw_additional(frame, now)`: 추가 시각화
4. `on_hit_events(hit_events, now)`: 이벤트 처리
5. `calculate_debug_info(...)`: 디버그 정보 계산
6. `format_judgement_text(judge_text, dt)`: 판정 텍스트 포맷팅

**구현 클래스**:
- `TestModeStrategy`: 테스트 모드 전용 로직
- `NormalModeStrategy`: 일반 모드 전용 로직

---

## 6. test_mode_strategy.py

**역할**: 테스트 모드 전략 구현

**주요 기능**:

### `handle_hits()`
- **공간 판정만 체크** (타이밍 무시)
- 노트가 히트존에 도달했는지 확인
- 노트가 히트존에 도달하고 손이 히트존 안에 있으면 → PERFECT
- 노트가 히트존에 도달했지만 손이 히트존 밖에 있으면 → "area"
- DUCK 노트는 무조건 PERFECT

### `draw_hud()`
- **디버그 정보 포함**:
  - 히트존 색상 변경 (녹색: 통과, 빨간색: 실패)
  - 판정 로그 (히트존 아래)
  - 실시간 디버그 텍스트 (Time, Dist)
  - 랜드마크 시각화 (코, 손의 중앙점, 거리/선)
  - 점수/콤보/통계 표시

### `draw_additional()`
- 이벤트 히스토리 표시 (왼쪽 하단에 점)
- "Test mode" 텍스트 표시 (오른쪽 아래)

### `on_hit_events()`
- 이벤트 히스토리 저장 (`event_history`)

### `calculate_debug_info()`
- 다음 노트의 남은 시간 계산
- 다음 노트의 공간 거리 계산

### `format_judgement_text()`
- 판정 텍스트에 `dt` 정보 포함: `"PERFECT (+0.05s)"`

---

## 7. normal_mode_strategy.py

**역할**: 일반 모드 전략 구현

**주요 기능**:

### `handle_hits()`
- **공간 + 타이밍 모두 체크**
- 공간 O + 타이밍 O → PERFECT/GREAT/GOOD (타이밍에 따라)
- 공간 O + 타이밍 X → "timing"
- 공간 X + 타이밍 O → "area"
- 공간 X + 타이밍 X → "area/timing"
- DUCK 노트도 타이밍에 따라 판정

### `draw_hud()`
- **깔끔한 HUD** (디버그 정보 제외):
  - 히트존 원 (기본 색상)
  - 점수/콤보/통계 표시
  - DUCK LINE 표시

### `draw_additional()`
- 추가 시각화 없음

### `on_hit_events()`
- 추가 처리 없음

### `calculate_debug_info()`
- 디버그 정보 계산 없음

### `format_judgement_text()`
- 판정 텍스트만 반환 (dt 정보 없음)

---

## 파일 간 의존성

```
main.py
  └── scenes/
      ├── base_scene.py (추상 클래스)
      │
      ├── main_menu_scene.py (BaseScene 상속)
      │
      ├── game_scene.py (BaseScene 상속)
      │   ├── game_mode_strategy.py (추상 클래스)
      │   ├── test_mode_strategy.py (GameModeStrategy 구현)
      │   └── normal_mode_strategy.py (GameModeStrategy 구현)
      │
      └── result_scene.py (BaseScene 상속)
```

---

## 씬 전환 흐름

```
main.py
  ↓
MainMenuScene (startup)
  ↓ SPACE 입력
GameScene (startup)
  ├── CALIBRATING (캘리브레이션)
  ├── COUNTDOWN (카운트다운)
  ├── PLAYING (게임 플레이)
  │   └── Strategy 패턴으로 모드별 로직 처리
  └── GAME_OVER → cleanup()
      ↓
ResultScene (startup)
  ↓ SPACE 입력
GameScene (재시작)
```

---

## 주요 설계 패턴

### 1. Strategy 패턴 (GameScene)
- **목적**: 일반 모드와 테스트 모드 로직 분리
- **구현**: `GameModeStrategy` 추상 클래스 + 구체적 구현 클래스

### 2. Template Method 패턴 (BaseScene)
- **목적**: 모든 씬이 공통 인터페이스를 가지도록 보장
- **구현**: BaseScene에서 메서드 시그니처 정의, 자식 클래스에서 구현

### 3. State 패턴 (GameScene 내부)
- **목적**: GameScene 내부 상태 관리 (CALIBRATING, COUNTDOWN, PLAYING, GAME_OVER)
- **구현**: `scene_state` 변수로 상태 관리

---

## 각 파일의 라인 수 (대략)

- `base_scene.py`: ~50줄
- `main_menu_scene.py`: ~60줄
- `game_scene.py`: ~800줄 (가장 큰 파일)
- `result_scene.py`: ~75줄
- `game_mode_strategy.py`: ~41줄
- `test_mode_strategy.py`: ~275줄
- `normal_mode_strategy.py`: ~130줄

**총 약 1,400줄**

