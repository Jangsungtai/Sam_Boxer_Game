# scenes/game_scene.py

import cv2
import time
import json
import numpy as np
import os
import sys
from collections import deque
import pygame
import mediapipe as mp 

from scenes.base_scene import BaseScene
# (수정) PoseTracker 임포트 제거
# from core.pose_tracker import PoseTracker 
from core.note import Note

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

mp_pose = mp.solutions.pose

class GameScene(BaseScene):
    def __init__(self, screen, audio_manager, config, pose_tracker):
        super().__init__(screen, audio_manager, config, pose_tracker)
        
        self.width = int(self.screen.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.config_rules = config["rules"]; self.config_difficulty = config["difficulty"]; self.config_ui = config["ui"]
        difficulty_name = "Normal"
        self.difficulty = self.config_difficulty["levels"].get(difficulty_name, self.config_difficulty["levels"]["Normal"])
        self.judge_timing = {k: v * self.difficulty["judge_timing_scale"] for k, v in self.config_rules["judge_timing"].items()}
        self.pre_spawn_time = self.difficulty["pre_spawn_time"]; self.score_multiplier = self.difficulty["score_multiplier"]
        self.bomb_penalty = self.config_rules["bomb_penalty"]
        
        beatmap_path = resource_path("assets/beatmaps/song1/beatmap.json")
        try:
            with open(beatmap_path, 'r') as f: beat_map_data = json.load(f)
        except FileNotFoundError:
            print(f"오류: 비트맵 파일을 찾을 수 없습니다! {beatmap_path}"); beat_map_data = [{"t": 3.0, "type": "END"}]
        self.beat_map = sorted(beat_map_data, key=lambda x: x['t'])
        music_path_rel = os.path.join("assets/beatmaps/song1", "music.mp3")
        self.audio_manager.load_music(music_path_rel)

        self.calib_hold_time = self.config_rules.get("calibration_hold_time", 3.0)
        
        cfg_targets = self.config_ui["positions"].get("calibration_targets")
        if cfg_targets:
            def get_target(name):
                cfg = cfg_targets[name]
                pos = (int(self.width * cfg["pos_ratio"][0]), int(self.height * cfg["pos_ratio"][1]))
                rad = int(self.width * cfg["radius_ratio_w"])
                return {"pos": pos, "radius": rad}
            
            self.calib_targets = {
                "head": get_target("head"),
                "left_fist": get_target("left_fist"),
                "right_fist": get_target("right_fist")
            }
        else:
            print("[경고] ui.json에 calibration_targets가 없습니다. 기본값을 사용합니다.")
            self.calib_targets = {
                "head": {"pos": (self.width//2, self.height//2 - 100), "radius": 50},
                "left_fist": {"pos": (self.width//2 - 200, self.height//2), "radius": 40},
                "right_fist": {"pos": (self.width//2 + 200, self.height//2), "radius": 40}
            }
            
        try:
            img_path = resource_path("assets/images/headgear.png")
            self.img_headgear_orig = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
            if self.img_headgear_orig is None: print("[경고] headgear.png 로드 실패")
                
        except Exception as e:
            print(f"[오류] 장비 이미지 로드 실패: {e}")
            self.img_headgear_orig = None

        self.reset_game_state()
        self.scene_state = "IDLE"; self.state_start_time = 0

    def reset_game_state(self):
        self.next_note_idx = 0; self.state = {"score": 0, "combo": 0, "start_time": None, "game_over": False}
        self.active_notes = []; self.judges_log = deque(maxlen=5)
        
        # --- (수정) hit_zone을 동적 변수로 초기화 ---
        # (ui.json의 값 대신 기본 중앙값으로 시작)
        self.hit_zone = (int(self.width * 0.5), int(self.height * 0.6)) 
        # --- (수정 끝) ---
        
        self.duck_line_y = int(self.height * 0.7); self.audio_manager.stop_music()
        
        self.calib_hold_start_time = 0.0
        self.last_pose_landmarks = None
        self.calib_status = (False, False, False) # (head_ok, lw_ok, rw_ok)
        
        self.calib_landmark_pos = {
            "head_center": None, "nose": None, "left_eye_inner": None, "right_eye_inner": None,
            "left_wrist": None, "right_wrist": None, 
            "left_elbow": None, "right_elbow": None,
            "shoulders": (None, None),
            "left_ear": None, "right_ear": None,
            "left_mouth": None, "right_mouth": None,
            "left_index": None, "right_index": None
        } 
        self.smoothed_landmark_pos = self.calib_landmark_pos.copy()
        
        self.base_ear_distance = 150.0 
        self.dynamic_size_ratio = 1.0 
        self.smoothed_dynamic_size_ratio = 1.0

        self.head_angle = 0.0
        self.smoothed_head_angle = 0.0
        
        print("GameScene: 게임 상태가 리셋되었습니다.")

    def startup(self, persistent_data):
        super().startup(persistent_data)
        print("GameScene: Startup! 캘리브레이션을 시작합니다.")
        
        self.reset_game_state()
        self.scene_state = "CALIBRATING"
        self.state_start_time = time.time()
        
    def cleanup(self):
        print("GameScene: Cleanup! 음악을 정지합니다."); self.audio_manager.stop_music()
        self.persistent_data["final_score"] = self.state["score"]; self.persistent_data["max_combo"] = 0
        return super().cleanup() 

    def handle_event(self, key):
        if self.scene_state == "CALIBRATING" and key == ord('0'):
            print("Calibration: '0' key pressed. Skipping calibration.")
            
            self.duck_line_y = self.pose_tracker.calib_data['duck_line_y'] 
            
            if self.last_pose_landmarks:
                 self.pose_tracker.calibrate_from_pose(self.last_pose_landmarks)
                 self.duck_line_y = self.pose_tracker.calib_data['duck_line_y']
                 if self.smoothed_landmark_pos["left_ear"] and self.smoothed_landmark_pos["right_ear"]:
                    l_ear = np.array(self.smoothed_landmark_pos["left_ear"])
                    r_ear = np.array(self.smoothed_landmark_pos["right_ear"])
                    self.base_ear_distance = np.linalg.norm(l_ear - r_ear)
                    print(f"Calibration Done (SKIPPED): Base Ear Distance set to {self.base_ear_distance:.1f}px")
                 else:
                    print(f"Calibration Warning (SKIPPED): Could not set Base Ear Distance. Using default {self.base_ear_distance}px")
            else:
                print(f"Calibration Warning (SKIPPED): No pose detected. Using default {self.base_ear_distance}px")
                
            self.scene_state = "COUNTDOWN"
            self.state_start_time = time.time()
    
    def _overlay_transparent_image(self, background_frame, overlay_img, pos):
        """
        배경 프레임(frame) 위에 투명 오버레이 이미지(overlay_img)를 특정 위치(pos)에 덧씌웁니다.
        pos는 덧씌울 이미지의 (x, y) 좌상단 좌표입니다.
        """
        try:
            x, y = pos
            h, w, _ = overlay_img.shape
            x1, y1 = max(x, 0), max(y, 0)
            x2, y2 = min(x + w, self.width), min(y + h, self.height)
            w_roi = x2 - x1
            h_roi = y2 - y1
            if w_roi <= 0 or h_roi <= 0: return 
            overlay_x1 = 0 if x >= 0 else -x
            overlay_y1 = 0 if y >= 0 else -y
            overlay_x2 = overlay_x1 + w_roi
            overlay_y2 = overlay_y1 + h_roi
            overlay_bgr = overlay_img[overlay_y1:overlay_y2, overlay_x1:overlay_x2, 0:3]
            alpha_mask = overlay_img[overlay_y1:overlay_y2, overlay_x1:overlay_x2, 3] / 255.0
            alpha_mask_3ch = cv2.merge([alpha_mask, alpha_mask, alpha_mask])
            roi = background_frame[y1:y2, x1:x2]
            bg_masked = (1.0 - alpha_mask_3ch) * roi
            fg_masked = alpha_mask_3ch * overlay_bgr
            blended_roi = cv2.add(bg_masked, fg_masked).astype(np.uint8)
            background_frame[y1:y2, x1:x2] = blended_roi
        except Exception as e:
            pass 

    def _check_calib_position(self, landmarks):
        """랜드마크가 타겟 안에 있는지 확인하고, 현재 좌표도 반환합니다."""
        
        # --- (수정) positions 딕셔너리 구조 유지 ---
        positions = {
            "head_center": None, "nose": None, "left_eye_inner": None, "right_eye_inner": None,
            "left_wrist": None, "right_wrist": None, 
            "left_elbow": None, "right_elbow": None,
            "shoulders": (None, None),
            "left_ear": None, "right_ear": None,
            "left_mouth": None, "right_mouth": None,
            "left_index": None, "right_index": None
        } 
        # --- (수정 끝) ---
        
        if not landmarks:
            return False, (False, False, False), positions

        lm = landmarks.landmark
        def P(i): return (lm[i].x * self.width, lm[i].y * self.height)
        
        try:
            NOSE = P(mp_pose.PoseLandmark.NOSE) # (0)
            L_EYE_INNER = P(mp_pose.PoseLandmark.LEFT_EYE_INNER) # (1)
            R_EYE_INNER = P(mp_pose.PoseLandmark.RIGHT_EYE_INNER) # (4)
            HEAD_CENTER = ( (L_EYE_INNER[0] + R_EYE_INNER[0]) / 2, (L_EYE_INNER[1] + R_EYE_INNER[1]) / 2 )
            
            L_WRIST = P(mp_pose.PoseLandmark.LEFT_WRIST) # (15)
            R_WRIST = P(mp_pose.PoseLandmark.RIGHT_WRIST) # (16)
            L_ELBOW = P(mp_pose.PoseLandmark.LEFT_ELBOW) # (13)
            R_ELBOW = P(mp_pose.PoseLandmark.RIGHT_ELBOW) # (14)
            L_SHOULDER = P(mp_pose.PoseLandmark.LEFT_SHOULDER) # (11)
            R_SHOULDER = P(mp_pose.PoseLandmark.RIGHT_SHOULDER) # (12)
            LEFT_EAR = P(mp_pose.PoseLandmark.LEFT_EAR) # (7)
            RIGHT_EAR = P(mp_pose.PoseLandmark.RIGHT_EAR) # (8)
            LEFT_MOUTH = P(mp_pose.PoseLandmark.MOUTH_LEFT) # (9)
            RIGHT_MOUTH = P(mp_pose.PoseLandmark.MOUTH_RIGHT) # (10)
            L_INDEX = P(mp_pose.PoseLandmark.LEFT_INDEX) # (19)
            R_INDEX = P(mp_pose.PoseLandmark.RIGHT_INDEX) # (20)
            
            positions = {
                "head_center": HEAD_CENTER, "nose": NOSE,
                "left_eye_inner": L_EYE_INNER, "right_eye_inner": R_EYE_INNER,
                "left_wrist": L_WRIST, "right_wrist": R_WRIST,
                "left_elbow": L_ELBOW, "right_elbow": R_ELBOW,
                "shoulders": (L_SHOULDER, R_SHOULDER),
                "left_ear": LEFT_EAR, "right_ear": RIGHT_EAR,
                "left_mouth": LEFT_MOUTH, "right_mouth": RIGHT_MOUTH,
                "left_index": L_INDEX, "right_index": R_INDEX
            }
            
        except Exception:
            return False, (False, False, False), positions

        def dist(p1, p2): 
            return np.linalg.norm(np.array(p1) - np.array(p2))

        target_h = self.calib_targets["head"]
        target_l = self.calib_targets["left_fist"]
        target_r = self.calib_targets["right_fist"]

        head_ok = dist(NOSE, target_h["pos"]) < target_h["radius"]
        
        lw_ok = dist(R_WRIST, target_l["pos"]) < target_l["radius"]
        rw_ok = dist(L_WRIST, target_r["pos"]) < target_r["radius"]
        
        all_ok = head_ok and lw_ok and rw_ok
        
        return all_ok, (head_ok, lw_ok, rw_ok), positions

    # --- (수정) _spawn_notes (hit_zone 제거) ---
    def _spawn_notes(self, t_game):
        while (self.next_note_idx < len(self.beat_map) and
               self.beat_map[self.next_note_idx]['t'] - self.pre_spawn_time <= t_game):
            item = self.beat_map[self.next_note_idx]; self.next_note_idx += 1
            if item['type'] == 'END': self.state['game_over'] = True; break
            # (수정) Note 생성자에서 self.hit_zone 제거
            note = Note(item, self.width, self.height, self.duck_line_y, self.pre_spawn_time, self.config_ui["colors"]["notes"])
            self.active_notes.append(note)
    # --- (수정 끝) ---

    def _judge_time(self, dt):
        adt = abs(dt)
        if adt <= self.judge_timing['perfect']: return 'PERFECT'
        if adt <= self.judge_timing['great']: return 'GREAT'
        if adt <= self.judge_timing['good']: return 'GOOD'
        return 'MISS'
        
    def _add_judgement(self, judge_text, note_type):
        color = tuple(self.config_ui["colors"]["judgement"].get(judge_text, [255,255,255])); self.judges_log.appendleft((judge_text, color))
        self.audio_manager.play_sfx(judge_text)
        if judge_text == 'MISS' or judge_text == 'BOMB!':
            self.state['combo'] = 0
            if judge_text == 'BOMB!': self.state['score'] += self.bomb_penalty
        else:
            self.state['combo'] += 1; score_gain = self.config_rules["score_base"].get(judge_text, 0); score_gain *= self.score_multiplier
            combo_bonus = (self.state['combo'] // 10) * (score_gain * 0.1); self.state['score'] += int(score_gain + combo_bonus)

    def _handle_hits(self, hit_events, t_game):
        now = time.time()
        for ev in hit_events:
            ev_type = ev["type"]; t_hit = ev["t_hit"]
            if ev_type.startswith("JAB"):
                bombs = [n for n in self.active_notes if n.typ == "BOMB" and not n.hit and not n.missed]
                for b in bombs:
                    dt = t_hit - (self.state['start_time'] + b.t)
                    if abs(dt) < self.judge_timing['good']: b.hit = True; self._add_judgement("BOMB!", "BOMB"); return
            candidates = [n for n in self.active_notes if n.typ == ev_type and not n.hit and not n.missed]
            if not candidates: continue
            target_note = min(candidates, key=lambda n: abs(t_hit - (self.state['start_time'] + n.t)))
            dt = t_hit - (self.state['start_time'] + target_note.t); judge_result = self._judge_time(dt)
            if judge_result != 'MISS': target_note.hit = True; self._add_judgement(judge_result, target_note.typ)
            
    def _check_misses(self, t_game):
        judge_limit = self.judge_timing['good']
        for note in self.active_notes:
            if note.hit or note.missed: continue
            if t_game > (note.t + judge_limit):
                note.missed = True
                if note.typ != "BOMB": self._add_judgement("MISS", note.typ)

    # --- (수정) _draw_hud (hit_zone을 동적으로 사용) ---
    def _draw_hud(self, frame):
        ui_cfg = self.config_ui; pos_cfg = ui_cfg["positions"]; col_cfg = ui_cfg["colors"]["hud"]
        
        duck_y = self.duck_line_y
        
        cv2.line(frame, (0, duck_y), (self.width, duck_y), tuple(col_cfg["duck_line"]), 2)
        cv2.putText(frame, "DUCK LINE", (10, duck_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, tuple(col_cfg["duck_line"]), 2)
        
        # (수정) self.hit_zone이 매 프레임 업데이트되므로, 여기서 그릴 때 동적으로 그려짐
        hz_x, hz_y = self.hit_zone 
        cv2.circle(frame, (hz_x, hz_y), 30, tuple(col_cfg["hit_zone"]), 6)
        
        score_pos = tuple(pos_cfg["score"]); score_text = f"Score: {self.state['score']}"; combo_text = f"Combo: {self.state['combo']}"
        cv2.putText(frame, score_text, score_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["score_text"]), 3)
        (text_width, _), _ = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)
        combo_pos = (self.width - text_width - 20, score_pos[1])
        cv2.putText(frame, combo_text, combo_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["combo_text"]), 3)
        log_start_pos = tuple(pos_cfg["judge_log_start"])
        for i, (text, color) in enumerate(self.judges_log):
            y_pos = log_start_pos[1] + i * 40
            cv2.putText(frame, text, (log_start_pos[0], y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    # --- (수정 끝) ---
            
    def update(self, frame, hit_events, landmarks, now):
        
        # 1. 랜드마크가 있으면 저장
        if landmarks:
            self.last_pose_landmarks = landmarks
        
        # 2. 캘리브레이션 조준 확인
        all_ok, self.calib_status, raw_landmark_pos = self._check_calib_position(landmarks)

        # 3. '귀-귀' 벡터로 각도/크기 계산
        raw_L_EAR = raw_landmark_pos.get("left_ear")
        raw_R_EAR = raw_landmark_pos.get("right_ear")
        
        if raw_L_EAR and raw_R_EAR:
            l_ear_pos = np.array(raw_L_EAR)
            r_ear_pos = np.array(raw_R_EAR)
            
            ear_vec = l_ear_pos - r_ear_pos
            self.head_angle = -np.degrees(np.arctan2(ear_vec[1], ear_vec[0]))

            current_ear_distance = np.linalg.norm(ear_vec)
            self.dynamic_size_ratio = current_ear_distance / self.base_ear_distance
            self.dynamic_size_ratio = np.clip(self.dynamic_size_ratio, 0.7, 1.5)
        else:
            self.head_angle = 0.0
            self.dynamic_size_ratio = 1.0
        
        # 4. 스무딩
        SMOOTH_FACTOR = 0.5 
        
        # --- (수정) 스무딩 로직 (어깨 튜플 처리) ---
        for key in self.smoothed_landmark_pos.keys():
            raw_pos = raw_landmark_pos.get(key)
            prev_pos = self.smoothed_landmark_pos.get(key)
            
            if key == "shoulders":
                raw_l, raw_r = raw_pos if raw_pos and None not in raw_pos else (None, None)
                prev_l, prev_r = prev_pos if prev_pos and None not in prev_pos else (None, None)
                
                def smooth_point(raw, prev):
                    if raw:
                        if prev:
                            x = prev[0] * (1.0 - SMOOTH_FACTOR) + raw[0] * SMOOTH_FACTOR
                            y = prev[1] * (1.0 - SMOOTH_FACTOR) + raw[1] * SMOOTH_FACTOR
                            return (x, y)
                        return raw
                    return None
                    
                self.smoothed_landmark_pos[key] = (smooth_point(raw_l, prev_l), smooth_point(raw_r, prev_r))
                continue # 'shoulders' 키는 스무딩 후 건너뛰기

            # (기존 랜드마크 스무딩)
            if raw_pos:
                if prev_pos:
                    new_x = prev_pos[0] * (1.0 - SMOOTH_FACTOR) + raw_pos[0] * SMOOTH_FACTOR
                    new_y = prev_pos[1] * (1.0 - SMOOTH_FACTOR) + raw_pos[1] * SMOOTH_FACTOR
                    self.smoothed_landmark_pos[key] = (new_x, new_y)
                else:
                    self.smoothed_landmark_pos[key] = raw_pos
            else:
                self.smoothed_landmark_pos[key] = None
        # --- (스무딩 로직 끝) ---
        
        # 각도/크기 스무딩
        self.smoothed_head_angle = self.smoothed_head_angle * (1.0 - SMOOTH_FACTOR) + self.head_angle * SMOOTH_FACTOR
        self.smoothed_dynamic_size_ratio = self.smoothed_dynamic_size_ratio * (1.0 - SMOOTH_FACTOR) + self.dynamic_size_ratio * SMOOTH_FACTOR

        # --- (추가) 5. 동적 히트존 계산 ---
        sm_l_shoulder, sm_r_shoulder = self.smoothed_landmark_pos.get("shoulders", (None, None))
        sm_l_mouth = self.smoothed_landmark_pos.get("left_mouth")
        sm_r_mouth = self.smoothed_landmark_pos.get("right_mouth")

        # 5a. Y좌표 (턱 높이)
        if sm_l_mouth and sm_r_mouth:
            mouth_mid_y = (sm_l_mouth[1] + sm_r_mouth[1]) / 2
            # (귀-귀 거리의 10% 정도를 턱 길이로 추정)
            chin_offset = (self.base_ear_distance * self.smoothed_dynamic_size_ratio) * 0.2
            target_y = mouth_mid_y + chin_offset
        else:
            target_y = self.hit_zone[1] # 이전 값 유지

        # 5b. X좌표 (어깨 안쪽)
        if sm_l_shoulder and sm_r_shoulder:
            # sm_l_shoulder = P(11) (화면 오른쪽), sm_r_shoulder = P(12) (화면 왼쪽)
            screen_left_shoulder_x = sm_r_shoulder[0]
            screen_right_shoulder_x = sm_l_shoulder[0]
            
            torso_center_x = (screen_left_shoulder_x + screen_right_shoulder_x) / 2
            
            # 어깨 안쪽으로 10% 정도 패딩
            padding = (screen_right_shoulder_x - screen_left_shoulder_x) * 0.1
            min_x = screen_left_shoulder_x + padding
            max_x = screen_right_shoulder_x - padding
            
            # X좌표를 어깨 안쪽으로 제한 (clamp)
            target_x = np.clip(torso_center_x, min_x, max_x)
        else:
            target_x = self.hit_zone[0] # 이전 값 유지
            
        # 5c. self.hit_zone 업데이트
        self.hit_zone = (int(target_x), int(target_y))
        # --- (동적 히트존 계산 끝) ---


        # 6. 씬 상태에 따른 로직 분기
        if self.scene_state == "CALIBRATING":
            
            if all_ok:
                if self.calib_hold_start_time == 0.0:
                    print("Calibration: In position! Hold...")
                    self.calib_hold_start_time = now
                
                t_held = now - self.calib_hold_start_time
                
                if t_held >= self.calib_hold_time:
                    print("GameScene: 캘리브레이션 성공. 카운트다운 시작.")
                    self.pose_tracker.calibrate_from_pose(self.last_pose_landmarks)
                    self.duck_line_y = self.pose_tracker.calib_data['duck_line_y']
                    
                    if self.smoothed_landmark_pos["left_ear"] and self.smoothed_landmark_pos["right_ear"]:
                        l_ear = np.array(self.smoothed_landmark_pos["left_ear"])
                        r_ear = np.array(self.smoothed_landmark_pos["right_ear"])
                        self.base_ear_distance = np.linalg.norm(l_ear - r_ear)
                        print(f"Calibration Done: Base Ear Distance set to {self.base_ear_distance:.1f}px")
                    else:
                        print(f"Calibration Warning: Could not set Base Ear Distance. Using default {self.base_ear_distance}px")
                    
                    self.scene_state = "COUNTDOWN"
                    self.state_start_time = now
            
            else:
                if self.calib_hold_start_time != 0.0:
                    print("Calibration: Moved! Resetting hold timer.")
                self.calib_hold_start_time = 0.0
            
            return
            
        elif self.scene_state == "COUNTDOWN":
            t_elapsed = now - self.state_start_time
            if t_elapsed >= 3.0:
                print("GameScene: 게임 시작!"); self.scene_state = "PLAYING"; self.state["start_time"] = now; self.audio_manager.play_music()
            return
            
        elif self.scene_state == "PLAYING":
            if self.state["game_over"]:
                print("GameScene: 게임 종료. 결과 씬으로 전환합니다."); self.scene_state = "GAME_OVER"; self.state_start_time = now
                self.next_scene_name = "RESULT"; return
            t_game = now - self.state["start_time"]
            self._spawn_notes(t_game)
            if hit_events: self._handle_hits(hit_events, t_game)
            self._check_misses(t_game)

    def _draw_equipment(self, frame):
        """
        현재 씬 상태와 랜드마크 위치에 따라 헤드기어만 그립니다.
        """
        draw_head = False
        current_head_center_pos = self.smoothed_landmark_pos["head_center"]

        if self.scene_state == "CALIBRATING":
            draw_head = False 
        else:
            if current_head_center_pos:
                draw_head = True
        
        HEADGEAR_WIDTH_K = 1.8 # (헤드기어 너비 = 귀-귀 거리 * 1.8)
        
        # 1. 헤드기어 (미간 기준)
        if draw_head and self.img_headgear_orig is not None and current_head_center_pos:
            
            target_width = int(self.base_ear_distance * self.smoothed_dynamic_size_ratio * HEADGEAR_WIDTH_K)
            if target_width <= 0: target_width = 1 
            
            try:
                orig_h, orig_w, _ = self.img_headgear_orig.shape
                aspect_ratio = orig_h / orig_w
                target_height = int(target_width * aspect_ratio)
                if target_height <= 0: target_height = 1

                resized_img = cv2.resize(self.img_headgear_orig, (target_width, target_height), interpolation=cv2.INTER_AREA)
                
                (h_img, w_img) = resized_img.shape[:2]
                center = (w_img // 2, h_img // 2)
                
                M = cv2.getRotationMatrix2D(center, self.smoothed_head_angle, 1.0) 
                
                rotated_img = cv2.warpAffine(resized_img, M, (w_img, h_img), 
                                                flags=cv2.INTER_LINEAR, 
                                                borderMode=cv2.BORDER_CONSTANT, 
                                                borderValue=(0, 0, 0, 0))
                
                h_rot, w_rot, _ = rotated_img.shape
                top_left = (int(current_head_center_pos[0] - w_rot/2), int(current_head_center_pos[1] - h_rot/2))
                
                self._overlay_transparent_image(frame, rotated_img, top_left)
                
            except Exception as e: 
                # print(f"Headgear draw error: {e}") 
                pass 

    def draw(self, frame):
        now = time.time()
        
        # 1. 장비 그리기를 항상 맨 먼저 호출
        self._draw_equipment(frame)

        if self.scene_state == "CALIBRATING":
            # 캘리브레이션 UI (원, 텍스트) 그리기
            (head_ok, lw_ok, rw_ok) = self.calib_status
            color_target = (255, 255, 255); color_ok = (0, 255, 0)
            
            target_h = self.calib_targets["head"]
            target_l = self.calib_targets["left_fist"]
            target_r = self.calib_targets["right_fist"]

            cv2.circle(frame, target_h["pos"], target_h["radius"], color_ok if head_ok else color_target, 2)
            cv2.circle(frame, target_l["pos"], target_l["radius"], color_ok if lw_ok else color_target, 2)
            cv2.circle(frame, target_r["pos"], target_r["radius"], color_ok if rw_ok else color_target, 2)

            text_pos = (self.width // 2 - 350, self.height // 2)
            if self.calib_hold_start_time > 0:
                t_held = now - self.calib_hold_start_time
                countdown = self.calib_hold_time - t_held
                text = f"HOLD! {countdown:.1f}s"
                cv2.putText(frame, text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 2, color_ok, 4)
            else:
                text = "Match the silhouette"
                cv2.putText(frame, text, (text_pos[0] + 50, text_pos[1]), cv2.FONT_HERSHEY_SIMPLEX, 2, color_target, 4)
            
        elif self.scene_state == "COUNTDOWN":
            # 카운트다운 텍스트
            t_elapsed = now - self.state_start_time; countdown = 3.0 - t_elapsed
            cv2.putText(frame, f"{countdown:.1f}", (self.width//2 - 50, self.height//2), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 5)
            
        elif self.scene_state == "PLAYING":
            # 게임 HUD 및 노트 그리기
            self._draw_hud(frame)
            
            # --- (수정) note.update_and_draw에 동적 self.hit_zone 전달 ---
            for note in self.active_notes:
                note.update_and_draw(frame, now, self.state["start_time"], self.hit_zone)
            # --- (수정 끝) ---
                
            self.active_notes = [n for n in self.active_notes if not n.hit and not n.missed]