# Beat Boxer (v0.9)

`MediaPipe Pose Estimation`을 활용한 실시간 모션 인식 권투 리듬 게임입니다.
OpenCV로 카메라 영상을 받아 실시간으로 사용자의 펀치(Jab) 및 회피(Duck) 동작을 감지하고, 음악 비트에 맞춰 날아오는 노트를 처리하는 게임입니다.

## 🕹️ 주요 기능

* **실시간 모션 감지:** MediaPipe Pose를 통한 전신 랜드마크 추적 및 스무딩
* **동작 판정:** 펀치(좌/우 잽) 및 더킹(숙이기) 동작 인식
* **리듬 게임 시스템:** 리듬 기반 비트맵(`beatmap.txt`)에 맞춰 노트 스폰 및 판정 (Perfect, Great, Good, Miss)
* **공간 + 타이밍 판정:** 손 랜드마크 위치와 타이밍을 모두 고려한 정확한 판정
* **씬(Scene) 관리:** 메인 메뉴, 게임 플레이(캘리브레이션, 카운트다운, 플레이), 결과 화면
* **BPM 동기화 비프음:** BPM에 맞춰 자동 재생되는 400Hz 가이드 비프음
* **전략 패턴:** 일반 모드와 테스트 모드를 Strategy 패턴으로 분리
* **설정 분리:** 게임 밸런스(`rules.json`), 난이도(`difficulty.json`), UI(`ui.json`)를 외부 파일로 분리
* **박자 단위 설정:** BPM에 따라 자동으로 조정되는 박자 기반 설정 시스템

## 💻 사용된 기술 스택

* **Python 3.11+**
* **OpenCV:** 카메라 입출력 및 UI 렌더링
* **MediaPipe:** 실시간 포즈 인식
* **Pygame:** 오디오 재생 및 키보드 이벤트 처리
* **NumPy:** 랜드마크 좌표 계산

---

## 🚀 설치 및 실행 방법

1.  **Git 저장소 복제 (Clone)**
    ```bash
    git clone [https://github.com/Jangsungtai/beat-boxer-game.git](https://github.com/Jangsungtai/beat-boxer-game.git)
    cd beat-boxer-game
    ```

2.  **Conda 가상 환경 생성 및 활성화**
    ```bash
    # (Python 3.11 또는 3.12 권장)
    conda create -n beat_boxer_game python=3.11
    conda activate beat_boxer_game
    ```

3.  **필요한 라이브러리 설치**
    ```bash
    pip install -r requirements.txt
    ```

4.  **프로그램 실행**
    ```bash
    python main.py
    ```

### ⌨️ 조작 키

* **[전역]** `Q` / `ESC` : 프로그램 즉시 종료
* **[메뉴]** `Spacebar` : 게임 시작
* **[게임 중]** `M` : 메인 메뉴로
* **[결과]** `M` : 메인 메뉴로
* **[결과]** `Spacebar` : 게임 재시작

---

## 📂 폴더 구조

```
beat_boxer_game/
├── main.py                          # 프로그램 진입점
├── requirements.txt                  # Python 패키지 의존성
│
├── config/                          # 설정 파일 (JSON)
│   ├── rules.json                   # 게임 규칙 및 판정 설정
│   ├── difficulty.json              # 난이도별 설정 (BPM, 판정 시간 - 박자 단위)
│   └── ui.json                       # UI 색상, 위치, 스타일 설정
│
├── core/                            # 핵심 게임 로직
│   ├── pose_tracker.py              # 포즈 추적 및 동작 감지 (랜드마크 스무딩 포함)
│   ├── note.py                       # 노트 객체 클래스
│   └── audio_manager.py              # 오디오 관리 (사운드, 음악, 비프음)
│
├── scenes/                          # 게임 씬 관리
│   ├── base_scene.py                 # 씬 기본 클래스
│   ├── main_menu_scene.py            # 메인 메뉴 씬
│   ├── game_scene.py                 # 게임 플레이 씬 (핵심)
│   ├── result_scene.py                # 결과 화면 씬
│   ├── game_mode_strategy.py         # 전략 패턴 추상 클래스
│   ├── normal_mode_strategy.py       # 일반 모드 전략 구현
│   └── test_mode_strategy.py         # 테스트 모드 전략 구현
│
└── assets/                          # 리소스 파일
    ├── beatmaps/                    # 비트맵 데이터
    │   └── song1/
    │       ├── beatmap.txt           # 리듬 기반 비트맵 (BPM/division 사용)
    │       └── music.mp3             # 배경 음악
    ├── sounds/                      # 효과음 파일
    └── images/                      # 이미지 리소스
```

## 🎮 게임 모드

### 일반 모드 (Normal Mode)
- 기본 게임 플레이 모드
- BPM 동기화 비프음 재생
- 히트존 색상 변경 (판정 결과에 따라)
- 판정 결과 표시

### 테스트 모드 (Test Mode)
- 캘리브레이션 화면에서 `0` 키를 눌러 진입
- 일반 모드와 동일한 판정 로직
- 추가 디버그 정보 표시 (이벤트 히스토리, "Test mode" 텍스트)
- BPM 동기화 비프음만 재생 (assets 사운드 무시)

## 📋 버전 관리

### v0.9 (2024-12)

**리팩토링 완료 버전**

#### 🏗️ 주요 리팩토링
* **Phase 1: PoseTracker 역할 확장**
  - 랜드마크 스무딩 및 주먹 중심점 계산을 `PoseTracker`로 이동
  - `GameScene` 코드 약 200줄 감소
  - `PoseTracker`가 포즈 관련 모든 데이터를 캡슐화

* **Phase 2: Strategy 패턴 재정립**
  - 공통 HUD 로직을 `GameModeStrategy`에 통합
  - `normal_mode_strategy`와 `test_mode_strategy`의 공통 로직 제거
  - Strategy 독립성 향상 (필요한 데이터만 받아서 처리)

* **Phase 3: BPM 연동 로직 개선**
  - 설정을 박자 단위로 변경 (`judge_timing_base_beats`, `pre_spawn_beats`)
  - BPM 변경 시 모든 타이밍이 자동으로 조정됨
  - 비선형 스케일링 로직 제거로 코드 단순화

* **Phase 4: 캘리브레이션 로직 이동**
  - 캘리브레이션 위치 확인 로직을 `PoseTracker`로 이동
  - 일관성 있는 모듈 구조 확보

#### ✨ 새로운 기능
* **BPM 동기화 비프음:** 400Hz 가이드 비프음이 BPM에 맞춰 자동 재생
* **박자 단위 설정:** `difficulty.json`에서 박자 단위로 설정 (BPM에 따라 자동 변환)
* **공간 판정 모드:** `spatial_judge_mode` 설정으로 손목만 또는 손 랜드마크 4개 + 주먹 중심 판정
* **판정 실패 이유 표시:** "timing", "area", "area/timing"으로 실패 원인 구분
* **히트존 색상 변경:** 판정 결과에 따라 히트존 색상 및 두께 변경

#### 📝 개선 사항
* **코드 구조:** 모듈 책임 분리, 코드 중복 제거
* **유지보수성:** 각 모듈의 역할이 명확해짐
* **확장성:** 새로운 모드 추가가 쉬워짐
* **설정 직관성:** 박자 단위 설정으로 더 직관적

#### ⚠️ 주의사항
* `difficulty.json` 설정 파일 구조 변경:
  - `judge_timing_base` → `judge_timing_base_beats` (박자 단위)
  - `pre_spawn_time` → `pre_spawn_beats` (박자 단위)
  - 기존 설정 파일을 박자 단위로 변환 필요

---

### v0.1a (2025-11-01)

* 최초 플레이 가능 빌드 (Alpha)
* `main` / `develop` / `feature` 브랜치 전략을 사용한 Git 형상관리 시작
* 씬 관리 시스템 도입 (메인 메뉴, 게임, 결과 화면)
* MediaPipe Pose 기반 펀치(Jab) / 더킹(Duck) 판정 로직 구현
* Pygame 오디오 및 BGM/SFX 연동 (`core/audio_manager.py`)
* `config` 폴더를 통한 핵심 설정값(규칙, 난이도, UI) 분리
* OpenCV `cv2.waitKey` 기반의 키 입력 시스템으로 안정화
* macOS 연속성 카메라(아이폰) 문제를 회피하는 카메라 인덱스 탐색 기능 추가