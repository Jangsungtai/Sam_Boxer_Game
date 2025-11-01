# scenes/main_menu_scene.py

import cv2
import pygame
from scenes.base_scene import BaseScene

class MainMenuScene(BaseScene):
    def __init__(self, screen, audio_manager, config):
        super().__init__(screen, audio_manager, config)
        self.width = self.screen.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.screen.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        # 텍스트 위치 계산
        self.title_pos = (int(self.width // 2 - 250), int(self.height // 2 - 50))
        self.start_pos = (int(self.width // 2 - 200), int(self.height // 2 + 50))
        
        # 폰트 설정
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale_title = 2.5
        self.font_scale_start = 1.5
        self.color = (255, 255, 255)
        self.thickness = 3

    def handle_event(self, event):
        # 's' 키를 누르면 게임 씬으로 전환
        if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
            print("MainMenu: 'S' 키 입력. GameScene으로 전환합니다.")
            self.next_scene_name = "GAME"

    def update(self, frame, now):
        # 메뉴 씬은 특별히 업데이트할 로직이 없음
        pass

    def draw(self, frame):
        # 화면에 "BEAT BOXER"와 "Press 'S' to Start" 그리기
        cv2.putText(frame, "BEAT BOXER", 
                    self.title_pos, self.font, self.font_scale_title, self.color, self.thickness + 2)
        
        cv2.putText(frame, "Press 'S' to Start", 
                    self.start_pos, self.font, self.font_scale_start, self.color, self.thickness)