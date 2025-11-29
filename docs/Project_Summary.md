프로젝트 구조와 포즈 데이터 관련 코드 확인 중.


[7 tools called]


프로젝트 요약 문서 작성 중. 포즈 데이터 저장 및 판단 부분을 중심으로 정리합니다.


[3 tools called]


프로젝트 요약 문서 마크다운 작성 중. 포즈 데이터 저장 및 판단 부분을 중심으로 정리합니다.

```markdown
# Beat Boxer Game - 프로젝트 요약 문서

## 1. 프로젝트 개요

Beat Boxer는 MediaPipe를 사용한 실시간 포즈 인식 기반 리듬 게임입니다. 사용자는 카메라 앞에서 복싱 동작을 수행하여 화면에 나타나는 노트에 맞춰 타이밍에 맞게 동작을 취해야 합니다.

### 주요 기술 스택
- **게임 엔진**: Arcade (Python 2D 게임 라이브러리)
- **포즈 인식**: MediaPipe Pose
- **비디오 처리**: OpenCV
- **오디오**: Pygame

## 2. 프로젝트 구조

```
beat_boxer_game/
├── main.py                          # 메인 진입점
├── core/                            # 핵심 게임 로직
│   ├── pose_tracker.py              # MediaPipe 포즈 추적
│   ├── pose_data_collector.py       # 포즈 데이터 수집 및 CSV 저장
│   ├── note.py                      # 노트 클래스
│   ├── note_manager.py              # 노트 관리
│   ├── judgment_processor.py        # 판정 처리
│   ├── judgment_logic.py            # 판정 로직
│   ├── score_manager.py             # 점수 관리
│   ├── beatmap_loader.py            # 비트맵 로드
│   ├── game_state.py                # 게임 상태 관리
│   └── ...
├── scenes/                          # 게임 씬
│   ├── game_scene.py                # 메인 게임 씬
│   ├── test_mode_strategy.py        # 테스트 모드 전략 (포즈 데이터 수집)
│   ├── normal_mode_strategy.py      # 일반 모드 전략
│   ├── calibration_scene.py         # 캘리브레이션 씬
│   └── ...
├── config/                          # 설정 파일
│   ├── difficulty.json              # 난이도 설정
│   ├── rules.json                   # 게임 규칙
│   └── ui.json                      # UI 설정
└── assets/                          # 게임 리소스
    ├── beatmaps/                    # 비트맵 파일
    └── images/                      # 이미지 파일
```

## 3. 포즈 데이터 수집 및 판단 시스템

### 3.1 개요

테스트 모드에서 노트가 hit area에 도달할 때 사용자의 포즈 데이터를 수집하여 CSV 파일로 저장합니다. 이 데이터는 향후 사용자의 습관을 파악하고 개선점을 제시하는 데 사용됩니다.

### 3.2 핵심 컴포넌트

#### 3.2.1 PoseDataCollector (`core/pose_data_collector.py`)

포즈 데이터를 수집하고 CSV 파일로 저장하는 클래스입니다.

**주요 메서드:**

1. **`__init__(test_mode: bool)`**
   - 테스트 모드 활성화 여부를 받아 초기화
   - 출력 디렉토리: `data/pose_data/`
   - 데이터 저장 리스트 초기화

2. **`collect_data(note_type: str, pose_data: Dict[str, Any])`**
   - 노트 타입과 포즈 데이터를 받아 저장
   - 노트 타입별로 해당 컬럼에만 데이터 저장
   - 포즈 데이터는 JSON 문자열로 변환하여 저장

3. **`save_to_csv() -> Optional[str]`**
   - 수집된 데이터를 CSV 파일로 저장
   - 파일명 형식: `pose_data_YYYYMMDD_HHMMSS.csv`
   - 저장 위치: `data/pose_data/`

**CSV 파일 구조:**

```csv
노트명, 가드 데이터, 잽 데이터, 스트레이트 데이터, 위빙 데이터 L, 위빙 데이터 R
Guard, {"left_fist_dist": 0.2, ...}, , , ,
Jab, , {"left_arm_angle": 165, ...}, , ,
Straight, , , {"right_arm_angle": 160, ...}, ,
Weaving (L), , , , {"nose_position": 0.3, ...},
Weaving (R), , , , , {"nose_position": -0.4, ...}
```

**노트 타입 매핑:**
- `GUARD` → "가드 데이터" 컬럼
- `JAB_L` → "잽 데이터" 컬럼
- `JAB_R` → "스트레이트 데이터" 컬럼
- `WEAVE_L` → "위빙 데이터 L" 컬럼
- `WEAVE_R` → "위빙 데이터 R" 컬럼

#### 3.2.2 TestModeStrategy (`scenes/test_mode_strategy.py`)

테스트 모드에서 포즈 데이터 수집을 담당하는 전략 클래스입니다.

**주요 메서드:**

1. **`__init__(game_scene)`**
   - `PoseDataCollector` 인스턴스 생성 (test_mode=True)
   - 이벤트 히스토리 초기화

2. **`check_and_collect_pose_data(game_time, active_notes, judge_timing)`**
   - 노트가 hit area에 도달했는지 확인
   - 도달한 노트의 포즈 데이터를 수집
   - 중복 수집 방지 (note.pose_data_collected 플래그 사용)

3. **`_calculate_pose_data(game_scene) -> dict`**
   - MediaPipe 랜드마크로부터 포즈 판정 데이터 계산
   - 반환되는 데이터 구조는 아래 참조

4. **`save_pose_data() -> Optional[str]`**
   - 수집된 데이터를 CSV 파일로 저장

### 3.3 포즈 데이터 계산 (`_calculate_pose_data`)

**입력 데이터:**
- `game_scene.last_nose_pos`: 코 위치 (카메라 좌표)
- `game_scene.last_left_fist`: 왼손 중심점 (4개 랜드마크의 평균)
- `game_scene.last_right_fist`: 오른손 중심점 (4개 랜드마크의 평균)
- `game_scene.pose_tracker.get_smoothed_landmarks()`: 스무딩된 랜드마크
  - `shoulders`: (left_shoulder, right_shoulder)
  - `left_elbow`, `right_elbow`
  - `left_wrist`, `right_wrist`
- `shoulder_width`: 어깨 너비 (캘리브레이션에서 계산)

**출력 데이터 (딕셔너리):**

```python
{
    # 왼손 데이터 (코 기준)
    "left_fist_dist": float,      # 왼손 거리 (어깨 너비로 정규화)
    "left_fist_angle": float,     # 왼손 각도 (0-360도, Y축 반전)
    
    # 오른손 데이터 (코 기준)
    "right_fist_dist": float,     # 오른손 거리 (어깨 너비로 정규화)
    "right_fist_angle": float,    # 오른손 각도 (0-360도, Y축 반전)
    
    # 팔 각도 데이터
    "left_arm_angle": float,      # 왼팔 각도 (어깨-팔꿈치-손목, 0-180도)
    "right_arm_angle": float,     # 오른팔 각도 (어깨-팔꿈치-손목, 0-180도)
    
    # 코 위치 데이터
    "nose_position": float,       # 코 위치 (화면 중앙 기준, 어깨 너비로 정규화)
    "nose_above_shoulder": bool   # 코가 어깨보다 위에 있는지 여부
}
```

**계산 방법:**

1. **거리 계산 (`_calculate_distance`)**
   ```python
   dist = sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
   normalized_dist = dist / shoulder_width
   ```

2. **각도 계산 (`_calculate_angle_from_nose`)**
   ```python
   dx = target[0] - nose[0]
   dy = nose[1] - target[1]  # Y축 반전
   angle_rad = atan2(dy, dx)
   angle_deg = degrees(angle_rad)
   if angle_deg < 0:
       angle_deg += 360
   ```

3. **팔 각도 계산 (`_calculate_arm_angle`)**
   ```python
   v1 = shoulder - elbow
   v2 = wrist - elbow
   cos_angle = dot(v1, v2) / (norm(v1) * norm(v2))
   angle_rad = acos(clip(cos_angle, -1.0, 1.0))
   angle_deg = degrees(angle_rad)
   ```

4. **코 위치 계산**
   ```python
   nose_screen_x, nose_screen_y = to_arcade_xy(nose)
   center_x = screen_width / 2
   nose_position = (nose_screen_x - center_x) / shoulder_width
   ```

### 3.4 포즈 판별 (`_detect_current_pose`)

현재 포즈를 판별하는 메서드입니다. 5가지 포즈 타입을 구분합니다.

**판별 조건:**

1. **가드 (Guard Stance)**
   ```python
   guard_ok = (
       0.1 < left_fist_dist < 0.3 and 10 < left_fist_angle < 80 and
       0.2 < right_fist_dist < 0.5 and 100 < right_fist_angle < 170
   )
   ```

2. **왼손 잽 (Jab Left)**
   ```python
   jab_left_ok = (
       left_arm_angle > 150 and
       0.2 < right_fist_dist < 0.5
   )
   ```

3. **오른손 스트레이트 (Straight Right)**
   ```python
   straight_right_ok = (
       right_arm_angle > 150 and
       right_fist_dist > 0.8 and
       0.1 < left_fist_dist < 0.3
   )
   ```

4. **위빙 좌 (Weave Left)**
   ```python
   weave_left_ok = (
       guard_ok and
       0.2 < nose_position < 0.5 and
       nose_above_shoulder
   )
   ```

5. **위빙 우 (Weave Right)**
   ```python
   weave_right_ok = (
       guard_ok and
       -0.5 < nose_position < -0.2 and
       nose_above_shoulder
   )
   ```

**우선순위:** 공격 포즈 > 위빙 > 가드

### 3.5 데이터 수집 흐름

1. **게임 시작**
   - 테스트 모드 활성화 (9번 키 또는 캘리브레이션에서 9번 키)
   - `TestModeStrategy` 초기화 시 `PoseDataCollector` 생성

2. **게임 플레이 중 (`GameScene.update`)**
   - 매 프레임 `check_and_collect_pose_data` 호출
   - 활성 노트 확인
   - 각 노트에 대해:
     - `note.pose_data_collected`가 False인지 확인
     - `abs(game_time - note.t) <= judgment_window` 확인 (hit area 도달)
     - 도달한 경우:
       - `_calculate_pose_data`로 포즈 데이터 계산
       - `PoseDataCollector.collect_data(note.typ, pose_data)` 호출
       - `note.pose_data_collected = True` 설정

3. **게임 종료 (`GameScene.cleanup`)**
   - `TestModeStrategy.save_pose_data()` 호출
   - `PoseDataCollector.save_to_csv()` 실행
   - CSV 파일 저장: `data/pose_data/pose_data_YYYYMMDD_HHMMSS.csv`

### 3.6 노트 타입

**지원되는 노트 타입:**
- `GUARD` (0): 가드 자세
- `JAB_L` (1): 왼손 잽
- `JAB_R` (2): 오른손 스트레이트
- `WEAVE_L` (3): 위빙 좌
- `WEAVE_R` (4): 위빙 우

**비트맵 파일 형식 (`beatmap.txt`):**
```
# BPM: 120
00000000000000000000  # 가드 노트
11111111111111111111  # 잽 노트
22222222222222222222  # 스트레이트 노트
33333333333333333333  # 위빙 좌 노트
44444444444444444444  # 위빙 우 노트
```

### 3.7 주의사항

1. **테스트 모드에서만 작동**: `PoseDataCollector.test_mode`가 True일 때만 데이터 수집
2. **중복 수집 방지**: `note.pose_data_collected` 플래그로 같은 노트에서 여러 번 수집하지 않음
3. **Hit Area 도달 기준**: 판정 창(good 창, 기본 0.5초) 내에 노트가 있을 때 수집
4. **데이터 형식**: 포즈 데이터는 JSON 문자열로 저장되어 CSV의 단일 셀에 저장됨

## 4. 주요 파일 및 역할

### 4.1 Core 모듈

- **`pose_tracker.py`**: MediaPipe를 사용한 포즈 추적, 랜드마크 스무딩, 주먹 중심점 계산
- **`pose_data_collector.py`**: 포즈 데이터 수집 및 CSV 저장
- **`note.py`**: 노트 클래스 (포즈 데이터 수집 플래그 포함)
- **`judgment_processor.py`**: 판정 처리 (PERFECT/GREAT/GOOD/MISS)
- **`judgment_logic.py`**: 판정 로직 (WEAVE 노트의 코 위치 기반 판정)

### 4.2 Scene 모듈

- **`game_scene.py`**: 메인 게임 씬, 노트 스폰, 판정 처리, 포즈 데이터 수집 트리거
- **`test_mode_strategy.py`**: 테스트 모드 전략, 포즈 데이터 계산 및 수집
- **`calibration_scene.py`**: 캘리브레이션 씬 (어깨 너비 등 측정)

## 5. 설정 파일

### 5.1 `config/difficulty.json`
- BPM 설정
- 판정 타이밍 (perfect, great, good 창 크기)
- 난이도별 스케일

### 5.2 `config/rules.json`
- 액션 임계값 (속도, 각도 등)
- 공간 판정 모드
- 캘리브레이션 유지 시간

### 5.3 `config/ui.json`
- UI 색상 설정
- 위치 설정 (hit zone, 캘리브레이션 타겟 등)
- 스타일 설정 (노트 크기, 폰트 등)

## 6. 실행 방법

1. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

2. **게임 실행**
   ```bash
   python main.py
   ```

3. **테스트 모드 진입**
   - 메인 메뉴에서 SPACE로 캘리브레이션 시작
   - 캘리브레이션 화면에서 9번 키로 테스트 모드 진입
   - 또는 게임 중 T 키로 테스트 모드 토글

4. **포즈 데이터 확인**
   - 게임 종료 후 `data/pose_data/` 디렉토리에서 CSV 파일 확인

## 7. 향후 활용 방안

수집된 포즈 데이터는 다음과 같이 활용할 수 있습니다:

1. **사용자 습관 분석**
   - 각 포즈 타입별 데이터 분포 분석
   - 일관성 있는 패턴 발견
   - 개선이 필요한 포즈 식별

2. **머신러닝 모델 학습**
   - 클러스터링: 사용자 그룹 분류
   - 강화학습: 개인화된 피드백 제공
   - 예측 모델: 다음 동작 예측

3. **게임 밸런스 조정**
   - 판정 기준 조정
   - 난이도 커스터마이징
   - 개인별 맞춤형 트레이닝 제공
```
