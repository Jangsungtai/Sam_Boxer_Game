# scenes/normal_mode_strategy.py

import cv2
import numpy as np
from scenes.game_mode_strategy import GameModeStrategy

class NormalModeStrategy(GameModeStrategy):
    """일반 모드 전략: 일반 게임플레이 판정 및 시각화"""
    
    def handle_hits(self, hit_events, t_game, now):
        """일반 모드: 공간 + 타이밍 모두 체크, 노트가 히트존에 도달했는지 확인"""
        for ev in hit_events:
            ev_type = ev["type"]
            t_hit = ev["t_hit"]
            
            if ev_type.startswith("JAB"):
                # BOMB 체크
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
                
                # 노트의 현재 위치 계산
                prog = target_note.get_progress(now, self.game_scene.state['start_time'])
                hz_x, hz_y = self.game_scene.hit_zone
                
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
                
                # 일반 모드: 공간 + 타이밍 모두 체크 (노트가 히트존에 도달했을 때만 판정)
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
                # 일반 모드: 타이밍에 따라 판정
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
        """일반 모드: 깔끔한 HUD (디버그 정보 제외)"""
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
        
        # 랜드마크 시각화 (코, 손 중앙점만 표시, 연결선 제외)
        nose_pos = self.game_scene.smoothed_landmark_pos.get("nose")
        if nose_pos:
            nx, ny = int(nose_pos[0]), int(nose_pos[1])
            cv2.circle(frame, (nx, ny), 8, (0, 255, 255), -1)  # 노란색 원
        
        if self.game_scene.left_fist_center:
            lx, ly = self.game_scene.left_fist_center
            cv2.circle(frame, (lx, ly), 10, (0, 0, 255), 2)  # 빨간색 원 (연결선 없음)
        
        if self.game_scene.right_fist_center:
            rx, ry = self.game_scene.right_fist_center
            cv2.circle(frame, (rx, ry), 10, (0, 0, 255), 2)  # 빨간색 원 (연결선 없음)
        
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
    
    def draw_additional(self, frame, now):
        """일반 모드: 추가 시각화 없음"""
        pass
    
    def format_judgement_text(self, judge_text, dt):
        """일반 모드: dt 정보 없이 판정 텍스트만 반환"""
        return judge_text
    
    def on_hit_events(self, hit_events, now):
        """일반 모드: 추가 처리 없음"""
        pass
    
    def calculate_debug_info(self, active_notes, hit_zone, smoothed_landmark_pos, start_time, now):
        """일반 모드: 디버그 정보 계산 없음"""
        pass

