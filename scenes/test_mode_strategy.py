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
        for idx, entry in enumerate(game_scene.game_state.judge_log):
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
        
        # 판정 디버깅 정보
        debug_start_x = game_scene.window.width - 300
        debug_start_y = game_scene.window.height - 100
        debug_line_height = 18
        
        arcade.draw_text(
            "Judgment Debug",
            debug_start_x,
            debug_start_y,
            arcade.color.CYAN,
            font_size=14,
            bold=True,
        )
        
        # 판정 창 정보
        judge_timing = game_scene.judge_timing
        arcade.draw_text(
            f"Perfect: ±{judge_timing.get('perfect', 0.2):.2f}s",
            debug_start_x,
            debug_start_y - debug_line_height * 1,
            arcade.color.GOLD,
            font_size=12,
        )
        arcade.draw_text(
            f"Great: ±{judge_timing.get('great', 0.35):.2f}s",
            debug_start_x,
            debug_start_y - debug_line_height * 2,
            arcade.color.ORANGE,
            font_size=12,
        )
        arcade.draw_text(
            f"Good: ±{judge_timing.get('good', 0.5):.2f}s",
            debug_start_x,
            debug_start_y - debug_line_height * 3,
            arcade.color.YELLOW,
            font_size=12,
        )
        
        # 활성 노트 정보
        active_notes = game_scene.note_manager.get_active_notes() if game_scene.note_manager else []
        active_jab_notes = [n for n in active_notes if n.typ in ["JAB_L", "JAB_R"] and not n.hit and not n.missed]
        if game_scene.game_state.song_start_time:
            game_time = now - game_scene.game_state.song_start_time
            arcade.draw_text(
                f"Game Time: {game_time:.2f}s",
                debug_start_x,
                debug_start_y - debug_line_height * 5,
                arcade.color.WHITE,
                font_size=12,
            )
            arcade.draw_text(
                f"Active JAB Notes: {len(active_jab_notes)}",
                debug_start_x,
                debug_start_y - debug_line_height * 6,
                arcade.color.WHITE,
                font_size=12,
            )
            
            # 가장 가까운 노트 정보 표시
            if active_jab_notes:
                closest_note = min(active_jab_notes, key=lambda n: abs(n.t - game_time))
                time_diff = closest_note.t - game_time
                arcade.draw_text(
                    f"Closest: {closest_note.typ}",
                    debug_start_x,
                    debug_start_y - debug_line_height * 7,
                    arcade.color.LIGHT_GREEN,
                    font_size=11,
                )
                arcade.draw_text(
                    f"  Note t: {closest_note.t:.2f}s",
                    debug_start_x,
                    debug_start_y - debug_line_height * 8,
                    arcade.color.LIGHT_GRAY,
                    font_size=11,
                )
                arcade.draw_text(
                    f"  Δ: {time_diff:+.3f}s",
                    debug_start_x,
                    debug_start_y - debug_line_height * 9,
                    arcade.color.LIGHT_GREEN if abs(time_diff) <= judge_timing.get('good', 0.5) else arcade.color.RED,
                    font_size=11,
                )

    def on_hit_events(self, hit_events, now: float) -> None:
        self.handle_hits(hit_events, t_game=0.0, now=now)

