from __future__ import annotations

import json
import os
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import arcade

from core.hit_effect import HitEffectSystem
from core.note import Note
from scenes.base_scene import BaseScene
from scenes.game_mode_strategy import GameModeStrategy
from scenes.normal_mode_strategy import NormalModeStrategy
from scenes.test_mode_strategy import TestModeStrategy
from judgment_logic import JudgmentLogic
from constants import (
    DODGE_LEFT_LINE_X, DODGE_CENTER_LINE_X, DODGE_RIGHT_LINE_X,
    DODGE_LINE_Y_TOP, DODGE_LINE_Y_BOTTOM,
    COLOR_DODGE_LINE, SCREEN_WIDTH, SCREEN_HEIGHT
)


class GameScene(BaseScene):
    """Arcade 기반 게임 플레이 씬."""

    def __init__(self, window: arcade.Window, audio_manager, config: Dict[str, Any], pose_tracker) -> None:
        super().__init__(window, audio_manager, config, pose_tracker)

        self.config_rules = config.get("rules", {})
        self.config_ui = config.get("ui", {})
        self.config_colors = self.config_ui.get("colors", {})
        self.config_difficulty = config.get("difficulty", {})

        # Gameplay state
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.status_text: str = "Ready!"

        self.hit_zone_camera: Tuple[int, int] = (0, 0)
        self.duck_line_camera: int = 0
        self.hit_zone_radius: float = 80.0
        self.hit_zone_thickness: int = 6
        self.hit_zone_color_rgb: Tuple[int, int, int] = (255, 255, 255)
        self.duck_line_color_rgb: Tuple[int, int, int] = (0, 255, 0)

        self.mode_strategy: Optional[GameModeStrategy] = None

        self.active_notes: List[Note] = []
        self.beatmap_items: List[Dict[str, Any]] = []
        self.beatmap_index: int = 0

        self.countdown_duration: float = 3.0
        self.countdown_start: Optional[float] = None
        self.song_start_time: Optional[float] = None
        self.game_finished: bool = False
        self.finish_delay: float = 2.5
        self.finish_trigger_time: Optional[float] = None
        self.music_loaded: bool = False

        self.judge_log: Deque[str] = deque(maxlen=10)
        self.last_judgement_type: Optional[str] = None
        self.last_judgement_time: float = 0.0

        self.last_nose_pos: Optional[Tuple[float, float]] = None
        self.last_left_fist: Optional[Tuple[float, float]] = None
        self.last_right_fist: Optional[Tuple[float, float]] = None

        self.test_mode: bool = False

        self.pre_spawn_time: float = 1.0
        self.judge_timing: Dict[str, float] = {"perfect": 0.2, "great": 0.35, "good": 0.5}
        self.score_values: Dict[str, int] = self.config_rules.get("score_base", {})
        self.score_multiplier: float = 1.0
        self.timing_offset: float = float(self.config_rules.get("timing_offset", 0.0))
        self.bomb_penalty: int = int(self.config_rules.get("bomb_penalty", -500))

        # Hit effect system
        self.hit_effect_system: HitEffectSystem = HitEffectSystem()
        self.last_update_time: float = 0.0

        # Background image
        self.background_sprite: Optional[arcade.Sprite] = None
        self.background_sprite_list: Optional[arcade.SpriteList] = None
        self.background_configured: bool = False

        # Judgment logic for weave detection
        self.judgment_logic: JudgmentLogic = JudgmentLogic()

    def on_resize(self, width: int, height: int) -> None:
        """창 크기 변경 시 배경을 다시 설정합니다."""
        super().on_resize(width, height)
        # Reset background configuration flag to allow reconfiguration
        self.background_configured = False
        self._configure_background()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
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
        
        # Configure background sprite position and scale once
        self._configure_background()

    def startup(self, persistent_data):
        super().startup(persistent_data)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.status_text = "Get Ready!"
        self.countdown_start = None
        self.song_start_time = None
        self.game_finished = False
        self.finish_trigger_time = None
        self.last_judgement_type = None
        self.last_judgement_time = 0.0
        self.judge_log.clear()
        self.last_nose_pos = None
        self.last_left_fist = None
        self.last_right_fist = None
        self.test_mode = bool(persistent_data.get("test_mode", False))

        self.hit_effect_system.clear()
        self.last_update_time = 0.0

        # Load background image
        self._load_background()
        # Configure background after loading
        self._configure_background()

        self._load_difficulty_settings()
        self._load_beatmap()
        self.active_notes = []
        self.beatmap_index = 0
        self._update_strategy()
        if self.pose_tracker:
            self.pose_tracker.set_test_mode(self.test_mode)
        if self.audio_manager:
            music_path = os.path.join("assets", "beatmaps", "song1", "music.mp3")
            self.music_loaded = self.audio_manager.load_music(music_path)

    def cleanup(self) -> Dict[str, Any]:
        self.persistent_data.update(
            {
                "score": self.score,
                "combo": self.combo,
                "max_combo": self.max_combo,
                "final_score": self.score,
                "test_mode": self.test_mode,
            }
        )
        return super().cleanup() 

    # ------------------------------------------------------------------ #
    # Input handling
    # ------------------------------------------------------------------ #
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.T:
            self._toggle_test_mode()

    def _toggle_test_mode(self) -> None:
        self.test_mode = not self.test_mode
        state = "enabled" if self.test_mode else "disabled"
        print(f"[GameScene] Test mode {state}.")
        self._update_strategy()
        if self.pose_tracker:
            self.pose_tracker.set_test_mode(self.test_mode)
        for note in self.active_notes:
            note.test_mode = self.test_mode

    def _update_strategy(self) -> None:
        self.mode_strategy = TestModeStrategy(self) if self.test_mode else NormalModeStrategy(self)

    # ------------------------------------------------------------------ #
    # Update loop
    # ------------------------------------------------------------------ #
    def update(self, delta_time: float, **kwargs: Any) -> None:
        super().update(delta_time, **kwargs)

        frame = kwargs.get("frame")
        hit_events = kwargs.get("hit_events", []) or []
        landmarks = kwargs.get("landmarks")
        now = kwargs.get("now", time.time())

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

        if self.game_finished:
            if self.finish_trigger_time and (now - self.finish_trigger_time) > self.finish_delay:
                self.next_scene_name = "RESULT"
            return

        if frame is None:
            self.status_text = "카메라 영상 대기 중..."
            return

        if self.pose_tracker and landmarks is None:
            self.status_text = "포즈 분석 중..."
        else:
            self.status_text = "READY" if not self.song_start_time else "GO!"

        if self.song_start_time is None:
            if self.countdown_start is None:
                self.countdown_start = now
            remaining = max(0.0, self.countdown_duration - (now - self.countdown_start))
            self.status_text = f"{remaining:0.1f}"
            if remaining <= 0.0:
                self.song_start_time = now
                self.status_text = "GO!"
                if self.audio_manager and self.music_loaded:
                    self.audio_manager.play_music()
            return

        game_time = now - self.song_start_time
        self._spawn_notes(game_time)
        self._update_notes(now)
        if self.mode_strategy and hit_events:
            self.mode_strategy.on_hit_events(hit_events, now)
        self._process_hit_events(game_time, hit_events, now)
        # 위빙 판정 처리 (코 위치 기반)
        self._process_weave_judgments(game_time, now)
        self._process_misses(game_time, now)

        # Update hit effect system
        if self.last_update_time > 0:
            delta_time = now - self.last_update_time
            # Clamp delta_time to reasonable values to prevent large jumps
            delta_time = min(delta_time, 0.1)
            self.hit_effect_system.update(now, delta_time)
        self.last_update_time = now

        if self._is_chart_completed():
            self._trigger_finish(now)

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def draw_scene(self) -> None:
        width = self.window.width
        height = self.window.height

        # Draw background image first (bottom layer) - position and scale are fixed
        if self.background_sprite_list:
            self.background_sprite_list.draw()

        arcade.draw_text(
            " ",
            width / 2,
            height - 60,
            arcade.color.WHITE,
            font_size=30,
            anchor_x="center",
        )

        arcade.draw_text(
            self.status_text,
            width / 2,
            height - 100,
            arcade.color.AQUA,
            font_size=20,
            anchor_x="center",
        )

        hit_zone_x, hit_zone_y = self.to_arcade_xy(self.hit_zone_camera)
        hit_color = self.hit_zone_color_rgb
        if self.mode_strategy:
            hit_color = self.mode_strategy.get_hit_zone_color(hit_color)
        arcade.draw_circle_outline(hit_zone_x, hit_zone_y, self.hit_zone_radius, hit_color, self.hit_zone_thickness)

        # Draw Dodge lines (위빙 판정용 수직선 3개)
        self._draw_dodge_lines(width, height)

        coord_converter = self.to_arcade_xy
        color_converter = self.bgr_to_rgb
        for note in self.active_notes:
            note.draw(self.window.height, color_converter, coord_converter)

        # Draw hit effects (after notes, before HUD)
        self.hit_effect_system.draw()

        # Draw pose markers (always visible, like calibration screen)
        self._draw_pose_markers()

        stats_x = 40
        stats_y = height - 60
        arcade.draw_text(f"Score: {self.score}", stats_x, stats_y, arcade.color.LIGHT_GREEN, 20)
        arcade.draw_text(f"Combo: {self.combo}", stats_x, stats_y - 30, arcade.color.LIGHT_GREEN, 18)
        arcade.draw_text(f"Max Combo: {self.max_combo}", stats_x, stats_y - 60, arcade.color.LIGHT_GREEN, 18)
        arcade.draw_text(f"Last: {self.last_judgement_type or '-'}", stats_x, stats_y - 90, arcade.color.LIGHT_GREEN, 18)

        if self.last_judgement_type:
            age = time.time() - self.last_judgement_time
            if age < 1.0:
                judge_color_bgr = self.config_colors.get("judgement", {}).get(self.last_judgement_type, (255, 255, 255))
                judge_color_rgb = self.bgr_to_rgb(tuple(judge_color_bgr))
                arcade.draw_text(
                    self.last_judgement_type,
                    width / 2,
                    hit_zone_y - 200,
                    judge_color_rgb,
                    font_size=28,
                    anchor_x="center",
                )

        if self.mode_strategy:
            self.mode_strategy.draw_hud()
            self.mode_strategy.draw_additional(time.time())

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _draw_pose_markers(self) -> None:
        """캘리브레이션 화면과 동일한 스타일로 랜드마크를 그립니다."""
        marker_radius = 8 * max(self.x_scale, self.y_scale, 1.0)

        if self.last_nose_pos:
            self._draw_marker(self.last_nose_pos, arcade.color.GOLD, marker_radius)

        # 화면 기준 왼쪽 = 실제 오른손 (right_fist)
        if self.last_right_fist:
            self._draw_marker(self.last_right_fist, arcade.color.LIGHT_SKY_BLUE, marker_radius)

        # 화면 기준 오른쪽 = 실제 왼손 (left_fist)
        if self.last_left_fist:
            self._draw_marker(self.last_left_fist, arcade.color.SALMON, marker_radius)

    def _draw_marker(self, pos: Tuple[float, float], color: Tuple[int, int, int], radius: float) -> None:
        """캘리브레이션 화면과 동일한 스타일로 마커를 그립니다 (색상 원 + 흰색 외곽선)."""
        cx, cy = self.to_arcade_xy(pos)
        arcade.draw_circle_filled(cx, cy, radius, color)
        arcade.draw_circle_outline(cx, cy, radius + 2, arcade.color.WHITE, 2)

    def _draw_dodge_lines(self, width: int, height: int) -> None:
        """Dodge 라인(위빙 판정용 수직선)을 네온 효과와 함께 그립니다."""
        center_x = width / 2
        line_offset = 180 * self.x_scale  # 스케일 적용
        
        left_line_x = center_x - line_offset
        center_line_x = center_x
        right_line_x = center_x + line_offset
        
        # Y 좌표 변환 (상단/하단)
        top_y = height * 0.9
        bottom_y = height * 0.1
        
        # 네온 빨간색 (밝은 빨간색)
        neon_red = (255, 0, 0)
        neon_red_glow = (255, 100, 100)  # 글로우용 밝은 빨간색
        line_thickness = 1  # 얇게
        glow_thickness = 3  # 글로우 레이어
        
        def draw_neon_line(x: float, y1: float, y2: float, is_dashed: bool = False) -> None:
            """네온 효과가 있는 선을 그립니다."""
            if is_dashed:
                # 점선: 작은 선분들을 반복
                dash_length = 8
                gap_length = 4
                current_y = y1
                while current_y < y2:
                    # 글로우 레이어 (점선)
                    end_y = min(current_y + dash_length, y2)
                    arcade.draw_line(x, current_y, x, end_y, neon_red_glow, glow_thickness)
                    # 메인 레이어 (점선)
                    arcade.draw_line(x, current_y, x, end_y, neon_red, line_thickness)
                    current_y += dash_length + gap_length
            else:
                # 실선: 글로우 레이어 먼저
                arcade.draw_line(x, y1, x, y2, neon_red_glow, glow_thickness)
                # 메인 레이어
                arcade.draw_line(x, y1, x, y2, neon_red, line_thickness)
        
        # 왼쪽 라인 (실선, 네온 효과)
        draw_neon_line(left_line_x, bottom_y, top_y, is_dashed=False)
        
        # 중앙 라인 (점선, 네온 효과)
        draw_neon_line(center_line_x, bottom_y, top_y, is_dashed=True)
        
        # 오른쪽 라인 (실선, 네온 효과)
        draw_neon_line(right_line_x, bottom_y, top_y, is_dashed=False)

    def _load_background(self) -> None:
        """배경 이미지를 로드합니다."""
        try:
            bg_path = os.path.join("assets", "images", "arena_bg.jpg")
            if os.path.exists(bg_path):
                # Create sprite for background image
                self.background_sprite = arcade.Sprite(bg_path, center_x=0, center_y=0)
                # Create sprite list for drawing
                self.background_sprite_list = arcade.SpriteList()
                self.background_sprite_list.append(self.background_sprite)
                self.background_configured = False
                print(f"[GameScene] 배경 이미지 로드됨: {bg_path}")
            else:
                print(f"[GameScene] 배경 이미지를 찾을 수 없습니다: {bg_path}")
                self.background_sprite = None
                self.background_sprite_list = None
                self.background_configured = False
        except Exception as e:
            print(f"[GameScene] 배경 이미지 로드 실패: {e}")
            self.background_sprite = None
            self.background_sprite_list = None
            self.background_configured = False

    def _configure_background(self) -> None:
        """배경 스프라이트의 위치와 스케일을 설정하여 화면을 완전히 채웁니다."""
        if self.background_sprite:
            window_width = getattr(self.window, "width", 0) or 0
            window_height = getattr(self.window, "height", 0) or 0
            if window_width > 0 and window_height > 0:
                # Set position to center of window
                self.background_sprite.center_x = window_width / 2
                self.background_sprite.center_y = window_height / 2
                # Scale sprite to cover entire window (add small margin to ensure full coverage)
                if self.background_sprite.width > 0 and self.background_sprite.height > 0:
                    scale_x = window_width / self.background_sprite.width
                    scale_y = window_height / self.background_sprite.height
                    # Use max to ensure image covers entire screen, add 0.01 margin for safety
                    self.background_sprite.scale = max(scale_x, scale_y) * 1.01
                self.background_configured = True

    def _load_difficulty_settings(self) -> None:
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
        beatmap_dir = os.path.join("assets", "beatmaps", "song1")
        text_path = os.path.join(beatmap_dir, "beatmap.txt")
        json_path = os.path.join(beatmap_dir, "beatmap.json")

        if os.path.exists(text_path):
            self.beatmap_items = self._parse_text_beatmap(text_path)
        else:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.beatmap_items = json.load(f)
            except FileNotFoundError:
                print(f"[경고] 비트맵 파일을 찾을 수 없습니다. ({beatmap_dir})")
                self.beatmap_items = []
        self.beatmap_items = [item for item in self.beatmap_items if item.get("type") != "END"]
        self.beatmap_items.sort(key=lambda item: item.get("t", 0.0))

    def _parse_text_beatmap(self, text_path: str) -> List[Dict[str, Any]]:
        mapping = {"0": None, "1": "JAB_L", "2": "JAB_R", "3": "WEAVE_L", "4": "WEAVE_R"}
        song_info = self.config_difficulty.get("song_info", {})
        bpm = float(song_info.get("bpm", 120))
        division = int(song_info.get("division", 4))
        start_delay = float(song_info.get("start_delay", 0.0))

        seconds_per_step = 60.0 / max(1e-6, bpm) / max(1, division)
        step_index = 0
        beatmap: List[Dict[str, Any]] = []

        with open(text_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                for ch in line:
                    note_type = mapping.get(ch)
                    if note_type:
                        beatmap.append({"t": start_delay + step_index * seconds_per_step, "type": note_type})
                    step_index += 1
        return beatmap

    def _spawn_notes(self, game_time: float) -> None:
        while self.beatmap_index < len(self.beatmap_items):
            item = self.beatmap_items[self.beatmap_index]
            spawn_time = item.get("t", 0.0) - self.pre_spawn_time
            if game_time < spawn_time:
                break
            note = Note(
                item,
                max(1, self.source_width or self.window.width),
                max(1, self.source_height or self.window.height),
                int((self.source_height or self.window.height) * 0.7),
                self.pre_spawn_time,
                self.config_colors.get("notes", {}),
                self.judge_timing,
                self.test_mode,
                self.config_ui.get("styles", {}).get("notes", {}),
            )
            self.active_notes.append(note)
            self.beatmap_index += 1

    def _update_notes(self, now: float) -> None:
        if self.song_start_time is None:
            return
        for note in self.active_notes:
            note.update(now, self.song_start_time, self.hit_zone_camera)

    def _process_hit_events(self, game_time: float, hit_events: List[Dict[str, Any]], now: float) -> None:
        if not hit_events:
            return
        
        jab_events = [e for e in hit_events if e.get("type") in ["JAB_L", "JAB_R"]]
        if self.test_mode and jab_events:
            print(f"[GAME] Received {len(jab_events)} JAB events, game_time={game_time:.2f}, song_start_time={self.song_start_time}, active_notes={len(self.active_notes)}")
        
        for event in hit_events:
            # 이미 사용된 이벤트는 건너뛰기
            if event.get("used", False):
                continue
            
            note_type = event.get("type")
            event_time = event.get("t_hit", now)
            # hit_events의 시간(t_hit)을 게임 시간으로 변환
            # event_time은 절대 시간이므로, song_start_time을 빼서 게임 시간으로 변환
            # timing_offset을 더해 타이밍 보정 적용
            if self.song_start_time:
                adjusted_time = (event_time - self.song_start_time) + self.timing_offset
            else:
                adjusted_time = 0.0
                if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                    print(f"[GAME WARN] song_start_time is None for {note_type}, adjusted_time=0.0")
            
            # 노트 매칭: 이벤트 시간에 가장 가까운 미판정 노트 찾기
            candidate = self._find_best_matching_note(note_type, adjusted_time)
            if not candidate:
                if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                    # 디버깅: 왜 매칭 실패했는지 확인
                    candidates_all = [n for n in self.active_notes if n.typ == note_type and not n.hit and not n.missed]
                    print(f"[GAME] No candidate for {note_type}: adjusted_time={adjusted_time:.2f}, all_candidates={len(candidates_all)}")
                    
                    # active_notes의 모든 해당 타입 노트 상태 확인
                    all_notes_of_type = [n for n in self.active_notes if n.typ == note_type]
                    if all_notes_of_type:
                        print(f"[GAME] All {note_type} notes in active_notes:")
                        for n in all_notes_of_type:
                            print(f"  - t={n.t:.2f}, hit={n.hit}, missed={n.missed}, delta_from_event={abs(n.t - adjusted_time):.2f}")
                    
                    # beatmap에서 다음 노트 확인
                    future_notes = [item for item in self.beatmap_items[self.beatmap_index:] if item.get("type") == note_type]
                    if future_notes:
                        next_note = future_notes[0]
                        next_note_time = next_note.get("t", 0.0)
                        print(f"[GAME] Next {note_type} in beatmap: t={next_note_time:.2f}, spawn_time={next_note_time - self.pre_spawn_time:.2f}")
                    
                    if candidates_all:
                        closest = min(candidates_all, key=lambda n: abs(n.t - adjusted_time))
                        delta_closest = abs(closest.t - adjusted_time)
                        max_window = max(
                            self.judge_timing.get("perfect", 0.2),
                            self.judge_timing.get("great", 0.35),
                            self.judge_timing.get("good", 0.5)
                        ) + 0.1
                        print(f"[GAME] Closest note: t={closest.t:.2f}, delta={delta_closest:.2f}, max_window={max_window:.2f}")
                continue
            
            # 판정 등급 결정
            delta = abs(adjusted_time - candidate.t)
            judgement = self._determine_judgement(delta)
            if judgement is None:
                if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                    print(f"[GAME] No judgement for {note_type}: delta={delta:.3f}, thresholds={self.judge_timing}")
                continue
            
            # 판정 등록: 점수 및 콤보 업데이트
            self._register_hit(candidate, judgement, delta, now)
            if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                print(f"[GAME SUCCESS] {note_type} -> {judgement} (delta={delta:.3f}s)")
            
            # 이벤트 소비: 판정에 성공한 hit_event는 사용 표시하여 재사용 방지
            event["used"] = True

    def _find_best_matching_note(self, note_type: Optional[str], adjusted_time: float) -> Optional[Note]:
        if note_type is None:
            return None
        candidates = [note for note in self.active_notes if note.typ == note_type and not note.hit and not note.missed]
        if not candidates:
            return None
        
        # 판정 창 내의 노트만 필터링 (가장 넓은 판정 창 사용)
        max_window = max(
            self.judge_timing.get("perfect", 0.2),
            self.judge_timing.get("great", 0.35),
            self.judge_timing.get("good", 0.5)
        )
        # 추가 여유 시간(0.1초)을 더해 더 관대하게 처리
        max_window += 0.1
        
        valid_candidates = [
            note for note in candidates 
            if abs(note.t - adjusted_time) <= max_window
        ]
        
        if not valid_candidates:
            return None
        
        return min(valid_candidates, key=lambda note: abs(note.t - adjusted_time))

    def _determine_judgement(self, delta: float) -> Optional[str]:
        thresholds = [
            ("PERFECT", self.judge_timing.get("perfect", 0.2)),
            ("GREAT", self.judge_timing.get("great", 0.35)),
            ("GOOD", self.judge_timing.get("good", 0.5)),
        ]
        for judge, window in thresholds:
            if delta <= window:
                return judge
        return None

    def _register_hit(self, note: Note, judgement: str, delta: float, now: float) -> None:
        note.hit = True
        note.judge_result = judgement
        self.last_judgement_type = judgement
        self.last_judgement_time = now
        self.judge_log.appendleft(f"{judgement} ({note.typ}) Δ={delta:0.3f}")

        base_score = self.score_values.get(judgement, 0)
        gained = int(base_score * self.score_multiplier)
        self.score += gained
        if judgement == "MISS":
            self.combo = 0
        else:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)

        # Spawn hit effect at hit zone center
        hit_zone_arcade = self.to_arcade_xy(self.hit_zone_camera)
        judgement_color_bgr = self.config_colors.get("judgement", {}).get(judgement, (255, 255, 255))
        judgement_color_rgb = self.bgr_to_rgb(tuple(judgement_color_bgr))
        self.hit_effect_system.spawn_effect(
            hit_zone_arcade[0],
            hit_zone_arcade[1],
            judgement,
            judgement_color_rgb,
            now,
        )

        if self.audio_manager:
            sfx_key = judgement if judgement in self.score_values else "MISS"
            self.audio_manager.play_sfx(sfx_key)

    def _process_weave_judgments(self, game_time: float, now: float) -> None:
        """위빙 비트에 대한 판정을 처리합니다 (코 위치 기반)."""
        if not self.pose_tracker:
            return

        # 위빙 타입 노트만 필터링
        weave_notes = [
            note for note in self.active_notes
            if note.typ in ["WEAVE_L", "WEAVE_R"] and not note.hit and not note.missed
        ]

        for note in weave_notes:
            # 시간 판정: 판정 창에 도달했는지 확인
            time_diff = abs(game_time - note.t)
            from constants import JUDGMENT_WINDOW
            if time_diff > JUDGMENT_WINDOW:
                continue  # 아직 판정 시간 아님

            # JudgmentLogic을 사용하여 판정
            judgment = self.judgment_logic.check_hit(
                note,
                self.pose_tracker,
                game_time,
                self.window.width,
                self.window.height
            )

            if judgment == 'HIT':
                # HIT 판정
                delta = time_diff
                judgement = self._determine_judgement(delta)
                if judgement:
                    self._register_hit(note, judgement, delta, now)
            elif judgment == 'MISS':
                # MISS 판정 (시간이 지났거나 위치가 맞지 않음)
                note.missed = True
                note.judge_result = "MISS"
                self.last_judgement_type = "MISS"
                self.last_judgement_time = now
                self.judge_log.appendleft(f"MISS ({note.typ})")
                self.combo = 0

                # Spawn miss effect at note position
                note_pos_arcade = self.to_arcade_xy((note.x, note.y))
                miss_color_bgr = self.config_colors.get("judgement", {}).get("MISS", (255, 255, 255))
                miss_color_rgb = self.bgr_to_rgb(tuple(miss_color_bgr))
                self.hit_effect_system.spawn_effect(
                    note_pos_arcade[0],
                    note_pos_arcade[1],
                    "MISS",
                    miss_color_rgb,
                    now,
                )

                if self.audio_manager:
                    self.audio_manager.play_sfx("MISS")

    def _process_misses(self, game_time: float, now: float) -> None:
        # MISS 판정 창을 good 창보다 약간 더 크게 설정 (1.2배)
        miss_window = self.judge_timing.get("good", 0.5) * 1.2
        for note in self.active_notes:
            if note.hit or note.missed:
                continue
            # 위빙 노트는 별도 처리하므로 제외
            if note.typ in ["WEAVE_L", "WEAVE_R"]:
                continue
            if game_time > note.t + miss_window:
                note.missed = True
                note.judge_result = "MISS"
                self.last_judgement_type = "MISS"
                self.last_judgement_time = now
                self.judge_log.appendleft(f"MISS ({note.typ})")
                self.combo = 0
                
                # Spawn miss effect at note position
                note_pos_arcade = self.to_arcade_xy((note.x, note.y))
                miss_color_bgr = self.config_colors.get("judgement", {}).get("MISS", (255, 255, 255))
                miss_color_rgb = self.bgr_to_rgb(tuple(miss_color_bgr))
                self.hit_effect_system.spawn_effect(
                    note_pos_arcade[0],
                    note_pos_arcade[1],
                    "MISS",
                    miss_color_rgb,
                    now,
                )
                
                if self.audio_manager:
                    self.audio_manager.play_sfx("MISS")
        self.active_notes = [note for note in self.active_notes if not note.hit and not note.missed]

    def _is_chart_completed(self) -> bool:
        if self.beatmap_index < len(self.beatmap_items):
            return False
        return not any(not note.hit and not note.missed for note in self.active_notes)

    def _trigger_finish(self, now: float) -> None:
        if not self.game_finished:
            self.game_finished = True
            self.finish_trigger_time = now
            self.status_text = "Finished!"
            if self.audio_manager:
                self.audio_manager.stop_music()

    def is_point_inside_hit_zone(self, point: Optional[Tuple[float, float]]) -> bool:
        if point is None:
            return False
        hx, hy = self.hit_zone_camera
        px, py = point
        radius = self.hit_zone_radius / max(self.x_scale, 1e-6)
        return (px - hx) ** 2 + (py - hy) ** 2 <= radius ** 2