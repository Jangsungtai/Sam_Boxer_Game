import json
import os
import sys

import time
from typing import Any, Dict, Optional

DEPS_PATH = os.path.join(os.path.dirname(__file__), ".deps")
if os.path.isdir(DEPS_PATH) and DEPS_PATH not in sys.path:
    sys.path.insert(0, DEPS_PATH)

import arcade
import cv2
import pygame

from core.audio_manager import AudioManager
from core.pose_tracker import PoseTracker
from scenes.calibration_scene import CalibrationScene
from scenes.game_scene import GameScene
from scenes.main_menu_scene import MainMenuScene
from scenes.result_scene import ResultScene


def resource_path(relative_path: str) -> str:
    """PyInstaller 지원을 위한 자원 경로 헬퍼."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_best_camera_index() -> int:
    """사용 가능한 카메라 인덱스를 탐색하여 반환합니다."""
    print("사용 가능한 카메라를 찾는 중...")
    for index in range(4, -1, -1):
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            print(f"카메라 발견: 인덱스 {index}")
            cap.release()
            return index
    print("사용 가능한 카메라가 없습니다. 0번 인덱스로 시도합니다.")
    return 0


class GameWindow(arcade.Window):
    """Arcade 기반 메인 윈도우. 카메라 데이터와 포즈 트래킹 결과를 각 Scene(View)에 전달합니다."""

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        config: Dict[str, Any],
        audio_manager: Optional[AudioManager],
        pose_tracker: Optional[PoseTracker],
        capture: Optional[cv2.VideoCapture],
        source_width: int,
        source_height: int,
    ) -> None:
        super().__init__(width, height, title, resizable=True, update_rate=1 / 60)
        self.app_config = config
        self.audio_manager = audio_manager
        self.pose_tracker = pose_tracker
        self.capture = capture
        self.source_width = source_width
        self.source_height = source_height

        self.update_data: Dict[str, Any] = {
            "frame": None,
            "hit_events": [],
            "landmarks": None,
            "mask": None,
            "now": time.time(),
        }
        self._current_scene_name: Optional[str] = None

        self._setup_initial_view()

    # ---------------------------------------------------------------------- #
    # Arcade window lifecycle
    # ---------------------------------------------------------------------- #
    def _setup_initial_view(self) -> None:
        """초기 씬을 생성하여 표시합니다."""
        menu_scene = self._create_scene("MENU", {})
        if menu_scene is None:
            raise RuntimeError("초기 MainMenuScene을 생성할 수 없습니다.")
        self.show_view(menu_scene)
        self._current_scene_name = "MENU"
        print("[GameWindow] initial view: MainMenuScene")

    def _create_scene(self, scene_name: str, persistent_data: Dict[str, Any]) -> Optional[arcade.View]:
        """씬 이름에 따라 새로운 View 인스턴스를 생성합니다."""
        scene: Optional[arcade.View] = None
        if scene_name == "MENU":
            scene = MainMenuScene(self, self.audio_manager, self.app_config, self.pose_tracker)
        elif scene_name == "CALIBRATION":
            scene = CalibrationScene(self, self.audio_manager, self.app_config, self.pose_tracker)
        elif scene_name == "GAME":
            scene = GameScene(self, self.audio_manager, self.app_config, self.pose_tracker)
        elif scene_name == "RESULT":
            scene = ResultScene(self, self.audio_manager, self.app_config, self.pose_tracker)
        else:
            print(f"[경고] 알 수 없는 씬 요청: {scene_name}")
            return None

        if hasattr(scene, "set_source_dimensions"):
            scene.set_source_dimensions(self.source_width, self.source_height)  # type: ignore[attr-defined]

        if hasattr(scene, "startup"):
            scene.startup(persistent_data)  # type: ignore[attr-defined]

        return scene

    def _switch_scene(self, scene_name: str, persistent_data: Dict[str, Any]) -> None:
        """다음 씬으로 전환합니다."""
        next_scene = self._create_scene(scene_name, persistent_data)
        if next_scene is None:
            print(f"[경고] {scene_name} 씬을 생성하지 못했습니다. 전환을 취소합니다.")
            return

        self.show_view(next_scene)
        self._current_scene_name = scene_name
        print(f"[GameWindow] scene switched to {scene_name}")

    # ---------------------------------------------------------------------- #
    # Arcade event handlers
    # ---------------------------------------------------------------------- #
    def on_update(self, delta_time: float) -> None:
        """카메라 프레임과 포즈 정보를 갱신하고 현재 뷰에 전달합니다."""
        frame = None
        hit_events = []
        landmarks = None
        mask = None
        now = time.time()

        if self.capture is not None:
            ret, source_frame = self.capture.read()
            if ret:
                frame = cv2.flip(source_frame, 1)
            else:
                print("[경고] 카메라 프레임을 읽지 못했습니다.")

        if self.pose_tracker is not None and frame is not None:
            try:
                pose_frame = frame.copy()
                hit_events, landmarks, mask = self.pose_tracker.process_frame(pose_frame, now)
            except Exception as exc:
                print(f"[경고] PoseTracker 업데이트 실패: {exc}")

        self.update_data.update(
            {
                "frame": frame,
                "hit_events": hit_events,
                "landmarks": landmarks,
                "mask": mask,
                "now": now,
            }
        )

        current_view = self.current_view
        if current_view is None:
            return

        current_view.update(delta_time, **self.update_data)

        next_scene = getattr(current_view, "next_scene_name", None)
        if next_scene:
            persistent = {}
            if hasattr(current_view, "cleanup"):
                persistent = current_view.cleanup()  # type: ignore[assignment]
            self._switch_scene(next_scene, persistent)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ESCAPE:
            print("[GameWindow] ESC pressed. Closing window.")
            self.close()
            return
        current_view = self.current_view
        if current_view is not None:
            current_view.on_key_press(symbol, modifiers)

    def on_close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        try:
            pygame.quit()
        finally:
            super().on_close()


def main() -> None:
    # ------------------------------------------------------------------ #
    # 오디오 초기화
    # ------------------------------------------------------------------ #
    audio_manager: Optional[AudioManager] = None
    try:
        pygame.init()
        print("Pygame 모듈 초기화 성공")
        audio_manager = AudioManager()
        sfx_map = {
            "PERFECT": "hit_perfect.wav",
            "GREAT": "hit_good.wav",
            "GOOD": "hit_good.wav",
            "MISS": "miss.wav",
            "BOMB!": "bomb.wav",
        }
        audio_manager.load_sounds(sfx_map)
    except Exception as exc:
        print(f"[경고] 오디오 초기화 실패: {exc}")
        audio_manager = None

    # ------------------------------------------------------------------ #
    # 카메라 초기화
    # ------------------------------------------------------------------ #
    camera_index = get_best_camera_index()
    capture = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
    if capture is not None and capture.isOpened():
        source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        print(f"카메라 초기화 성공 (인덱스: {camera_index}, {source_width}x{source_height})")
    else:
        print(f"[경고] 카메라(인덱스 {camera_index})를 열 수 없습니다. 카메라 없이 실행합니다.")
        if capture is not None:
            capture.release()
        capture = None
        source_width, source_height = 1280, 720

    # ------------------------------------------------------------------ #
    # 설정 로드
    # ------------------------------------------------------------------ #
    try:
        print("Loading config files...")
        config = {
            "rules": json.load(open(resource_path("config/rules.json"), "r")),
            "difficulty": json.load(open(resource_path("config/difficulty.json"), "r")),
            "ui": json.load(open(resource_path("config/ui.json"), "r")),
        }
    except FileNotFoundError as exc:
        print(f"[오류] 필수 config 파일을 찾을 수 없습니다: {exc}")
        if capture is not None:
            capture.release()
        pygame.quit()
        return

    # ------------------------------------------------------------------ #
    # PoseTracker 초기화
    # ------------------------------------------------------------------ #
    pose_tracker: Optional[PoseTracker] = None
    try:
        print("Initializing Pose Tracker...")
        pose_tracker = PoseTracker(source_width, source_height, config["rules"], config["ui"])
    except Exception as exc:
        print(f"[경고] PoseTracker 초기화 실패: {exc}")
        pose_tracker = None

    # ------------------------------------------------------------------ #
    # Arcade 윈도우 생성 및 실행
    # ------------------------------------------------------------------ #
    window = GameWindow(
        width=1280,
        height=720,
        title="Beat Boxer",
        config=config,
        audio_manager=audio_manager,
        pose_tracker=pose_tracker,
        capture=capture,
        source_width=source_width,
        source_height=source_height,
    )
    arcade.run()
    window.close()


if __name__ == "__main__":
    main()