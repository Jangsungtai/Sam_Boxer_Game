# scenes/game_scene.py

import cv2
import time
import json
import numpy as np
import os
import sys
from collections import deque
import pygame

from scenes.base_scene import BaseScene
from core.pose_tracker import PoseTracker
from core.note import Note

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

class GameScene(BaseScene):
    def __init__(self, screen, audio_manager, config):
        # ( ... __init__ 의 다른 코드는 4단계, 5단계와 동일 ... )
        # ( ... 생략 ... )
        super().__init__(screen, audio_manager, config)
        
        self.width = int(self.screen.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.config_rules = config["rules"]
        self.config_difficulty = config["difficulty"]
        self.config_ui = config["ui"]
        
        difficulty_name = "Normal" 
        self.difficulty = self.config_difficulty["levels"].get(difficulty_name, self.config_difficulty["levels"]["Normal"])
        self.judge_timing = {k: v * self.difficulty["judge_timing_scale"] for k, v in self.config_rules["judge_timing"].items()}
        self.pre_spawn_time = self.difficulty["pre_spawn_time"]
        self.score_multiplier = self.difficulty["score_multiplier"]
        self.bomb_penalty = self.config_rules["bomb_penalty"]

        self.pose_tracker = PoseTracker(self.width, self.height, self.config_rules, self.config_ui)
        
        beatmap_path = resource_path("assets/beatmaps/song1/beatmap.json")
        with open(beatmap_path, 'r') as f:
            beat_map_data = json.load(f)
        self.beat_map = sorted(beat_map_data, key=lambda x: x['t'])
        
        music_path_rel = os.path.join("assets/beatmaps/song1", "music.mp3")
        self.audio_manager.load_music(music_path_rel)
        
        self.reset_game_state()
        
        self.scene_state = "CALIBRATING"
        self.calibration_frames = []
        self.state_start_time = time.time()


    def reset_game_state(self):
        # ( ... 동일 ... )
        self.next_note_idx = 0
        self.state = {"score": 0, "combo": 0, "start_time": None, "game_over": False}
        self.active_notes = []
        self.judges_log = deque(maxlen=5)
        hz_ratio = self.config_ui["positions"]["hit_zone_ratio"]
        self.hit_zone = (int(self.width * hz_ratio[0]), int(self.height * hz_ratio[1]))
        self.duck_line_y = int(self.height * 0.7)
        self.audio_manager.stop_music()
        print("GameScene: 게임 상태가 리셋되었습니다.")

    def startup(self, persistent_data):
        # ( ... 동일 ... )
        print("GameScene: Startup! 캘리브레이션을 시작합니다.")
        self.reset_game_state()
        self.scene_state = "CALIBRATING"
        self.calibration_frames = []
        self.state_start_time = time.time()
        
    def cleanup(self):
        # ( ... 동일 ... )
        print("GameScene: Cleanup! 음악을 정지합니다.")
        self.audio_manager.stop_music()
        self.persistent_data["final_score"] = self.state["score"]
        self.persistent_data["max_combo"] = 0
        # (!!!) 부모 클래스의 cleanup을 호출하여 next_scene_name을 리셋해야 함
        return super().cleanup() # BaseScene의 cleanup 호출

    def handle_event(self, event):
        # --- (수정) 'q' 대신 'm' 키로 메뉴 이동 ---
        """'M'/'m' 키를 누르면 메뉴로 돌아갑니다."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m: # M key
            print("GameScene: 'M' 키 입력. 메뉴로 돌아갑니다.")
            self.next_scene_name = "MENU"
        # --- (수정 끝) ---
            
    # ( ... _spawn_notes, _judge_time, _add_judgement ... )
    # ( ... _handle_hits, _check_misses, _draw_hud ... )
    # ( ... update, draw 메서드들은 5단계와 동일 ... )
    # ( ... (생략) ... )
    def _spawn_notes(self, t_game):
        while (self.next_note_idx < len(self.beat_map) and
               self.beat_map[self.next_note_idx]['t'] - self.pre_spawn_time <= t_game):
            item = self.beat_map[self.next_note_idx]
            self.next_note_idx += 1
            if item['type'] == 'END':
                self.state['game_over'] = True
                break
            note = Note(item, self.width, self.height, 
                        self.hit_zone, self.duck_line_y, self.pre_spawn_time,
                        self.config_ui["colors"]["notes"])
            self.active_notes.append(note)

    def _judge_time(self, dt):
        adt = abs(dt)
        if adt <= self.judge_timing['perfect']: return 'PERFECT'
        if adt <= self.judge_timing['great']: return 'GREAT'
        if adt <= self.judge_timing['good']: return 'GOOD'
        return 'MISS'
        
    def _add_judgement(self, judge_text, note_type):
        color = tuple(self.config_ui["colors"]["judgement"].get(judge_text, [255,255,255]))
        self.judges_log.appendleft((judge_text, color))
        self.audio_manager.play_sfx(judge_text)
        if judge_text == 'MISS' or judge_text == 'BOMB!':
            self.state['combo'] = 0
            if judge_text == 'BOMB!':
                self.state['score'] += self.bomb_penalty
        else:
            self.state['combo'] += 1
            score_gain = self.config_rules["score_base"].get(judge_text, 0)
            score_gain *= self.score_multiplier
            combo_bonus = (self.state['combo'] // 10) * (score_gain * 0.1) 
            self.state['score'] += int(score_gain + combo_bonus)

    def _handle_hits(self, hit_events, t_game):
        now = time.time()
        for ev in hit_events:
            ev_type = ev["type"]; t_hit = ev["t_hit"]
            if ev_type.startswith("JAB"):
                bombs = [n for n in self.active_notes if n.typ == "BOMB" and not n.hit and not n.missed]
                for b in bombs:
                    dt = t_hit - (self.state['start_time'] + b.t)
                    if abs(dt) < self.judge_timing['good']:
                        b.hit = True
                        self._add_judgement("BOMB!", "BOMB")
                        return
            candidates = [n for n in self.active_notes if n.typ == ev_type and not n.hit and not n.missed]
            if not candidates: continue
            target_note = min(candidates, key=lambda n: abs(t_hit - (self.state['start_time'] + n.t)))
            dt = t_hit - (self.state['start_time'] + target_note.t)
            judge_result = self._judge_time(dt)
            if judge_result != 'MISS':
                target_note.hit = True
                self._add_judgement(judge_result, target_note.typ)
            
    def _check_misses(self, t_game):
        judge_limit = self.judge_timing['good']
        for note in self.active_notes:
            if note.hit or note.missed: continue
            if t_game > (note.t + judge_limit):
                note.missed = True
                if note.typ != "BOMB":
                    self._add_judgement("MISS", note.typ)

    def _draw_hud(self, frame):
        ui_cfg = self.config_ui; pos_cfg = ui_cfg["positions"]; col_cfg = ui_cfg["colors"]["hud"]
        duck_y = self.duck_line_y
        cv2.line(frame, (0, duck_y), (self.width, duck_y), tuple(col_cfg["duck_line"]), 2)
        cv2.putText(frame, "DUCK LINE", (10, duck_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, tuple(col_cfg["duck_line"]), 2)
        hz_x, hz_y = self.hit_zone
        cv2.circle(frame, (hz_x, hz_y), 30, tuple(col_cfg["hit_zone"]), 2)
        score_pos = tuple(pos_cfg["score"])
        score_text = f"Score: {self.state['score']}"
        combo_text = f"Combo: {self.state['combo']}"
        cv2.putText(frame, score_text, score_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["score_text"]), 3)
        (text_width, _), _ = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)
        combo_pos = (self.width - text_width - 20, score_pos[1])
        cv2.putText(frame, combo_text, combo_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["combo_text"]), 3)
        log_start_pos = tuple(pos_cfg["judge_log_start"])
        for i, (text, color) in enumerate(self.judges_log):
            y_pos = log_start_pos[1] + i * 40
            cv2.putText(frame, text, (log_start_pos[0], y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            
    def update(self, frame, now):
        if self.scene_state == "CALIBRATING":
            t_elapsed = now - self.state_start_time
            if t_elapsed >= 2.0:
                self.pose_tracker.calibrate_from_frames(self.calibration_frames)
                self.duck_line_y = self.pose_tracker.calib_data['duck_line_y']
                print("GameScene: 캘리브레이션 완료. 카운트다운 시작.")
                self.scene_state = "COUNTDOWN"
                self.state_start_time = now
            else:
                self.calibration_frames.append(frame.copy())
            return
        elif self.scene_state == "COUNTDOWN":
            t_elapsed = now - self.state_start_time
            if t_elapsed >= 3.0:
                print("GameScene: 게임 시작!")
                self.scene_state = "PLAYING"
                self.state["start_time"] = now
                self.audio_manager.play_music()
            return
        elif self.scene_state == "PLAYING":
            if self.state["game_over"]:
                print("GameScene: 게임 종료. 결과 씬으로 전환합니다.")
                self.scene_state = "GAME_OVER"
                self.state_start_time = now
                self.next_scene_name = "RESULT"
                return
            t_game = now - self.state["start_time"]
            hit_events, landmarks = self.pose_tracker.process_frame(frame, now)
            self._spawn_notes(t_game)
            if hit_events:
                self._handle_hits(hit_events, t_game)
            self._check_misses(t_game)

    def draw(self, frame):
        now = time.time()
        if self.scene_state == "CALIBRATING":
            t_elapsed = now - self.state_start_time
            countdown = 2.0 - t_elapsed
            cv2.putText(frame, f"Calibrating... {countdown:.1f}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        elif self.scene_state == "COUNTDOWN":
            t_elapsed = now - self.state_start_time
            countdown = 3.0 - t_elapsed
            cv2.putText(frame, f"{countdown:.1f}", (self.width//2 - 50, self.height//2), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 5)
        elif self.scene_state == "PLAYING":
            self._draw_hud(frame)
            for note in self.active_notes:
                note.update_and_draw(frame, now, self.state["start_time"])
            self.active_notes = [n for n in self.active_notes if not n.hit and not n.missed]