from __future__ import annotations

import math
from typing import Optional

import arcade
import mediapipe as mp
import numpy as np

from core.pose_data_collector import PoseDataCollector
from scenes.game_mode_strategy import GameModeStrategy

mp_pose = mp.solutions.pose


class TestModeStrategy(GameModeStrategy):
    """테스트 모드 전략: Arcade 디버그 HUD."""

    def __init__(self, game_scene) -> None:
        super().__init__(game_scene)
        self.event_history: list[tuple[str, float]] = []
        self.max_history = 20
        self.last_judge_log_size = 0  # 판정 로그 크기 추적
        # 포즈 데이터 수집기 초기화 (테스트 모드에서만 활성화)
        self.pose_data_collector = PoseDataCollector(test_mode=True)

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
        
        # 다음 노트 찾기
        next_note_text = ""
        next_note_color = arcade.color.YELLOW
        
        # 전체 노트 수와 잔여 노트 수 계산
        total_notes = len(self.game_scene.beatmap_items) if self.game_scene.beatmap_items else 0
        remaining_notes = 0
        
        if self.game_scene.note_manager and self.game_scene.game_state.song_start_time is not None and self.game_scene.game_state.song_start_time > 0:
            import time
            now = time.time()
            game_time = now - self.game_scene.game_state.song_start_time - self.game_scene.timing_offset
            
            active_notes = self.game_scene.note_manager.get_active_notes()
            # 아직 판정되지 않은 노트 중 가장 가까운 다음 노트 찾기
            upcoming_notes = [
                note for note in active_notes
                if not note.hit and not note.missed and note.t > game_time
            ]
            
            # 잔여 노트 수 계산: 아직 스폰되지 않은 노트 + 아직 판정되지 않은 active 노트
            # 아직 스폰되지 않은 노트 수
            unspawned_notes = max(0, total_notes - self.game_scene.beatmap_index)
            # 아직 판정되지 않은 active 노트 수
            unjudged_active_notes = len([note for note in active_notes if not note.hit and not note.missed])
            remaining_notes = unspawned_notes + unjudged_active_notes
            
            if upcoming_notes:
                # 가장 가까운 노트 선택
                next_note = min(upcoming_notes, key=lambda n: n.t)
                note_type = next_note.typ
                
                # 노트 타입에 따른 라벨 매핑
                type_to_label = {
                    "GUARD": "Guard",
                    "JAB_L": "Jab",
                    "JAB_R": "Straight",
                    "WEAVE_L": "Weaving (L)",
                    "WEAVE_R": "Weaving (R)",
                    "DUCK": "D",
                    "BOMB": "4"
                }
                label = type_to_label.get(note_type, note_type)
                time_until = next_note.t - game_time
                next_note_text = f"{label} ({time_until:.2f}s) ({remaining_notes}/{total_notes})"
            else:
                # 활성 노트가 있지만 모두 판정된 경우
                if active_notes:
                    next_note_text = f"다음 노트: 대기 중... ({remaining_notes}/{total_notes})"
                else:
                    next_note_text = f"다음 노트: 없음 ({remaining_notes}/{total_notes})"
        else:
            # 게임이 시작되지 않았을 때
            remaining_notes = total_notes
            next_note_text = f"대기 중... ({remaining_notes}/{total_notes})"
        
        arcade.draw_text(
            next_note_text,
            width / 2,
            height - 10,  # 최상단으로 이동
            next_note_color,
            font_size=36,
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
        
        # 판정 결과 텍스트 (PERFECT, GREAT, GOOD, MISS) - 헤더 위에 표시
        if game_scene.game_state.last_judgement_type:
            import time
            age = time.time() - game_scene.game_state.last_judgement_time
            if age < 1.0:
                judge_color_bgr = game_scene.config_colors.get("judgement", {}).get(
                    game_scene.game_state.last_judgement_type, (255, 255, 255)
                )
                judge_color_rgb = game_scene.bgr_to_rgb(tuple(judge_color_bgr))
                arcade.draw_text(
                    game_scene.game_state.last_judgement_type,
                    panel_start_x + 10,
                    header_y + 30,  # 헤더 위에 표시
                    judge_color_rgb,
                    font_size=24,
                    bold=True,
                )
        
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
        # self._draw_skeleton(width, height, game_scene)  # 주석 처리: 스켈레톤 표시 비활성화
        
        # 포즈 판정 데이터 표시
        pose_data = self._calculate_pose_data(game_scene)
        if pose_data and len(pose_data) > 0:
            current_pose = self._detect_current_pose(pose_data)
            # 디버깅: 포즈 판별 결과 확인
            if current_pose == "UNKNOWN":
                # UNKNOWN일 때도 기본 데이터 표시 (디버깅용)
                # 실제로는 조건을 완화해야 할 수 있음
                pass
            self._draw_pose_data_labels(game_scene, pose_data, current_pose)
    
    def check_and_collect_pose_data(self, game_time: float, active_notes: list, judge_timing: dict) -> None:
        """
        노트가 hit area에 도달했는지 확인하고 포즈 데이터를 수집합니다.
        
        Args:
            game_time: 현재 게임 시간
            active_notes: 활성 노트 리스트
            judge_timing: 판정 타이밍 딕셔너리
        """
        if not self.pose_data_collector or not self.pose_data_collector.test_mode:
            return
        
        # 판정 창 크기 (good 창 사용)
        judgment_window = judge_timing.get("good", 0.5)
        
        for note in active_notes:
            # 이미 수집된 노트는 건너뛰기
            if note.pose_data_collected:
                continue
            
            # 노트가 hit area에 도달했는지 확인 (판정 창 내에 있는지)
            time_diff = abs(game_time - note.t)
            if time_diff <= judgment_window:
                # 포즈 데이터 계산
                pose_data = self._calculate_pose_data(self.game_scene)
                
                if pose_data and len(pose_data) > 0:
                    # 포즈 데이터 수집
                    self.pose_data_collector.collect_data(note.typ, pose_data)
                    # 수집 완료 플래그 설정
                    note.pose_data_collected = True
    
    def save_pose_data(self) -> Optional[str]:
        """
        수집된 포즈 데이터를 CSV 파일로 저장합니다.
        
        Returns:
            저장된 파일 경로, 실패 시 None
        """
        if self.pose_data_collector:
            return self.pose_data_collector.save_to_csv()
        return None

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
    
    def _calculate_distance(self, pos1: tuple, pos2: tuple) -> float:
        """두 점 사이의 거리를 계산합니다."""
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)
    
    def _calculate_angle_from_nose(self, nose: tuple, target: tuple) -> float:
        """코에서 목표점까지의 각도를 계산합니다 (0-360도, Y축 반전)."""
        dx = target[0] - nose[0]
        dy = nose[1] - target[1]  # Y축 반전
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360
        return angle_deg
    
    def _calculate_arm_angle(self, shoulder: tuple, elbow: tuple, wrist: tuple) -> float:
        """팔의 각도를 계산합니다 (어깨-팔꿈치-손목, 0-180도)."""
        v1 = np.array([shoulder[0] - elbow[0], shoulder[1] - elbow[1]])
        v2 = np.array([wrist[0] - elbow[0], wrist[1] - elbow[1]])
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 > 0 and norm2 > 0:
            cos_angle = np.dot(v1, v2) / (norm1 * norm2)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle_rad = math.acos(cos_angle)
            return math.degrees(angle_rad)
        return 0.0
    
    def _get_midpoint(self, pos1: tuple, pos2: tuple) -> tuple:
        """두 점의 중간점을 반환합니다."""
        return ((pos1[0] + pos2[0]) / 2, (pos1[1] + pos2[1]) / 2)
    
    def _calculate_pose_data(self, game_scene) -> dict:
        """5가지 포즈 판정 기준 데이터를 계산합니다."""
        if not game_scene.pose_tracker:
            return {}
        
        landmarks = game_scene.pose_tracker.get_smoothed_landmarks()
        if not landmarks:
            return {}
        
        # last_left_fist와 last_right_fist 사용 (game_scene에서 업데이트된 값)
        left_fist = game_scene.last_left_fist
        right_fist = game_scene.last_right_fist
        nose = game_scene.last_nose_pos
        
        # 최소한 nose가 있어야 데이터 계산 가능
        if not nose:
            return {}
        
        shoulder_width = game_scene.pose_tracker.calib_data.get("shoulder_w", 300)
        screen_width = game_scene.window.width
        
        shoulders = landmarks.get("shoulders")
        if shoulders and isinstance(shoulders, tuple) and len(shoulders) >= 2:
            left_shoulder = shoulders[0]
            right_shoulder = shoulders[1]
        else:
            left_shoulder = None
            right_shoulder = None
        left_elbow = landmarks.get("left_elbow")
        right_elbow = landmarks.get("right_elbow")
        left_wrist = landmarks.get("left_wrist")
        right_wrist = landmarks.get("right_wrist")
        
        data = {}
        
        # 왼손 데이터 (left_fist가 있으면 계산)
        if nose and left_fist and shoulder_width > 0:
            # 왼손 거리
            dist = self._calculate_distance(nose, left_fist)
            data["left_fist_dist"] = dist / shoulder_width
            
            # 왼손 각도
            data["left_fist_angle"] = self._calculate_angle_from_nose(nose, left_fist)
        elif nose and shoulder_width > 0:
            # left_fist가 없어도 기본값 설정 (디버깅용)
            data["left_fist_dist"] = 0.0
            data["left_fist_angle"] = 0.0
        
        # 오른손 데이터 (right_fist가 있으면 계산)
        if nose and right_fist and shoulder_width > 0:
            # 오른손 거리
            dist = self._calculate_distance(nose, right_fist)
            data["right_fist_dist"] = dist / shoulder_width
            
            # 오른손 각도
            data["right_fist_angle"] = self._calculate_angle_from_nose(nose, right_fist)
        elif nose and shoulder_width > 0:
            # right_fist가 없어도 기본값 설정 (디버깅용)
            data["right_fist_dist"] = 0.0
            data["right_fist_angle"] = 0.0
        
        if left_shoulder and left_elbow and left_wrist:
            # 왼팔 각도
            data["left_arm_angle"] = self._calculate_arm_angle(left_shoulder, left_elbow, left_wrist)
        
        if right_shoulder and right_elbow and right_wrist:
            # 오른팔 각도
            data["right_arm_angle"] = self._calculate_arm_angle(right_shoulder, right_elbow, right_wrist)
        
        if nose and shoulder_width > 0:
            # 코 위치 (화면 중앙 기준)
            # nose는 이미 카메라 좌표이므로 화면 좌표로 변환
            nose_screen_x, nose_screen_y = game_scene.to_arcade_xy(nose)
            center_x = screen_width / 2
            data["nose_position"] = (nose_screen_x - center_x) / shoulder_width
            # 코 높이 (어깨 평균 높이 기준)
            if left_shoulder and right_shoulder:
                left_shoulder_screen = game_scene.to_arcade_xy(left_shoulder)
                right_shoulder_screen = game_scene.to_arcade_xy(right_shoulder)
                shoulder_avg_y = (left_shoulder_screen[1] + right_shoulder_screen[1]) / 2
                data["nose_above_shoulder"] = nose_screen_y > shoulder_avg_y
        
        return data
    
    def _detect_current_pose(self, pose_data: dict) -> str:
        """현재 포즈를 판별합니다."""
        # ① 가드 (Guard Stance)
        left_dist = pose_data.get("left_fist_dist", 0)
        left_angle = pose_data.get("left_fist_angle", 0)
        right_dist = pose_data.get("right_fist_dist", 0)
        right_angle = pose_data.get("right_fist_angle", 0)
        
        guard_ok = (
            0.1 < left_dist < 0.3 and 10 < left_angle < 80 and
            0.2 < right_dist < 0.5 and 100 < right_angle < 170
        )
        
        # ② 왼손 잽 (Jab Left)
        left_arm_angle = pose_data.get("left_arm_angle", 0)
        jab_left_ok = (
            left_arm_angle > 150 and
            0.2 < right_dist < 0.5
        )
        
        # ③ 오른손 스트레이트 (Straight Right)
        right_arm_angle = pose_data.get("right_arm_angle", 0)
        straight_right_ok = (
            right_arm_angle > 150 and
            right_dist > 0.8 and
            0.1 < left_dist < 0.3
        )
        
        # ④ 위빙 좌 (Weave Left)
        nose_pos = pose_data.get("nose_position", 0)
        nose_above = pose_data.get("nose_above_shoulder", False)
        weave_left_ok = (
            guard_ok and
            0.2 < nose_pos < 0.5 and
            nose_above
        )
        
        # ⑤ 위빙 우 (Weave Right)
        weave_right_ok = (
            guard_ok and
            -0.5 < nose_pos < -0.2 and
            nose_above
        )
        
        # 우선순위: 공격 포즈 > 위빙 > 가드
        if jab_left_ok:
            return "JAB_LEFT"
        elif straight_right_ok:
            return "STRAIGHT_RIGHT"
        elif weave_left_ok:
            return "WEAVE_LEFT"
        elif weave_right_ok:
            return "WEAVE_RIGHT"
        elif guard_ok:
            return "GUARD"
        else:
            return "UNKNOWN"
    
    def _draw_data_label(self, pos: tuple, text: str, game_scene) -> None:
        """데이터 레이블을 그립니다."""
        if pos is None:
            return
        try:
            arcade_x, arcade_y = game_scene.to_arcade_xy(pos)
            arcade.draw_text(
                text,
                arcade_x + 10,  # 랜드마크 오른쪽에 표시
                arcade_y,
                arcade.color.WHITE,
                font_size=14,  # 폰트 크기 증가
                anchor_x="left",
                anchor_y="center",
                bold=True  # 굵게 표시
            )
        except Exception as e:
            # 좌표 변환 실패 시 무시
            pass
    
    def _draw_pose_data_labels(self, game_scene, pose_data: dict, current_pose: str) -> None:
        """포즈 판정 데이터를 랜드마크 위치에 숫자로 표시합니다."""
        landmarks = game_scene.pose_tracker.get_smoothed_landmarks() if game_scene.pose_tracker else None
        
        # UNKNOWN일 때는 기본 데이터만 표시
        if current_pose == "UNKNOWN":
            # 기본 데이터 표시: 왼손/오른손 거리와 각도
            if game_scene.last_nose_pos and game_scene.last_left_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_left_fist)
                if "left_fist_dist" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"L:{pose_data['left_fist_dist']:.2f}",
                        game_scene
                    )
                if "left_fist_angle" in pose_data:
                    self._draw_data_label(
                        game_scene.last_left_fist,
                        f"{pose_data['left_fist_angle']:.1f}°",
                        game_scene
                    )
            
            if game_scene.last_nose_pos and game_scene.last_right_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_right_fist)
                if "right_fist_dist" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"R:{pose_data['right_fist_dist']:.2f}",
                        game_scene
                    )
                if "right_fist_angle" in pose_data:
                    self._draw_data_label(
                        game_scene.last_right_fist,
                        f"{pose_data['right_fist_angle']:.1f}°",
                        game_scene
                    )
            
            # 코 위치 표시
            if game_scene.last_nose_pos and "nose_position" in pose_data:
                self._draw_data_label(
                    game_scene.last_nose_pos,
                    f"N:{pose_data['nose_position']:.2f}",
                    game_scene
                )
            return
        
        # ① 가드 (Guard Stance)
        if current_pose == "GUARD":
            # 왼손 거리와 각도 (코-왼손 중간점에 표시)
            if game_scene.last_nose_pos and game_scene.last_left_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_left_fist)
                if "left_fist_dist" in pose_data and "left_fist_angle" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"{pose_data['left_fist_dist']:.1f}",
                        game_scene
                    )
                    # 각도는 왼손 위치에 표시
                    self._draw_data_label(
                        game_scene.last_left_fist,
                        f"{pose_data['left_fist_angle']:.1f}°",
                        game_scene
                    )
            
            # 오른손 거리와 각도 (코-오른손 중간점에 표시)
            if game_scene.last_nose_pos and game_scene.last_right_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_right_fist)
                if "right_fist_dist" in pose_data and "right_fist_angle" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"{pose_data['right_fist_dist']:.1f}",
                        game_scene
                    )
                    # 각도는 오른손 위치에 표시
                    self._draw_data_label(
                        game_scene.last_right_fist,
                        f"{pose_data['right_fist_angle']:.1f}°",
                        game_scene
                    )
        
        # ② 왼손 잽 (Jab Left)
        elif current_pose == "JAB_LEFT":
            # 왼팔 각도 (팔꿈치 위치에 표시)
            if landmarks:
                left_elbow = landmarks.get("left_elbow")
                if left_elbow and "left_arm_angle" in pose_data:
                    self._draw_data_label(
                        left_elbow,
                        f"{pose_data['left_arm_angle']:.1f}°",
                        game_scene
                    )
            
            # 오른손 거리 (코-오른손 중간점에 표시)
            if game_scene.last_nose_pos and game_scene.last_right_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_right_fist)
                if "right_fist_dist" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"{pose_data['right_fist_dist']:.1f}",
                        game_scene
                    )
        
        # ③ 오른손 스트레이트 (Straight Right)
        elif current_pose == "STRAIGHT_RIGHT":
            # 오른팔 각도 (팔꿈치 위치에 표시)
            if landmarks:
                right_elbow = landmarks.get("right_elbow")
                if right_elbow and "right_arm_angle" in pose_data:
                    self._draw_data_label(
                        right_elbow,
                        f"{pose_data['right_arm_angle']:.1f}°",
                        game_scene
                    )
            
            # 오른손 거리 (코-오른손 중간점에 표시)
            if game_scene.last_nose_pos and game_scene.last_right_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_right_fist)
                if "right_fist_dist" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"{pose_data['right_fist_dist']:.1f}",
                        game_scene
                    )
            
            # 왼손 거리 (코-왼손 중간점에 표시)
            if game_scene.last_nose_pos and game_scene.last_left_fist:
                mid_point = self._get_midpoint(game_scene.last_nose_pos, game_scene.last_left_fist)
                if "left_fist_dist" in pose_data:
                    self._draw_data_label(
                        mid_point,
                        f"{pose_data['left_fist_dist']:.1f}",
                        game_scene
                    )
        
        # ④ 위빙 좌 (Weave Left)
        elif current_pose == "WEAVE_LEFT":
            # 코 위치 (코 위치에 표시)
            if game_scene.last_nose_pos and "nose_position" in pose_data:
                self._draw_data_label(
                    game_scene.last_nose_pos,
                    f"{pose_data['nose_position']:.1f}",
                    game_scene
                )
        
        # ⑤ 위빙 우 (Weave Right)
        elif current_pose == "WEAVE_RIGHT":
            # 코 위치 (코 위치에 표시)
            if game_scene.last_nose_pos and "nose_position" in pose_data:
                self._draw_data_label(
                    game_scene.last_nose_pos,
                    f"{pose_data['nose_position']:.1f}",
                    game_scene
                )


