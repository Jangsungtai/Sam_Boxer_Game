from __future__ import annotations

import arcade

from scenes.game_mode_strategy import GameModeStrategy


class TestModeStrategy(GameModeStrategy):
    """테스트 모드 전략: Arcade 디버그 HUD."""

    def __init__(self, game_scene) -> None:
        super().__init__(game_scene)
        self.event_history: list[tuple[str, float]] = []
        self.max_history = 20

    def handle_hits(self, hit_events, t_game, now, **kwargs) -> None:
        for ev in hit_events:
            self.event_history.append((ev.get("type", "UNKNOWN"), now))
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history :]

    def _draw_mode_specific_hud(self) -> None:
        arcade.draw_text(
            "Test Mode",
            self.game_scene.window.width - 160,
            self.game_scene.window.height - 40,
            arcade.color.YELLOW,
            font_size=18,
        )

    def get_hit_zone_color(self, default_color):
        inside_left = self.game_scene.is_point_inside_hit_zone(self.game_scene.last_left_fist)
        inside_right = self.game_scene.is_point_inside_hit_zone(self.game_scene.last_right_fist)
        return arcade.color.GREEN if inside_left or inside_right else arcade.color.RED

    def draw_additional(self, now: float) -> None:
        game_scene = self.game_scene
        hit_center = game_scene.to_arcade_xy(game_scene.hit_zone_camera)

        # Note: Pose markers are now drawn in GameScene.draw_scene() for all modes
        # Only draw connection lines in test mode

        def to_screen(point):
            return game_scene.to_arcade_xy(point) if point else None

        nose_screen = to_screen(game_scene.last_nose_pos)
        right_screen = to_screen(game_scene.last_right_fist)
        left_screen = to_screen(game_scene.last_left_fist)

        if nose_screen and right_screen:
            arcade.draw_line(*nose_screen, *right_screen, arcade.color.LIGHT_SKY_BLUE, 2)
        if nose_screen and left_screen:
            arcade.draw_line(*nose_screen, *left_screen, arcade.color.SALMON, 2)
        if right_screen:
            arcade.draw_line(*right_screen, *hit_center, arcade.color.LIGHT_SKY_BLUE, 1)
        if left_screen:
            arcade.draw_line(*left_screen, *hit_center, arcade.color.SALMON, 1)

        # Floating judgement logs just below the hit zone
        log_start_y = hit_center[1] - game_scene.hit_zone_radius - 40
        for idx, entry in enumerate(game_scene.judge_log):
            arcade.draw_text(
                entry,
                hit_center[0] - 120,
                log_start_y - idx * 18,
                arcade.color.LIGHT_GREEN,
                font_size=14,
            )

        # Event history (recent raw hit events)
        start_x = 40
        start_y = 200
        line_height = 20

        arcade.draw_text(
            "Recent Events",
            start_x,
            start_y + line_height * 2,
            arcade.color.LIGHT_YELLOW,
            font_size=14,
        )

        for idx, (ev_type, ts) in enumerate(reversed(self.event_history[-5:])):
            age = now - ts
            arcade.draw_text(
                f"{ev_type} ({age:0.1f}s)",
                start_x,
                start_y + idx * line_height,
                arcade.color.LIGHT_GRAY,
                font_size=12,
            )

    def on_hit_events(self, hit_events, now: float) -> None:
        self.handle_hits(hit_events, t_game=0.0, now=now)

