# scenes/main_menu_scene.py

import cv2
import pygame
import time
from scenes.base_scene import BaseScene

class MainMenuScene(BaseScene):
    # --- (수정) __init__ 시그니처 변경 ---
    def __init__(self, screen, audio_manager, config, pose_tracker):
        super().__init__(screen, audio_manager, config, pose_tracker)
        # --- (수정 끝) ---
        
        self.width = int(self.screen.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.title_pos = (int(self.width // 2 - 250), int(self.height // 2 - 50))
        self.start_pos = (int(self.width // 2 - 260), int(self.height // 2 + 50))
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale_title = 2.5
        self.font_scale_start = 1.5
        self.thickness = 3

        self.key_press_time = 0
        self.default_color = (255, 255, 255) # 기본 흰색
        self.press_color = (0, 255, 255)   # 누르면 노란색
        self.start_text_color = self.default_color

    def startup(self, persistent_data):
        """씬이 시작될 때 호출됩니다."""
        super().startup(persistent_data)
        self.start_text_color = self.default_color
        self.key_press_time = 0

    def handle_event(self, key):
        if key == ord(' ') or key == 32:  # Spacebar
            print("MainMenu: 'Spacebar' 키 입력. GameScene으로 전환합니다.")
            self.next_scene_name = "GAME"
            self.key_press_time = time.time()
            self.start_text_color = self.press_color

    # --- (수정) update 시그니처 변경 ---
    def update(self, frame, hit_events, landmarks, now):
        # --- (수정 끝) ---
        
        # 깜빡임 로직
        if self.key_press_time > 0 and (now - self.key_press_time) > 0.2:
            self.start_text_color = self.default_color
            self.key_press_time = 0 # 상태 리셋

    def draw(self, frame):
        # (frame은 main.py에서 블러 처리된 프레임이 넘어옴)
        
        # 타이틀 그리기
        cv2.putText(frame, "BEAT BOXER", 
                    self.title_pos, self.font, self.font_scale_title, self.default_color, self.thickness + 2)
        
        cv2.putText(frame, "Press 'Space' to Start", 
                    self.start_pos, self.font, self.font_scale_start, self.start_text_color, self.thickness)