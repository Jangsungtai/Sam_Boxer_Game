from __future__ import annotations

import time

import arcade

from scenes.base_scene import BaseScene


class MainMenuScene(BaseScene):
    def __init__(self, window, audio_manager, config, pose_tracker) -> None:
        super().__init__(window, audio_manager, config, pose_tracker)
        self.title_text = "BEAT BOXER"
        self.start_text = "Press SPACE to Start"
        self.key_press_time: float = 0.0
        self.title_color = arcade.color.WHITE
        self.start_color = arcade.color.WHITE
        self.start_pressed_color = arcade.color.YELLOW

    def startup(self, persistent_data):
        super().startup(persistent_data)
        self.key_press_time = 0.0
        self.start_color = arcade.color.WHITE

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE:
            if self.pose_tracker is not None:
                print("MainMenu: SPACE pressed. Switching to CALIBRATION scene.")
                self.next_scene_name = "CALIBRATION"
            else:
                print("MainMenu: SPACE pressed. Pose tracker missing, skipping to GAME scene.")
                self.next_scene_name = "GAME"
            self.key_press_time = time.time()
            self.start_color = self.start_pressed_color

    def update(self, delta_time: float, **kwargs):
        super().update(delta_time, **kwargs)
        now = kwargs.get("now", time.time())
        if self.key_press_time > 0 and (now - self.key_press_time) > 0.2:
            self.start_color = arcade.color.WHITE
            self.key_press_time = 0.0

    def draw_scene(self) -> None:
        width = max(1, int(self.window.width))
        height = max(1, int(self.window.height))

        arcade.draw_text(
            self.title_text,
            width / 2,
            height / 2 + 40,
            self.title_color,
            font_size=48,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            self.start_text,
            width / 2,
            height / 2 - 40,
            self.start_color,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
        )