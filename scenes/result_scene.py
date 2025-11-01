# scenes/result_scene.py

import cv2
import pygame
from scenes.base_scene import BaseScene

class ResultScene(BaseScene):
    def __init__(self, screen, audio_manager, config):
        super().__init__(screen, audio_manager, config)
        self.width = self.screen.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        # 텍스트 위치
        self.title_pos = (int(self.width // 2 - 200), int(self.height // 2 - 100))
        self.score_pos = (int(self.width // 2 - 250), int(self.height // 2))
        self.menu_pos = (int(self.width // 2 - 280), int(self.height // 2 + 100))
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.final_score = 0

    def startup(self, persistent_data):
        """GameScene에서 최종 점수를 받습니다."""
        self.final_score = persistent_data.get("final_score", 0)
        print(f"ResultScene: 최종 점수 {self.final_score}를 받았습니다.")

    def handle_event(self, event):
        # 'm' 키를 누르면 메뉴 씬으로 전환
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            print("ResultScene: 'M' 키 입력. MainMenu로 전환합니다.")
            self.next_scene_name = "MENU"

    def update(self, frame, now):
        # 점수만 보여주므로 업데이트 로직 없음
        pass

    def draw(self, frame):
        # 화면에 "GAME OVER"와 최종 점수 그리기
        cv2.putText(frame, "GAME OVER", 
                    self.title_pos, self.font, 2.5, (0, 0, 255), 5)
        
        cv2.putText(frame, f"Final Score: {self.final_score}", 
                    self.score_pos, self.font, 2.0, (255, 255, 255), 3)
                    
        cv2.putText(frame, "Press 'M' to Main Menu", 
                    self.menu_pos, self.font, 1.5, (200, 200, 200), 2)