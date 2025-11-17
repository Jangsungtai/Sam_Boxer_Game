import os
import sys

import time
from typing import TYPE_CHECKING, Any, Dict, Optional

DEPS_PATH = os.path.join(os.path.dirname(__file__), ".deps")
if os.path.isdir(DEPS_PATH) and DEPS_PATH not in sys.path:
    sys.path.insert(0, DEPS_PATH)

import arcade
import cv2

from core.game_factory import GameFactory, resource_path
from scenes.calibration_scene import CalibrationScene
from scenes.game_scene import GameScene
from scenes.main_menu_scene import MainMenuScene
from scenes.result_scene import ResultScene

if TYPE_CHECKING:
    from core.audio_manager import AudioManager
    from core.pose_tracker import PoseTracker


class GameWindow(arcade.Window):
    """Arcade 기반 메인 윈도우. 카메라 데이터와 포즈 트래킹 결과를 각 Scene(View)에 전달합니다."""

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        config: Dict[str, Any],
        audio_manager: Optional[Any],
        pose_tracker: Optional[Any],
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
        super().on_close()


def main() -> None:
    # ------------------------------------------------------------------ #
    # 컴포넌트 초기화 (GameFactory 사용)
    # ------------------------------------------------------------------ #
    # 설정 로드
    try:
        config_manager = GameFactory.create_config_manager()
        config = config_manager.get_config()
    except FileNotFoundError as exc:
        from core.logger import get_logger
        logger = get_logger()
        logger.error(f"필수 config 파일을 찾을 수 없습니다: {exc}")
        return

    # 오디오 초기화
    audio_manager = GameFactory.create_audio_manager()

    # 카메라 초기화
    capture, source_width, source_height = GameFactory.create_camera()

    # PoseTracker 초기화
    pose_tracker = GameFactory.create_pose_tracker(source_width, source_height, config)

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