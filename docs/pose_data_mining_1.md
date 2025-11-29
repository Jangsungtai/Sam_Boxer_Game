# 1단계: 고급자세 기준 정의

## 개요

1단계에서는 상급자 데이터를 분석하여 각 복싱 동작(포즈 타입)의 '정답'이 무엇인지를 수학적으로 정의합니다. 이를 위해 K-Means 클러스터링 기법을 사용하여 각 포즈 타입별 기준 포즈 벡터(Centroid)를 추출합니다.

## 목표

- 상급자 데이터에서 각 포즈 타입별 대표 포즈를 자동으로 추출
- 수학적으로 정의된 기준 포즈 벡터 생성
- 향후 사용자 포즈 평가의 기준점 제공

## 처리 과정

### 1. 데이터 로드 및 전처리

#### 1.1 CSV 파일 읽기
- 입력 파일: `data/pose_data/상급자 Sample1.csv`
- 전체 데이터: 약 320개 포즈 샘플
- 포즈 타입: GUARD, JAB_L, STRAIGHT_R, WEAVE_L, WEAVE_R

#### 1.2 포즈 타입별 데이터 분리
각 포즈 타입별로 데이터를 분리합니다:
- **GUARD**: 약 80개 샘플
- **JAB_L**: 약 80개 샘플
- **STRAIGHT_R**: 약 80개 샘플
- **WEAVE_L**: 약 40개 샘플
- **WEAVE_R**: 약 40개 샘플

#### 1.3 IQR 기반 이상치 제거
Interquartile Range (IQR) 방법을 사용하여 이상치를 제거합니다:

```
Q1 = 25번째 백분위수
Q3 = 75번째 백분위수
IQR = Q3 - Q1
하한 = Q1 - 1.5 × IQR
상한 = Q3 + 1.5 × IQR
```

각 변수에 대해 하한과 상한 범위를 벗어나는 데이터를 이상치로 간주하여 제거합니다.

**이상치 제거 결과 예시:**
- GUARD: 80개 → 63개 (17개 제거)
- JAB_L: 80개 → 61개 (19개 제거)
- STRAIGHT_R: 80개 → 67개 (13개 제거)
- WEAVE_L: 40개 → 22개 (18개 제거)
- WEAVE_R: 40개 → 21개 (19개 제거)

#### 1.4 변수 추출
다음 8개 변수를 사용합니다:
1. `left_fist_dist`: 왼손 거리 (정규화)
2. `left_fist_angle`: 왼손 각도
3. `right_fist_dist`: 오른손 거리 (정규화)
4. `right_fist_angle`: 오른손 각도
5. `left_arm_angle`: 왼팔 각도 (어깨-팔꿈치-손목)
6. `right_arm_angle`: 오른팔 각도 (어깨-팔꿈치-손목)
7. `nose_position`: 코 위치 (화면 중앙 기준, 정규화)
8. `nose_above_shoulder`: 코가 어깨 위에 있는지 여부 (0 또는 1)

### 2. 최적 K 탐색

#### 2.1 K-Means 클러스터링
각 포즈 타입별로 K=1, 2, 3에 대해 K-Means 클러스터링을 수행합니다.

- **K=1**: 단일 기준 포즈 정의 (모든 데이터를 하나의 클러스터로)
- **K=2**: 두 가지 스타일의 올바른 포즈 포괄
- **K=3**: 세 가지 스타일의 올바른 포즈 포괄

#### 2.2 Silhouette Score 계산
각 K 값에 대해 Silhouette Score를 계산하여 클러스터링 품질을 평가합니다.

**Silhouette Score 해석:**
- **-1 ~ 0**: 클러스터가 잘못 형성됨
- **0 ~ 0.5**: 클러스터가 약하게 형성됨
- **0.5 ~ 1**: 클러스터가 잘 형성됨

**K=1의 경우:**
- Silhouette Score를 계산할 수 없으므로 0.0으로 설정
- 단일 클러스터이므로 비교 기준으로만 사용

#### 2.3 최적 K 자동 선정
각 포즈 타입별로 가장 높은 Silhouette Score를 가진 K 값을 최적 K로 선정합니다.

**실제 분석 결과 예시:**
- **GUARD**: K=2 (Silhouette Score: 0.2654)
- **JAB_L**: K=2 (Silhouette Score: 0.6388)
- **STRAIGHT_R**: K=2 (Silhouette Score: 0.2875)
- **WEAVE_L**: K=2 (Silhouette Score: 0.5112)
- **WEAVE_R**: K=2 (Silhouette Score: 0.4275)

대부분의 포즈 타입에서 K=2가 최적값으로 선정되었으며, 이는 상급자들이 각 포즈를 수행할 때 두 가지 주요 스타일이 존재함을 의미합니다.

### 3. 기준 생성 및 저장

#### 3.1 Centroid 계산
선정된 최적 K의 클러스터 중심(Centroid)을 계산합니다.

- **K=1**: 단일 Centroid 벡터 (8개 변수의 평균값)
- **K>1**: 가장 큰 클러스터의 Centroid를 기준 포즈로 사용

#### 3.2 JSON 형식 저장
결과를 `data/pose_standards.json` 파일에 저장합니다.

**JSON 구조:**
```json
{
  "metadata": {
    "description": "상급자 데이터 기반 포즈 타입별 기준 포즈 벡터 (Centroid)",
    "data_source": "파일 경로",
    "variables": ["변수 목록"],
    "pose_types": ["포즈 타입 목록"]
  },
  "results": {
    "포즈타입": {
      "optimal_k": 최적K값,
      "k_results": {
        "1": {
          "silhouette_score": 점수,
          "centroid": [8개 변수 값],
          "inertia": 관성값
        },
        "2": { ... },
        "3": { ... }
      },
      "data_count": 데이터개수,
      "centroid": {
        "변수명": 값,
        ...
      }
    }
  }
}
```

**주요 필드 설명:**
- `optimal_k`: Silhouette Score로 선정된 최적 K 값
- `k_results`: K=1, 2, 3에 대한 모든 결과 (비교용)
- `centroid`: 최적 K의 기준 포즈 벡터 (8개 변수)
- `data_count`: 이상치 제거 후 데이터 개수

## 시각화 리포트

### 리포트 파일
1. `reports/pose_analysis.png`: 박스플롯 및 히스토그램
2. `reports/1.0_pose_radar_chart.png`: 전체 포즈 타입 정규화된 Centroid 패턴 레이더 차트
3. `reports/1.1_pose_radar_chart_guard.png`: GUARD 포즈 개별 레이더 차트
4. `reports/1.2_pose_radar_chart_jab_l.png`: JAB_L 포즈 개별 레이더 차트
5. `reports/1.3_pose_radar_chart_straight_r.png`: STRAIGHT_R 포즈 개별 레이더 차트
6. `reports/1.4_pose_radar_chart_weave_l.png`: WEAVE_L 포즈 개별 레이더 차트
7. `reports/1.5_pose_radar_chart_weave_r.png`: WEAVE_R 포즈 개별 레이더 차트
8. `reports/2.0_pose_radar_chart.png`: 초심자 데이터 전체 포즈 타입 레이더 차트
9. `reports/2.1_pose_radar_chart_guard.png`: 초심자 GUARD 포즈 개별 레이더 차트
10. `reports/2.2_pose_radar_chart_jab_l.png`: 초심자 JAB_L 포즈 개별 레이더 차트
11. `reports/2.3_pose_radar_chart_straight_r.png`: 초심자 STRAIGHT_R 포즈 개별 레이더 차트
12. `reports/2.4_pose_radar_chart_weave_l.png`: 초심자 WEAVE_L 포즈 개별 레이더 차트
13. `reports/2.5_pose_radar_chart_weave_r.png`: 초심자 WEAVE_R 포즈 개별 레이더 차트
14. `reports/3.1_pose_radar_chart_comparison_guard.png`: 상급자 vs 초심자 GUARD 비교 레이더 차트
15. `reports/3.2_pose_radar_chart_comparison_jab_l.png`: 상급자 vs 초심자 JAB_L 비교 레이더 차트
16. `reports/3.3_pose_radar_chart_comparison_straight_r.png`: 상급자 vs 초심자 STRAIGHT_R 비교 레이더 차트
17. `reports/3.4_pose_radar_chart_comparison_weave_l.png`: 상급자 vs 초심자 WEAVE_L 비교 레이더 차트
18. `reports/3.5_pose_radar_chart_comparison_weave_r.png`: 상급자 vs 초심자 WEAVE_R 비교 레이더 차트

### 시각화 내용

#### 1. 레이더 차트 (Radar Chart)
각 포즈 타입별 정규화된 Centroid 패턴을 원형 차트로 시각화합니다.

**레이더 차트 종류:**
- **전체 레이더 차트** (`1.0_pose_radar_chart.png`): 모든 포즈 타입을 한 번에 비교
- **개별 레이더 차트**: 각 포즈 타입별로 별도 파일 생성
  - `1.1_pose_radar_chart_guard.png`: GUARD
  - `1.2_pose_radar_chart_jab_l.png`: JAB_L
  - `1.3_pose_radar_chart_straight_r.png`: STRAIGHT_R
  - `1.4_pose_radar_chart_weave_l.png`: WEAVE_L
  - `1.5_pose_radar_chart_weave_r.png`: WEAVE_R

**레이더 차트 특징:**
- 8개 변수를 원형으로 배치
- 각 포즈 타입을 다른 색상으로 표시
- Min-Max 정규화 (0-1 범위)를 적용하여 변수 간 비교 가능
- 포즈 타입 간 패턴 차이를 한눈에 파악 가능

**레이더 차트 해석:**
- **전체 차트**: 모든 포즈 타입을 한 번에 비교하여 그룹화 확인
  - **GUARD, JAB_L, STRAIGHT_R**: 유사한 패턴 (상단 오른쪽 영역에서 높은 값)
  - **WEAVE_L, WEAVE_R**: 유사한 패턴 (하단 영역에서 높은 값)
  - 두 그룹 간 명확한 차이 존재
- **개별 차트**: 각 포즈 타입의 세부 패턴을 독립적으로 분석 가능
- **비교 차트** (`3.X_pose_radar_chart_comparison_*.png`): 상급자와 초심자를 같은 차트에 표시
  - 상급자: 빨간색 선
  - 초심자: 파란색 선
  - 두 그룹 간 패턴 차이를 한눈에 비교 가능

#### 2. 박스플롯 및 히스토그램

#### 1. 박스플롯 (Box Plot)
각 포즈 타입별, 각 변수별로 데이터 분포를 박스플롯으로 표시합니다.

**박스플롯 해석:**
- **박스**: 25번째 백분위수(Q1) ~ 75번째 백분위수(Q3)
- **중간선**: 중앙값 (Median)
- **수염**: 최소값 ~ 최대값 (이상치 제외)
- **빨간 점선**: Centroid 값 (기준 포즈)

#### 3. 히스토그램 (Histogram)
각 포즈 타입별, 각 변수별로 데이터 분포를 히스토그램으로 표시합니다.

**히스토그램 해석:**
- **막대**: 각 구간의 데이터 빈도
- **빨간 점선**: Centroid 값 (기준 포즈)

### 시각화 활용 방법

1. **레이더 차트**:
   - 포즈 타입 간 패턴 비교
   - 각 변수의 상대적 중요도 파악
   - 포즈 그룹화 확인 (GUARD/JAB_L/STRAIGHT_R vs WEAVE_L/WEAVE_R)

2. **박스플롯**:
   - 각 변수가 어떤 범위에 분포하는지 확인
   - Centroid 위치 확인 (기준 포즈가 데이터 분포의 어디에 위치하는지)
   - 이상치 패턴 확인

3. **히스토그램**:
   - 데이터 분포의 형태 확인 (정규분포, 편향 등)
   - Centroid 위치 확인

4. **종합 분석**:
   - 서로 다른 포즈 타입 간 변수 분포 비교
   - 포즈 타입별 특징 파악

## 결과 활용 방법

### 1. 기준 포즈 벡터 사용
`pose_standards.json` 파일에서 각 포즈 타입의 `centroid` 값을 읽어 사용합니다.

```python
import json

with open('data/pose_standards.json', 'r', encoding='utf-8') as f:
    standards = json.load(f)

guard_centroid = standards['results']['GUARD']['centroid']
# guard_centroid = {
#     'left_fist_dist': 0.2599,
#     'left_fist_angle': 323.36,
#     ...
# }
```

### 2. 최적 K 값 확인
각 포즈 타입의 최적 K 값을 확인하여, 해당 포즈에 몇 가지 스타일이 있는지 파악할 수 있습니다.

### 3. K=1, 2, 3 결과 비교
`k_results` 필드를 통해 K=1, 2, 3에 대한 모든 결과를 비교할 수 있습니다.

## 초심자 데이터 분석

스크립트는 상급자 데이터 분석 후, 초심자 데이터도 자동으로 분석합니다.

### 초심자 데이터 처리 과정
1. **데이터 로드**: `data/pose_data/초심자 Sample1.csv`
2. **IQR 이상치 제거**: 상급자와 동일한 방법 적용
3. **K-Means 클러스터링**: 각 포즈 타입별 Centroid 계산
4. **레이더 차트 생성**: `2.0_pose_radar_chart.png`

### 초심자 vs 상급자 비교
- **1.0_pose_radar_chart.png**: 상급자 데이터 기준 포즈 패턴 (전체)
- **2.0_pose_radar_chart.png**: 초심자 데이터 기준 포즈 패턴 (전체)
- **1.X_pose_radar_chart_*.png**: 상급자 포즈별 개별 레이더 차트
- **2.X_pose_radar_chart_*.png**: 초심자 포즈별 개별 레이더 차트
- 두 차트를 비교하여 숙련도에 따른 포즈 패턴 차이를 확인할 수 있습니다.
- 예: `1.1_pose_radar_chart_guard.png` vs `2.1_pose_radar_chart_guard.png`로 GUARD 포즈의 숙련도 차이 비교

## 실행 방법

```bash
python scripts/step1_define_pose_centroid.py
```

스크립트는 자동으로 상급자와 초심자 데이터를 모두 분석합니다.

## 출력 파일

1. **data/pose_standards.json**: 기준 포즈 벡터 및 분석 결과
2. **reports/pose_analysis.png**: 포즈 타입별 변수 분포 시각화 (박스플롯 + 히스토그램)
3. **reports/1.0_pose_radar_chart.png**: 전체 포즈 타입 정규화된 Centroid 패턴 레이더 차트
4. **reports/1.1_pose_radar_chart_guard.png**: GUARD 포즈 개별 레이더 차트
5. **reports/1.2_pose_radar_chart_jab_l.png**: JAB_L 포즈 개별 레이더 차트
6. **reports/1.3_pose_radar_chart_straight_r.png**: STRAIGHT_R 포즈 개별 레이더 차트
7. **reports/1.4_pose_radar_chart_weave_l.png**: WEAVE_L 포즈 개별 레이더 차트
8. **reports/1.5_pose_radar_chart_weave_r.png**: WEAVE_R 포즈 개별 레이더 차트
9. **reports/2.0_pose_radar_chart.png**: 초심자 데이터 전체 포즈 타입 레이더 차트
10. **reports/2.1_pose_radar_chart_guard.png**: 초심자 GUARD 포즈 개별 레이더 차트
11. **reports/2.2_pose_radar_chart_jab_l.png**: 초심자 JAB_L 포즈 개별 레이더 차트
12. **reports/2.3_pose_radar_chart_straight_r.png**: 초심자 STRAIGHT_R 포즈 개별 레이더 차트
13. **reports/2.4_pose_radar_chart_weave_l.png**: 초심자 WEAVE_L 포즈 개별 레이더 차트
14. **reports/2.5_pose_radar_chart_weave_r.png**: 초심자 WEAVE_R 포즈 개별 레이더 차트
15. **reports/3.1_pose_radar_chart_comparison_guard.png**: 상급자 vs 초심자 GUARD 비교 레이더 차트
16. **reports/3.2_pose_radar_chart_comparison_jab_l.png**: 상급자 vs 초심자 JAB_L 비교 레이더 차트
17. **reports/3.3_pose_radar_chart_comparison_straight_r.png**: 상급자 vs 초심자 STRAIGHT_R 비교 레이더 차트
18. **reports/3.4_pose_radar_chart_comparison_weave_l.png**: 상급자 vs 초심자 WEAVE_L 비교 레이더 차트
19. **reports/3.5_pose_radar_chart_comparison_weave_r.png**: 상급자 vs 초심자 WEAVE_R 비교 레이더 차트

## 주의사항

1. **소규모 데이터셋**: 현재 약 320개 샘플로 구성된 소규모 데이터셋이므로, 향후 더 많은 데이터가 수집되면 결과가 개선될 수 있습니다.

2. **K=1 vs K>1**: 
   - K=1은 단일 기준 포즈를 의미합니다.
   - K>1은 여러 스타일의 올바른 포즈가 존재함을 의미합니다.
   - 최적 K가 2 이상인 경우, 가장 큰 클러스터의 Centroid를 기준으로 사용합니다.

3. **이상치 제거**: IQR 방법으로 이상치를 제거하지만, 일부 유효한 데이터도 제거될 수 있습니다. 필요시 이상치 제거 기준을 조정할 수 있습니다.

4. **변수 스케일**: 모든 변수가 동일한 스케일을 가지지 않으므로, 필요시 정규화를 고려할 수 있습니다.

## 다음 단계

1단계에서 생성된 기준 포즈 벡터는 다음 단계에서 사용됩니다:
- **2단계**: 평가항목 정의 (변수 중요도 추출)
- **3단계**: 포즈품질 습관 평가 (가중 유클리드 거리 계산)

## 참고 자료

- K-Means Clustering: [scikit-learn 문서](https://scikit-learn.org/stable/modules/clustering.html#k-means)
- Silhouette Score: [scikit-learn 문서](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html)
- IQR 이상치 제거: [Wikipedia - Interquartile Range](https://en.wikipedia.org/wiki/Interquartile_range)

---

## 1단계 결과 요약: 포즈 타입별 기준 벡터 (Centroid)

### 개요

1단계 K-Means 클러스터링을 통해 상급자 데이터로부터 각 포즈 타입별 기준 포즈 벡터(Centroid)를 추출했습니다. 이 벡터들은 각 포즈 타입의 "정답"으로 사용됩니다.

### 분석 결과 요약

| 포즈 타입 | 최적 K | Silhouette Score | 데이터 개수 | 기준 벡터 파일 |
|----------|--------|------------------|-------------|---------------|
| GUARD | 2 | 0.2654 | 63 | `data/pose_standards.json` |
| JAB_L | 2 | 0.6388 | 61 | `data/pose_standards.json` |
| STRAIGHT_R | 2 | 0.2875 | 67 | `data/pose_standards.json` |
| WEAVE_L | 2 | 0.5112 | 22 | `data/pose_standards.json` |
| WEAVE_R | 2 | 0.4275 | 21 | `data/pose_standards.json` |

**주요 발견:**
- 모든 포즈 타입에서 K=2가 최적값으로 선정됨
- 이는 상급자들 사이에도 두 가지 주요 스타일이 존재함을 의미
- 가장 큰 클러스터의 Centroid를 기준 포즈로 사용

### 포즈 타입별 기준 벡터 (Centroid)

#### 1. GUARD (가드) 포즈 기준 벡터

**최적 K**: 2  
**Silhouette Score**: 0.2654  
**데이터 개수**: 63개 (이상치 제거 후)

**기준 벡터 (Centroid)**:
```
GUARD_Centroid = {
    'left_fist_dist': 0.2599,
    'left_fist_angle': 323.36°,
    'right_fist_dist': 0.4489,
    'right_fist_angle': 126.24°,
    'left_arm_angle': 3.53°,
    'right_arm_angle': 9.98°,
    'nose_position': 0.027,
    'nose_above_shoulder': 1.0
}
```

**벡터 형태**:
```
[0.2599, 323.36, 0.4489, 126.24, 3.53, 9.98, 0.027, 1.0]
```

**해석**:
- 왼손과 오른손이 얼굴 근처에 위치 (거리: 0.26, 0.45)
- 왼손 각도: 323.36° (얼굴 왼쪽)
- 오른손 각도: 126.24° (얼굴 오른쪽)
- 양팔 각도가 작음 (3.53°, 9.98°) → 팔이 구부러진 상태
- 코 위치: 거의 중앙 (0.027)
- 코가 어깨 위에 있음 (1.0)

#### 2. JAB_L (왼손 잽) 포즈 기준 벡터

**최적 K**: 2  
**Silhouette Score**: 0.6388  
**데이터 개수**: 61개 (이상치 제거 후)

**기준 벡터 (Centroid)**:
```
JAB_L_Centroid = {
    'left_fist_dist': 0.2704,
    'left_fist_angle': 320.16°,
    'right_fist_dist': 0.5981,
    'right_fist_angle': 107.61°,
    'left_arm_angle': 3.05°,
    'right_arm_angle': 143.06°,
    'nose_position': -0.064,
    'nose_above_shoulder': 1.0
}
```

**해석**:
- 왼손이 앞으로 뻗어있음 (거리: 0.27)
- 오른손이 더 멀리 위치 (거리: 0.60) → 가드 유지
- 오른팔 각도가 큼 (143.06°) → 오른팔이 펴진 상태
- 왼팔 각도가 작음 (3.05°) → 왼팔이 구부러진 상태

#### 3. STRAIGHT_R (오른손 스트레이트) 포즈 기준 벡터

**최적 K**: 2  
**Silhouette Score**: 0.2875  
**데이터 개수**: 67개 (이상치 제거 후)

**기준 벡터 (Centroid)**:
```
STRAIGHT_R_Centroid = {
    'left_fist_dist': 0.2801,
    'left_fist_angle': 316.55°,
    'right_fist_dist': 0.5310,
    'right_fist_angle': 121.44°,
    'left_arm_angle': 4.92°,
    'right_arm_angle': 13.77°,
    'nose_position': 0.014,
    'nose_above_shoulder': 1.0
}
```

**해석**:
- 오른손이 앞으로 뻗어있음 (거리: 0.53)
- 왼손은 가드 위치 유지 (거리: 0.28)
- 양팔 각도가 상대적으로 작음 → 팔이 구부러진 상태

#### 4. WEAVE_L (위빙 좌) 포즈 기준 벡터

**최적 K**: 2  
**Silhouette Score**: 0.5112  
**데이터 개수**: 22개 (이상치 제거 후)

**기준 벡터 (Centroid)**:
```
WEAVE_L_Centroid = {
    'left_fist_dist': 0.7774,
    'left_fist_angle': 81.34°,
    'right_fist_dist': 0.2806,
    'right_fist_angle': 249.99°,
    'left_arm_angle': 133.22°,
    'right_arm_angle': 31.08°,
    'nose_position': -0.038,
    'nose_above_shoulder': 1.0
}
```

**해석**:
- 왼손이 멀리 위치 (거리: 0.78) → 왼쪽으로 기울임
- 왼팔 각도가 큼 (133.22°) → 왼팔이 펴진 상태
- 오른손은 가드 유지 (거리: 0.28)
- 코 위치가 약간 왼쪽 (-0.038)

#### 5. WEAVE_R (위빙 우) 포즈 기준 벡터

**최적 K**: 2  
**Silhouette Score**: 0.4275  
**데이터 개수**: 21개 (이상치 제거 후)

**기준 벡터 (Centroid)**:
```
WEAVE_R_Centroid = {
    'left_fist_dist': 0.6025,
    'left_fist_angle': 77.78°,
    'right_fist_dist': 0.1791,
    'right_fist_angle': 191.87°,
    'left_arm_angle': 113.14°,
    'right_arm_angle': 27.31°,
    'nose_position': -0.013,
    'nose_above_shoulder': 1.0
}
```

**해석**:
- 오른손이 멀리 위치 (거리: 0.18) → 오른쪽으로 기울임
- 왼손도 멀리 위치 (거리: 0.60)
- 양팔 각도가 큼 (113.14°, 27.31°) → 팔이 펴진 상태
- 코 위치가 약간 왼쪽 (-0.013)

### 벡터 활용 방법

각 포즈 타입의 기준 벡터는 `data/pose_standards.json` 파일에 저장되어 있으며, 다음과 같이 사용할 수 있습니다:

```python
import json

# 기준 벡터 로드
with open('data/pose_standards.json', 'r', encoding='utf-8') as f:
    standards = json.load(f)

# GUARD 포즈의 기준 벡터
guard_centroid = standards['results']['GUARD']['centroid']
# guard_centroid = {
#     'left_fist_dist': 0.2599,
#     'left_fist_angle': 323.36,
#     ...
# }

# 사용자 포즈와 비교
user_pose = {
    'left_fist_dist': 0.28,
    'left_fist_angle': 325.0,
    ...
}

# 가중 유클리드 거리 계산 (3단계에서 사용)
distance = calculate_weighted_distance(user_pose, guard_centroid, weights)
```

### 시각화

각 포즈 타입의 기준 벡터는 레이더 차트로 시각화되어 있습니다:
- `reports/1.1_pose_radar_chart_guard.png`: GUARD 포즈 기준 벡터
- `reports/1.2_pose_radar_chart_jab_l.png`: JAB_L 포즈 기준 벡터
- `reports/1.3_pose_radar_chart_straight_r.png`: STRAIGHT_R 포즈 기준 벡터
- `reports/1.4_pose_radar_chart_weave_l.png`: WEAVE_L 포즈 기준 벡터
- `reports/1.5_pose_radar_chart_weave_r.png`: WEAVE_R 포즈 기준 벡터

### 결론

1단계 K-Means 클러스터링을 통해 상급자 데이터로부터 5가지 포즈 타입별 기준 벡터를 성공적으로 추출했습니다. 이 벡터들은 다음 단계에서 사용자 포즈 평가의 기준점으로 활용됩니다.

