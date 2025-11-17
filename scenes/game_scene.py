"""
리팩토링된 게임 씬
새로운 모듈 구조를 사용합니다.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import arcade

from core.hit_effect import HitEffectSystem
from core.note import Note
from core.game_state import GameState
from core.note_manager import NoteManager
from core.beatmap_loader import BeatmapLoader
from core.score_manager import ScoreManager
from core.judgment_processor import JudgmentProcessor
from core.silhouette_renderer import SilhouetteRenderer
from core.logger import get_logger
from scenes.base_scene import BaseScene
from scenes.game_mode_strategy import GameModeStrategy
from scenes.normal_mode_strategy import NormalModeStrategy
from scenes.test_mode_strategy import TestModeStrategy
from core.constants import (
    DODGE_LEFT_LINE_X, DODGE_CENTER_LINE_X, DODGE_RIGHT_LINE_X,
    DODGE_LINE_Y_TOP, DODGE_LINE_Y_BOTTOM,
    COLOR_DODGE_LINE, SCREEN_WIDTH, SCREEN_HEIGHT
)

logger = get_logger()


class GameScene(BaseScene):
    """Arcade 기반 게임 플레이 씬 (리팩토링 버전)"""

    def __init__(self, window: arcade.Window, audio_manager, config: Dict[str, Any], pose_tracker) -> None:
        super().__init__(window, audio_manager, config, pose_tracker)

        self.config_rules = config.get("rules", {})
        self.config_ui = config.get("ui", {})
        self.config_colors = self.config_ui.get("colors", {})
        self.config_difficulty = config.get("difficulty", {})

        # Game state
        self.game_state = GameState()
        
        # UI settings
        self.hit_zone_camera: Tuple[int, int] = (0, 0)
        self.duck_line_camera: int = 0
        self.hit_zone_radius: float = 80.0
        self.hit_zone_thickness: int = 6
        self.hit_zone_color_rgb: Tuple[int, int, int] = (255, 255, 255)
        self.duck_line_color_rgb: Tuple[int, int, int] = (0, 255, 0)

        self.mode_strategy: Optional[GameModeStrategy] = None

        # Beatmap
        self.beatmap_items: List[Dict[str, Any]] = []
        self.beatmap_index: int = 0
        self.beatmap_loader = BeatmapLoader(self.config_difficulty)

        # Game timing
        self.countdown_duration: float = 3.0
        self.finish_delay: float = 2.5
        self.music_loaded: bool = False

        # Settings
        self.pre_spawn_time: float = 1.0
        self.judge_timing: Dict[str, float] = {"perfect": 0.2, "great": 0.35, "good": 0.5}
        self.score_values: Dict[str, int] = self.config_rules.get("score_base", {})
        self.score_multiplier: float = 1.0
        self.timing_offset: float = float(self.config_rules.get("timing_offset", 0.0))

        # Components (will be initialized in startup)
        self.note_manager: Optional[NoteManager] = None
        self.score_manager: Optional[ScoreManager] = None
        self.judgment_processor: Optional[JudgmentProcessor] = None
        self.hit_effect_system: HitEffectSystem = HitEffectSystem()
        self.last_update_time: float = 0.0

        # Background image
        self.background_sprite: Optional[arcade.Sprite] = None
        self.background_sprite_list: Optional[arcade.SpriteList] = None
        self.background_configured: bool = False

        # Pose tracking
        self.last_nose_pos: Optional[Tuple[float, float]] = None
        self.last_left_fist: Optional[Tuple[float, float]] = None
        self.last_right_fist: Optional[Tuple[float, float]] = None

    def on_resize(self, width: int, height: int) -> None:
        """창 크기 변경 시 배경을 다시 설정합니다."""
        super().on_resize(width, height)
        self.background_configured = False
        self._configure_background()

    def set_source_dimensions(self, width: int, height: int) -> None:
        super().set_source_dimensions(width, height)
        positions = self.config_ui.get("positions", {})
        hit_ratio = positions.get("hit_zone", {}).get("pos_ratio", [0.5, 0.3])
        self.hit_zone_camera = (
            int(self.source_width * hit_ratio[0]) if self.source_width else 0,
            int(self.source_height * hit_ratio[1]) if self.source_height else 0,
        )
        self.duck_line_camera = int(self.source_height * 0.6) if self.source_height else 0

        hud_styles = self.config_ui.get("styles", {}).get("hud", {})
        hud_colors = self.config_colors.get("hud", {})
        self.hit_zone_radius = float(hud_styles.get("hit_zone_radius", 100))
        self.hit_zone_thickness = int(hud_styles.get("hit_zone_thickness", 6))
        self.hit_zone_color_rgb = self.bgr_to_rgb(tuple(hud_colors.get("hit_zone", (255, 255, 255))))
        self.duck_line_color_rgb = self.bgr_to_rgb(tuple(hud_colors.get("duck_line", (0, 255, 0))))
        
        self._configure_background()

    def startup(self, persistent_data):
        super().startup(persistent_data)
        
        # Reset game state
        self.game_state.reset()
        self.game_state.test_mode = bool(persistent_data.get("test_mode", False))
        self.game_state.status_text = "Get Ready!"
        
        # Load settings
        self._load_difficulty_settings()
        self._load_beatmap()
        
        # Load background image
        self._load_background()
        self._configure_background()
        
        # Initialize components
        self._initialize_components()
        
        # Initialize game
        self.beatmap_index = 0
        self._update_strategy()
        
        if self.pose_tracker:
            self.pose_tracker.set_test_mode(self.game_state.test_mode)
        
        if self.audio_manager:
            music_path = os.path.join("assets", "beatmaps", "song1", "music.mp3")
            self.music_loaded = self.audio_manager.load_music(music_path)

    def _initialize_components(self) -> None:
        """게임 컴포넌트를 초기화합니다."""
        # Note Manager
        self.note_manager = NoteManager(
            self.source_width,
            self.source_height,
            self.pre_spawn_time,
            self.config_colors,
            self.judge_timing,
            self.game_state.test_mode,
            self.config_ui.get("styles", {}).get("notes", {})
        )
        
        # Score Manager
        self.score_manager = ScoreManager(
            self.score_values,
            self.score_multiplier,
            self.game_state
        )
        
        # Judgment Processor
        self.judgment_processor = JudgmentProcessor(
            self.judge_timing,
            self.score_manager,
            self.hit_effect_system,
            self.audio_manager,
            self.pose_tracker,
            self.window.width,
            self.window.height,
            self.to_arcade_xy,
            self.bgr_to_rgb,
            self.config_colors,
            self.hit_zone_camera,
            self.game_state.test_mode,
            self.x_scale,
            self.y_scale
        )

    def cleanup(self) -> Dict[str, Any]:
        self.persistent_data.update({
            "score": self.game_state.score,
            "combo": self.game_state.combo,
            "max_combo": self.game_state.max_combo,
            "final_score": self.game_state.score,
            "test_mode": self.game_state.test_mode,
        })
        return super().cleanup()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.T:
            self._toggle_test_mode()

    def _toggle_test_mode(self) -> None:
        self.game_state.test_mode = not self.game_state.test_mode
        state = "enabled" if self.game_state.test_mode else "disabled"
        logger.info(f"Test mode {state}.")
        self._update_strategy()
        if self.pose_tracker:
            self.pose_tracker.set_test_mode(self.game_state.test_mode)
        if self.note_manager:
            for note in self.note_manager.get_active_notes():
                note.test_mode = self.game_state.test_mode

    def _update_strategy(self) -> None:
        self.mode_strategy = TestModeStrategy(self) if self.game_state.test_mode else NormalModeStrategy(self)

    def update(self, delta_time: float, **kwargs: Any) -> None:
        super().update(delta_time, **kwargs)

        frame = kwargs.get("frame")
        hit_events = kwargs.get("hit_events", []) or []
        landmarks = kwargs.get("landmarks")
        mask = kwargs.get("mask")
        now = kwargs.get("now", time.time())

        # Update pose tracking
        if self.pose_tracker and frame is not None:
            smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
            if smoothed_landmarks:
                self.last_nose_pos = smoothed_landmarks.get("nose")
            left_fist, right_fist = self.pose_tracker.get_fist_centroids()
            self.last_left_fist = left_fist
            self.last_right_fist = right_fist
        else:
            self.last_nose_pos = None
            self.last_left_fist = None
            self.last_right_fist = None

        # Check if game is finished
        if self.game_state.game_finished:
            if self.game_state.finish_trigger_time and (now - self.game_state.finish_trigger_time) > self.finish_delay:
                self.next_scene_name = "RESULT"
            return

        # Status updates
        if frame is None:
            self.game_state.status_text = "카메라 영상 대기 중..."
            return

        if self.pose_tracker and landmarks is None:
            self.game_state.status_text = "포즈 분석 중..."
        else:
            self.game_state.status_text = "READY" if not self.game_state.song_start_time else "GO!"

        # Countdown
        if self.game_state.song_start_time is None:
            if self.game_state.countdown_start is None:
                self.game_state.countdown_start = now
            remaining = max(0.0, self.countdown_duration - (now - self.game_state.countdown_start))
            self.game_state.status_text = f"{remaining:0.1f}"
            if remaining <= 0.0:
                self.game_state.song_start_time = now
                self.game_state.status_text = "GO!"
                if self.audio_manager and self.music_loaded:
                    self.audio_manager.play_music()
            return

        # Gameplay loop
        game_time = now - self.game_state.song_start_time
        
        # Spawn and update notes
        self._spawn_notes(game_time)
        if self.note_manager:
            self.note_manager.update_notes(now, self.game_state.song_start_time, self.hit_zone_camera)
        
        # Process judgments
        if self.mode_strategy and hit_events:
            self.mode_strategy.on_hit_events(hit_events, now)
        
        if self.judgment_processor:
            active_notes = self.note_manager.get_active_notes() if self.note_manager else []
            self.judgment_processor.process_hit_events(
                game_time,
                hit_events,
                active_notes,
                self.game_state.song_start_time,
                self.timing_offset,
                now
            )
            # 창 크기가 변경되었을 수 있으므로 스케일 업데이트
            if self.judgment_processor:
                self.judgment_processor.x_scale = self.x_scale
                self.judgment_processor.y_scale = self.y_scale
            
            self.judgment_processor.process_weave_judgments(game_time, active_notes, now)
            self.judgment_processor.process_misses(game_time, active_notes, now)
        
        # Cleanup hit notes
        if self.note_manager:
            self.note_manager.cleanup_hit_notes()

        # Update hit effect system
        if self.last_update_time > 0:
            delta_time = now - self.last_update_time
            delta_time = min(delta_time, 0.1)
            self.hit_effect_system.update(now, delta_time)
        self.last_update_time = now

        # Check completion
        if self.note_manager and self._is_chart_completed():
            self._trigger_finish(now)

    def draw_scene(self) -> None:
        width = self.window.width
        height = self.window.height

        # Draw background
        if self.background_sprite_list:
            self.background_sprite_list.draw()

        # Status text
        arcade.draw_text(
            self.game_state.status_text,
            width / 2,
            height - 100,
            arcade.color.AQUA,
            font_size=20,
            anchor_x="center",
        )

        # Hit zone
        hit_zone_x, hit_zone_y = self.to_arcade_xy(self.hit_zone_camera)
        hit_color = self.hit_zone_color_rgb
        if self.mode_strategy:
            hit_color = self.mode_strategy.get_hit_zone_color(hit_color)
        
        # 스케일 적용 (평균 스케일 사용)
        scale = (self.x_scale + self.y_scale) / 2.0
        scaled_radius = self.hit_zone_radius * scale
        scaled_thickness = self.hit_zone_thickness * scale
        arcade.draw_circle_outline(hit_zone_x, hit_zone_y, int(scaled_radius), hit_color, int(scaled_thickness))

        # Draw Dodge lines
        self._draw_dodge_lines(width, height)

        # Draw notes
        if self.note_manager:
            coord_converter = self.to_arcade_xy
            color_converter = self.bgr_to_rgb
            for note in self.note_manager.get_active_notes():
                note.draw(height, color_converter, coord_converter, self.x_scale, self.y_scale)

        # Draw hit effects
        self.hit_effect_system.draw()

        # Draw pose markers
        self._draw_pose_markers()

        # Draw HUD
        stats_x = 40
        stats_y = height - 60
        arcade.draw_text(f"Score: {self.game_state.score}", stats_x, stats_y, arcade.color.LIGHT_GREEN, 20)
        arcade.draw_text(f"Combo: {self.game_state.combo}", stats_x, stats_y - 30, arcade.color.LIGHT_GREEN, 18)
        arcade.draw_text(f"Max Combo: {self.game_state.max_combo}", stats_x, stats_y - 60, arcade.color.LIGHT_GREEN, 18)
        arcade.draw_text(f"Last: {self.game_state.last_judgement_type or '-'}", stats_x, stats_y - 90, arcade.color.LIGHT_GREEN, 18)

        # Draw judgement text
        if self.game_state.last_judgement_type:
            age = time.time() - self.game_state.last_judgement_time
            if age < 1.0:
                judge_color_bgr = self.config_colors.get("judgement", {}).get(self.game_state.last_judgement_type, (255, 255, 255))
                judge_color_rgb = self.bgr_to_rgb(tuple(judge_color_bgr))
                arcade.draw_text(
                    self.game_state.last_judgement_type,
                    width / 2,
                    hit_zone_y - 200,
                    judge_color_rgb,
                    font_size=28,
                    anchor_x="center",
                )

        if self.mode_strategy:
            self.mode_strategy.draw_hud()
            self.mode_strategy.draw_additional(time.time())

    def _draw_pose_markers(self) -> None:
        """캘리브레이션 화면과 동일한 스타일로 랜드마크를 그립니다."""
        marker_radius = 8 * max(self.x_scale, self.y_scale, 1.0)

        if self.last_nose_pos:
            self._draw_marker(self.last_nose_pos, arcade.color.GOLD, marker_radius)

        if self.last_right_fist:
            self._draw_marker(self.last_right_fist, arcade.color.LIGHT_SKY_BLUE, marker_radius)

        if self.last_left_fist:
            self._draw_marker(self.last_left_fist, arcade.color.SALMON, marker_radius)

    def _draw_marker(self, pos: Tuple[float, float], color: Tuple[int, int, int], radius: float) -> None:
        """마커를 그립니다."""
        cx, cy = self.to_arcade_xy(pos)
        arcade.draw_circle_filled(cx, cy, radius, color)
        arcade.draw_circle_outline(cx, cy, radius + 2, arcade.color.WHITE, 2)

    def _draw_dodge_lines(self, width: int, height: int) -> None:
        """Dodge 라인을 그립니다."""
        center_x = width / 2
        line_offset = 180 * self.x_scale
        
        left_line_x = center_x - line_offset
        center_line_x = center_x
        right_line_x = center_x + line_offset
        
        top_y = height * 0.9
        bottom_y = height * 0.1
        
        neon_red = (255, 0, 0)
        neon_red_glow = (255, 100, 100)
        line_thickness = 1
        glow_thickness = 3
        
        def draw_neon_line(x: float, y1: float, y2: float, is_dashed: bool = False) -> None:
            if is_dashed:
                dash_length = 8
                gap_length = 4
                current_y = y1
                while current_y < y2:
                    end_y = min(current_y + dash_length, y2)
                    arcade.draw_line(x, current_y, x, end_y, neon_red_glow, glow_thickness)
                    arcade.draw_line(x, current_y, x, end_y, neon_red, line_thickness)
                    current_y += dash_length + gap_length
            else:
                arcade.draw_line(x, y1, x, y2, neon_red_glow, glow_thickness)
                arcade.draw_line(x, y1, x, y2, neon_red, line_thickness)
        
        draw_neon_line(left_line_x, bottom_y, top_y, is_dashed=False)
        draw_neon_line(center_line_x, bottom_y, top_y, is_dashed=True)
        draw_neon_line(right_line_x, bottom_y, top_y, is_dashed=False)

    def _load_background(self) -> None:
        """배경 이미지를 로드합니다."""
        try:
            bg_path = os.path.join("assets", "images", "arena_bg.jpg")
            if os.path.exists(bg_path):
                self.background_sprite = arcade.Sprite(bg_path, center_x=0, center_y=0)
                self.background_sprite_list = arcade.SpriteList()
                self.background_sprite_list.append(self.background_sprite)
                self.background_configured = False
                logger.info(f"배경 이미지 로드됨: {bg_path}")
            else:
                logger.warning(f"배경 이미지를 찾을 수 없습니다: {bg_path}")
                self.background_sprite = None
                self.background_sprite_list = None
        except Exception as e:
            logger.error(f"배경 이미지 로드 실패: {e}")
            self.background_sprite = None
            self.background_sprite_list = None

    def _configure_background(self) -> None:
        """배경 스프라이트를 설정합니다."""
        if self.background_sprite:
            window_width = getattr(self.window, "width", 0) or 0
            window_height = getattr(self.window, "height", 0) or 0
            if window_width > 0 and window_height > 0:
                self.background_sprite.center_x = window_width / 2
                self.background_sprite.center_y = window_height / 2
                if self.background_sprite.width > 0 and self.background_sprite.height > 0:
                    scale_x = window_width / self.background_sprite.width
                    scale_y = window_height / self.background_sprite.height
                    self.background_sprite.scale = max(scale_x, scale_y) * 1.01
                self.background_configured = True

    def _load_difficulty_settings(self) -> None:
        """난이도 설정을 로드합니다."""
        levels = self.config_difficulty.get("levels", {})
        default_level = self.config_difficulty.get("default")
        difficulty = levels.get(default_level) or next(iter(levels.values()), {})

        base_timing = self.config_difficulty.get(
            "judge_timing_base",
            {"perfect": 0.25, "great": 0.4, "good": 0.6},
        )
        scale = float(difficulty.get("judge_timing_scale", 1.0))
        self.judge_timing = {key: float(value) * scale for key, value in base_timing.items()}
        self.pre_spawn_time = float(difficulty.get("pre_spawn_time", 1.2))
        self.score_multiplier = float(difficulty.get("score_multiplier", 1.0))

    def _load_beatmap(self) -> None:
        """비트맵을 로드합니다."""
        beatmap_dir = os.path.join("assets", "beatmaps", "song1")
        self.beatmap_items = self.beatmap_loader.load_beatmap(beatmap_dir)

    def _spawn_notes(self, game_time: float) -> None:
        """노트를 스폰합니다."""
        if not self.note_manager:
            return
        
        while self.beatmap_index < len(self.beatmap_items):
            item = self.beatmap_items[self.beatmap_index]
            spawn_time = item.get("t", 0.0) - self.pre_spawn_time
            if game_time < spawn_time:
                break
            
            self.note_manager.spawn_note(
                item,
                self.window.width,
                self.window.height,
                self.hit_zone_camera
            )
            self.beatmap_index += 1

    def _is_chart_completed(self) -> bool:
        """차트가 완료되었는지 확인합니다."""
        if not self.note_manager:
            return False
        return self.note_manager.is_chart_completed(self.beatmap_index, len(self.beatmap_items))

    def _trigger_finish(self, now: float) -> None:
        """게임 종료를 트리거합니다."""
        if not self.game_state.game_finished:
            self.game_state.game_finished = True
            self.game_state.finish_trigger_time = now
            self.game_state.status_text = "Finished!"
            if self.audio_manager:
                self.audio_manager.stop_music()
    
    def is_point_inside_hit_zone(self, point: Optional[Tuple[float, float]]) -> bool:
        """점이 히트존 안에 있는지 확인합니다."""
        if point is None:
            return False
        hx, hy = self.hit_zone_camera
        px, py = point
        radius = self.hit_zone_radius / max(self.x_scale, 1e-6)
        return (px - hx) ** 2 + (py - hy) ** 2 <= radius ** 2

