from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import arcade


class BaseScene(arcade.View):
    """Arcade View 기반의 공통 Scene 베이스 클래스."""

    def __init__(self, window: arcade.Window, audio_manager, config: Dict[str, Any], pose_tracker) -> None:
        super().__init__(window)
        self.window: arcade.Window = window
        self.audio_manager = audio_manager
        self.config = config
        self.pose_tracker = pose_tracker

        self.next_scene_name: Optional[str] = None
        self.persistent_data: Dict[str, Any] = {}
        self.source_width: int = 0
        self.source_height: int = 0
        self.latest_inputs: Dict[str, Any] = {}
        self.x_scale: float = 1.0
        self.y_scale: float = 1.0

    # ------------------------------------------------------------------ #
    # Lifecycle helpers
    # ------------------------------------------------------------------ #
    def startup(self, persistent_data: Optional[Dict[str, Any]]) -> None:
        self.persistent_data = persistent_data or {}
        self.next_scene_name = None

    def cleanup(self) -> Dict[str, Any]:
        self.next_scene_name = None
        return self.persistent_data

    def set_source_dimensions(self, width: int, height: int) -> None:
        self.source_width = max(0, int(width))
        self.source_height = max(0, int(height))
        self._update_scale()

    def _update_scale(self) -> None:
        window_width = getattr(self.window, "width", 0) or 0
        window_height = getattr(self.window, "height", 0) or 0
        if self.source_width > 0 and window_width:
            self.x_scale = window_width / self.source_width
        else:
            self.x_scale = 1.0
        if self.source_height > 0 and window_height:
            self.y_scale = window_height / self.source_height
        else:
            self.y_scale = 1.0

    # ------------------------------------------------------------------ #
    # Arcade hooks
    # ------------------------------------------------------------------ #
    def on_show(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)

    def update(self, delta_time: float, **kwargs: Any) -> None:  # pragma: no cover - override as needed
        self.latest_inputs = kwargs

    def on_draw(self) -> None:  # pragma: no cover - override as needed
        self.window.clear()
        self.draw_scene()

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self._update_scale()

    def on_key_press(self, symbol: int, modifiers: int) -> None:  # pragma: no cover - override as needed
        pass

    # ------------------------------------------------------------------ #
    # Helpers for subclasses
    # ------------------------------------------------------------------ #
    def draw_scene(self) -> None:  # pragma: no cover - override as needed
        """하위 클래스가 실제 렌더링을 구현하도록 비워둡니다."""
        pass

    @staticmethod
    def bgr_to_rgb(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return (color[2], color[1], color[0])

    def to_arcade_xy(self, point: Tuple[float, float]) -> Tuple[float, float]:
        x, y = point
        if self.source_width and self.source_height:
            x *= self.x_scale
            y *= self.y_scale
        window_height = getattr(self.window, "height", 0) or 0
        y = window_height - y
        return x, y

    def to_arcade_y(self, y: float) -> float:
        if self.source_height:
            y *= self.y_scale
        window_height = getattr(self.window, "height", 0) or 0
        return window_height - y