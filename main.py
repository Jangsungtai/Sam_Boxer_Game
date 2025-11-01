# main.py

import sys
import pygame
import cv2
import json
import time
import os  # <--- 이 줄을 추가하세요

# 씬(Scene) 임포트
from scenes.main_menu_scene import MainMenuScene
from scenes.game_scene import GameScene
from scenes.result_scene import ResultScene
from core.audio_manager import AudioManager

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # PyInstaller가 아닌 일반 .py 실행 환경
        base_path = os.path.abspath(".") # (이제 'os'를 인식합니다)

    return os.path.join(base_path, relative_path) # (이제 'os'를 인식합니다)


def main():
    # 1. Pygame 초기화 (오디오/이벤트)
    try:
        pygame.init()
        print("Pygame 모듈 초기화 성공")
    except Exception as e:
        print(f"Pygame 초기화 실패: {e}")
        return

    # 2. OpenCV 카메라 초기화
    cap = cv2.VideoCapture(0) # 1번 카메라 (이전 오류 수정)
    if not cap.isOpened():
        print("오류: 카메라를 열 수 없습니다.")
        pygame.quit()
        return
    print("카메라 초기화 성공")

    # 3. 설정 파일 로드
    try:
        print("Loading config files...")
        CONFIG = {
            "rules": json.load(open(resource_path("config/rules.json"), 'r')),
            "difficulty": json.load(open(resource_path("config/difficulty.json"), 'r')),
            "ui": json.load(open(resource_path("config/ui.json"), 'r'))
        }
    except FileNotFoundError as e:
        print(f"오류: 필수 config 파일을 찾을 수 없습니다. {e}")
        cap.release()
        pygame.quit()
        return

    # 4. 오디오 매니저 생성
    audio_manager = AudioManager()
    sfx_map = {
        "PERFECT": "hit_perfect.wav", "GREAT": "hit_good.wav",
        "GOOD": "hit_good.wav", "MISS": "miss.wav", "BOMB!": "bomb.wav"
    }
    audio_manager.load_sounds(sfx_map)

    # 5. 모든 씬(Scene) 생성
    scenes = {
        "MENU": MainMenuScene(cap, audio_manager, CONFIG),
        "GAME": GameScene(cap, audio_manager, CONFIG),
        "RESULT": ResultScene(cap, audio_manager, CONFIG)
    }
    
    active_scene = scenes["MENU"] 
    active_scene.startup({})
    
    print("메인 루프를 시작합니다. (첫 씬: MENU)")

    # 6. 메인 게임 루프 (씬 매니저)
    try:
        while True:
            # --- (수정) 1. 글로벌 이벤트 처리 (종료) ---
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    print("종료 이벤트 (pygame.QUIT)")
                    return # ★★★ GLOBAL QUIT ★★★

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q: # Q/q 키
                        print("'(Q)uit' 키 입력. 강제 종료.")
                        return # ★★★ GLOBAL QUIT ★★★
                    
                    if event.key == pygame.K_ESCAPE: # ESC 키
                        print("'(ESC)ape' 키 입력. 강제 종료.")
                        return # ★★★ GLOBAL QUIT ★★★

                # 씬에 이벤트 전달 (Q, ESC가 아닌 모든 이벤트)
                active_scene.handle_event(event)
            # --- (수정 끝) ---

            # (2) 카메라 프레임 읽기
            ret, frame = cap.read()
            if not ret:
                print("오류: 프레임 읽기 실패")
                break
            frame = cv2.flip(frame, 1)
            
            # (3) 현재 씬 로직 업데이트
            active_scene.update(frame, time.time())
            
            # (4) 현재 씬 그리기
            active_scene.draw(frame)
            
            # (5) 화면 표시
            cv2.imshow("Beat Boxer", frame)

            # (6) 씬 전환 확인
            next_scene_name = active_scene.next_scene_name
            if next_scene_name:
                print(f"씬 전환: {active_scene.__class__.__name__} -> {next_scene_name}")
                persistent_data = active_scene.cleanup() 
                active_scene = scenes.get(next_scene_name)
                if not active_scene:
                    print(f"오류: {next_scene_name} 씬을 찾을 수 없습니다. 종료합니다.")
                    break
                active_scene.startup(persistent_data)

            # --- (수정) (7) 프레임 대기 (OpenCV 창 유지를 위해 1ms 대기) ---
            # 키보드 입력은 Pygame 루프가 전담하므로 여기서는 키 검사 안 함
            cv2.waitKey(1)
            # --- (수정 끝) ---
                
    except KeyboardInterrupt:
        print("\n(Ctrl+C) 게임 실행을 강제 중단합니다.")
    except Exception as e:
        print(f"메인 루프 중 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 7. 종료
        print("모든 리소스를 정리합니다...")
        cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        print("프로그램을 종료합니다.")

if __name__ == "__main__":
    main()