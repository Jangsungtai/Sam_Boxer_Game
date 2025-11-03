# scenes/result_scene.py

import cv2
import pygame
import time
from scenes.base_scene import BaseScene

class ResultScene(BaseScene):
    def __init__(self, screen, audio_manager, config):
        super().__init__(screen, audio_manager, config)
        self.width = int(self.screen.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 텍스트 위치
        self.title_pos = (int(self.width // 2 - 200), int(self.height // 2 - 100))
        self.score_pos = (int(self.width // 2 - 250), int(self.height // 2))
        self.menu_pos = (int(self.width // 2 - 300), int(self.height // 2 + 100))
        
        # --- (추가) 재시작 텍스트 위치 ---
        self.restart_pos = (int(self.width // 2 - 300), int(self.height // 2 + 150))
        # --- (추가 끝) ---
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.final_score = 0

        # --- (수정) 깜빡임 효과용 변수 (키별로 분리) ---
        self.key_press_time_m = 0 # 'M' 키
        self.key_press_time_space = 0 # 'Space' 키
        self.default_color = (200, 200, 200) # 기본 회색
        self.press_color = (0, 255, 255)   # 누르면 노란색
        self.menu_text_color = self.default_color
        self.restart_text_color = self.default_color # 재시작 텍스트 색상
        # --- (수정 끝) ---

    def startup(self, persistent_data):
        """GameScene에서 최종 점수를 받습니다."""
        super().startup(persistent_data) # 부모 startup 호출
        self.final_score = persistent_data.get("final_score", 0)
        print(f"ResultScene: 최종 점수 {self.final_score}를 받았습니다.")
        
        # --- (수정) 씬이 다시 시작될 때 모든 색상/키 초기화 ---
        self.menu_text_color = self.default_color
        self.restart_text_color = self.default_color
        self.key_press_time_m = 0
        self.key_press_time_space = 0
        # --- (수정 끝) ---
    def handle_event(self, key):
        if key == ord(' ') or key == 32:
            print("ResultScene: 'Space' 키 입력. GameScene(재시작)으로 전환합니다.")
            self.next_scene_name = "GAME"
            self.key_press_time_space = time.time()
            self.restart_text_color = self.press_color


        # --- (추가) 스페이스바를 누르면 게임 씬(재시작)으로 전환 ---
        elif key == ord(' ') or key == 32:
            print("ResultScene: 'Space' 키 입력. GameScene(재시작)으로 전환합니다.")
            self.next_scene_name = "GAME"
            # 키 눌림 상태 저장 (깜빡임)
            self.key_press_time_space = time.time()
            self.restart_text_color = self.press_color
        # --- (추가 끝) ---

    def update(self, frame, now):
        # M키 깜빡임 로직
        if self.key_press_time_m > 0 and (now - self.key_press_time_m) > 0.2:
            self.menu_text_color = self.default_color
            self.key_press_time_m = 0 # 상태 리셋
            
        # --- (추가) 스페이스바 깜빡임 로직 ---
        if self.key_press_time_space > 0 and (now - self.key_press_time_space) > 0.2:
            self.restart_text_color = self.default_color
            self.key_press_time_space = 0 # 상태 리셋
        # --- (추가 끝) ---

    def draw(self, frame):
        # "GAME OVER" 및 최종 점수 표시
        cv2.putText(frame, "GAME OVER", 
                    self.title_pos, self.font, 2.5, (0, 0, 255), 5)
        
        cv2.putText(frame, f"Final Score: {self.final_score}", 
                    self.score_pos, self.font, 2.0, (255, 255, 255), 3)
        
        # --- 메뉴 텍스트 제거됨 ---
        # cv2.putText(frame, "Press 'M' to Main Menu", 
        #             self.menu_pos, self.font, 1.5, self.menu_text_color, 2)
        
        # 재시작 텍스트만 유지
        cv2.putText(frame, "Press 'Space' to Restart", 
                    self.restart_pos, self.font, 1.5, self.restart_text_color, 2)
