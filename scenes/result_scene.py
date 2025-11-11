from __future__ import annotations

import time

import arcade

from scenes.base_scene import BaseScene


class ResultScene(BaseScene):
    def __init__(self, window, audio_manager, config, pose_tracker) -> None:
        super().__init__(window, audio_manager, config, pose_tracker)
        self.final_score: int = 0
        self.restart_color = arcade.color.LIGHT_GRAY
        self.restart_pressed_color = arcade.color.YELLOW
        self.restart_flash_time: float = 0.0

    def startup(self, persistent_data):
        super().startup(persistent_data)
        self.final_score = persistent_data.get("final_score", 0)
        print(f"ResultScene: received final score {self.final_score}.")
        self.restart_color = arcade.color.LIGHT_GRAY
        self.restart_flash_time = 0.0

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE:
            print("ResultScene: SPACE pressed. Restarting game.")
            self.next_scene_name = "GAME"
            self.restart_color = self.restart_pressed_color
            self.restart_flash_time = time.time()

    def update(self, delta_time: float, **kwargs):
        super().update(delta_time, **kwargs)
        now = kwargs.get("now", time.time())
        if self.restart_flash_time and (now - self.restart_flash_time) > 0.25:
            self.restart_color = arcade.color.LIGHT_GRAY
            self.restart_flash_time = 0.0

    def draw_scene(self) -> None:
        width = max(1, int(self.window.width))
        height = max(1, int(self.window.height))

        arcade.draw_text(
            "GAME OVER",
            width / 2,
            height / 2 + 80,
            arcade.color.RED,
            font_size=42,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            f"Final Score: {self.final_score}",
            width / 2,
            height / 2,
            arcade.color.WHITE,
            font_size=28,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            "Press SPACE to Restart",
            width / 2,
            height / 2 - 80,
            self.restart_color,
            font_size=20,
            anchor_x="center",
            anchor_y="center",
        )