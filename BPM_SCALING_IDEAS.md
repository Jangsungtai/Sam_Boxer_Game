# BPM 스케일링 아이디어 (30~100 BPM 범위)

## 문제점
현재 `difficulty.json`에서 BPM만 수정하면:
- 판정 시간(`judge_timing_base`)이 고정되어 있어서 BPM이 빠를수록 판정이 어려워짐
- 스폰 시간(`pre_spawn_time`)이 고정되어 있어서 BPM이 빠를수록 노트가 너무 빨리 등장함

## 해결 아이디어

### 아이디어 1: 선형 역비례 스케일링 (간단)
**개념**: BPM 60을 기준점으로 설정하고, BPM에 반비례하여 시간 값 조정

```
BPM 스케일 팩터 = 60 / BPM
적용 대상: judge_timing_base, pre_spawn_time
```

**예시**:
- BPM 30: 스케일 = 2.0 → 판정 시간 2배, 스폰 시간 2배 (느림)
- BPM 60: 스케일 = 1.0 → 기준값 (변화 없음)
- BPM 100: 스케일 = 0.6 → 판정 시간 0.6배, 스폰 시간 0.6배 (빠름)

**장점**: 간단하고 직관적
**단점**: BPM이 매우 빠르면 판정 시간이 너무 짧아짐

---

### 아이디어 2: 비선형 스케일링 (권장)
**개념**: BPM에 따라 지수적으로 스케일링하여 극단적인 변화를 완화

```
BPM 스케일 팩터 = (60 / BPM) ^ 0.7
적용 대상: judge_timing_base, pre_spawn_time
```

**예시**:
- BPM 30: 스케일 = (60/30)^0.7 = 1.62 → 판정 시간 1.62배
- BPM 60: 스케일 = 1.0 → 기준값
- BPM 100: 스케일 = (60/100)^0.7 = 0.72 → 판정 시간 0.72배

**장점**: 극단적인 BPM에서도 플레이 가능한 범위 유지
**단점**: 계산이 약간 복잡

---

### 아이디어 3: BPM 범위별 분류 (가장 안정적)
**개념**: BPM을 범위별로 나누어 각 범위에 적합한 스케일을 적용

```
BPM 30-50 (느림):   스케일 = 1.3 ~ 1.5
BPM 50-70 (보통):   스케일 = 0.9 ~ 1.1
BPM 70-100 (빠름):  스케일 = 0.7 ~ 0.9
```

**구현 방식**:
```python
if bpm < 50:
    bpm_scale = 1.5 - (bpm - 30) * 0.01  # 30일 때 1.5, 50일 때 1.3
elif bpm < 70:
    bpm_scale = 1.3 - (bpm - 50) * 0.02  # 50일 때 1.3, 70일 때 0.9
else:
    bpm_scale = 0.9 - (bpm - 70) * (0.0067)  # 70일 때 0.9, 100일 때 0.7
```

**장점**: 각 BPM 범위에서 최적화된 게임플레이
**단점**: 구현이 복잡

---

### 아이디어 4: 최소/최대 제한 + 스케일링 (권장)
**개념**: 아이디어 2 + 최소/최대 제한값 설정

```
BPM 스케일 팩터 = (60 / BPM) ^ 0.7
최소 스케일 = 0.5 (판정 시간이 절반 이하로 줄어들지 않음)
최대 스케일 = 2.0 (판정 시간이 2배 이상 늘어나지 않음)
```

**예시**:
- BPM 30: 스케일 = min(2.0, 1.62) = 1.62
- BPM 60: 스케일 = 1.0
- BPM 100: 스케일 = max(0.5, 0.72) = 0.72

**장점**: 극단적인 BPM에서도 플레이 가능한 범위 보장
**단점**: 계산이 약간 복잡

---

## 추천 구현 방식

**아이디어 4 (비선형 + 제한)**를 권장합니다.

### 구현 위치
`scenes/game_scene.py`의 `__init__` 메서드에서:
1. BPM 읽기 (이미 있음)
2. BPM 스케일 팩터 계산
3. `judge_timing_base`에 스케일 적용
4. `pre_spawn_time`에 스케일 적용

### 코드 구조
```python
# BPM 스케일링 계산
bpm = float(song_info.get("bpm", 120))
reference_bpm = 60.0  # 기준 BPM
bpm_scale = (reference_bpm / bpm) ** 0.7  # 비선형 스케일
bpm_scale = max(0.5, min(2.0, bpm_scale))  # 0.5 ~ 2.0 범위 제한

# 판정 시간에 스케일 적용
base_timing = self.config_difficulty.get("judge_timing_base", {...})
scale = self.difficulty.get("judge_timing_scale", 1.0)
self.judge_timing = {k: v * scale * bpm_scale for k, v in base_timing.items()}

# 스폰 시간에 스케일 적용
base_pre_spawn = self.difficulty["pre_spawn_time"]
self.pre_spawn_time = base_pre_spawn * bpm_scale
```

---

## 추가 고려사항

1. **디버그 정보 표시**: BPM 스케일 팩터를 화면에 표시하여 테스트 용이성 향상
2. **설정 파일 옵션**: `difficulty.json`에 `bpm_scaling_enabled` 플래그 추가 (선택적 사용)
3. **BPM 범위 경고**: BPM이 30 미만 또는 100 초과일 때 경고 메시지 표시

