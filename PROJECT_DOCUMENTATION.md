# Beat Boxer Game - 프로젝트 전체 문서

이 문서는 Beat Boxer 게임 프로젝트의 전체 구조와 각 파일의 역할을 상세히 설명합니다. GPT와 같은 다른 LLM 모델이 프로젝트를 이해하고 작업할 수 있도록 작성되었습니다.

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [프로젝트 구조](#프로젝트-구조)
3. [파일별 상세 설명](#파일별-상세-설명)
4. [데이터 흐름](#데이터-흐름)
5. [주요 시스템](#주요-시스템)
6. [설정 파일](#설정-파일)

---

## 프로젝트 개요

**Beat Boxer**는 MediaPipe Pose Estimation을 활용한 실시간 모션 인식 권투 리듬 게임입니다. 사용자의 펀치(JAB) 및 회피(WEAVE) 동작을 실시간으로 감지하고, 음악 비트에 맞춰 노트를 처리하는 게임입니다.

### 기술 스택
- **Python 3.11+**
- **Arcade**: 2D 게임 엔진 (씬 관리, 렌더링)
- **OpenCV**: 카메라 입출력 및 이미지 처리
- **MediaPipe**: 실시간 포즈 인식 및 세그멘테이션
- **Pygame**: 오디오 재생
- **NumPy**: 수치 계산

---

## 프로젝트 구조

```
beat_boxer_game/
├── main.py                          # 프로그램 진입점
├── constants.py                     # 게임 상수 정의
├── requirements.txt                 # Python 패키지 의존성
├── readme.md                        # 프로젝트 README
├── PROJECT_DOCUMENTATION.md         # 이 문서
│
├── config/                          # 설정 파일 (JSON)
│   ├── rules.json                   # 게임 규칙 및 판정 설정
│   ├── difficulty.json              # 난이도별 설정
│   └── ui.json                      # UI 색상, 위치, 스타일 설정
│
├── core/                            # 핵심 게임 로직
│   ├── pose_tracker.py              # 포즈 추적 및 동작 감지
│   ├── note.py                      # 노트 객체 클래스
│   ├── audio_manager.py             # 오디오 관리
│   ├── hit_effect.py                # 히트 효과 파티클 시스템
│   ├── silhouette.py                # 실루엣 추출 모듈 (독립 실행 가능)
│   └── judgement.py                 # 판정 로직 (미사용 가능성)
│
├── scenes/                          # 게임 씬 관리
│   ├── base_scene.py                # 씬 기본 클래스
│   ├── main_menu_scene.py           # 메인 메뉴 씬
│   ├── calibration_scene.py         # 캘리브레이션 씬
│   ├── game_scene.py                # 게임 플레이 씬 (핵심)
│   ├── result_scene.py              # 결과 화면 씬
│   ├── game_mode_strategy.py        # 전략 패턴 추상 클래스
│   ├── normal_mode_strategy.py      # 일반 모드 전략 구현
│   ├── test_mode_strategy.py        # 테스트 모드 전략 구현
│   └── __init__.py                  # 패키지 초기화
│
├── judgment_logic.py                # 위빙 판정 로직
├── beat_manager.py                  # 비트 관리 (미사용 가능성)
│
└── assets/                          # 리소스 파일
    ├── beatmaps/                    # 비트맵 데이터
    │   └── song1/
    │       ├── beatmap.txt          # 텍스트 기반 비트맵
    │       ├── beatmap.json         # JSON 기반 비트맵
    │       └── music.mp3            # 배경 음악
    ├── sounds/                      # 효과음 파일
    │   ├── hit_perfect.wav
    │   ├── hit_good.wav
    │   ├── miss.wav
    │   └── bomb.wav
    └── images/                      # 이미지 리소스
        ├── arena_bg.jpg              # 게임 배경 이미지
        ├── glove_left.png
        ├── glove_right.png
        └── headgear.png
```

---

## 파일별 상세 설명

### 🎯 진입점 및 핵심 파일

#### `main.py`
**역할**: 프로그램의 진입점 및 메인 윈도우 관리

**주요 기능**:
- `main()`: 프로그램 초기화 및 실행
  - 오디오 매니저 초기화 (Pygame)
  - 카메라 초기화 (OpenCV, Mac 기본 카메라 자동 탐지)
  - 설정 파일 로드 (`config/rules.json`, `config/difficulty.json`, `config/ui.json`)
  - PoseTracker 초기화
  - GameWindow 생성 및 실행

- `get_best_camera_index()`: Mac에서 사용 가능한 카메라 인덱스 탐색
  - `cv2.CAP_AVFOUNDATION` 사용
  - 인덱스 4부터 0까지 역순으로 탐색

- `GameWindow` 클래스: Arcade 기반 메인 윈도우
  - `on_update()`: 매 프레임마다 실행
    - 카메라 프레임 읽기 및 `cv2.flip(source_frame, 1)` 적용 (좌우 반전)
    - PoseTracker로 포즈 분석 및 hit_events 생성
    - 현재 씬에 데이터 전달 (`frame`, `hit_events`, `landmarks`, `mask`, `now`)
  - `_create_scene()`: 씬 생성 팩토리
  - `_switch_scene()`: 씬 전환 관리
  - `on_key_press()`: 전역 키 입력 처리 (ESC로 종료)

**중요 사항**:
- `cv2.flip(source_frame, 1)`로 프레임을 좌우 반전하여 화면에 표시
- MediaPipe는 반전된 프레임을 처리하므로, 랜드마크 좌표도 반전된 프레임 기준

---

#### `constants.py`
**역할**: 게임 전역 상수 정의

**주요 상수**:
- **화면 설정**: `SCREEN_WIDTH = 1280`, `SCREEN_HEIGHT = 720`
- **비트 타이밍**: `BEAT_TIME = 0.5`, `JUDGMENT_WINDOW = 0.2`
- **Dodge 라인 위치**: 
  - `DODGE_CENTER_LINE_X`: 중앙 라인 (점선)
  - `DODGE_LEFT_LINE_X`: 왼쪽 라인 (실선)
  - `DODGE_RIGHT_LINE_X`: 오른쪽 라인 (실선)
  - `DODGE_LINE_OFFSET = 180`: 중앙선으로부터 좌우 라인까지의 거리
- **비트 타입**: 
  - `BEAT_JAB_L = 1`: 왼손 잽
  - `BEAT_JAB_R = 2`: 오른손 잽
  - `BEAT_WEAVE_L = 3`: 왼쪽으로 피하기
  - `BEAT_WEAVE_R = 4`: 오른쪽으로 피하기
- **랜드마크 인덱스**: `NOSE_LANDMARK = 0`, `LEFT_HAND_LANDMARK = 15`, `RIGHT_HAND_LANDMARK = 16`
- **색상 정의**: RGB 튜플 형태

---

### 🎮 씬 (Scene) 파일

#### `scenes/base_scene.py`
**역할**: 모든 씬의 기본 클래스

**주요 기능**:
- `BaseScene(arcade.View)`: Arcade View를 상속
- **좌표 변환**:
  - `to_arcade_xy()`: 카메라 좌표를 Arcade 화면 좌표로 변환
    - x축 스케일링: `x * x_scale`
    - y축 스케일링 및 반전: `window_height - (y * y_scale)` (Arcade는 y축이 아래에서 위로)
  - `to_arcade_y()`: y 좌표만 변환
- **색상 변환**: `bgr_to_rgb()`: OpenCV BGR을 Arcade RGB로 변환
- **생명주기**: `startup()`, `cleanup()`, `set_source_dimensions()`
- **스케일 관리**: `_update_scale()`: 카메라 해상도와 윈도우 해상도 간 스케일 계산

**중요 사항**:
- 모든 씬은 이 클래스를 상속받아 구현
- 좌표 변환은 카메라 좌표계와 Arcade 좌표계 간 변환을 처리

---

#### `scenes/main_menu_scene.py`
**역할**: 메인 메뉴 화면

**주요 기능**:
- 타이틀 "BEAT BOXER" 표시
- "Press SPACE to Start" 안내
- `on_key_press()`: SPACE 키 입력 시
  - PoseTracker가 있으면 `CALIBRATION` 씬으로 이동
  - 없으면 `GAME` 씬으로 직접 이동
- 키 입력 시 색상 변경 효과

---

#### `scenes/calibration_scene.py`
**역할**: 사용자 포즈 캘리브레이션 화면

**주요 기능**:
- **캘리브레이션 타겟 3개**:
  - 머리 (코): 화면 중앙 상단
  - 왼손 주먹: 화면 왼쪽 중앙
  - 오른손 주먹: 화면 오른쪽 중앙
- **캘리브레이션 프로세스**:
  - 3개 타겟 모두 달성 시 3초 카운트다운 시작
  - 카운트다운 완료 시 `GAME` 씬으로 이동
- **키 입력**:
  - `0`: 일반 모드로 게임 시작 (캘리브레이션 스킵)
  - `9`: 테스트 모드로 게임 시작 (캘리브레이션 스킵)
- **렌더링**:
  - 타겟 원 그리기 (달성 시 녹색, 미달성 시 빨간색)
  - 타겟 아래 라벨 표시 ("머리를 원 아래 맞춰주세요" 등)
  - 실시간 실루엣 외곽선 그리기 (`_draw_pose_silhouette()`)
  - 포즈 랜드마크 표시 (코, 왼손, 오른손)
  - 중앙 카운트다운 표시 (3.00 -> 0.00)

**중요 메서드**:
- `_build_targets()`: UI 설정에서 캘리브레이션 타겟 위치 계산
- `_draw_pose_silhouette()`: MediaPipe 세그멘테이션 마스크로 실루엣 외곽선 그리기
- `update()`: `PoseTracker.check_calibration_position()`으로 타겟 달성 여부 확인

---

#### `scenes/game_scene.py`
**역할**: 메인 게임 플레이 씬 (가장 복잡한 씬)

**주요 기능**:

1. **게임 상태 관리**:
   - 점수, 콤보, 최대 콤보
   - 노트 스폰 및 업데이트
   - 판정 처리 (PERFECT, GREAT, GOOD, MISS)
   - 게임 종료 처리

2. **비트맵 로드 및 파싱**:
   - `_load_beatmap()`: `beatmap.txt` 또는 `beatmap.json` 로드
   - `_parse_text_beatmap()`: 텍스트 비트맵 파싱
     - 매핑: `"1"` → `"JAB_L"`, `"2"` → `"JAB_R"`, `"3"` → `"WEAVE_L"`, `"4"` → `"WEAVE_R"`, `"0"` → `None`
     - BPM과 division 기반으로 시간 계산

3. **노트 관리**:
   - `_spawn_notes()`: 게임 시간에 따라 노트 스폰
   - `_update_notes()`: 노트 위치 업데이트
   - `_process_misses()`: 판정 창을 지나간 노트를 MISS 처리

4. **판정 시스템**:
   - `_process_hit_events()`: PoseTracker에서 생성된 hit_events 처리
     - 시간 동기화: `adjusted_time = (event_time - song_start_time) + timing_offset`
     - `_find_best_matching_note()`: 가장 가까운 노트 찾기 (판정 창 내)
     - `_determine_judgement()`: 시간 차이로 판정 등급 결정 (PERFECT, GREAT, GOOD)
   - `_process_weave_judgments()`: 위빙 노트 판정 (코 위치 기반)
   - `_register_hit()`: 히트 등록 및 점수/콤보 업데이트

5. **렌더링**:
   - 배경 이미지 (`arena_bg.jpg`) - 고정 위치, 전체 화면
   - Dodge 라인 그리기 (`_draw_dodge_lines()`): 3개 수직선 (왼쪽, 중앙 점선, 오른쪽)
   - 노트 그리기
   - 히트 효과 파티클 그리기
   - 포즈 랜드마크 표시 (코, 왼손, 오른손)
   - 실루엣 외곽선 그리기 (`_draw_pose_silhouette()`)
   - HUD (점수, 콤보, 판정 결과)

6. **모드 관리**:
   - 일반 모드 (`NormalModeStrategy`)
   - 테스트 모드 (`TestModeStrategy`)
   - `M` 키로 모드 전환

**중요 메서드**:
- `_find_best_matching_note()`: 판정 창 내의 노트만 필터링하여 매칭
- `_determine_judgement()`: 시간 차이(`delta`)로 판정 등급 결정
- `_draw_dodge_lines()`: 네온 효과가 있는 Dodge 라인 그리기
- `_draw_pose_silhouette()`: MediaPipe 세그멘테이션 마스크로 실루엣 외곽선 그리기
- `_draw_pose_markers()`: 포즈 랜드마크 표시

---

#### `scenes/result_scene.py`
**역할**: 게임 종료 후 결과 화면

**주요 기능**:
- 최종 점수 표시
- "GAME OVER" 메시지
- "Press SPACE to Restart" 안내
- `on_key_press()`: SPACE 키 입력 시 게임 재시작

---

#### `scenes/game_mode_strategy.py`
**역할**: 전략 패턴 추상 클래스

**주요 기능**:
- `GameModeStrategy`: 게임 모드 전략의 기본 클래스
- 추상 메서드:
  - `handle_hits()`: hit_events 처리
  - `_draw_mode_specific_hud()`: 모드별 HUD 그리기
- 공통 메서드:
  - `draw_hud()`: 공통 HUD 그리기
  - `draw_additional()`: 추가 디버그 정보 (선택적)
  - `on_hit_events()`: hit_events 콜백

---

#### `scenes/normal_mode_strategy.py`
**역할**: 일반 게임 모드 전략

**주요 기능**:
- `NormalModeStrategy`: 일반 모드 구현
- "Normal Mode" 텍스트 표시
- 기본 HUD 표시

---

#### `scenes/test_mode_strategy.py`
**역할**: 테스트/디버그 모드 전략

**주요 기능**:
- `TestModeStrategy`: 테스트 모드 구현
- **디버그 정보 표시**:
  - 판정 창 정보 (Perfect, Great, Good)
  - 게임 시간
  - 활성 JAB 노트 수
  - 가장 가까운 노트 정보 및 시간 차이(Δ)
  - 최근 hit_events 히스토리
  - 판정 로그
- 히트존 색상 변경 (손이 히트존 안에 있으면 녹색, 밖에 있으면 빨간색)
- 포즈 랜드마크 연결선 그리기

---

### 🎯 핵심 로직 파일

#### `core/pose_tracker.py`
**역할**: MediaPipe 포즈 추적 및 동작 감지의 핵심 클래스

**주요 기능**:

1. **초기화**:
   - MediaPipe Pose 솔루션 초기화 (`model_complexity=2`, `enable_segmentation=True`)
   - 히스토리 deque 초기화 (시간, 손목, 어깨, 팔꿈치)
   - 캘리브레이션 데이터 기본값 설정
   - 판정 임계값 로드 (`V_THRESH`, `ANG_THRESH`, `REFRACTORY`)

2. **프레임 처리** (`process_frame()`):
   - MediaPipe로 포즈 분석
   - 랜드마크 좌표 추출 및 변환
   - 속도 및 각도 계산
   - **hit_events 생성**:
     - **일반 모드**: 속도, 각도, 구역, 쿨타임 모두 체크
       - JAB_L: RIGHT_WRIST의 속도/각도 사용, 화면 왼쪽 구역 확인
       - JAB_R: LEFT_WRIST의 속도/각도 사용, 화면 오른쪽 구역 확인
     - **테스트 모드**: 손의 중심점이 히트존을 나갔다가 다시 들어온 것을 감지
   - 세그멘테이션 마스크 반환

3. **랜드마크 스무딩** (`update_landmark_smoothing()`):
   - 지수 이동 평균으로 랜드마크 좌표 스무딩
   - `smoothing_alpha = 0.7` 사용

4. **주먹 중심점 계산** (`calculate_fist_centroids()`):
   - `spatial_judge_mode`에 따라:
     - 모드 1: 손목만 사용
     - 모드 2: 손목, 새끼손가락, 검지, 엄지의 평균

5. **캘리브레이션**:
   - `calibrate_from_pose()`: 어깨 너비, 머리 중심, 더킹 라인 계산
   - `check_calibration_position()`: 캘리브레이션 타겟 달성 여부 확인

6. **좌표계 처리**:
   - MediaPipe는 반전된 프레임을 처리하므로, 랜드마크 좌표도 반전된 프레임 기준
   - 화면 왼쪽에 보이는 손 = 사용자의 오른손 = RIGHT_WRIST
   - 화면 오른쪽에 보이는 손 = 사용자의 왼손 = LEFT_WRIST

**중요 메서드**:
- `process_frame()`: 프레임 처리 및 hit_events 생성
- `get_smoothed_landmarks()`: 스무딩된 랜드마크 반환
- `get_fist_centroids()`: 주먹 중심점 반환
- `set_test_mode()`: 테스트 모드 설정

---

#### `core/note.py`
**역할**: 리듬 노트 객체 클래스

**주요 기능**:
- **노트 타입**: `JAB_L`, `JAB_R`, `DUCK`, `BOMB`, `WEAVE_L`, `WEAVE_R`
- **초기 위치**:
  - JAB_L: 화면 왼쪽 밖 (`-100, target_y`)
  - JAB_R: 화면 오른쪽 밖 (`width + 100, target_y`)
  - WEAVE_L: 왼쪽 레인 (`-100, -100`)
  - WEAVE_R: 오른쪽 레인 (`width + 100, -100`)
- **애니메이션**: `update()`로 히트존까지 이동
- **렌더링**: `draw()`로 원형 또는 사각형(DUCK) 그리기
- **라벨**: 노트 타입에 따른 텍스트 표시 ("J", "S", "WL", "WR" 등)

**중요 속성**:
- `t`: 노트의 게임 시간 (초)
- `typ`: 노트 타입
- `hit`: 히트 여부
- `missed`: 미스 여부
- `judge_result`: 판정 결과 (PERFECT, GREAT, GOOD, MISS)

---

#### `core/audio_manager.py`
**역할**: 오디오 재생 관리

**주요 기능**:
- Pygame Mixer 초기화
- 효과음 로드 및 재생 (`load_sounds()`, `play_sfx()`)
- 배경 음악 로드 및 재생 (`load_music()`, `play_music()`, `stop_music()`)
- 400Hz 비프음 생성 (`_generate_beep()`): 테스트 모드용

**효과음 매핑**:
- `PERFECT` → `hit_perfect.wav`
- `GREAT` → `hit_good.wav`
- `GOOD` → `hit_good.wav`
- `MISS` → `miss.wav`
- `BOMB!` → `bomb.wav`

---

#### `core/hit_effect.py`
**역할**: 히트 효과 파티클 시스템

**주요 클래스**:
- `HitParticle`: 개별 파티클
  - 타입: `ring` (확장하는 링), `burst` (폭발), `spark` (불꽃)
  - 생명주기 관리 및 페이드 아웃
- `HitEffectSystem`: 파티클 시스템 관리
  - `spawn_effect()`: 판정 결과에 따라 다른 효과 생성
    - PERFECT: 4개 링 + 25개 불꽃 + 10개 폭발
    - GREAT: 2개 링 + 15개 폭발
    - GOOD: 1개 링 + 10개 폭발
    - MISS: 6개 폭발 (어두운 색상)

---

#### `core/silhouette.py`
**역할**: 실시간 실루엣 외곽선 추출 모듈 (독립 실행 가능)

**주요 기능**:
- MediaPipe Selfie Segmentation으로 사람 마스크 추출
- MediaPipe Pose로 뼈대 와이어프레임 그리기
- OpenCV 후처리:
  - Gaussian Blur
  - Thresholding
  - Morphology 연산 (닫기 → 열기)
  - Contour 추출 (`cv2.CHAIN_APPROX_NONE`로 최대 부드러움)
- 네온 글로우 효과 (다중 레이어 그리기)
- Mac 기본 카메라 자동 탐지
- ESC 키로 종료
- 좌우 반전 및 중앙 정렬

**중요 함수**:
- `get_best_camera_index()`: Mac 카메라 탐지
- `extract_silhouette()`: 마스크에서 외곽선 추출
- `draw_outline()`: 네온 효과가 있는 외곽선 그리기
- `draw_pose_wireframe()`: 포즈 뼈대 그리기
- `main()`: 독립 실행 진입점

---

#### `judgment_logic.py`
**역할**: 위빙(WEAVE) 노트 판정 로직

**주요 기능**:
- `JudgmentLogic.check_hit()`: 위빙 노트의 HIT/MISS 판정
  - 시간 판정: `JUDGMENT_WINDOW` 내에 있는지 확인
  - 위치 판정: 코 랜드마크 위치 확인
    - WEAVE_L: 코가 중앙선과 오른쪽 라인 사이에 있어야 함
    - WEAVE_R: 코가 왼쪽 라인과 중앙선 사이에 있어야 함
  - 좌표 변환: 카메라 좌표를 화면 좌표로 변환

**중요 사항**:
- JAB 판정은 `PoseTracker`에서 처리
- 위빙 판정만 이 모듈에서 처리

---

### 📁 설정 파일

#### `config/rules.json`
**역할**: 게임 규칙 및 판정 설정

**주요 설정**:
- `spatial_judge_mode`: 1 (손목만) 또는 2 (손 랜드마크 4개)
- `timing_offset`: 시스템 지연 보상값 (초, 음수 = 판정을 더 일찍)
- `score_base`: 판정별 점수 (PERFECT: 300, GREAT: 200, GOOD: 100, MISS: 0)
- `action_thresholds`:
  - `action_refractory`: 0.25초 (쿨타임)
  - `action_v_thresh`: 1.0 (속도 임계값)
  - `action_ang_thresh`: 160도 (각도 임계값, 거의 직선)
- `calibration_hold_time`: 3.0초 (캘리브레이션 유지 시간)

---

#### `config/difficulty.json`
**역할**: 난이도별 설정

**주요 설정**:
- `song_info`:
  - `bpm`: 30 (BPM, 현재 느리게 설정됨)
  - `division`: 4 (박자 분할)
- `judge_timing_base`: 기본 판정 창 (초)
  - `perfect`: 0.50초
  - `great`: 0.75초
  - `good`: 3.00초
- `levels`: 난이도별 설정
  - `Easy`: `judge_timing_scale: 4.0` (매우 관대)
  - `Normal`: `judge_timing_scale: 1.2` (보통)
  - `Hard`: `judge_timing_scale: 1.0` (엄격)
  - `pre_spawn_time`: 노트 사전 스폰 시간 (초)
  - `score_multiplier`: 점수 배수

---

#### `config/ui.json`
**역할**: UI 색상, 위치, 스타일 설정

**주요 설정**:
- `colors`: 색상 정의 (BGR 순서)
  - `notes`: 노트 타입별 색상
  - `judgement`: 판정 텍스트 색상
  - `hud`: HUD 요소 색상
- `positions`: 화면 내 요소 위치 (비율 기반)
  - `hit_zone`: 히트존 중심 위치
  - `calibration_targets`: 캘리브레이션 타겟 위치
- `styles`: 스타일 설정 (크기, 두께)
  - `hud`: 히트존 반지름, 두께
  - `notes`: 노트 원 반지름, 라벨 폰트 크기

---

### 📝 비트맵 파일

#### `assets/beatmaps/song1/beatmap.txt`
**역할**: 텍스트 기반 비트맵 (원본 소스)

**형식**:
- 한 줄이 4박자(1마디)
- 문자 매핑:
  - `1` = JAB_L
  - `2` = JAB_R
  - `3` = WEAVE_L
  - `4` = WEAVE_R
  - `0` = 휴식 (쉼표)
- `#`으로 시작하는 줄은 주석

**예시**:
```
3040304030403040  # 위빙 패턴
1010101010101010  # 왼손 잽 반복
2020202020202020  # 오른손 잽 반복
```

---

#### `assets/beatmaps/song1/beatmap.json`
**역할**: JSON 기반 비트맵 (파싱된 결과)

**형식**:
```json
[
  {"t": 0.0, "type": "JAB_L"},
  {"t": 0.5, "type": "JAB_R"},
  ...
]
```

**중요 사항**:
- `beatmap.txt`가 있으면 우선 사용
- 없으면 `beatmap.json` 사용

---

## 데이터 흐름

### 1. 게임 시작 흐름
```
main() 
  → GameWindow 생성
    → MainMenuScene 표시
      → SPACE 키 입력
        → CalibrationScene 표시
          → 캘리브레이션 완료 또는 0/9 키 입력
            → GameScene 표시
              → 게임 플레이
                → 게임 종료
                  → ResultScene 표시
```

### 2. 프레임 처리 흐름
```
GameWindow.on_update()
  → 카메라 프레임 읽기
    → cv2.flip() 적용
      → PoseTracker.process_frame()
        → MediaPipe 포즈 분석
          → hit_events 생성
            → GameScene.update()
              → _process_hit_events()
                → 노트 매칭 및 판정
                  → 점수/콤보 업데이트
```

### 3. 판정 흐름
```
PoseTracker.process_frame()
  → 속도/각도 계산
    → 구역 확인
      → hit_events 생성
        → GameScene._process_hit_events()
          → 시간 동기화
            → _find_best_matching_note()
              → _determine_judgement()
                → _register_hit()
                  → 점수/콤보 업데이트
                    → 히트 효과 생성
```

---

## 주요 시스템

### 좌표계 변환

1. **카메라 좌표계** (MediaPipe):
   - 원점: 왼쪽 상단
   - x축: 왼쪽 → 오른쪽
   - y축: 위 → 아래
   - 범위: `0 ~ width`, `0 ~ height`

2. **Arcade 좌표계**:
   - 원점: 왼쪽 하단
   - x축: 왼쪽 → 오른쪽
   - y축: 아래 → 위
   - 범위: `0 ~ window.width`, `0 ~ window.height`

3. **변환 함수** (`BaseScene.to_arcade_xy()`):
   ```python
   x_arcade = x_camera * x_scale
   y_arcade = window_height - (y_camera * y_scale)
   ```

### cv2.flip과 좌표계

- `main.py`에서 `cv2.flip(source_frame, 1)`로 프레임을 좌우 반전
- MediaPipe는 반전된 프레임을 처리하므로, 랜드마크 좌표도 반전된 프레임 기준
- 화면 왼쪽에 보이는 손 = 사용자의 오른손 = RIGHT_WRIST
- 화면 오른쪽에 보이는 손 = 사용자의 왼손 = LEFT_WRIST

### 판정 시스템

1. **JAB 판정** (PoseTracker):
   - 속도 임계값: `V_THRESH = 1.0`
   - 각도 임계값: `ANG_THRESH = 160도`
   - 구역 확인: 손이 화면 왼쪽/오른쪽에 있는지
   - 쿨타임: `REFRACTORY = 0.25초`

2. **WEAVE 판정** (JudgmentLogic):
   - 시간 창: `JUDGMENT_WINDOW = 0.2초`
   - 위치 확인: 코 랜드마크가 Dodge 라인 사이에 있는지

3. **판정 등급** (GameScene):
   - PERFECT: `delta <= perfect_window`
   - GREAT: `delta <= great_window`
   - GOOD: `delta <= good_window`
   - MISS: 판정 창을 지나감

### 비트맵 파싱

1. **텍스트 비트맵** (`beatmap.txt`):
   - BPM과 division 기반으로 시간 계산
   - `seconds_per_step = 60.0 / bpm / division`
   - 각 문자를 시간에 매핑

2. **JSON 비트맵** (`beatmap.json`):
   - 직접 시간 정보 포함
   - `{"t": 0.0, "type": "JAB_L"}` 형식

---

## 설정 파일 상세

### `config/rules.json` 구조
```json
{
  "spatial_judge_mode": 2,
  "timing_offset": -0.15,
  "score_base": {
    "PERFECT": 300,
    "GREAT": 200,
    "GOOD": 100,
    "MISS": 0
  },
  "action_thresholds": {
    "action_refractory": 0.25,
    "action_v_thresh": 1.0,
    "action_ang_thresh": 160
  },
  "calibration_hold_time": 3.0
}
```

### `config/difficulty.json` 구조
```json
{
  "default": "Easy",
  "song_info": {
    "bpm": 30,
    "division": 4
  },
  "judge_timing_base": {
    "perfect": 0.50,
    "great": 0.75,
    "good": 3.00
  },
  "levels": {
    "Easy": {
      "pre_spawn_time": 1.5,
      "judge_timing_scale": 4.0,
      "score_multiplier": 0.8
    },
    "Normal": {
      "pre_spawn_time": 1.2,
      "judge_timing_scale": 1.2,
      "score_multiplier": 1.0
    },
    "Hard": {
      "pre_spawn_time": 1.0,
      "judge_timing_scale": 1.0,
      "score_multiplier": 1.2
    }
  }
}
```

### `config/ui.json` 구조
```json
{
  "colors": {
    "notes": { ... },
    "judgement": { ... },
    "hud": { ... }
  },
  "positions": {
    "hit_zone": { ... },
    "calibration_targets": { ... }
  },
  "styles": {
    "hud": { ... },
    "notes": { ... }
  }
}
```

---

## 주요 알고리즘

### 1. 랜드마크 스무딩
```python
new_x = prev_x * (1.0 - alpha) + raw_x * alpha
new_y = prev_y * (1.0 - alpha) + raw_y * alpha
```
- `alpha = 0.7`: 스무딩 계수
- 지수 이동 평균 사용

### 2. 속도 계산
```python
radial_speed = (r_now - r_prev) / dt
```
- 어깨에서 손목까지의 방사형 거리 변화율
- 정규화: 어깨 너비로 나눔

### 3. 각도 계산
```python
angle = arccos(dot(ab, cb) / (|ab| * |cb|))
```
- 어깨-팔꿈치-손목 각도
- 160도 이상이면 거의 직선 (펀치 동작)

### 4. 노트 매칭
```python
candidates = [note for note in active_notes 
              if note.typ == note_type 
              and not note.hit 
              and not note.missed]
valid_candidates = [note for note in candidates 
                    if abs(note.t - adjusted_time) <= max_window]
best = min(valid_candidates, key=lambda n: abs(n.t - adjusted_time))
```
- 판정 창 내의 노트만 필터링
- 가장 가까운 노트 선택

---

## 디버깅 및 테스트

### 테스트 모드 활성화
- 캘리브레이션 화면에서 `0` 키: 일반 모드로 게임 시작
- 캘리브레이션 화면에서 `9` 키: 테스트 모드로 게임 시작
- 게임 중 `M` 키: 테스트 모드 토글

### 테스트 모드 기능
- 판정 디버깅 정보 표시
- 히트존 색상 변경 (손 위치에 따라)
- 최근 hit_events 히스토리
- 포즈 랜드마크 연결선

---

## 알려진 이슈 및 주의사항

1. **좌표계 불일치**:
   - `cv2.flip`으로 프레임 반전 시 MediaPipe 좌표도 반전된 프레임 기준
   - 추가 좌표 반전 불필요

2. **판정 조건**:
   - `V_THRESH = 1.0`, `ANG_THRESH = 160`이 동시에 충족되어야 함
   - 조건이 엄격할 수 있음

3. **시간 동기화**:
   - `timing_offset`으로 시스템 지연 보상
   - 음수 값 = 판정을 더 일찍

4. **BPM 설정**:
   - 현재 `bpm: 30`으로 설정되어 매우 느림
   - `config/difficulty.json`에서 조정 가능

---

## 확장 가능성

1. **새로운 노트 타입 추가**:
   - `constants.py`에 비트 타입 정의
   - `note.py`에 렌더링 로직 추가
   - `beatmap.txt` 매핑 추가

2. **새로운 게임 모드 추가**:
   - `game_mode_strategy.py`를 상속받아 구현
   - `GameScene`에서 전략 선택

3. **새로운 판정 로직 추가**:
   - `judgment_logic.py`에 메서드 추가
   - `GameScene`에서 호출

---

이 문서는 프로젝트의 전체 구조와 각 파일의 역할을 상세히 설명합니다. GPT와 같은 다른 LLM 모델이 이 문서를 참고하여 프로젝트를 이해하고 작업할 수 있습니다.

