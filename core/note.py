from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import arcade
import numpy as np


class Note:
    """리듬 노트의 Arcade 버전."""

    def __init__(
        self,
        item: Dict[str, any],
        width: int,
        height: int,
        duck_line_y: int,
        pre_spawn_time: float,
        config_colors: Dict[str, Tuple[int, int, int]],
        judge_timing: Dict[str, float],
        test_mode: bool,
        config_note_styles: Optional[Dict[str, float]] = None,
    ) -> None:
        self.t = item["t"]
        self.typ = item["type"]
        self.lane = item.get("lane", "C")
        self.pre_spawn = pre_spawn_time

        self.hit = False
        self.missed = False
        self.judge_result: Optional[str] = None

        self.width = width
        self.height = height
        self.duck_line_y = duck_line_y

        self.color_bgr = tuple(config_colors.get(self.typ, (255, 255, 255)))
        self.outline_bgr = (255, 255, 255)

        styles = config_note_styles or {}
        self.circle_radius = int(styles.get("circle_radius", 30))
        self.circle_outline_thickness = int(styles.get("circle_outline_thickness", 3))
        self.duck_half_width = int(styles.get("duck_half_width", 200))
        self.duck_half_height = int(styles.get("duck_half_height", 15))
        self.duck_outline_thickness = int(styles.get("duck_outline_thickness", 2))
        self.label_font_size_circle = int(styles.get("label_font_size_circle", 28))
        self.label_font_size_duck = int(styles.get("label_font_size_duck", 24))

        self.judge_timing = judge_timing
        self.test_mode = test_mode

        self.x0, self.y0 = self._initial_position(width, height)
        self.x = self.x0
        self.y = self.y0

        type_to_label = {"JAB_L": "J", "JAB_R": "S", "DUCK": "D", "BOMB": "4", "WEAVE_L": "WL", "WEAVE_R": "WR"}
        self.label = type_to_label.get(self.typ)

    def _initial_position(self, width: int, height: int) -> Tuple[int, int]:
        target_x = int(width * 0.5)
        target_y = int(height * 0.6)
        if self.typ == "JAB_L":
            return -100, target_y
        if self.typ == "JAB_R":
            return width + 100, target_y
        if self.typ == "DUCK":
            return target_x, -100
        if self.typ == "BOMB":
            return (-100 if self.lane == "L" else width + 100, target_y)
        if self.typ == "WEAVE_L":
            # 위빙 L: 왼쪽 레인에서 시작하여 중앙으로 이동
            return -100, -100
        if self.typ == "WEAVE_R":
            # 위빙 R: 오른쪽 레인에서 시작하여 중앙으로 이동
            return width + 100, -100
        return target_x, target_y

    def get_progress(self, now: float, start_time: float) -> float:
        spawn_time = start_time + self.t - self.pre_spawn
        if now < spawn_time:
            return 0.0
        return float(np.clip((now - spawn_time) / self.pre_spawn, 0.0, 1.0))

    def update(self, now: float, start_time: float, dynamic_hit_zone: Tuple[int, int]) -> None:
        prog = self.get_progress(now, start_time)
        target_x, target_y = dynamic_hit_zone

        if self.typ == "DUCK":
            self.x = int((1 - prog) * self.x0 + prog * target_x)
            self.y = int((1 - prog) * self.y0 + prog * self.duck_line_y)
        else:
            self.x = int((1 - prog) * self.x0 + prog * target_x)
            self.y = int((1 - prog) * self.y0 + prog * target_y)

    def draw(
        self,
        screen_height: int,
        color_converter: Callable[[Tuple[int, int, int]], Tuple[int, int, int]],
        coord_converter: Callable[[Tuple[int, int]], Tuple[float, float]],
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> None:
        if self.hit and not self.missed:
            return

        color_rgb = color_converter(self.color_bgr)
        outline_rgb = color_converter(self.outline_bgr)
        center_x, center_y = coord_converter((self.x, self.y))
        
        # 스케일 적용 (평균 스케일 사용)
        scale = (scale_x + scale_y) / 2.0

        if self.typ == "DUCK":
            width = (self.duck_half_width * 2) * scale_x
            height = (self.duck_half_height * 2) * scale_y
            thickness = self.duck_outline_thickness * scale
            self._draw_rect(center_x, center_y, width, height, color_rgb)
            self._draw_rect_outline(center_x, center_y, width, height, outline_rgb, int(thickness))
        else:
            radius = self.circle_radius * scale
            thickness = self.circle_outline_thickness * scale
            arcade.draw_circle_filled(center_x, center_y, int(radius), color_rgb)
            arcade.draw_circle_outline(center_x, center_y, int(radius), outline_rgb, int(thickness))

        if not self.label:
            return

        font_size = (self.label_font_size_circle if self.typ != "DUCK" else self.label_font_size_duck) * scale
        arcade.draw_text(
            self.label,
            center_x,
            center_y,
            arcade.color.BLACK,
            font_size=int(font_size),
            anchor_x="center",
            anchor_y="center",
        )
#center_y """- font_size / 3""",

    @staticmethod
    def _draw_rect(center_x: float, center_y: float, width: float, height: float, color) -> None:
        half_w = width / 2
        half_h = height / 2
        points = [
            (center_x - half_w, center_y - half_h),
            (center_x + half_w, center_y - half_h),
            (center_x + half_w, center_y + half_h),
            (center_x - half_w, center_y + half_h),
        ]
        arcade.draw_polygon_filled(points, color)

    @staticmethod
    def _draw_rect_outline(center_x: float, center_y: float, width: float, height: float, color, thickness: int) -> None:
        half_w = width / 2
        half_h = height / 2
        points = [
            (center_x - half_w, center_y - half_h),
            (center_x + half_w, center_y - half_h),
            (center_x + half_w, center_y + half_h),
            (center_x - half_w, center_y + half_h),
        ]
        arcade.draw_polygon_outline(points, color, thickness)