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
from scenes.test_mode_strategy import TestModeStrategy
from scenes.normal_mode_strategy import NormalModeStrategy

def resource_path(relative_path):
    """리소스 파일의 절대 경로를 반환합니다 (실행 환경별 경로 처리)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

mp_pose = mp.solutions.pose

class GameScene(BaseScene):
    def __init__(self, screen, audio_manager, config, pose_tracker):
        """게임 씬을 초기화하고 설정/리소스를 로드합니다."""
        super().__init__(screen, audio_manager, config, pose_tracker)
        
        self.width = int(self.screen.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.config_rules = config["rules"]; self.config_difficulty = config["difficulty"]; self.config_ui = config["ui"]
        difficulty_name = "Normal"
        self.difficulty = self.config_difficulty["levels"].get(difficulty_name, self.config_difficulty["levels"]["Normal"])
        
        # --- (리듬 기반 비트맵 로딩) beatmap.txt + BPM/division 사용 ---
        song_info = self.config_difficulty.get("song_info", {})
        bpm = float(song_info.get("bpm", 120))
        
        # Phase 3: 박자 단위를 초 단위로 변환 (BPM 기반)
        seconds_per_beat = 60.0 / max(1e-6, bpm)
        
        # 판정 시간: 박자 단위 → 초 단위
        base_timing_beats = self.config_difficulty.get("judge_timing_base_beats", {
            "perfect_beats": 0.5, 
            "great_beats": 0.75, 
            "good_beats": 1.0
        })
        scale = self.difficulty.get("judge_timing_scale", 1.0)
        
        self.judge_timing = {}
        for key, beats in base_timing_beats.items():
            if key.endswith("_beats"):
                # 박자 → 초 변환
                seconds = beats * seconds_per_beat
                # 난이도 배율 적용
                timing_key = key.replace("_beats", "")
                self.judge_timing[timing_key] = seconds * scale
        
        # 스폰 시간: 박자 단위 → 초 단위
        pre_spawn_beats = self.difficulty.get("pre_spawn_beats", 2.0)
        self.pre_spawn_time = pre_spawn_beats * seconds_per_beat
        
        self.score_multiplier = self.difficulty["score_multiplier"]
        self.bomb_penalty = self.config_rules["bomb_penalty"]
        
        # 디버그 정보 출력
        print(f"[Phase 3: BPM 연동] BPM: {bpm}, 박자당 초: {seconds_per_beat:.3f}s, 판정 시간: {self.judge_timing}, 스폰 시간: {self.pre_spawn_time:.3f}s")
        
        division = int(song_info.get("division", 4))
        seconds_per_division = seconds_per_beat / max(1, division)

        rhythm_map = {
            '1': "JAB_L",
            '2': "JAB_R",
            '3': "DUCK",
            '4': "BOMB",
            '0': None
        }

        self.beat_map = []
        current_time = 0.0
        txt_path = resource_path("assets/beatmaps/song1/beatmap.txt")
        try:
            with open(txt_path, 'r') as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith('#'):
                        continue
                    for ch in line:
                        note_type = rhythm_map.get(ch)
                        if note_type is not None:
                            self.beat_map.append({"t": current_time, "type": note_type})
                        current_time += seconds_per_division
        except FileNotFoundError:
            print(f"오류: 리듬 비트맵 파일을 찾을 수 없습니다! {txt_path}")
            self.beat_map = [{"t": 3.0, "type": "END"}]

        # END 마커 추가 및 정렬
        if self.beat_map:
            self.beat_map.append({"t": current_time + 2.0, "type": "END"})
            self.beat_map = sorted(self.beat_map, key=lambda x: x['t'])
        # --- (리듬 기반 로딩 끝) ---
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
        
        # (수정) test_mode를 인스턴스 변수로 관리 (캘리브레이션에서 '0' 키로 설정)
        self.test_mode = False
        
        # (추가) Strategy 패턴: test_mode에 따라 전략 선택
        self._update_strategy()

    def reset_game_state(self):
        """게임 진행 관련 상태값과 표시용 데이터를 초기화합니다."""
        self.next_note_idx = 0; self.state = {"score": 0, "combo": 0, "start_time": None, "game_over": False}
        self.active_notes = []; self.floating_judgement_logs = deque(maxlen=1)  # 최근 판정 하나만 표시
        
        # (추가) test_mode 초기화 (새 게임 시작 시 일반 모드)
        if not hasattr(self, 'test_mode'):
            self.test_mode = False
        # 판정 통계 초기화 (PERFECT, GREAT, GOOD, MISS)
        self.judgement_stats = {"PERFECT": 0, "GREAT": 0, "GOOD": 0, "MISS": 0}
        # 최근 판정 결과 저장 (히트존 색상 변경용)
        self.last_judgement = None
        # 디버그 정보 초기화
        self.debug_remaining_time = None
        self.debug_spatial_distance = None
        # 이벤트 히스토리 (테스트 모드용)
        self.event_history = deque(maxlen=50)  # 최근 50개 이벤트 저장
        # 비프음 타이머 (테스트 모드용)
        self.next_beep_time = 0.0
        
        # --- (수정) hit_zone을 ui.json에서 정적 위치로 초기화 ---
        pos_cfg = self.config_ui.get("positions", {})
        hit_zone_cfg = pos_cfg.get("hit_zone", {})
        hit_zone_ratio = hit_zone_cfg.get("pos_ratio", [0.5, 0.5])
        self.hit_zone = (int(self.width * hit_zone_ratio[0]), int(self.height * hit_zone_ratio[1]))
        # --- (수정 끝) ---
        
        # --- (추가) ui.json에서 히트존 반지름을 읽어 저장 ---
        hud_styles = self.config_ui.get("styles", {}).get("hud", {})
        self.hit_zone_radius = int(hud_styles.get("hit_zone_radius", 30))
        # --- (추가 끝) ---
        
        self.duck_line_y = int(self.height * 0.7); self.audio_manager.stop_music()
        
        self.calib_hold_start_time = 0.0
        self.last_pose_landmarks = None
        self.calib_status = (False, False, False) # (head_ok, lw_ok, rw_ok)
        
        # Phase 1: 랜드마크 데이터는 PoseTracker에서 관리
        # self.calib_landmark_pos, self.smoothed_landmark_pos 제거
        # self.left_fist_center, self.right_fist_center 제거
        
        self.base_ear_distance = 150.0 
        self.dynamic_size_ratio = 1.0 
        self.smoothed_dynamic_size_ratio = 1.0

        self.head_angle = 0.0
        self.smoothed_head_angle = 0.0
        
        print("GameScene: 게임 상태가 리셋되었습니다.")

    def startup(self, persistent_data):
        """씬 시작 시 캘리브레이션 상태로 전환하고 준비합니다."""
        super().startup(persistent_data)
        print("GameScene: Startup! 캘리브레이션을 시작합니다.")
        
        # (추가) 새 게임 시작 시 test_mode 초기화
        self.test_mode = False
        self._update_strategy()
        
        self.reset_game_state()
        self.scene_state = "CALIBRATING"
        self.state_start_time = time.time()
        
    def cleanup(self):
        """씬 종료 시 음악 정지 및 결과 데이터를 반환합니다."""
        print("GameScene: Cleanup! 음악을 정지합니다."); self.audio_manager.stop_music()
        self.persistent_data["final_score"] = self.state["score"]; self.persistent_data["max_combo"] = 0
        return super().cleanup() 

    def handle_event(self, key):
        """키 입력을 처리하여 캘리브레이션 스킵 등 상태를 변경합니다."""
        if self.scene_state == "CALIBRATING" and key == ord('0'):
            print("Calibration: '0' key pressed. Test mode 활성화 및 캘리브레이션 스킵.")
            
            # (추가) '0' 키를 누르면 test_mode 활성화
            self.test_mode = True
            self._update_strategy()
            
            self.duck_line_y = self.pose_tracker.calib_data['duck_line_y'] 
            
            if self.last_pose_landmarks:
                 self.pose_tracker.calibrate_from_pose(self.last_pose_landmarks)
                 self.duck_line_y = self.pose_tracker.calib_data['duck_line_y']
                 smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
                 if smoothed_landmarks.get("left_ear") and smoothed_landmarks.get("right_ear"):
                    l_ear = np.array(smoothed_landmarks["left_ear"])
                    r_ear = np.array(smoothed_landmarks["right_ear"])
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

    # Phase 4: _check_calib_position 메서드는 PoseTracker.check_calibration_position으로 이동됨

    def _hand_inside_hit_zone(self, ev_type):
        """이벤트 타입(JAB_L/JAB_R)에 해당하는 손 랜드마크가 히트존 원 내부인지 확인합니다 (Phase 1)."""
        if not hasattr(self, "hit_zone") or not hasattr(self, "hit_zone_radius"):
            return False
        cx, cy = self.hit_zone
        radius = self.hit_zone_radius
        if radius <= 0:
            return False

        # Phase 1: 스무딩된 랜드마크는 PoseTracker에서 가져옴
        smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
        left_fist, right_fist = self.pose_tracker.get_fist_centroids()

        # 모드: 1=손목만, 2=손목/새끼/검지/엄지 중 하나라도
        # (수정) cv2.flip을 고려하여 반대로 확인: JAB_L은 오른쪽 랜드마크, JAB_R은 왼쪽 랜드마크
        mode = int(self.config_rules.get("spatial_judge_mode", 2))
        if ev_type == "JAB_L":
            # 왼손 펀치 (화면 왼쪽) -> 실제로는 오른손 랜드마크 확인
            landmark_keys = ["right_wrist"] if mode == 1 else ["right_wrist", "right_pinky", "right_index", "right_thumb"]
        elif ev_type == "JAB_R":
            # 오른손 펀치 (화면 오른쪽) -> 실제로는 왼손 랜드마크 확인
            landmark_keys = ["left_wrist"] if mode == 1 else ["left_wrist", "left_pinky", "left_index", "left_thumb"]
        else:
            return False

        # (수정) 모든 랜드마크가 None인 경우를 명시적으로 처리
        valid_landmarks = []
        for key in landmark_keys:
            pt = smoothed_landmarks.get(key)
            if pt is not None:
                valid_landmarks.append((key, pt))
        
        # 모든 랜드마크가 None이면 False 반환
        if not valid_landmarks:
            return False
        
        # (Check 1: 개별 랜드마크) 하나라도 히트존 안에 있으면 True 반환
        for key, pt in valid_landmarks:
            dx = pt[0] - cx
            dy = pt[1] - cy
            if (dx * dx + dy * dy) <= (radius * radius):
                return True
        
        # (Check 2: 주먹 중심) 개별 랜드마크가 닿지 않았으면 주먹 중심도 체크
        hz_pos = np.array([cx, cy])
        fist_center = None
        
        if ev_type == "JAB_L":  # 화면 왼쪽 펀치
            fist_center = right_fist  # 사람의 오른쪽 손
        elif ev_type == "JAB_R":  # 화면 오른쪽 펀치
            fist_center = left_fist  # 사람의 왼쪽 손
        
        if fist_center:
            dist = np.linalg.norm(np.array(fist_center) - hz_pos)
            if dist <= radius:
                return True
        
        return False

    # --- (수정) _spawn_notes (hit_zone 제거) ---
    def _spawn_notes(self, t_game):
        """현재 게임 시간에 따라 노트를 생성하여 활성 목록에 추가합니다."""
        # (수정) config_rules 대신 인스턴스 변수 사용
        test_mode = self.test_mode
        while (self.next_note_idx < len(self.beat_map) and
               self.beat_map[self.next_note_idx]['t'] - self.pre_spawn_time <= t_game):
            item = self.beat_map[self.next_note_idx]; self.next_note_idx += 1
            if item['type'] == 'END': self.state['game_over'] = True; break
            # (수정) Note 생성 시 색상 + 스타일 + 판정 시간 + 테스트 모드 전달
            note_styles = self.config_ui.get("styles", {}).get("notes", {})
            note = Note(item, self.width, self.height, self.duck_line_y, self.pre_spawn_time, self.config_ui["colors"]["notes"], self.judge_timing, test_mode, note_styles)
            self.active_notes.append(note)
    # --- (수정 끝) ---

    def _judge_time(self, dt):
        """타격 시점 오차에 따라 판정 등급을 계산합니다."""
        adt = abs(dt)
        if adt <= self.judge_timing['perfect']: return 'PERFECT'
        if adt <= self.judge_timing['great']: return 'GREAT'
        if adt <= self.judge_timing['good']: return 'GOOD'
        return 'MISS'
        
    def _update_strategy(self):
        """test_mode에 따라 Strategy를 선택 또는 재선택합니다."""
        if self.test_mode:
            self.mode_strategy = TestModeStrategy(self)
            print("[GameScene] Test Mode Strategy 활성화")
        else:
            self.mode_strategy = NormalModeStrategy(self)
            print("[GameScene] Normal Mode Strategy 활성화")
    
    def _update_beep_time(self):
        """다음 비프음이 울릴 시각을 계산합니다 (BPM 동기화)."""
        song_info = self.config_difficulty.get("song_info", {})
        bpm = float(song_info.get("bpm", 120))
        division = int(song_info.get("division", 4))
        
        # BPM에 따라 division 간격 계산
        seconds_per_beat = 60.0 / max(1e-6, bpm)
        seconds_per_division = seconds_per_beat / max(1, division)
        
        # 다음 비프음 시각 설정
        now = time.time()
        if self.next_beep_time == 0.0:
            # 첫 비프음: 게임 시작 시간으로 설정 (division 간격 후)
            if self.state.get("start_time"):
                self.next_beep_time = self.state["start_time"] + seconds_per_division
            else:
                self.next_beep_time = now + seconds_per_division
        else:
            # 이후 비프음: division 간격만큼 추가
            self.next_beep_time += seconds_per_division
    
    def _add_judgement(self, judge_text, note_type, dt=None, pos=None):
        """판정 결과를 기록하고 점수/콤보/사운드를 갱신합니다."""
        # Strategy 패턴: format_judgement_text 사용
        display_text = self.mode_strategy.format_judgement_text(judge_text, dt)
        
        # (수정) floating_judgement_logs에 저장 (pos는 _draw_hud에서 계산)
        # "timing" 판정은 로그에 표시하지 않음
        if judge_text != "timing":
            color = tuple(self.config_ui["colors"]["judgement"].get(judge_text, [255, 255, 255]))
            # pos는 _draw_hud에서 계산하므로 여기서는 None으로 저장
            display_pos = None
            self.floating_judgement_logs.appendleft((display_text, color, display_pos))
        
        # 판정 통계 업데이트
        if judge_text in ["PERFECT", "GREAT", "GOOD"]:
            self.judgement_stats[judge_text] = self.judgement_stats.get(judge_text, 0) + 1
        elif judge_text in ["timing", "area", "area/timing"]:
            self.judgement_stats["MISS"] = self.judgement_stats.get("MISS", 0) + 1
        
        # 최근 판정 결과 저장 (히트존 색상 변경용)
        if judge_text in ["PERFECT", "GREAT", "GOOD"]:
            self.last_judgement = judge_text
        elif judge_text in ["timing", "area", "area/timing"]:
            self.last_judgement = "MISS"
        
        # 테스트 모드: assets 사운드 무시 (비프음은 BPM에 맞춰 자동 재생)
        # 일반 모드: assets 사운드 무시 (비프음만 재생)
        # if not self.test_mode:
        #     # 일반 모드: assets 사운드 재생
        #     sfx_name = judge_text
        #     if judge_text not in ["PERFECT", "GREAT", "GOOD", "BOMB!"]:
        #         sfx_name = "MISS"
        #     self.audio_manager.play_sfx(sfx_name)
        if judge_text in ["PERFECT", "GREAT", "GOOD"]:
            # --- 점수/콤보 계산 로직 ---
            self.state['combo'] += 1
            score_gain = self.config_rules["score_base"].get(judge_text, 0)
            score_gain *= self.score_multiplier
            combo_bonus = (self.state['combo'] // 10) * (score_gain * 0.1)
            self.state['score'] += int(score_gain + combo_bonus)
            # --- 점수/콤보 계산 로직 끝 ---
        else:
            self.state['combo'] = 0
            if judge_text == 'BOMB!': 
                self.state['score'] += self.bomb_penalty

    def _handle_hits(self, hit_events, t_game):
        """감지된 히트 이벤트를 해당 노트와 매칭하여 판정합니다."""
        now = time.time()
        # Strategy 패턴: 모드별 판정 로직 위임
        self.mode_strategy.handle_hits(hit_events, t_game, now)
            
    def _check_misses(self, t_game):
        """판정 가능 시간 초과 노트를 미스로 처리합니다."""
        judge_limit = self.judge_timing['good']
        now = time.time()
        for note in self.active_notes:
            if note.hit or note.missed: continue
            
            # 모든 모드: 타이밍 기반 MISS 처리 (플레이어 액션이 없을 때)
            if t_game > (note.t + judge_limit):
                # (수정) 텍스트를 띄울 위치를 미리 저장 (note.missed = True 전에)
                pos = (note.x, note.y)
                note.missed = True
                if note.typ != "BOMB":
                    # (추가) 얼마나 늦었는지 dt 계산 (t_game은 이미 상대 시간)
                    dt = t_game - note.t
                    note.judge_result = "timing"
                    self._add_judgement("timing", note.typ, dt=dt, pos=pos)

    # --- (수정) _draw_hud: Strategy 패턴으로 위임 ---
    def _draw_hud(self, frame):
        """점수/콤보/히트존/덕 라인 등 HUD 요소를 그립니다."""
        # Strategy 패턴: 모드별 HUD 그리기 위임
        if self.scene_state == "PLAYING":
            self.mode_strategy.draw_hud(frame)
            
    def update(self, frame, hit_events, landmarks, now):
        """포즈/상태를 갱신하고 씬 상태에 따라 게임 로직을 진행합니다."""
        
        # Phase 1: 랜드마크 스무딩은 PoseTracker에서 처리됨
        if landmarks:
            self.last_pose_landmarks = landmarks
        
        # Phase 4: 캘리브레이션 조준 확인은 PoseTracker에서 처리
        all_ok, self.calib_status, raw_landmark_pos = self.pose_tracker.check_calibration_position(self.calib_targets)

        # 3. '귀-귀' 벡터로 각도/크기 계산
        # Phase 1: 스무딩된 랜드마크는 PoseTracker에서 가져옴
        smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
        raw_L_EAR = smoothed_landmarks.get("left_ear")
        raw_R_EAR = smoothed_landmarks.get("right_ear")
        
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
        
        # Phase 1: 주먹 중심점은 PoseTracker에서 계산됨
        # self.left_fist_center, self.right_fist_center 제거
        
        # 각도/크기 스무딩
        SMOOTH_FACTOR = 0.7
        self.smoothed_head_angle = self.smoothed_head_angle * (1.0 - SMOOTH_FACTOR) + self.head_angle * SMOOTH_FACTOR
        self.smoothed_dynamic_size_ratio = self.smoothed_dynamic_size_ratio * (1.0 - SMOOTH_FACTOR) + self.dynamic_size_ratio * SMOOTH_FACTOR

        # 5. 씬 상태에 따른 로직 분기 (히트존은 정적 위치 사용)
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
                    
                    # Phase 1: 스무딩된 랜드마크는 PoseTracker에서 가져옴
                    smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
                    if smoothed_landmarks.get("left_ear") and smoothed_landmarks.get("right_ear"):
                        l_ear = np.array(smoothed_landmarks["left_ear"])
                        r_ear = np.array(smoothed_landmarks["right_ear"])
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
                print("GameScene: 게임 시작!"); self.scene_state = "PLAYING"; self.state["start_time"] = now
                # 비프음 타이머 초기화 (일반 모드와 테스트 모드 모두)
                self.next_beep_time = 0.0  # 리셋
                self._update_beep_time()  # 첫 비프음 시각 설정
                
                # 일반 모드: 배경 음악 재생 (비프음만 재생하도록 주석 처리)
                # if not self.test_mode:
                #     self.audio_manager.play_music()
            return
            
        elif self.scene_state == "PLAYING":
            if self.state["game_over"]:
                print("GameScene: 게임 종료. 결과 씬으로 전환합니다."); self.scene_state = "GAME_OVER"; self.state_start_time = now
                self.next_scene_name = "RESULT"; return
            t_game = now - self.state["start_time"]
            self._spawn_notes(t_game)
            
            # 비프음 재생 (BPM에 맞춰, 일반 모드와 테스트 모드 모두)
            if self.next_beep_time > 0.0:
                if now >= self.next_beep_time:
                    self.audio_manager.play_sfx('BEEP')
                    self._update_beep_time()  # 다음 비프음 시각 업데이트
            
            # Strategy 패턴: 모드별 이벤트 처리
            if hit_events:
                self.mode_strategy.on_hit_events(hit_events, now)
                self._handle_hits(hit_events, t_game)
            self._check_misses(t_game)
            
            # Phase 2: 디버그 정보 계산은 GameScene에서 수행 (calculate_debug_info 제거)
            # 필요 시 여기서 계산

    def _draw_equipment(self, frame):
        """
        현재 씬 상태와 랜드마크 위치에 따라 헤드기어만 그립니다.
        """
        draw_head = False
        smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
        current_head_center_pos = smoothed_landmarks.get("head_center")

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
        """현재 씬 상태에 맞는 UI와 노트를 화면에 렌더링합니다."""
        now = time.time()
        
        # 1. 장비 그리기 비활성화 (헤드기어 오버레이 일시 중지)
        # self._draw_equipment(frame)

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
            
            # (수정) 캘리브레이션 화면에서 코, 양손의 중앙점 표시 (게임 화면과 동일한 방식)
            # Phase 1: 스무딩된 랜드마크는 PoseTracker에서 가져옴
            smoothed_landmarks = self.pose_tracker.get_smoothed_landmarks()
            left_fist, right_fist = self.pose_tracker.get_fist_centroids()
            
            nose_pos = smoothed_landmarks.get("nose")
            
            if nose_pos:
                nx, ny = int(nose_pos[0]), int(nose_pos[1])
                cv2.circle(frame, (nx, ny), 8, (0, 255, 255), -1)  # 노란색 원
            
            # 손의 중앙점 표시 (spatial_judge_mode에 따라 계산된 중앙점 사용)
            if left_fist:
                lx, ly = left_fist
                cv2.circle(frame, (lx, ly), 8, (0, 255, 255), -1)  # 노란색 원
            
            if right_fist:
                rx, ry = right_fist
                cv2.circle(frame, (rx, ry), 8, (0, 255, 255), -1)  # 노란색 원

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
            
            # 노트 제거 로직:
            # 1. hit된 노트는 바로 제거
            # 2. missed된 노트는 다음 노트가 히트존에 도달할 때까지 유지
            now_time = time.time()
            hz_x, hz_y = self.hit_zone
            
            # 다음 노트가 히트존에 도달했는지 확인
            next_note_reached_hit_zone = False
            for note in self.active_notes:
                if note.hit or note.missed:
                    continue
                prog = note.get_progress(now_time, self.state["start_time"])
                if note.typ == "DUCK":
                    note_x = int((1 - prog) * note.x0 + prog * hz_x)
                    note_y = int((1 - prog) * note.y0 + prog * note.duck_line_y)
                    note_reached = (abs(note_y - note.duck_line_y) < 5) and (abs(note_x - hz_x) < 5)
                else:
                    note_x = int((1 - prog) * note.x0 + prog * hz_x)
                    note_y = int((1 - prog) * note.y0 + prog * hz_y)
                    note_to_hz_dist = np.sqrt((note_x - hz_x)**2 + (note_y - hz_y)**2)
                    note_reached = (note_to_hz_dist <= 5)
                
                if note_reached:
                    next_note_reached_hit_zone = True
                    break
            
            # hit된 노트는 바로 제거, missed된 노트는 다음 노트가 히트존에 도달했을 때만 제거
            if next_note_reached_hit_zone:
                # 다음 노트가 히트존에 도달했으면, hit된 노트와 missed된 노트 모두 제거
                self.active_notes = [n for n in self.active_notes if not n.hit and not n.missed]
            else:
                # 다음 노트가 아직 히트존에 도달하지 않았으면, hit된 노트만 제거 (missed 노트는 유지)
                self.active_notes = [n for n in self.active_notes if not n.hit]
            
            # Strategy 패턴: 모드별 추가 시각화 위임
            if self.scene_state == "PLAYING":
                self.mode_strategy.draw_additional(frame, now)