# scenes/result_scene.py

import cv2
import pygame
import time
from scenes.base_scene import BaseScene

class ResultScene(BaseScene):
    # --- (수정) __init__ 시그니처 변경 ---
    def __init__(self, screen, audio_manager, config, pose_tracker):
        super().__init__(screen, audio_manager, config, pose_tracker)
        # --- (수정 끝) ---
        
        self.width = int(self.screen.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.title_pos = (int(self.width // 2 - 200), int(self.height // 2 - 100))
        self.score_pos = (int(self.width // 2 - 250), int(self.height // 2))
        self.menu_pos = (int(self.width // 2 - 300), int(self.height // 2 + 100))
        self.restart_pos = (int(self.width // 2 - 300), int(self.height // 2 + 150))
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.final_score = 0

        self.key_press_time_m = 0
        self.key_press_time_space = 0
        self.default_color = (200, 200, 200)
        self.press_color = (0, 255, 255)
        self.menu_text_color = self.default_color
        self.restart_text_color = self.default_color

    def startup(self, persistent_data):
        """GameScene에서 최종 점수를 받습니다."""
        super().startup(persistent_data)
        self.final_score = persistent_data.get("final_score", 0)
        print(f"ResultScene: 최종 점수 {self.final_score}를 받았습니다.")
        
        self.menu_text_color = self.default_color
        self.restart_text_color = self.default_color
        self.key_press_time_m = 0
        self.key_press_time_space = 0

    def handle_event(self, key):
        if key == ord(' ') or key == 32:
            print("ResultScene: 'Space' 키 입력. GameScene(재시작)으로 전환합니다.")
            self.next_scene_name = "GAME"
            self.key_press_time_space = time.time()
            self.restart_text_color = self.press_color

    # --- (수정) update 시그니처 변경 ---
    def update(self, frame, hit_events, landmarks, now):
        # --- (수정 끝) ---
        
        # M키 깜빡임 로직
        if self.key_press_time_m > 0 and (now - self.key_press_time_m) > 0.2:
            self.menu_text_color = self.default_color
            self.key_press_time_m = 0
            
        # 스페이스바 깜빡임 로직
        if self.key_press_time_space > 0 and (now - self.key_press_time_space) > 0.2:
            self.restart_text_color = self.default_color
            self.key_press_time_space = 0

    def draw(self, frame):
        # (frame은 main.py에서 블러 처리된 프레임이 넘어옴)
        
        cv2.putText(frame, "GAME OVER", 
                    self.title_pos, self.font, 2.5, (0, 0, 255), 5)
        
        cv2.putText(frame, f"Final Score: {self.final_score}", 
                    self.score_pos, self.font, 2.0, (255, 255, 255), 3)
        
        cv2.putText(frame, "Press 'Space' to Restart", 
                    self.restart_pos, self.font, 1.5, self.restart_text_color, 2)