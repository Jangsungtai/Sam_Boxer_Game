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
        self.last_judge_log_size = 0  # 판정 로그 크기 추적

    def handle_hits(self, hit_events, t_game, now, **kwargs) -> None:
        """히트 이벤트를 받아서 이벤트 히스토리에 추가합니다."""
        if hit_events:
            for ev in hit_events:
                event_type = ev.get("type", "UNKNOWN")
                self.event_history.append((event_type, now))
            # 최대 개수 제한
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history :]

    def _draw_mode_specific_hud(self) -> None:
        width = self.game_scene.window.width
        height = self.game_scene.window.height
        arcade.draw_text(
            "Test Mode",
            width / 2,
            height - 10,  # 최상단으로 이동
            arcade.color.YELLOW,
            font_size=48,
            anchor_x="center",
            anchor_y="top",
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

        # 오른쪽 판정창 전체 설정 (박스 오른쪽을 화면 오른쪽과 얼라인)
        panel_box_width = 300  # 박스 너비 약간 감소
        panel_right_padding = 10  # 화면 오른쪽에서 10픽셀 여백
        panel_start_x = width - panel_box_width - panel_right_padding  # 왼쪽으로 이동
        panel_start_y = height - 60
        debug_line_height = 18
        
        # ===== 1. 판정 창 정보 (현재 노트) - 맨 위 =====
        debug_info_start_y = panel_start_y
        debug_box_height = 340  # 박스 높이 증가 (글자 겹침 방지)
        
        # 배경 박스
        debug_box_center_x = panel_start_x + panel_box_width / 2
        debug_box_center_y = debug_info_start_y - debug_box_height / 2
        debug_box_points = [
            (debug_box_center_x - panel_box_width / 2, debug_box_center_y - debug_box_height / 2),
            (debug_box_center_x + panel_box_width / 2, debug_box_center_y - debug_box_height / 2),
            (debug_box_center_x + panel_box_width / 2, debug_box_center_y + debug_box_height / 2),
            (debug_box_center_x - panel_box_width / 2, debug_box_center_y + debug_box_height / 2),
        ]
        arcade.draw_polygon_filled(debug_box_points, (0, 0, 0, 180))
        
        # 헤더 (한글과 영문 분리 - 영문은 별도 줄, 박스 안쪽 상단)
        header_y = debug_info_start_y - 40  # 20픽셀 아래로 이동
        arcade.draw_text(
            "판정 창 정보",
            panel_start_x + 10,
            header_y,
            arcade.color.CYAN,
            font_size=15,
            bold=True,
        )
        # 영문 부분 (다음 줄에 표시, 폰트 크기 줄임)
        arcade.draw_text(
            "(Judgment Windows)",
            panel_start_x + 10,
            header_y - 22,  # 한글 아래 줄 (간격 증가로 겹침 방지)
            arcade.color.CYAN,
            font_size=11,  # 15에서 4 줄임
            bold=False,
        )
        
        # 판정 창 정보
        judge_timing = game_scene.judge_timing
        # 헤더 영문이 debug_info_start_y - 62이므로, 그 아래 여유 공간을 확보하여 더 아래로
        current_y = debug_info_start_y - 85  # 헤더(한글+영문 2줄)와 간격 조정, 겹침 방지
        
        # 판정 창 시간
        arcade.draw_text(
            "PERFECT:",
            panel_start_x + 10,
            current_y,
            arcade.color.WHITE,
            font_size=13,
        )
        arcade.draw_text(
            f"±{judge_timing.get('perfect', 0.2):.2f}s",
            panel_start_x + 100,
            current_y,
            arcade.color.GOLD,
            font_size=13,
        )
        current_y -= debug_line_height
        
        arcade.draw_text(
            "GREAT:",
            panel_start_x + 10,
            current_y,
            arcade.color.WHITE,
            font_size=13,
        )
        arcade.draw_text(
            f"±{judge_timing.get('great', 0.35):.2f}s",
            panel_start_x + 100,
            current_y,
            arcade.color.ORANGE,
            font_size=13,
        )
        current_y -= debug_line_height
        
        arcade.draw_text(
            "GOOD:",
            panel_start_x + 10,
            current_y,
            arcade.color.WHITE,
            font_size=13,
        )
        arcade.draw_text(
            f"±{judge_timing.get('good', 0.5):.2f}s",
            panel_start_x + 100,
            current_y,
            arcade.color.YELLOW,
            font_size=13,
        )
        current_y -= debug_line_height * 1.5
        
        # 구분선
        arcade.draw_line(
            panel_start_x + 10,
            current_y,
            panel_start_x + panel_box_width - 10,
            current_y,
            arcade.color.GRAY,
            1
        )
        current_y -= debug_line_height * 0.5
        
        # 현재 노트 정보
        active_notes = game_scene.note_manager.get_active_notes() if game_scene.note_manager else []
        active_jab_notes = [n for n in active_notes if n.typ in ["JAB_L", "JAB_R", "WEAVE_L", "WEAVE_R"] and not n.hit and not n.missed]
        
        if game_scene.game_state.song_start_time:
            game_time = now - game_scene.game_state.song_start_time
            
            arcade.draw_text(
                "게임 시간:",
                panel_start_x + 10,
                current_y,
                arcade.color.WHITE,
                font_size=12,
            )
            arcade.draw_text(
                f"{game_time:.2f}s",
                panel_start_x + 120,
                current_y,
                arcade.color.LIGHT_BLUE,
                font_size=12,
            )
            current_y -= debug_line_height
            
            arcade.draw_text(
                "활성 노트:",
                panel_start_x + 10,
                current_y,
                arcade.color.WHITE,
                font_size=12,
            )
            arcade.draw_text(
                f"{len(active_jab_notes)}개",
                panel_start_x + 120,
                current_y,
                arcade.color.LIGHT_BLUE,
                font_size=12,
            )
            current_y -= debug_line_height * 2  # 간격 증가 (글자 겹침 방지)
            
            # 가장 가까운 노트 (현재 노트)
            if active_jab_notes:
                closest_note = min(active_jab_notes, key=lambda n: abs(n.t - game_time))
                time_diff = closest_note.t - game_time
                
                # 현재 노트 헤더 (한글과 영문 분리 - 영문은 별도 줄)
                arcade.draw_text(
                    "현재 노트",
                    panel_start_x + 10,
                    current_y,
                    arcade.color.LIGHT_YELLOW,
                    font_size=13,
                    bold=True,
                )
                # 영문 부분 (다음 줄에 표시, 폰트 크기 줄임)
                arcade.draw_text(
                    "(Current Note)",
                    panel_start_x + 10,
                    current_y - 18,  # 한글 아래 줄 (간격 증가로 겹침 방지)
                    arcade.color.LIGHT_YELLOW,
                    font_size=9,  # 13에서 4 줄임
                    bold=False,
                )
                current_y -= debug_line_height * 2.5  # 영문 줄 포함해서 간격 증가 (글자 겹침 방지)
                
                arcade.draw_text(
                    f"타입: {closest_note.typ}",
                    panel_start_x + 20,
                    current_y,
                    arcade.color.LIGHT_GREEN,
                    font_size=12,
                )
                current_y -= debug_line_height
                
                arcade.draw_text(
                    f"시간: {closest_note.t:.2f}s",
                    panel_start_x + 20,
                    current_y,
                    arcade.color.LIGHT_GRAY,
                    font_size=12,
                )
                current_y -= debug_line_height
                
                arcade.draw_text(
                    f"차이: {time_diff:+.3f}s",
                    panel_start_x + 20,
                    current_y,
                    arcade.color.LIGHT_GREEN if abs(time_diff) <= judge_timing.get('good', 0.5) else arcade.color.RED,
                    font_size=12,
                )
        
        # ===== 2. 판정 로그 - 중간 =====
        log_start_y = debug_info_start_y - debug_box_height - 20  # 간격 증가 (글자 겹침 방지)
        log_line_height = 16
        log_box_height = 10 * log_line_height + 80  # 박스 높이 증가 (헤더 및 내용 공간 확보)
        
        # 배경 박스
        log_box_center_x = panel_start_x + panel_box_width / 2
        log_box_center_y = log_start_y - log_box_height / 2
        log_box_points = [
            (log_box_center_x - panel_box_width / 2, log_box_center_y - log_box_height / 2),
            (log_box_center_x + panel_box_width / 2, log_box_center_y - log_box_height / 2),
            (log_box_center_x + panel_box_width / 2, log_box_center_y + log_box_height / 2),
            (log_box_center_x - panel_box_width / 2, log_box_center_y + log_box_height / 2),
        ]
        arcade.draw_polygon_filled(log_box_points, (0, 0, 0, 180))
        
        # 헤더 (한글과 영문 분리 - 영문은 별도 줄, 박스 안쪽 상단)
        log_header_y = log_start_y - 30  # 20픽셀 아래로 이동
        arcade.draw_text(
            "판정 로그",
            panel_start_x + 10,
            log_header_y,
            arcade.color.CYAN,
            font_size=14,
            bold=True,
        )
        # 영문 부분 (다음 줄에 표시, 폰트 크기 줄임)
        arcade.draw_text(
            "(Judgment Log)",
            panel_start_x + 10,
            log_header_y - 20,  # 한글 아래 줄 (간격 증가로 겹침 방지)
            arcade.color.CYAN,
            font_size=10,  # 14에서 4 줄임
            bold=False,
        )
        
        # 판정 로그 변경 사항을 이벤트 히스토리에 추가 (WEAVE_L, WEAVE_R 등 판정 결과 포함)
        current_judge_log_size = len(game_scene.game_state.judge_log)
        if current_judge_log_size > self.last_judge_log_size:
            # 새로운 판정이 추가됨
            judge_log_list = list(game_scene.game_state.judge_log)
            new_entries = judge_log_list[self.last_judge_log_size:]
            for entry in new_entries:
                # 판정 로그 형식: "PERFECT (JAB_L) Δ=0.106" 또는 "MISS (WEAVE_R) Δ=0.000"
                # 이벤트 히스토리에 추가 (간단한 형식으로)
                if "(" in entry and ")" in entry:
                    try:
                        event_type = entry.split("(")[1].split(")")[0]
                        self.event_history.append((event_type, now))
                    except (IndexError, ValueError):
                        # 파싱 실패 시 전체 항목 추가
                        self.event_history.append((entry.split()[0] if entry.split() else "UNKNOWN", now))
            self.last_judge_log_size = current_judge_log_size
            # 최대 개수 제한
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history :]
        
        # judge_log는 deque이므로 list로 변환
        judge_log_list = list(game_scene.game_state.judge_log)
        # 헤더 영문이 log_start_y - 50이므로, 그 아래 여유 공간을 확보하여 더 아래로
        for idx, entry in enumerate(judge_log_list):
            arcade.draw_text(
                entry,
                panel_start_x + 10,
                log_start_y - 80 - idx * log_line_height,  # 헤더(한글+영문 2줄)와 간격 조정, 겹침 방지
                arcade.color.LIGHT_GREEN,
                font_size=12,
            )

        # ===== 3. 최근 이벤트 기록 - 아래 =====
        event_start_y = log_start_y - log_box_height - 20  # 간격 증가 (글자 겹침 방지)
        event_line_height = 18
        event_box_height = 190  # 박스 높이 증가 (헤더 및 내용 공간 확보)
        
        # 배경 박스
        event_box_center_x = panel_start_x + panel_box_width / 2
        event_box_center_y = event_start_y - event_box_height / 2
        event_box_points = [
            (event_box_center_x - panel_box_width / 2, event_box_center_y - event_box_height / 2),
            (event_box_center_x + panel_box_width / 2, event_box_center_y - event_box_height / 2),
            (event_box_center_x + panel_box_width / 2, event_box_center_y + event_box_height / 2),
            (event_box_center_x - panel_box_width / 2, event_box_center_y + event_box_height / 2),
        ]
        arcade.draw_polygon_filled(event_box_points, (0, 0, 0, 180))
        
        # 헤더 (한글과 영문 분리 - 영문은 별도 줄, 박스 안쪽 상단)
        event_header_y = event_start_y - 30  # 20픽셀 아래로 이동
        arcade.draw_text(
            "최근 이벤트",
            panel_start_x + 10,
            event_header_y,
            arcade.color.LIGHT_YELLOW,
            font_size=14,
            bold=True,
        )
        # 영문 부분 (다음 줄에 표시, 폰트 크기 줄임)
        arcade.draw_text(
            "(Recent Events)",
            panel_start_x + 10,
            event_header_y - 20,  # 한글 아래 줄 (간격 증가로 겹침 방지)
            arcade.color.LIGHT_YELLOW,
            font_size=10,  # 14에서 4 줄임
            bold=False,
        )

        # 최근 이벤트 표시 (최대 6개)
        # 헤더 영문이 event_start_y - 50이므로, 그 아래 여유 공간을 확보하여 더 아래로
        for idx, (ev_type, ts) in enumerate(reversed(self.event_history[-6:])):
            age = now - ts
            arcade.draw_text(
                f"• {ev_type} ({age:0.1f}s 전)",
                panel_start_x + 10,
                event_start_y - 80 - idx * event_line_height,  # 헤더(한글+영문 2줄)와 간격 조정, 겹침 방지
                arcade.color.LIGHT_GRAY,
                font_size=12,
            )
        
        # 스켈레톤 표시 (중앙)
        self._draw_skeleton(width, height, game_scene)

    def _draw_skeleton(self, width: int, height: int, game_scene) -> None:
        """중앙에 스켈레톤을 그립니다."""
        if not game_scene.pose_tracker:
            return
        
        # pose_landmarks 가져오기 (update_data에서)
        update_data = getattr(game_scene.window, 'update_data', {})
        landmarks = update_data.get('landmarks')
        
        if not landmarks or not landmarks.landmark:
            return
        
        # 스켈레톤 박스 설정 (중앙)
        skeleton_box_width = 245
        skeleton_box_height = 300
        skeleton_box_x = (width - skeleton_box_width) / 2
        skeleton_box_y = (height + skeleton_box_height) / 2 - 200
        
        # # 반 투명 검은색
        box_points = [
            (skeleton_box_x, skeleton_box_y - skeleton_box_height),
            (skeleton_box_x + skeleton_box_width, skeleton_box_y - skeleton_box_height),
            (skeleton_box_x + skeleton_box_width, skeleton_box_y),
            (skeleton_box_x, skeleton_box_y),
        ]
        arcade.draw_polygon_filled(box_points, (0, 0, 0, 180))  # 반 투명 검은색
        
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
        """히트 이벤트를 받아서 처리합니다."""
        self.handle_hits(hit_events, t_game=0.0, now=now)
    
    def record_judgment_event(self, note_type: str, judgement: str, now: float) -> None:
        """판정 결과를 이벤트 히스토리에 추가합니다. (WEAVE_L, WEAVE_R 등 판정 결과 포함)"""
        # 판정 결과를 이벤트 히스토리에 추가
        self.event_history.append((f"{judgement} ({note_type})", now))
        # 최대 개수 제한
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history :]


