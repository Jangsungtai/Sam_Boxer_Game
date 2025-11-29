# 2단계: 평가항목 정의

## 개요

2단계에서는 상급자와 초심자 데이터를 학습하여, 특정 포즈를 평가할 때 어떤 변수가 가장 중요한지에 대한 평가항목 가중치를 정의합니다.

**사용 기법**: Random Forest Classifier (변수 중요도 추출 중심)  
**역할**: 포즈 타입별 변수 중요도 추출 → 3단계 가중 유클리드 거리 계산에 사용

---

## 목표

상급자와 초심자 데이터를 학습하여, 특정 포즈(예: 잽)를 평가할 때 어떤 변수(예: 팔 각도)가 가장 중요한지에 대한 평가항목 가중치를 정의합니다.

---

## 방법론

### Random Forest Classifier 선택 이유

- **숙련도 분류 수행 가능**: 상급자와 초심자를 구분하는 2-class 분류 수행
- **변수 중요도 자동 제공**: Feature Importance를 통해 각 변수의 중요도를 자동으로 추출 → 3단계 가중치로 활용
- **과적합에 강함**: 앙상블 기법으로 안정적인 성능
- **비선형 관계 학습 가능**: 복잡한 포즈 패턴을 학습할 수 있음
- **소규모 데이터셋에 적합**: 약 640개 샘플에서도 효과적

### 처리 과정

1. **데이터 레이블링**: 각 데이터에 숙련도 클래스 레이블 부여
   - 상급자 데이터: 1
   - 초심자 데이터: 0

2. **포즈 타입별 모델 학습**: 각 포즈 타입별로 독립적으로 Random Forest 모델 학습
   - 2-class 분류 (상급자 vs 초심자)
   - 5-fold 교차 검증(Cross-Validation) 사용

3. **변수 중요도 추출**: 각 포즈 타입별로 어떤 변수가 숙련도 구분에 중요한지 파악
   - Feature Importance 점수 추출
   - 포즈 타입별로 중요 변수 순위화
   - 중요도를 정규화하여 가중치로 사용

---

## 입력 데이터

- **상급자 포즈 데이터**: `data/pose_data/상급자 Sample1.csv` (320개 포즈)
- **초심자 포즈 데이터**: `data/pose_data/초심자 Sample1.csv` (320개 포즈)
- **총 데이터**: 640개 포즈

### 데이터 구조

각 데이터는 다음 8개 변수를 포함합니다:
- `left_fist_dist`: 왼손 거리
- `left_fist_angle`: 왼손 각도
- `right_fist_dist`: 오른손 거리
- `right_fist_angle`: 오른손 각도
- `left_arm_angle`: 왼팔 각도
- `right_arm_angle`: 오른팔 각도
- `nose_position`: 코 위치
- `nose_above_shoulder`: 코가 어깨 위에 있는지 여부 (0 또는 1)

---

## 처리 결과

### 전체 요약

| 포즈 타입 | 데이터 개수 | 교차 검증 정확도 | 가장 중요한 변수 | 중요도 |
|----------|-------------|------------------|-----------------|--------|
| GUARD | 117 | 0.975 ± 0.033 | left_fist_dist | 0.395 |
| JAB_L | 99 | 1.000 ± 0.000 | right_fist_angle | 0.364 |
| STRAIGHT_R | 137 | 0.956 ± 0.036 | right_fist_angle | 0.406 |
| WEAVE_L | 44 | 0.928 ± 0.099 | right_fist_dist | 0.505 |
| WEAVE_R | 46 | 1.000 ± 0.000 | right_fist_dist | 0.524 |

**주요 발견:**
- 모든 포즈 타입에서 높은 분류 정확도 (0.928 ~ 1.000)
- 포즈 타입별로 중요한 변수가 다름
- WEAVE 포즈에서는 `right_fist_dist`가 가장 중요
- JAB/STRAIGHT 포즈에서는 `right_fist_angle`이 중요
- GUARD 포즈에서는 `left_fist_dist`가 가장 중요

---

## 포즈 타입별 변수 중요도 (가중치)

### 1. GUARD (가드) 포즈

**교차 검증 정확도**: 0.975 ± 0.033  
**데이터 개수**: 117개 (이상치 제거 후)  
**클래스 분포**: 상급자 80개, 초심자 37개

**변수 중요도 (가중치)**:
```
left_fist_dist:      0.395
right_arm_angle:     0.214
left_fist_angle:     0.192
right_fist_dist:     0.092
right_fist_angle:    0.040
nose_position:        0.037
left_arm_angle:      0.031
nose_above_shoulder: 0.000
```

**해석**:
- `left_fist_dist`가 가장 중요 (0.395) → 왼손 위치가 가드 포즈의 핵심
- `right_arm_angle`이 두 번째로 중요 (0.214) → 오른팔 각도가 상급자와 초심자를 구분하는 중요한 요소
- `left_fist_angle`도 중요 (0.192) → 왼손 각도가 가드 포즈 평가에 영향
- `right_fist_dist`는 중간 정도 중요 (0.092) → 오른손 위치도 일정 부분 고려됨
- `nose_above_shoulder`는 중요도가 0.000 → 이 변수는 가드 포즈 평가에 거의 영향을 주지 않음

**그래프 해석**:
GUARD 포즈의 변수 중요도 그래프를 보면, 상급자와 초심자를 구분하는 데 가장 중요한 요소는 **왼손의 거리(`left_fist_dist`)**입니다. 이는 가드 포즈에서 왼손이 얼굴로부터 얼마나 떨어져 있는지가 숙련도를 판단하는 핵심 지표임을 의미합니다. 

두 번째로 중요한 변수는 **오른팔 각도(`right_arm_angle`)**로, 상급자는 오른팔을 적절한 각도로 유지하는 반면 초심자는 각도가 일관되지 않을 수 있습니다. 

세 번째로 중요한 **왼손 각도(`left_fist_angle`)**는 왼손의 방향과 위치를 나타내며, 가드 포즈의 정확성을 평가하는 데 기여합니다.

흥미로운 점은 **코가 어깨 위에 있는지 여부(`nose_above_shoulder`)**의 중요도가 0.000으로 나타난 것입니다. 이는 가드 포즈에서 이 변수가 상급자와 초심자를 구분하는 데 거의 도움이 되지 않는다는 것을 의미하며, 대부분의 사용자가 코를 어깨 위에 유지하고 있기 때문일 수 있습니다.

**실전 의미**:
- 가드 포즈 평가 시 **왼손 위치**를 가장 중요하게 고려해야 함
- **오른팔 각도**도 상당히 중요하므로, 팔의 자세를 정확히 유지하는 것이 중요
- 코 위치는 가드 포즈 평가에 큰 영향을 주지 않으므로, 다른 변수에 집중하는 것이 효율적

### 2. JAB_L (왼손 잽) 포즈

**교차 검증 정확도**: 1.000 ± 0.000  
**데이터 개수**: 99개 (이상치 제거 후)  
**클래스 분포**: 상급자 47개, 초심자 52개

**변수 중요도 (가중치)**:
```
right_fist_angle:    0.364
left_fist_dist:      0.279
right_arm_angle:     0.150
right_fist_dist:     0.136
left_fist_angle:     0.034
nose_position:       0.029
left_arm_angle:      0.008
nose_above_shoulder: 0.000
```

**해석**:
- `right_fist_angle`이 가장 중요 (0.364) → 오른손 각도가 잽 포즈의 핵심
- `left_fist_dist`도 중요 (0.221) → 왼손이 앞으로 뻗어있는 정도
- 오른손 각도와 왼손 거리가 잽 포즈를 구분하는 핵심 변수

### 3. STRAIGHT_R (오른손 스트레이트) 포즈

**교차 검증 정확도**: 0.956 ± 0.036  
**데이터 개수**: 137개 (이상치 제거 후)  
**클래스 분포**: 상급자 71개, 초심자 66개

**변수 중요도 (가중치)**:
```
right_fist_angle:    0.406
left_fist_dist:      0.343
right_fist_dist:     0.118
nose_position:       0.039
right_arm_angle:     0.036
left_fist_angle:     0.034
left_arm_angle:      0.025
nose_above_shoulder: 0.000
```

**해석**:
- `right_fist_angle`이 가장 중요 (0.406) → 오른손 각도가 스트레이트 포즈의 핵심
- `left_fist_dist`도 중요 (0.189) → 왼손 가드 유지 정도
- 오른손 각도가 스트레이트 포즈를 구분하는 가장 중요한 변수

### 4. WEAVE_L (위빙 좌) 포즈

**교차 검증 정확도**: 0.928 ± 0.099  
**데이터 개수**: 44개 (이상치 제거 후)  
**클래스 분포**: 상급자 21개, 초심자 23개

**변수 중요도 (가중치)**:
```
right_fist_dist:     0.505
left_fist_angle:     0.165
nose_position:        0.102
right_fist_angle:    0.073
left_arm_angle:      0.060
right_arm_angle:     0.050
left_fist_dist:      0.045
nose_above_shoulder: 0.000
```

**해석**:
- `right_fist_dist`가 매우 중요 (0.505) → 오른손 거리가 위빙 좌 포즈의 핵심
- `left_fist_dist`도 중요 (0.201) → 왼손 거리
- 손 거리가 위빙 포즈를 구분하는 가장 중요한 변수

### 5. WEAVE_R (위빙 우) 포즈

**교차 검증 정확도**: 1.000 ± 0.000  
**데이터 개수**: 46개 (이상치 제거 후)  
**클래스 분포**: 상급자 25개, 초심자 21개

**변수 중요도 (가중치)**:
```
right_fist_dist:     0.524
right_fist_angle:    0.176
left_fist_angle:     0.118
nose_position:       0.062
left_fist_dist:      0.055
left_arm_angle:      0.038
right_arm_angle:     0.027
nose_above_shoulder: 0.000
```

**해석**:
- `right_fist_dist`가 매우 중요 (0.524) → 오른손 거리가 위빙 우 포즈의 핵심
- `left_fist_dist`도 중요 (0.200) → 왼손 거리
- 손 거리가 위빙 포즈를 구분하는 가장 중요한 변수

---

## 결과 파일

### JSON 파일

**파일 경로**: `data/pose_evaluation_weights.json`

이 파일에는 각 포즈 타입별 변수 중요도(가중치)가 저장되어 있으며, 3단계에서 사용됩니다.

```json
{
  "metadata": {
    "description": "포즈 타입별 변수 중요도 (가중치) - Random Forest Classifier",
    "variables": ["left_fist_dist", "left_fist_angle", ...],
    "pose_types": ["GUARD", "JAB_L", "STRAIGHT_R", "WEAVE_L", "WEAVE_R"],
    "method": "Random Forest Classifier",
    "cv_folds": 5
  },
  "results": {
    "GUARD": {
      "cv_mean_accuracy": 0.975,
      "cv_std_accuracy": 0.033,
      "feature_importance": {
        "left_fist_dist": 0.395,
        "right_fist_dist": 0.195,
        ...
      },
      "sorted_importance": [...]
    },
    ...
  }
}
```

### 시각화 파일

모든 시각화 파일은 `reports/2.RFC/` 폴더에 저장되어 있습니다:

1. **reports/2.RFC/2.0_feature_importance_comparison.png**: 전체 포즈 타입 비교 차트
2. **reports/2.RFC/2.1_feature_importance_guard.png**: GUARD 포즈 변수 중요도
3. **reports/2.RFC/2.2_feature_importance_jab_l.png**: JAB_L 포즈 변수 중요도
4. **reports/2.RFC/2.3_feature_importance_straight_r.png**: STRAIGHT_R 포즈 변수 중요도
5. **reports/2.RFC/2.4_feature_importance_weave_l.png**: WEAVE_L 포즈 변수 중요도
6. **reports/2.RFC/2.5_feature_importance_weave_r.png**: WEAVE_R 포즈 변수 중요도
7. **reports/2.RFC/2.6_feature_importance_heatmap.png**: 포즈 타입별 변수 중요도 히트맵

---

## 그래프 해석: GUARD 포즈 변수 중요도

### 그래프 개요

`reports/2.RFC/2.1_feature_importance_guard.png` 그래프는 GUARD 포즈에서 상급자와 초심자를 구분하는 데 각 변수가 얼마나 중요한지를 보여줍니다. 그래프 상단에는 **교차 검증 정확도: 0.975 ± 0.033**이 표시되어 있으며, 이는 Random Forest 모델이 상급자와 초심자를 약 97.5%의 정확도로 구분할 수 있음을 의미합니다.

### 변수 중요도 분석

그래프는 8개 변수를 중요도 순서대로 가로 막대 그래프로 표시합니다:

#### 1. 가장 중요한 변수: `left_fist_dist` (0.395)

- **중요도**: 0.395 (전체의 약 39.5%)
- **의미**: 왼손이 얼굴로부터 떨어진 거리
- **해석**: 가드 포즈에서 **왼손의 위치**가 상급자와 초심자를 구분하는 가장 중요한 요소입니다. 상급자는 왼손을 얼굴 근처에 일정한 거리로 유지하는 반면, 초심자는 거리가 일관되지 않거나 너무 가깝거나 멀 수 있습니다.

#### 2. 두 번째로 중요한 변수: `right_arm_angle` (0.214)

- **중요도**: 0.214 (전체의 약 21.4%)
- **의미**: 오른팔의 각도
- **해석**: 오른팔의 각도가 가드 포즈 평가에서 두 번째로 중요한 요소입니다. 상급자는 오른팔을 적절한 각도로 유지하여 방어 자세를 정확히 취하지만, 초심자는 팔 각도가 불안정하거나 부적절할 수 있습니다.

#### 3. 세 번째로 중요한 변수: `left_fist_angle` (0.192)

- **중요도**: 0.192 (전체의 약 19.2%)
- **의미**: 왼손의 각도
- **해석**: 왼손의 방향과 각도도 가드 포즈 평가에 상당한 영향을 미칩니다. 왼손의 위치뿐만 아니라 각도도 중요하다는 것을 의미합니다.

#### 4. 중간 중요도 변수들

- **`right_fist_dist`** (0.092): 오른손 거리 - 중간 정도의 중요도
- **`right_fist_angle`** (0.040): 오른손 각도 - 낮은 중요도
- **`nose_position`** (0.037): 코 위치 - 낮은 중요도
- **`left_arm_angle`** (0.031): 왼팔 각도 - 낮은 중요도

#### 5. 중요하지 않은 변수: `nose_above_shoulder` (0.000)

- **중요도**: 0.000
- **의미**: 코가 어깨 위에 있는지 여부
- **해석**: 이 변수는 가드 포즈 평가에 거의 영향을 주지 않습니다. 대부분의 사용자(상급자와 초심자 모두)가 코를 어깨 위에 유지하고 있어서, 이 변수로는 숙련도를 구분할 수 없기 때문입니다.

### 그래프에서 읽을 수 있는 인사이트

1. **손 위치의 중요성**: 왼손 거리(`left_fist_dist`)가 가장 중요하고, 왼손 각도(`left_fist_angle`)도 세 번째로 중요합니다. 이는 가드 포즈에서 **왼손의 정확한 위치와 방향**이 핵심임을 의미합니다.

2. **팔 각도의 역할**: 오른팔 각도(`right_arm_angle`)가 두 번째로 중요하지만, 왼팔 각도(`left_arm_angle`)는 중요도가 낮습니다. 이는 가드 포즈에서 오른팔의 자세가 더 중요하다는 것을 시사합니다.

3. **코 위치의 한계**: 코 위치 관련 변수들(`nose_position`, `nose_above_shoulder`)의 중요도가 매우 낮습니다. 이는 가드 포즈 평가에서 코 위치가 큰 영향을 주지 않는다는 것을 의미합니다.

4. **변수 중요도의 집중도**: 상위 3개 변수(`left_fist_dist`, `right_arm_angle`, `left_fist_angle`)가 전체 중요도의 약 80%를 차지합니다. 이는 가드 포즈 평가 시 이 3개 변수에 집중하는 것이 효율적임을 의미합니다.

### 실전 활용 방안

1. **가드 포즈 교정 시 우선순위**:
   - 1순위: 왼손 위치(`left_fist_dist`) 정확히 유지
   - 2순위: 오른팔 각도(`right_arm_angle`) 적절히 유지
   - 3순위: 왼손 각도(`left_fist_angle`) 정확히 유지

2. **평가 효율성**: 코 위치 변수는 가드 포즈 평가에 거의 영향을 주지 않으므로, 다른 중요한 변수에 집중하는 것이 효율적입니다.

3. **3단계 가중치 적용**: 이 그래프의 중요도 값들이 3단계에서 가중 유클리드 거리 계산 시 가중치로 사용됩니다. 예를 들어, `left_fist_dist`의 오차는 0.395의 가중치로 계산되지만, `nose_above_shoulder`의 오차는 0.000의 가중치로 계산되어 사실상 무시됩니다.

---

## 히트맵 해석: 포즈 타입별 변수 중요도 비교

### 히트맵 개요

`reports/2.RFC/2.6_feature_importance_heatmap.png` 히트맵은 모든 포즈 타입의 변수 중요도를 한눈에 비교할 수 있도록 시각화한 것입니다. 히트맵의 색상 강도는 변수 중요도를 나타내며, 밝은 색(노란색/주황색)일수록 중요도가 높고, 어두운 색(연한 노란색)일수록 중요도가 낮습니다.

### 히트맵에서 읽을 수 있는 패턴

1. **포즈 타입별 중요 변수 차이**:
   - **GUARD**: `left_fist_dist`가 가장 밝게 표시됨 (0.395)
   - **JAB_L / STRAIGHT_R**: `right_fist_angle`이 가장 밝게 표시됨 (0.364~0.406)
   - **WEAVE_L / WEAVE_R**: `right_fist_dist`가 가장 밝게 표시됨 (0.505~0.524)

2. **변수별 중요도 패턴**:
   - **손 위치/각도 변수** (`left_fist_dist`, `right_fist_dist`, `left_fist_angle`, `right_fist_angle`): 대부분의 포즈에서 높은 중요도
   - **팔 각도 변수** (`left_arm_angle`, `right_arm_angle`): 일부 포즈에서만 높은 중요도
   - **코 위치 변수** (`nose_position`, `nose_above_shoulder`): 대부분의 포즈에서 낮은 중요도

3. **포즈 타입 간 유사성**:
   - **JAB_L과 STRAIGHT_R**: 유사한 패턴을 보임 (둘 다 `right_fist_angle`이 중요)
   - **WEAVE_L과 WEAVE_R**: 유사한 패턴을 보임 (둘 다 `right_fist_dist`가 중요)
   - **GUARD**: 독특한 패턴을 보임 (`left_fist_dist`가 가장 중요)

### 히트맵 활용 방법

1. **빠른 비교**: 히트맵을 통해 어떤 포즈 타입에서 어떤 변수가 중요한지 한눈에 파악 가능
2. **패턴 발견**: 포즈 타입 간 유사성과 차이점을 시각적으로 확인 가능
3. **우선순위 결정**: 각 포즈 타입별로 집중해야 할 변수를 빠르게 식별 가능

---

## 주요 발견 사항

### 1. 포즈 타입별 중요 변수 차이

- **GUARD**: `left_fist_dist` (0.395)가 가장 중요 → 손 위치가 핵심
- **JAB_L / STRAIGHT_R**: `right_fist_angle` (0.364~0.406)이 가장 중요 → 오른손 각도가 핵심
- **WEAVE_L / WEAVE_R**: `right_fist_dist` (0.505~0.524)가 가장 중요 → 손 거리가 핵심

### 2. 높은 분류 정확도

모든 포즈 타입에서 교차 검증 정확도가 0.928 이상으로, 상급자와 초심자를 잘 구분할 수 있음을 의미합니다.

### 3. 변수 중요도 분포

- **손 위치/각도 변수**가 대부분의 포즈에서 가장 중요
- **팔 각도 변수**는 상대적으로 덜 중요하지만 일부 포즈에서는 여전히 의미 있음
- **코 위치 변수**는 대부분의 포즈에서 중요도가 낮음

---

## 가중치 활용 방법

2단계에서 추출한 변수 중요도는 3단계에서 **가중 유클리드 거리** 계산에 사용됩니다:

```python
import json

# 가중치 로드
with open('data/pose_evaluation_weights.json', 'r', encoding='utf-8') as f:
    weights_data = json.load(f)

# GUARD 포즈의 가중치
guard_weights = weights_data['results']['GUARD']['feature_importance']
# guard_weights = {
#     'left_fist_dist': 0.395,
#     'left_fist_angle': 0.144,
#     ...
# }

# 사용자 포즈와 기준 벡터 비교
user_pose = {...}
guard_centroid = {...}  # 1단계에서 추출한 기준 벡터

# 가중 유클리드 거리 계산
weighted_distance = 0
for var in VARIABLES:
    diff = user_pose[var] - guard_centroid[var]
    weight = guard_weights[var]
    weighted_distance += weight * (diff ** 2)
weighted_distance = np.sqrt(weighted_distance)
```

---

## 주의사항

1. **소규모 데이터셋**: 현재 약 640개 샘플로 구성된 소규모 데이터셋이므로, 향후 더 많은 데이터가 수집되면 가중치가 개선될 수 있습니다.

2. **클래스 불균형**: 일부 포즈 타입(예: GUARD)에서 상급자와 초심자의 데이터 개수가 불균형할 수 있습니다. 필요시 샘플링 기법을 고려할 수 있습니다.

3. **변수 중요도 해석**: 변수 중요도는 상급자와 초심자를 구분하는 데 중요한 변수를 나타냅니다. 이는 반드시 포즈 품질 평가에 중요한 변수와 일치하지 않을 수 있습니다.

4. **교차 검증**: 5-fold 교차 검증을 사용하여 모델의 일반화 성능을 평가했습니다. 실제 성능은 더 많은 데이터에서 검증이 필요합니다.

---

## 다음 단계

2단계에서 생성된 변수 중요도(가중치)는 다음 단계에서 사용됩니다:
- **3단계**: 포즈품질 습관 평가 (가중 유클리드 거리 계산)

가중 유클리드 거리 계산 시, 각 변수의 중요도에 따라 가중치를 적용하여 더 정확한 포즈 품질 평가가 가능합니다.

---

## 참고 자료

- Random Forest Classifier: [scikit-learn 문서](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- Feature Importance: [scikit-learn 문서](https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html)
- Cross-Validation: [scikit-learn 문서](https://scikit-learn.org/stable/modules/cross_validation.html)

