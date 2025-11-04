# GameScene 리팩토링 계획

## 현재 상황
- `game_scene.py`에 `test_mode` 분기가 22개 존재
- 판정 로직, 시각화, 디버그 정보 등 모든 곳에 분기 처리

## 리팩토링 옵션

### 옵션 1: 전략 패턴 (Strategy Pattern) - **추천**
**장점:**
- 코드 분리가 명확함
- 각 모드별 로직이 독립적으로 관리됨
- 테스트하기 쉬움
- 확장성이 좋음 (나중에 다른 모드 추가 가능)

**구조:**
```
GameScene (기본 클래스)
├── __init__에서 test_mode에 따라 Strategy 선택
├── _judge_strategy (TestModeStrategy 또는 NormalModeStrategy)
├── _handle_hits() → _judge_strategy.handle_hits()
├── _draw_hud() → _judge_strategy.draw_hud()
└── draw() → _judge_strategy.draw()
```

**파일 구조:**
- `scenes/game_scene.py` (기본 클래스)
- `scenes/game_mode_strategy.py` (추상 클래스)
- `scenes/test_mode_strategy.py` (테스트 모드)
- `scenes/normal_mode_strategy.py` (일반 모드)

---

### 옵션 2: 메서드 분리 (Method Extraction)
**장점:**
- 현재 구조를 크게 변경하지 않음
- 구현이 간단함
- 파일 수가 적음

**단점:**
- 분기 로직이 여전히 남아있음
- 클래스가 커짐

**구조:**
```
GameScene
├── _handle_hits_test()
├── _handle_hits_normal()
├── _draw_hud_test()
├── _draw_hud_normal()
└── 각 메서드에서 test_mode 체크 후 적절한 메서드 호출
```

---

### 옵션 3: 상속 구조 (Inheritance)
**장점:**
- 클래스 분리가 명확함
- 각 모드가 독립적인 클래스

**단점:**
- 공통 코드 중복 가능성
- 파일 수가 많아짐

**구조:**
```
GameSceneBase (추상 클래스)
├── TestGameScene
└── NormalGameScene
```

---

## 추천: 옵션 1 (전략 패턴)

### 구현 계획

1. **추상 전략 클래스 생성**
   - `GameModeStrategy` (추상 클래스)
   - `handle_hits()`, `draw_hud()`, `draw()` 등 추상 메서드

2. **구체적 전략 클래스 구현**
   - `TestModeStrategy`: 테스트 모드 전용 로직
   - `NormalModeStrategy`: 일반 모드 전용 로직

3. **GameScene 수정**
   - `__init__`에서 `test_mode`에 따라 Strategy 선택
   - 각 메서드에서 Strategy 위임

4. **공통 로직 처리**
   - 공통 로직은 `GameScene`에 유지
   - 모드별 차이만 Strategy로 분리

---

## 파일 구조 예시

```
scenes/
├── game_scene.py (기본 클래스, 공통 로직)
├── game_mode_strategy.py (추상 전략 클래스)
├── test_mode_strategy.py (테스트 모드 전략)
└── normal_mode_strategy.py (일반 모드 전략)
```

---

## 구현 예시

### game_mode_strategy.py
```python
from abc import ABC, abstractmethod

class GameModeStrategy(ABC):
    @abstractmethod
    def handle_hits(self, hit_events, t_game, now):
        pass
    
    @abstractmethod
    def draw_hud(self, frame):
        pass
    
    @abstractmethod
    def draw(self, frame, now):
        pass
```

### test_mode_strategy.py
```python
from scenes.game_mode_strategy import GameModeStrategy

class TestModeStrategy(GameModeStrategy):
    def __init__(self, game_scene):
        self.game_scene = game_scene
    
    def handle_hits(self, hit_events, t_game, now):
        # 테스트 모드 전용 판정 로직
        pass
    
    def draw_hud(self, frame):
        # 테스트 모드 전용 HUD (디버그 정보 포함)
        pass
```

---

## 마이그레이션 순서

1. 전략 패턴 구조 생성
2. 공통 로직 확인 및 분리
3. 테스트 모드 로직 분리
4. 일반 모드 로직 분리
5. GameScene에서 Strategy 위임
6. 테스트 및 검증

