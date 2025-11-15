from __future__ import annotations

import arcade
import mediapipe as mp

from scenes.game_mode_strategy import GameModeStrategy

mp_pose = mp.solutions.pose


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
        width = self.game_scene.window.width
        height = self.game_scene.window.height
        arcade.draw_text(
            "Test Mode",
            width / 2,
            height / 2,
            arcade.color.YELLOW,
            font_size=48,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )

    def get_hit_zone_color(self, default_color):
        inside_left = self.game_scene.is_point_inside_hit_zone(self.game_scene.last_left_fist)
        inside_right = self.game_scene.is_point_inside_hit_zone(self.game_scene.last_right_fist)
        return arcade.color.GREEN if inside_left or inside_right else arcade.color.RED

    def draw_additional(self, now: float) -> None:
        game_scene = self.game_scene
        hit_center = game_scene.to_arcade_xy(game_scene.hit_zone_camera)
        width = game_scene.window.width
        height = game_scene.window.height

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

        # 판정 로그 (히트존 아래, 왼쪽 정렬)
        log_start_x = 40
        log_start_y = hit_center[1] - game_scene.hit_zone_radius * 1.5 - 20
        log_line_height = 18
        
        # 배경 박스
        log_box_width = 280
        log_box_height = min(len(game_scene.game_state.judge_log) * log_line_height + 30, 200)
        log_box_center_x = log_start_x + log_box_width / 2
        log_box_center_y = log_start_y - log_box_height / 2
        log_box_points = [
            (log_box_center_x - log_box_width / 2, log_box_center_y - log_box_height / 2),
            (log_box_center_x + log_box_width / 2, log_box_center_y - log_box_height / 2),
            (log_box_center_x + log_box_width / 2, log_box_center_y + log_box_height / 2),
            (log_box_center_x - log_box_width / 2, log_box_center_y + log_box_height / 2),
        ]
        arcade.draw_polygon_filled(log_box_points, (0, 0, 0))
        
        arcade.draw_text(
            "판정 로그 (Judgment Log)",
            log_start_x + 10,
            log_start_y + 5,
            arcade.color.CYAN,
            font_size=14,
            bold=True,
        )
        
        # judge_log는 deque이므로 list로 변환 (이미 maxlen=10으로 제한됨)
        judge_log_list = list(game_scene.game_state.judge_log)
        for idx, entry in enumerate(judge_log_list):
            arcade.draw_text(
                entry,
                log_start_x + 10,
                log_start_y - 15 - idx * log_line_height,
                arcade.color.LIGHT_GREEN,
                font_size=13,
            )

        # 이벤트 히스토리 (왼쪽 하단)
        event_start_x = 40
        event_start_y = 180
        event_line_height = 20
        
        # 배경 박스
        event_box_width = 250
        event_box_height = 120
        event_box_center_x = event_start_x + event_box_width / 2
        event_box_center_y = event_start_y + event_box_height / 2 - 20
        event_box_points = [
            (event_box_center_x - event_box_width / 2, event_box_center_y - event_box_height / 2),
            (event_box_center_x + event_box_width / 2, event_box_center_y - event_box_height / 2),
            (event_box_center_x + event_box_width / 2, event_box_center_y + event_box_height / 2),
            (event_box_center_x - event_box_width / 2, event_box_center_y + event_box_height / 2),
        ]
        arcade.draw_polygon_filled(event_box_points, (0, 0, 0))
        
        arcade.draw_text(
            "최근 이벤트 (Recent Events)",
            event_start_x + 10,
            event_start_y + event_line_height * 2 + 5,
            arcade.color.LIGHT_YELLOW,
            font_size=14,
            bold=True,
        )

        for idx, (ev_type, ts) in enumerate(reversed(self.event_history[-5:])):
            age = now - ts
            arcade.draw_text(
                f"• {ev_type} ({age:0.1f}s 전)",
                event_start_x + 10,
                event_start_y + idx * event_line_height,
                arcade.color.LIGHT_GRAY,
                font_size=13,
            )
        
        # 판정 디버깅 정보 (오른쪽 상단)
        debug_start_x = width - 320
        debug_start_y = height - 80
        debug_line_height = 20
        
        # 배경 박스
        debug_box_width = 300
        debug_box_height = 300
        debug_box_center_x = debug_start_x + debug_box_width / 2
        debug_box_center_y = debug_start_y - debug_box_height / 2 + 40
        debug_box_points = [
            (debug_box_center_x - debug_box_width / 2, debug_box_center_y - debug_box_height / 2),
            (debug_box_center_x + debug_box_width / 2, debug_box_center_y - debug_box_height / 2),
            (debug_box_center_x + debug_box_width / 2, debug_box_center_y + debug_box_height / 2),
            (debug_box_center_x - debug_box_width / 2, debug_box_center_y + debug_box_height / 2),
        ]
        arcade.draw_polygon_filled(debug_box_points, (0, 0, 0))
        
        arcade.draw_text(
            "판정 창 정보 (Judgment Windows)",
            debug_start_x + 10,
            debug_start_y + 5,
            arcade.color.CYAN,
            font_size=15,
            bold=True,
        )
        
        # 판정 창 정보
        judge_timing = game_scene.judge_timing
        y_offset = 1
        arcade.draw_text(
            "PERFECT:",
            debug_start_x + 10,
            debug_start_y - debug_line_height * y_offset,
            arcade.color.WHITE,
            font_size=13,
        )
        arcade.draw_text(
            f"±{judge_timing.get('perfect', 0.2):.2f}s",
            debug_start_x + 100,
            debug_start_y - debug_line_height * y_offset,
            arcade.color.GOLD,
            font_size=13,
        )
        
        y_offset = 2
        arcade.draw_text(
            "GREAT:",
            debug_start_x + 10,
            debug_start_y - debug_line_height * y_offset,
            arcade.color.WHITE,
            font_size=13,
        )
        arcade.draw_text(
            f"±{judge_timing.get('great', 0.35):.2f}s",
            debug_start_x + 100,
            debug_start_y - debug_line_height * y_offset,
            arcade.color.ORANGE,
            font_size=13,
        )
        
        y_offset = 3
        arcade.draw_text(
            "GOOD:",
            debug_start_x + 10,
            debug_start_y - debug_line_height * y_offset,
            arcade.color.WHITE,
            font_size=13,
        )
        arcade.draw_text(
            f"±{judge_timing.get('good', 0.5):.2f}s",
            debug_start_x + 100,
            debug_start_y - debug_line_height * y_offset,
            arcade.color.YELLOW,
            font_size=13,
        )
        
        # 구분선
        arcade.draw_line(
            debug_start_x + 10,
            debug_start_y - debug_line_height * 3.5,
            debug_start_x + debug_box_width - 10,
            debug_start_y - debug_line_height * 3.5,
            arcade.color.GRAY,
            1
        )
        
        # 활성 노트 정보
        active_notes = game_scene.note_manager.get_active_notes() if game_scene.note_manager else []
        active_jab_notes = [n for n in active_notes if n.typ in ["JAB_L", "JAB_R"] and not n.hit and not n.missed]
        if game_scene.game_state.song_start_time:
            game_time = now - game_scene.game_state.song_start_time
            y_offset = 5
            arcade.draw_text(
                "게임 시간 (Game Time):",
                debug_start_x + 10,
                debug_start_y - debug_line_height * y_offset,
                arcade.color.WHITE,
                font_size=13,
            )
            arcade.draw_text(
                f"{game_time:.2f}s",
                debug_start_x + 200,
                debug_start_y - debug_line_height * y_offset,
                arcade.color.LIGHT_BLUE,
                font_size=13,
            )
            
            y_offset = 6
            arcade.draw_text(
                "활성 JAB 노트 (Active JAB):",
                debug_start_x + 10,
                debug_start_y - debug_line_height * y_offset,
                arcade.color.WHITE,
                font_size=13,
            )
            arcade.draw_text(
                f"{len(active_jab_notes)}개",
                debug_start_x + 200,
                debug_start_y - debug_line_height * y_offset,
                arcade.color.LIGHT_BLUE,
                font_size=13,
            )
            
            # 가장 가까운 노트 정보 표시
            if active_jab_notes:
                closest_note = min(active_jab_notes, key=lambda n: abs(n.t - game_time))
                time_diff = closest_note.t - game_time
                
                y_offset = 8
                arcade.draw_text(
                    "가장 가까운 노트 (Closest Note):",
                    debug_start_x + 10,
                    debug_start_y - debug_line_height * y_offset,
                    arcade.color.WHITE,
                    font_size=13,
                )
                
                y_offset = 9
                arcade.draw_text(
                    f"타입: {closest_note.typ}",
                    debug_start_x + 20,
                    debug_start_y - debug_line_height * y_offset,
                    arcade.color.LIGHT_GREEN,
                    font_size=12,
                )
                
                y_offset = 10
                arcade.draw_text(
                    f"노트 시간: {closest_note.t:.2f}s",
                    debug_start_x + 20,
                    debug_start_y - debug_line_height * y_offset,
                    arcade.color.LIGHT_GRAY,
                    font_size=12,
                )
                
                y_offset = 11
                arcade.draw_text(
                    f"시간 차이 (Δ): {time_diff:+.3f}s",
                    debug_start_x + 20,
                    debug_start_y - debug_line_height * y_offset,
                    arcade.color.LIGHT_GREEN if abs(time_diff) <= judge_timing.get('good', 0.5) else arcade.color.RED,
                    font_size=12,
                )
        
        # 스켈레톤 표시 (오른쪽 하단)
        self._draw_skeleton(width, height, game_scene)

    def _draw_skeleton(self, width: int, height: int, game_scene) -> None:
        """오른쪽 하단에 스켈레톤을 그립니다."""
        if not game_scene.pose_tracker:
            return
        
        # pose_landmarks 가져오기 (update_data에서)
        update_data = getattr(game_scene.window, 'update_data', {})
        landmarks = update_data.get('landmarks')
        
        if not landmarks or not landmarks.landmark:
            return
        
        # 스켈레톤 박스 설정
        skeleton_box_width = 200
        skeleton_box_height = 300
        skeleton_box_x = width - skeleton_box_width - 20
        skeleton_box_y = skeleton_box_height + 20
        
        # 파란색 배경 박스
        box_points = [
            (skeleton_box_x, skeleton_box_y - skeleton_box_height),
            (skeleton_box_x + skeleton_box_width, skeleton_box_y - skeleton_box_height),
            (skeleton_box_x + skeleton_box_width, skeleton_box_y),
            (skeleton_box_x, skeleton_box_y),
        ]
        arcade.draw_polygon_filled(box_points, (50, 100, 200))  # 파란색 배경
        
        # 랜드마크 추출
        lm = landmarks.landmark
        
        # 좌표 변환 함수 (카메라 좌표 -> 스켈레톤 박스 내 좌표)
        def to_skeleton_box(landmark):
            if landmark is None:
                return None
            # visibility 체크 제거 - 가려진 랜드마크도 표시
            # 랜드마크를 스켈레톤 박스 크기에 맞게 스케일링
            # MediaPipe 좌표는 0-1 범위이므로 카메라 크기로 변환 후 박스 크기로 스케일
            x_cam = landmark.x * game_scene.source_width
            y_cam = landmark.y * game_scene.source_height
            
            # 박스 내부 좌표로 변환 (중앙 정렬, 상하 반전)
            # 스케일 팩터를 조정하여 전체 몸이 보이도록
            scale_factor = 0.25
            x_box = skeleton_box_x + skeleton_box_width / 2 + (x_cam - game_scene.source_width / 2) * scale_factor
            y_box = skeleton_box_y - skeleton_box_height / 2 - (y_cam - game_scene.source_height / 2) * scale_factor
            
            # 박스 범위 내로 제한
            x_box = max(skeleton_box_x + 5, min(skeleton_box_x + skeleton_box_width - 5, x_box))
            y_box = max(skeleton_box_y - skeleton_box_height + 5, min(skeleton_box_y - 5, y_box))
            
            # visibility 정보도 함께 반환
            return (x_box, y_box, landmark.visibility)
        
        # 모든 랜드마크를 박스 좌표로 변환 (33개 랜드마크 모두, visibility 체크 없음)
        points = {}
        for idx in range(len(lm)):
            landmark = lm[idx]
            result = to_skeleton_box(landmark)
            if result:
                points[idx] = result  # (x, y, visibility) 튜플
        
        # MediaPipe Pose 표준 연결 구조 사용 (33개 랜드마크 전체 연결)
        connections = mp_pose.POSE_CONNECTIONS
        
        # 스켈레톤 그리기 (선)
        # visibility에 따라 색상 조정
        for start_idx, end_idx in connections:
            start_data = points.get(start_idx)
            end_data = points.get(end_idx)
            if start_data and end_data:
                start_point = (start_data[0], start_data[1])
                end_point = (end_data[0], end_data[1])
                start_vis = start_data[2]
                end_vis = end_data[2]
                
                # visibility가 낮으면 회색, 높으면 흰색
                avg_vis = (start_vis + end_vis) / 2.0
                if avg_vis < 0.5:
                    line_color = (150, 150, 150)  # 회색 (가려진 부분)
                else:
                    line_color = arcade.color.WHITE  # 흰색 (보이는 부분)
                
                arcade.draw_line(*start_point, *end_point, line_color, 1)
        
        # 랜드마크 점 그리기 (모든 랜드마크)
        for idx, point_data in points.items():
            if point_data:
                x, y, visibility = point_data
                # visibility에 따라 색상 조정
                if visibility < 0.5:
                    point_color = (150, 150, 150)  # 회색 (가려진 부분)
                else:
                    point_color = arcade.color.YELLOW  # 노란색 (보이는 부분)
                arcade.draw_circle_filled(x, y, 2, point_color)

    def on_hit_events(self, hit_events, now: float) -> None:
        self.handle_hits(hit_events, t_game=0.0, now=now)


