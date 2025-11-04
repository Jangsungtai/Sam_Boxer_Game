# scenes/test_mode_strategy.py

import cv2
import numpy as np
import time
from scenes.game_mode_strategy import GameModeStrategy

class TestModeStrategy(GameModeStrategy):
    """테스트 모드 전략: 디버깅 정보를 포함한 판정 및 시각화"""
    
    def handle_hits(self, hit_events, t_game, now):
        """테스트 모드: 공간 + 타이밍 모두 체크, 노트가 히트존에 도달했는지 확인"""
        for ev in hit_events:
            ev_type = ev["type"]
            t_hit = ev["t_hit"]
            
            if ev_type.startswith("JAB"):
                # BOMB 체크는 공통 로직
                bombs = [n for n in self.game_scene.active_notes if n.typ == "BOMB" and not n.hit and not n.missed]
                for b in bombs:
                    dt = t_hit - (self.game_scene.state['start_time'] + b.t)
                    if abs(dt) < self.game_scene.judge_timing['good']:
                        b.hit = True
                        self.game_scene._add_judgement("BOMB!", "BOMB", pos=(b.x, b.y))
                        return
                
                candidates = [n for n in self.game_scene.active_notes if n.typ == ev_type and not n.hit and not n.missed]
                if not candidates:
                    continue
                
                target_note = min(candidates, key=lambda n: abs(t_hit - (self.game_scene.state['start_time'] + n.t)))
                timing_offset = self.game_scene.config_rules.get("timing_offset", 0.0)
                dt = (t_hit + timing_offset) - (self.game_scene.state['start_time'] + target_note.t)
                judge_result = self.game_scene._judge_time(dt)
                is_in_time = (judge_result != 'MISS')
                is_in_space = self.game_scene._hand_inside_hit_zone(ev_type)
                
                # 디버깅 정보 출력
                print(f"[DEBUG] {ev_type}: dt={dt:.3f}, judge={judge_result}, is_in_time={is_in_time}, is_in_space={is_in_space}")
                
                # 노트의 현재 위치 계산
                prog = target_note.get_progress(now, self.game_scene.state['start_time'])
                hz_x, hz_y = self.game_scene.hit_zone
                hz_radius = self.game_scene.hit_zone_radius
                
                if target_note.typ == "DUCK":
                    note_x = int((1 - prog) * target_note.x0 + prog * hz_x)
                    note_y = int((1 - prog) * target_note.y0 + prog * target_note.duck_line_y)
                else:
                    note_x = int((1 - prog) * target_note.x0 + prog * hz_x)
                    note_y = int((1 - prog) * target_note.y0 + prog * hz_y)
                
                # 노트가 히트존 중앙에 도달했는지 확인 (노트 중심이 히트존 중심에 도달)
                note_to_hz_dist = np.sqrt((note_x - hz_x)**2 + (note_y - hz_y)**2)
                # 노트 중심이 히트존 중심에 거의 도달했을 때 판정 (5픽셀 이내)
                note_reached_hit_zone = (note_to_hz_dist <= 5)
                
                # 테스트 모드: 공간 + 타이밍 모두 체크 (노트가 히트존에 도달했을 때만 판정)
                if note_reached_hit_zone:
                    if is_in_space and is_in_time:
                        target_note.hit = True
                        target_note.judge_result = judge_result
                        self.game_scene._add_judgement(judge_result, target_note.typ, pos=(note_x, note_y))
                    elif is_in_space and not is_in_time:
                        target_note.missed = True
                        target_note.judge_result = "timing"
                        self.game_scene._add_judgement("timing", target_note.typ, dt=dt, pos=(note_x, note_y))
                    elif (not is_in_space) and is_in_time:
                        target_note.missed = True
                        target_note.judge_result = "area"
                        self.game_scene._add_judgement("area", target_note.typ, pos=(note_x, note_y))
                    else:
                        target_note.missed = True
                        target_note.judge_result = "area/timing"
                        self.game_scene._add_judgement("area/timing", target_note.typ, dt=dt, pos=(note_x, note_y))
                # 노트가 히트존에 도달하지 않았으면 판정하지 않음 (무시)
            
            elif ev_type == "DUCK":
                # 테스트 모드: DUCK은 타이밍에 따라 판정
                candidates = [n for n in self.game_scene.active_notes if n.typ == ev_type and not n.hit and not n.missed]
                if not candidates:
                    continue
                target_note = min(candidates, key=lambda n: abs(t_hit - (self.game_scene.state['start_time'] + n.t)))
                timing_offset = self.game_scene.config_rules.get("timing_offset", 0.0)
                dt = (t_hit + timing_offset) - (self.game_scene.state['start_time'] + target_note.t)
                judge_result = self.game_scene._judge_time(dt)
                is_in_time = (judge_result != 'MISS')
                
                if is_in_time:
                    target_note.hit = True
                    target_note.judge_result = judge_result
                    self.game_scene._add_judgement(judge_result, target_note.typ, pos=(target_note.x, target_note.y))
                else:
                    target_note.missed = True
                    target_note.judge_result = "timing"
                    self.game_scene._add_judgement("timing", target_note.typ, dt=dt, pos=(target_note.x, target_note.y))
    
    def draw_hud(self, frame):
        """테스트 모드: 디버그 정보를 포함한 HUD 그리기"""
        ui_cfg = self.game_scene.config_ui
        pos_cfg = ui_cfg["positions"]
        col_cfg = ui_cfg["colors"]["hud"]
        hud_styles = ui_cfg.get("styles", {}).get("hud", {})
        hit_zone_radius = int(getattr(self.game_scene, "hit_zone_radius", hud_styles.get("hit_zone_radius", 30)))
        hit_zone_thickness = int(hud_styles.get("hit_zone_thickness", 6))
        
        duck_y = self.game_scene.duck_line_y
        cv2.line(frame, (0, duck_y), (self.game_scene.width, duck_y), tuple(col_cfg["duck_line"]), 2)
        cv2.putText(frame, "DUCK LINE", (10, duck_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, tuple(col_cfg["duck_line"]), 2)
        
        hz_x, hz_y = self.game_scene.hit_zone
        
        # 판정 결과에 따라 히트존 색상 및 두께 변경
        last_judgement = self.game_scene.last_judgement
        base_thickness = hit_zone_thickness  # 기본 두께 저장
        
        if last_judgement == "PERFECT":
            hit_zone_color = (0, 255, 255)  # 노란색 (BGR)
            hit_zone_thickness = base_thickness * 2  # 선 두껍게
        elif last_judgement == "GREAT":
            hit_zone_color = (0, 255, 0)  # 녹색 (BGR)
        elif last_judgement == "GOOD":
            hit_zone_color = (255, 0, 0)  # 파란색 (BGR)
        elif last_judgement == "MISS":
            hit_zone_color = (0, 0, 255)  # 빨간색 (BGR)
        else:
            hit_zone_color = (128, 128, 128)  # 회색 (BGR) - 평상시
        
        cv2.circle(frame, (hz_x, hz_y), hit_zone_radius, hit_zone_color, hit_zone_thickness)
        
        # 히트존 원 위에 최근 판정 결과 하나만 표시
        if self.game_scene.floating_judgement_logs:
            text, color, _ = self.game_scene.floating_judgement_logs[0]
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = hz_x - (text_size[0] // 2)
            text_y = hz_y - (hit_zone_radius + 40)  # 히트존 원 위에 표시
            cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        
        # Score, Combo 표시
        score_pos = tuple(pos_cfg["score"])
        score_text = f"Score: {self.game_scene.state['score']}"
        combo_text = f"Combo: {self.game_scene.state['combo']}"
        cv2.putText(frame, score_text, score_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["score_text"]), 3)
        (text_width, _), _ = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)
        combo_pos = (self.game_scene.width - text_width - 20, score_pos[1])
        cv2.putText(frame, combo_text, combo_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["combo_text"]), 3)
        
        # 판정 통계 표시
        judgement_colors = ui_cfg.get("colors", {}).get("judgement", {})
        stats_y = score_pos[1] + 50
        font_scale = 0.7
        thickness = 2
        line_spacing = 30
        
        for i, judge_type in enumerate(["PERFECT", "GREAT", "GOOD", "MISS"]):
            count = self.game_scene.judgement_stats.get(judge_type, 0)
            text = f"{judge_type}: {count}"
            color = tuple(judgement_colors.get(judge_type, [255, 255, 255]))
            y_pos = stats_y + (i * line_spacing)
            cv2.putText(frame, text, (score_pos[0], y_pos), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
        
        # 랜드마크 시각화 (테스트 모드)
        nose_pos = self.game_scene.smoothed_landmark_pos.get("nose")
        if nose_pos:
            nx, ny = int(nose_pos[0]), int(nose_pos[1])
            cv2.circle(frame, (nx, ny), 8, (0, 255, 255), -1)  # 노란색 원
        
        # 랜드마크 시각화 (코, 손 중앙점만 표시, 연결선 제외)
        if self.game_scene.left_fist_center:
            lx, ly = self.game_scene.left_fist_center
            cv2.circle(frame, (lx, ly), 10, (0, 0, 255), 2)  # 빨간색 원 (연결선 없음)
        
        if self.game_scene.right_fist_center:
            rx, ry = self.game_scene.right_fist_center
            cv2.circle(frame, (rx, ry), 10, (0, 0, 255), 2)  # 빨간색 원 (연결선 없음)
    
    def draw_additional(self, frame, now):
        """테스트 모드: 이벤트 히스토리 표시 및 Test mode 텍스트"""
        # (확인) PLAYING 상태에서만 표시
        if self.game_scene.scene_state != "PLAYING":
            return
        
        # 이벤트 히스토리 표시
        event_colors = {
            "JAB_L": (255, 128, 0),   # 주황색
            "JAB_R": (0, 128, 255),   # 파란색
            "DUCK": (200, 200, 200)   # 회색
        }
        
        start_x = 20
        start_y = self.game_scene.height - 30
        recent_events = list(self.game_scene.event_history)[-30:]
        
        dot_size = 8
        spacing = 15
        max_age = 2.0
        
        for i, (ev_type, ev_time) in enumerate(recent_events):
            age = now - ev_time
            if age > max_age:
                continue
            
            alpha = 1.0 - (age / max_age)
            color = event_colors.get(ev_type, (255, 255, 255))
            adjusted_color = tuple(int(c * alpha) for c in color)
            
            x = start_x + i * spacing
            y = start_y
            
            if x >= self.game_scene.width - dot_size:
                break
            
            cv2.circle(frame, (x, y), dot_size, adjusted_color, -1)
            
            if age < 0.1:
                cv2.circle(frame, (x, y), dot_size + 2, adjusted_color, 2)
        
        # "Test mode" 텍스트 표시 (오른쪽 아래)
        text = "Test mode"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        color = (0, 0, 255)  # 빨간색 (BGR)
        
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        text_x = self.game_scene.width - text_width - 20
        text_y = self.game_scene.height - 20
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)
    
    def format_judgement_text(self, judge_text, dt):
        """테스트 모드: dt 정보를 포함한 판정 텍스트 포맷팅"""
        if dt is not None:
            return f"{judge_text} ({dt:+.2f}s)"
        return judge_text
    
    def on_hit_events(self, hit_events, now):
        """테스트 모드: 이벤트 히스토리 저장"""
        if hit_events:
            for ev in hit_events:
                self.game_scene.event_history.append((ev["type"], now))
    
    def calculate_debug_info(self, active_notes, hit_zone, smoothed_landmark_pos, start_time, now):
        """테스트 모드: 다음 노트의 시간/공간 정보 계산"""
        self.game_scene.debug_remaining_time = None
        self.game_scene.debug_spatial_distance = None
        
        if active_notes:
            next_note = active_notes[0]
            self.game_scene.debug_remaining_time = (start_time + next_note.t) - now
            
            note_type = next_note.typ
            landmark_key = None
            
            if note_type == "JAB_L":
                landmark_key = "right_wrist"
            elif note_type == "JAB_R":
                landmark_key = "left_wrist"
            
            if landmark_key:
                pos = smoothed_landmark_pos.get(landmark_key)
                if pos:
                    hz_pos = np.array(hit_zone)
                    hand_pos = np.array(pos)
                    self.game_scene.debug_spatial_distance = np.linalg.norm(hand_pos - hz_pos)

