# Beat Boxer Game - 리팩토링 결과 문서

## 📋 목차
1. [리팩토링 개요](#리팩토링-개요)
2. [Phase별 변경 사항](#phase별-변경-사항)
3. [파일별 상세 변경 내용](#파일별-상세-변경-내용)
4. [코드 변경 전/후 비교](#코드-변경-전후-비교)
5. [개선 효과](#개선-효과)
6. [마이그레이션 가이드](#마이그레이션-가이드)

---

## 리팩토링 개요

### 🎯 목표
1. **Strategy 패턴 목적 충족**: Strategy가 독립적으로 동작하며 테스트 가능하도록
2. **코드 중복 제거**: `normal_mode_strategy`와 `test_mode_strategy`의 공통 로직 통합
3. **책임 분리**: `GameScene`의 비대함 해소, 각 모듈의 명확한 역할 정의
4. **BPM 연동 개선**: 박자 단위 기반 설정으로 음악과 자연스럽게 동기화

### 📊 리팩토링 범위
- **Phase 1**: PoseTracker 역할 확장 (계산 통합)
- **Phase 2**: Strategy 패턴 재정립 (역할 분리)
- **Phase 3**: BPM 연동 로직 개선 (박자 단위)
- **Phase 4**: 캘리브레이션 로직 이동

---

## Phase별 변경 사항

### 🔹 Phase 1: PoseTracker 역할 확장

#### 목표
랜드마크 스무딩 및 주먹 중심점 계산을 `PoseTracker`로 이동하여 `GameScene`의 책임 축소

#### 주요 변경사항

**1. `core/pose_tracker.py`에 추가된 속성:**
```python
# 랜드마크 스무딩 데이터
self.smoothing_alpha = 0.7  # 스무딩 계수
self.calib_landmark_pos = {...}  # 캘리브레이션 랜드마크
self.smoothed_landmark_pos = {...}  # 스무딩된 랜드마크

# 주먹 중심점 (계산된 값)
self.left_fist_center = None
self.right_fist_center = None
```

**2. `core/pose_tracker.py`에 추가된 메서드:**
- `get_smoothed_landmarks()`: 현재 스무딩된 모든 랜드마크 반환
- `get_fist_centroids()`: 주먹 중심점 반환
- `update_landmark_smoothing(pose_landmarks)`: 랜드마크 스무딩 업데이트
- `calculate_fist_centroids()`: 주먹 중심점 계산

**3. `scenes/game_scene.py`에서 제거된 속성:**
- `self.calib_landmark_pos`
- `self.smoothed_landmark_pos`
- `self.left_fist_center`
- `self.right_fist_center`

**4. `scenes/game_scene.py`에서 제거된 로직:**
- `update()` 메서드 내 랜드마크 스무딩 로직 (약 60줄)
- `update()` 메서드 내 주먹 중심점 계산 로직 (약 20줄)

**5. `scenes/game_scene.py` 수정사항:**
- `update()`: `pose_tracker.get_smoothed_landmarks()` 호출
- `_hand_inside_hit_zone()`: `pose_tracker.get_smoothed_landmarks()`, `pose_tracker.get_fist_centroids()` 사용
- `draw()`: `pose_tracker.get_smoothed_landmarks()`, `pose_tracker.get_fist_centroids()` 사용

**예상 효과:**
- `GameScene` 코드 약 100줄 감소
- `PoseTracker`가 포즈 관련 모든 데이터를 캡슐화

---

### 🔹 Phase 2: Strategy 패턴 재정립

#### 목표
Strategy가 독립적으로 동작하며, 공통 로직을 통합하여 코드 중복 제거

#### 주요 변경사항

**1. `scenes/game_mode_strategy.py` 수정:**
- `draw_hud()`: 템플릿 메서드로 변경
- `_draw_common_hud()`: 공통 HUD 그리기 로직 추가 (히트존, 덕 라인, 점수/콤보, 판정 통계)
- `_draw_mode_specific_hud()`: 추상 메서드로 변경 (모드별 추가 로직)
- `handle_hits()`: 시그니처에 `**kwargs` 추가
- `calculate_debug_info()`: 제거 (GameScene에서 계산)

**2. `scenes/normal_mode_strategy.py` 수정:**
- `draw_hud()`: 제거, `_draw_mode_specific_hud()`만 구현
- 공통 HUD 로직 제거 (약 50줄)
- `handle_hits()`: 시그니처에 `**kwargs` 추가

**3. `scenes/test_mode_strategy.py` 수정:**
- `draw_hud()`: 제거, `_draw_mode_specific_hud()`만 구현
- 공통 HUD 로직 제거 (약 50줄)
- `calculate_debug_info()`: 제거
- `handle_hits()`: 시그니처에 `**kwargs` 추가

**4. `scenes/game_scene.py` 수정:**
- `_handle_hits()`: Strategy에게 필요한 데이터만 전달
  ```python
  smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
  left_fist, right_fist = self.pose_tracker.get_fist_centroids()
  
  self.mode_strategy.handle_hits(
      hit_events, 
      t_game, 
      now,
      smoothed_landmarks=smoothed_landmarks,
      left_fist_center=left_fist,
      right_fist_center=right_fist
  )
  ```
- `calculate_debug_info()` 호출 제거

**예상 효과:**
- 공통 HUD 로직 중복 제거 (약 100줄 감소)
- Strategy 독립성 향상

---

### 🔹 Phase 3: BPM 연동 로직 개선

#### 목표
설정을 박자 단위로 변경하여 BPM 변경에 자동 대응

#### 주요 변경사항

**1. `config/difficulty.json` 변경:**

**변경 전:**
```json
{
  "judge_timing_base": {
    "perfect": 0.50,  // 초 단위
    "great": 0.75,
    "good": 3.00
  },
  "levels": {
    "Normal": {
      "pre_spawn_time": 1.2  // 초 단위
    }
  }
}
```

**변경 후:**
```json
{
  "judge_timing_base_beats": {
    "perfect_beats": 0.5,  // 박자 단위
    "great_beats": 0.75,
    "good_beats": 1.0,
    "//": "박자 단위 (Phase 3: BPM에 따라 자동으로 초 단위로 변환됨)"
  },
  "levels": {
    "Normal": {
      "pre_spawn_beats": 2.0,  // 박자 단위
      "//": "pre_spawn_beats: 박자 단위 (Phase 3: BPM에 따라 자동으로 초 단위로 변환됨)"
    }
  }
}
```

**2. `scenes/game_scene.py` 수정:**

**변경 전:**
```python
# BPM 스케일링 계산 (비선형 스케일)
reference_bpm = 60.0
bpm_scale = (reference_bpm / max(1.0, bpm)) ** 0.7
bpm_scale = max(0.5, min(2.0, bpm_scale))

base_timing = self.config_difficulty.get("judge_timing_base", {...})
scale = self.difficulty.get("judge_timing_scale", 1.0)
self.judge_timing = {k: v * scale * bpm_scale for k, v in base_timing.items()}

base_pre_spawn = self.difficulty["pre_spawn_time"]
self.pre_spawn_time = base_pre_spawn * bpm_scale
```

**변경 후:**
```python
# Phase 3: 박자 단위를 초 단위로 변환 (BPM 기반)
seconds_per_beat = 60.0 / max(1e-6, bpm)

# 판정 시간: 박자 단위 → 초 단위
base_timing_beats = self.config_difficulty.get("judge_timing_base_beats", {...})
scale = self.difficulty.get("judge_timing_scale", 1.0)

self.judge_timing = {}
for key, beats in base_timing_beats.items():
    if key.endswith("_beats"):
        seconds = beats * seconds_per_beat
        timing_key = key.replace("_beats", "")
        self.judge_timing[timing_key] = seconds * scale

# 스폰 시간: 박자 단위 → 초 단위
pre_spawn_beats = self.difficulty.get("pre_spawn_beats", 2.0)
self.pre_spawn_time = pre_spawn_beats * seconds_per_beat
```

**예상 효과:**
- BPM 변경 시 모든 타이밍이 자동으로 조정됨
- 설정이 더 직관적이고 이해하기 쉬움
- 비선형 스케일링 로직 제거로 코드 단순화

---

### 🔹 Phase 4: 캘리브레이션 로직 이동

#### 목표
캘리브레이션 로직을 `PoseTracker`로 이동하여 일관성 있는 모듈 구조 확보

#### 주요 변경사항

**1. `core/pose_tracker.py`에 추가된 메서드:**
- `check_calibration_position(calib_targets)`: 캘리브레이션 위치 확인

**2. `scenes/game_scene.py` 수정:**
- `_check_calib_position()`: 제거 (로직은 `PoseTracker`로 이동)
- `update()`: `pose_tracker.check_calibration_position()` 호출
  ```python
  all_ok, self.calib_status, raw_landmark_pos = self.pose_tracker.check_calibration_position(self.calib_targets)
  ```

**예상 효과:**
- `GameScene` 코드 약 50줄 감소
- 캘리브레이션 로직이 포즈 관련 모듈로 통합

---

## 파일별 상세 변경 내용

### 📁 `core/pose_tracker.py`

#### 추가된 속성
```python
# 랜드마크 스무딩 데이터 (Phase 1)
self.smoothing_alpha = 0.7
self.calib_landmark_pos = {
    "head_center": None, "nose": None, ...
}
self.smoothed_landmark_pos = self.calib_landmark_pos.copy()

# 주먹 중심점 (Phase 1)
self.left_fist_center = None
self.right_fist_center = None
```

#### 추가된 메서드

**1. `get_smoothed_landmarks()`**
```python
def get_smoothed_landmarks(self):
    """현재 스무딩된 모든 랜드마크를 반환합니다 (Phase 1)."""
    return self.smoothed_landmark_pos.copy()
```

**2. `get_fist_centroids()`**
```python
def get_fist_centroids(self):
    """주먹 중심점을 계산하여 반환합니다 (Phase 1).
    
    Returns:
        (left_fist_center, right_fist_center): 
        - left_fist_center: (x, y) 또는 None
        - right_fist_center: (x, y) 또는 None
    """
    return (self.left_fist_center, self.right_fist_center)
```

**3. `update_landmark_smoothing(pose_landmarks)`**
```python
def update_landmark_smoothing(self, pose_landmarks):
    """랜드마크 스무딩을 업데이트합니다 (Phase 1)."""
    # 랜드마크 좌표 추출 및 스무딩 적용
    # (기존 GameScene.update()의 스무딩 로직 이동)
```

**4. `calculate_fist_centroids()`**
```python
def calculate_fist_centroids(self):
    """주먹 중심점을 계산합니다 (Phase 1)."""
    # spatial_judge_mode에 따라 주먹 중심점 계산
    # (기존 GameScene.update()의 계산 로직 이동)
```

**5. `check_calibration_position(calib_targets)` (Phase 4)**
```python
def check_calibration_position(self, calib_targets):
    """캘리브레이션 위치 확인 (Phase 4).
    
    Args:
        calib_targets: 캘리브레이션 타겟 정보 (head, left_fist, right_fist)
    
    Returns:
        (all_ok, (head_ok, left_fist_ok, right_fist_ok), raw_landmark_pos)
    """
    # (기존 GameScene._check_calib_position() 로직 이동)
```

#### 수정된 메서드

**`process_frame()`:**
```python
# Phase 1: 랜드마크 스무딩 및 주먹 중심점 계산 추가
if res.pose_landmarks:
    self.update_landmark_smoothing(res.pose_landmarks)
    self.calculate_fist_centroids()
```

**예상 코드 증가:** +200줄

---

### 📁 `scenes/game_scene.py`

#### 제거된 속성
- `self.calib_landmark_pos`
- `self.smoothed_landmark_pos`
- `self.left_fist_center`
- `self.right_fist_center`

#### 제거된 메서드
- `_check_calib_position()` (Phase 4: `PoseTracker.check_calibration_position()`로 이동)

#### 수정된 메서드

**1. `__init__()` (Phase 3: BPM 연동 개선)**
```python
# 변경 전: BPM 스케일링 (비선형)
reference_bpm = 60.0
bpm_scale = (reference_bpm / max(1.0, bpm)) ** 0.7
base_timing = self.config_difficulty.get("judge_timing_base", {...})
self.judge_timing = {k: v * scale * bpm_scale for k, v in base_timing.items()}

# 변경 후: 박자 단위 → 초 단위 변환
seconds_per_beat = 60.0 / max(1e-6, bpm)
base_timing_beats = self.config_difficulty.get("judge_timing_base_beats", {...})
for key, beats in base_timing_beats.items():
    if key.endswith("_beats"):
        seconds = beats * seconds_per_beat
        timing_key = key.replace("_beats", "")
        self.judge_timing[timing_key] = seconds * scale
```

**2. `reset_game_state()` (Phase 1)**
```python
# 변경 전:
self.calib_landmark_pos = {...}
self.smoothed_landmark_pos = self.calib_landmark_pos.copy()
self.left_fist_center = None
self.right_fist_center = None

# 변경 후:
# Phase 1: 랜드마크 데이터는 PoseTracker에서 관리
```

**3. `update()` (Phase 1, Phase 4)**
```python
# 변경 전:
# 2. 캘리브레이션 조준 확인
all_ok, self.calib_status, raw_landmark_pos = self._check_calib_position(landmarks)

# 4. 스무딩 (약 60줄의 스무딩 로직)
for key in self.smoothed_landmark_pos.keys():
    # ... 스무딩 로직 ...

# 주먹 중심점 계산 (약 20줄)
self.left_fist_center = calc_centroid(left_keys)
self.right_fist_center = calc_centroid(right_keys)

# 변경 후:
# Phase 1: 랜드마크 스무딩은 PoseTracker에서 처리됨
# Phase 4: 캘리브레이션 조준 확인은 PoseTracker에서 처리
all_ok, self.calib_status, raw_landmark_pos = self.pose_tracker.check_calibration_position(self.calib_targets)

# 스무딩된 랜드마크는 PoseTracker에서 가져옴
smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
```

**4. `_hand_inside_hit_zone()` (Phase 1)**
```python
# 변경 전:
pt = self.smoothed_landmark_pos.get(key)
fist_center = self.right_fist_center  # 또는 self.left_fist_center

# 변경 후:
smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
left_fist, right_fist = self.pose_tracker.get_fist_centroids()
pt = smoothed_landmarks.get(key)
fist_center = right_fist  # 또는 left_fist
```

**5. `_handle_hits()` (Phase 2)**
```python
# 변경 전:
self.mode_strategy.handle_hits(hit_events, t_game, now)

# 변경 후:
smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
left_fist, right_fist = self.pose_tracker.get_fist_centroids()

self.mode_strategy.handle_hits(
    hit_events, 
    t_game, 
    now,
    smoothed_landmarks=smoothed_landmarks,
    left_fist_center=left_fist,
    right_fist_center=right_fist
)
```

**6. `draw()` (Phase 1)**
```python
# 변경 전:
nose_pos = self.smoothed_landmark_pos.get("nose")
if self.left_fist_center:
    lx, ly = self.left_fist_center

# 변경 후:
smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
left_fist, right_fist = self.pose_tracker.get_fist_centroids()
nose_pos = smoothed_landmarks.get("nose")
if left_fist:
    lx, ly = left_fist
```

**예상 코드 감소:** -200줄

---

### 📁 `scenes/game_mode_strategy.py`

#### 추가된 메서드

**1. `_draw_common_hud()` (Phase 2: 공통 로직 통합)**
```python
def _draw_common_hud(self, frame):
    """공통 HUD 요소 그리기 (Phase 2: 공통 로직 통합)."""
    # 히트존, 덕 라인 그리기
    # 판정 결과에 따른 히트존 색상 변경
    # 히트존 원 위에 최근 판정 결과 표시
    # Score, Combo 표시
    # 판정 통계 표시
```

#### 수정된 메서드

**1. `draw_hud()` (Phase 2: 템플릿 메서드 패턴)**
```python
# 변경 전: 추상 메서드
@abstractmethod
def draw_hud(self, frame):
    pass

# 변경 후: 템플릿 메서드
def draw_hud(self, frame):
    """HUD 그리기 템플릿 메서드 (Phase 2: 공통 로직 통합)."""
    self._draw_common_hud(frame)
    self._draw_mode_specific_hud(frame)
```

**2. `handle_hits()` (Phase 2: kwargs 추가)**
```python
# 변경 전:
@abstractmethod
def handle_hits(self, hit_events, t_game, now):
    pass

# 변경 후:
@abstractmethod
def handle_hits(self, hit_events, t_game, now, **kwargs):
    """감지된 히트 이벤트를 해당 노트와 매칭하여 판정합니다 (Phase 2: kwargs 추가)."""
    pass
```

#### 제거된 메서드
- `calculate_debug_info()` (Phase 2: GameScene에서 계산)

**예상 코드 증가:** +80줄

---

### 📁 `scenes/normal_mode_strategy.py`

#### 제거된 메서드
- `draw_hud()` 전체 (약 50줄) - 부모 클래스의 템플릿 메서드 사용

#### 추가된 메서드
- `_draw_mode_specific_hud()`: 랜드마크 시각화만 구현

#### 수정된 메서드
- `handle_hits()`: 시그니처에 `**kwargs` 추가

**예상 코드 감소:** -50줄

---

### 📁 `scenes/test_mode_strategy.py`

#### 제거된 메서드
- `draw_hud()` 전체 (약 50줄) - 부모 클래스의 템플릿 메서드 사용
- `calculate_debug_info()` (Phase 2: GameScene에서 계산)

#### 추가된 메서드
- `_draw_mode_specific_hud()`: 랜드마크 시각화만 구현

#### 수정된 메서드
- `handle_hits()`: 시그니처에 `**kwargs` 추가

**예상 코드 감소:** -70줄

---

### 📁 `config/difficulty.json`

#### 변경 사항

**변경 전:**
```json
{
  "judge_timing_base": {
    "perfect": 0.50,
    "great": 0.75,
    "good": 3.00
  },
  "levels": {
    "Normal": {
      "pre_spawn_time": 1.2
    }
  }
}
```

**변경 후:**
```json
{
  "judge_timing_base_beats": {
    "perfect_beats": 0.5,
    "great_beats": 0.75,
    "good_beats": 1.0,
    "//": "박자 단위 (Phase 3: BPM에 따라 자동으로 초 단위로 변환됨)"
  },
  "levels": {
    "Normal": {
      "pre_spawn_beats": 2.0,
      "//": "pre_spawn_beats: 박자 단위 (Phase 3: BPM에 따라 자동으로 초 단위로 변환됨)"
    }
  }
}
```

**주의사항:**
- 기존 설정 파일과의 호환성 없음 (마이그레이션 필요)
- `judge_timing_base` → `judge_timing_base_beats`
- `pre_spawn_time` → `pre_spawn_beats`
- 단위가 초에서 박자로 변경됨

---

## 코드 변경 전/후 비교

### 예시 1: 랜드마크 스무딩 (Phase 1)

**변경 전 (`game_scene.py`):**
```python
# 4. 스무딩
SMOOTH_FACTOR = 0.7
for key in self.smoothed_landmark_pos.keys():
    raw_pos = raw_landmark_pos.get(key)
    prev_pos = self.smoothed_landmark_pos.get(key)
    # ... 약 60줄의 스무딩 로직 ...
```

**변경 후 (`game_scene.py`):**
```python
# Phase 1: 스무딩된 랜드마크는 PoseTracker에서 가져옴
smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
```

**변경 후 (`pose_tracker.py`):**
```python
def process_frame(self, frame, now):
    # ... 기존 로직 ...
    if res.pose_landmarks:
        self.update_landmark_smoothing(res.pose_landmarks)
        self.calculate_fist_centroids()
```

---

### 예시 2: 공통 HUD 로직 (Phase 2)

**변경 전 (`normal_mode_strategy.py`):**
```python
def draw_hud(self, frame):
    # 히트존 그리기 (약 20줄)
    # 점수/콤보 표시 (약 10줄)
    # 판정 통계 표시 (약 10줄)
    # 랜드마크 시각화 (약 10줄)
    # 총 약 50줄
```

**변경 후 (`normal_mode_strategy.py`):**
```python
def _draw_mode_specific_hud(self, frame):
    # 랜드마크 시각화만 (약 10줄)
```

**변경 후 (`game_mode_strategy.py`):**
```python
def _draw_common_hud(self, frame):
    # 히트존 그리기 (약 20줄)
    # 점수/콤보 표시 (약 10줄)
    # 판정 통계 표시 (약 10줄)
    # 총 약 40줄 (공통 로직)
```

---

### 예시 3: BPM 연동 (Phase 3)

**변경 전 (`game_scene.py`):**
```python
# 비선형 스케일링
reference_bpm = 60.0
bpm_scale = (reference_bpm / max(1.0, bpm)) ** 0.7
bpm_scale = max(0.5, min(2.0, bpm_scale))

base_timing = self.config_difficulty.get("judge_timing_base", {...})
self.judge_timing = {k: v * scale * bpm_scale for k, v in base_timing.items()}
```

**변경 후 (`game_scene.py`):**
```python
# 박자 단위 → 초 단위 변환
seconds_per_beat = 60.0 / max(1e-6, bpm)
base_timing_beats = self.config_difficulty.get("judge_timing_base_beats", {...})
for key, beats in base_timing_beats.items():
    if key.endswith("_beats"):
        seconds = beats * seconds_per_beat
        timing_key = key.replace("_beats", "")
        self.judge_timing[timing_key] = seconds * scale
```

---

## 개선 효과

### 📊 코드 라인 수 변화

| 파일 | 변경 전 | 변경 후 | 변화 |
|:---|:---:|:---:|:---:|
| `game_scene.py` | 888줄 | ~688줄 | -200줄 (-22.5%) |
| `pose_tracker.py` | 241줄 | ~441줄 | +200줄 (+83.0%) |
| `game_mode_strategy.py` | 40줄 | ~120줄 | +80줄 (+200.0%) |
| `normal_mode_strategy.py` | 187줄 | ~137줄 | -50줄 (-26.7%) |
| `test_mode_strategy.py` | 267줄 | ~197줄 | -70줄 (-26.2%) |
| **전체** | **~1,623줄** | **~1,583줄** | **-40줄 (-2.5%)** |

### 🎯 모듈 책임 분리

**Before:**
- `GameScene`: 모든 계산 로직 포함 (랜드마크 스무딩, 주먹 중심점, 캘리브레이션)
- `PoseTracker`: 이벤트 생성만 담당
- `Strategy`: 읽기 전용 (self.game_scene을 통해 모든 데이터 접근)

**After:**
- `GameScene`: 게임 플레이 로직만 집중 (노트 스폰, 판정, 점수/콤보)
- `PoseTracker`: 포즈 관련 모든 데이터 처리 (랜드마크 스무딩, 주먹 중심점, 캘리브레이션)
- `Strategy`: 독립적으로 동작 (필요한 데이터만 받아서 처리)

### 🔧 유지보수성 향상

1. **코드 중복 제거**: 공통 HUD 로직이 한 곳에 집중
2. **모듈 독립성**: Strategy를 독립적으로 테스트 가능
3. **명확한 책임**: 각 모듈의 역할이 명확해짐
4. **설정 단순화**: 박자 단위 설정으로 BPM 변경이 자동 반영

### 🚀 확장성 향상

1. **새로운 모드 추가 용이**: `GameModeStrategy`를 상속받아 `_draw_mode_specific_hud()`만 구현
2. **랜드마크 처리 확장**: `PoseTracker`에 새로운 계산 로직 추가 용이
3. **BPM 변경 자동 대응**: 설정 파일만 수정하면 모든 타이밍이 자동 조정

---

## 마이그레이션 가이드

### ⚠️ 주의사항

1. **설정 파일 호환성**: `difficulty.json`의 키 이름이 변경됨
   - `judge_timing_base` → `judge_timing_base_beats`
   - `pre_spawn_time` → `pre_spawn_beats`
   - 단위가 초에서 박자로 변경됨

2. **기존 설정 값 변환 필요**:
   - 기존 설정을 박자 단위로 변환해야 함
   - 예: `pre_spawn_time: 1.2` (초) → `pre_spawn_beats: 2.0` (박자, BPM 60 기준)

3. **코드 의존성 변경**:
   - `GameScene`에서 `smoothed_landmark_pos` 직접 접근 불가
   - `pose_tracker.get_smoothed_landmarks()` 사용 필요
   - `GameScene`에서 `left_fist_center`, `right_fist_center` 직접 접근 불가
   - `pose_tracker.get_fist_centroids()` 사용 필요

### 📝 마이그레이션 체크리스트

- [ ] `difficulty.json` 파일 업데이트
  - [ ] `judge_timing_base` → `judge_timing_base_beats` 변경
  - [ ] `pre_spawn_time` → `pre_spawn_beats` 변경
  - [ ] 단위를 초에서 박자로 변환
- [ ] 코드에서 `smoothed_landmark_pos` 직접 접근 제거
- [ ] 코드에서 `left_fist_center`, `right_fist_center` 직접 접근 제거
- [ ] `PoseTracker` 메서드 사용으로 변경
- [ ] 테스트: 랜드마크 스무딩이 정상 동작하는지 확인
- [ ] 테스트: 주먹 중심점 계산이 정상 동작하는지 확인
- [ ] 테스트: 캘리브레이션이 정상 동작하는지 확인
- [ ] 테스트: BPM 변경 시 타이밍이 자동 조정되는지 확인
- [ ] 테스트: 일반 모드와 테스트 모드가 정상 동작하는지 확인

### 🔄 설정 값 변환 예시

**BPM 60 기준:**
- `pre_spawn_time: 1.2` (초) → `pre_spawn_beats: 2.0` (박자)
- `judge_timing_base.perfect: 0.5` (초) → `judge_timing_base_beats.perfect_beats: 0.5` (박자)

**BPM 120 기준:**
- `pre_spawn_time: 1.2` (초) → `pre_spawn_beats: 2.4` (박자)
- `judge_timing_base.perfect: 0.5` (초) → `judge_timing_base_beats.perfect_beats: 1.0` (박자)

**변환 공식:**
```
박자 = 초 / (60.0 / BPM)
```

---

## 완료된 작업 요약

### ✅ Phase 1: PoseTracker 역할 확장
- [x] 랜드마크 스무딩 속성 추가
- [x] 주먹 중심점 속성 추가
- [x] `get_smoothed_landmarks()` 메서드 구현
- [x] `get_fist_centroids()` 메서드 구현
- [x] `update_landmark_smoothing()` 메서드 구현
- [x] `calculate_fist_centroids()` 메서드 구현
- [x] `GameScene`에서 스무딩 로직 제거
- [x] `GameScene`에서 주먹 중심점 계산 로직 제거

### ✅ Phase 2: Strategy 패턴 재정립
- [x] `GameModeStrategy`에 `_draw_common_hud()` 추가
- [x] `draw_hud()` 템플릿 메서드로 변경
- [x] `normal_mode_strategy.py`에서 공통 로직 제거
- [x] `test_mode_strategy.py`에서 공통 로직 제거
- [x] `handle_hits()` 시그니처에 `**kwargs` 추가
- [x] `calculate_debug_info()` 제거

### ✅ Phase 3: BPM 연동 로직 개선
- [x] `difficulty.json`을 박자 단위로 변경
- [x] `game_scene.py`의 `__init__()`에서 박자→초 변환 로직 추가
- [x] BPM 스케일링 로직 제거

### ✅ Phase 4: 캘리브레이션 로직 이동
- [x] `pose_tracker.py`에 `check_calibration_position()` 추가
- [x] `game_scene.py`의 `_check_calib_position()` 제거
- [x] `game_scene.py`의 `update()`에서 `pose_tracker.check_calibration_position()` 호출

---

## 다음 단계 제안

### 🔮 추가 개선 가능 사항

1. **테스트 코드 작성**: Strategy를 독립적으로 테스트할 수 있는 단위 테스트 추가
2. **에러 처리 강화**: 예외 처리 및 로깅 개선
3. **성능 최적화**: 불필요한 계산 제거, 캐싱 활용
4. **코드 문서화**: 함수별 docstring 보완
5. **타입 힌트 추가**: Python 타입 힌트를 추가하여 코드 가독성 향상

---

**작성일**: 2024년
**버전**: 1.0
**리팩토링 완료일**: 현재

