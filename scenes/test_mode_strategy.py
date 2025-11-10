# scenes/test_mode_strategy.py

import cv2
import numpy as np
import time
from scenes.game_mode_strategy import GameModeStrategy

class TestModeStrategy(GameModeStrategy):
    """테스트 모드 전략: 디버깅 정보를 포함한 판정 및 시각화"""
    
    def handle_hits(self, hit_events, t_game, now, **kwargs):
        """테스트 모드: 공간 + 타이밍 모두 체크, 노트가 히트존에 도달했는지 확인 (Phase 2: kwargs 추가)"""
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
    
    def _draw_mode_specific_hud(self, frame):
        """테스트 모드: 랜드마크 시각화만 추가 (Phase 2: 공통 로직은 부모 클래스에서 처리)"""
        # Phase 1: 스무딩된 랜드마크는 PoseTracker에서 가져옴
        smoothed_landmarks = self.game_scene.pose_tracker.get_smoothed_landmarks()
        left_fist, right_fist = self.game_scene.pose_tracker.get_fist_centroids()

        note_colors = self.game_scene.config_ui.get("colors", {}).get("notes", {})
        color_jab_l = tuple(note_colors.get("JAB_L", [255, 128, 0]))  # 실제 오른손
        color_jab_r = tuple(note_colors.get("JAB_R", [0, 128, 255]))  # 실제 왼손
        nose_color = (0, 255, 255)
        
        nose_pos = smoothed_landmarks.get("nose")
        if nose_pos:
            nx, ny = int(nose_pos[0]), int(nose_pos[1])
            cv2.circle(frame, (nx, ny), 8, nose_color, -1)  # 노란색 원
        
        # 랜드마크 시각화 (코, 손 중앙점만 표시, 연결선 제외)
        if left_fist:
            lx, ly = left_fist
            cv2.circle(frame, (lx, ly), 10, color_jab_r, -1)
        
        if right_fist:
            rx, ry = right_fist
            cv2.circle(frame, (rx, ry), 10, color_jab_l, -1)
    
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
    
    # Phase 2: calculate_debug_info 제거 (GameScene에서 계산)

