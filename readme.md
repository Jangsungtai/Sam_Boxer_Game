# Beat Boxer (v0.1a)

`MediaPipe Pose Estimation`을 활용한 실시간 모션 인식 권투 리듬 게임입니다.
OpenCV로 카메라 영상을 받아 실시간으로 사용자의 펀치(Jab) 및 회피(Duck) 동작을 감지하고, 음악 비트에 맞춰 날아오는 노트를 처리하는 게임입니다.

## 🕹️ 주요 기능

* **실시간 모션 감지:** MediaPipe Pose를 통한 전신 랜드마크 추적
* **동작 판정:** 펀치(좌/우 잽) 및 더킹(숙이기) 동작 인식
* **리듬 게임 시스템:** 비트맵(.json)에 맞춰 노트 스폰 및 판정 (Perfect, Great, Good, Miss)
* **씬(Scene) 관리:** 메인 메뉴, 게임 플레이(캘리브레이션, 카운트다운, 플레이), 결과 화면
* **오디오 연동:** Pygame을 통한 배경 음악(BGM) 및 효과음(SFX) 재생
* **설정 분리:** 게임 밸런스(`rules.json`), 난이도(`difficulty.json`), UI(`ui.json`)를 외부 파일로 분리

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







## 📋 버전 관리

### v0.1a (2025-11-01)

* 최초 플레이 가능 빌드 (Alpha)
* `main` / `develop` / `feature` 브랜치 전략을 사용한 Git 형상관리 시작
* 씬 관리 시스템 도입 (메인 메뉴, 게임, 결과 화면)
* MediaPipe Pose 기반 펀치(Jab) / 더킹(Duck) 판정 로직 구현
* Pygame 오디오 및 BGM/SFX 연동 (`core/audio_manager.py`)
* `config` 폴더를 통한 핵심 설정값(규칙, 난이도, UI) 분리
* OpenCV `cv2.waitKey` 기반의 키 입력 시스템으로 안정화
* macOS 연속성 카메라(아이폰) 문제를 회피하는 카메라 인덱스 탐색 기능 추가