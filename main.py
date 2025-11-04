import sys
import pygame
import cv2
import json
import time
import os

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
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_best_camera_index():
    """ 사용 가능한 카메라 인덱스를 역순으로 (e.g., 3, 2, 1, 0) 탐색합니다. """
    print("사용 가능한 카메라를 찾는 중...")
    # 4번부터 0번까지 역순으로 탐색
    for index in range(4, -1, -1):
        # cv2.CAP_AVFOUNDATION: Mac의 네이티브 카메라 API를 강제 사용
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            print(f"카메라 발견: 인덱스 {index}")
            cap.release() # 테스트 종료
            return index
    
            
    print("기본 카메라(0번)를 찾지 못했습니다. 0번으로 시도합니다.")
    return 0


def main():
    # 1. Pygame 초기화 (오디오)
    try:
        pygame.init()
        print("Pygame 모듈 초기화 성공")
    except Exception as e:
        print(f"Pygame 초기화 실패: {e}")
        return

    # 2. OpenCV 카메라 초기화
    camera_index = get_best_camera_index()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"오류: 카메라(인덱스 {camera_index})를 열 수 없습니다.")
        pygame.quit()
        return
    print(f"카메라 초기화 성공 (인덱스: {camera_index})")

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
        "PERFECT": "hit_perfect.wav",
        "GREAT": "hit_good.wav",
        "GOOD": "hit_good.wav",
        "MISS": "miss.wav",
        "BOMB!": "bomb.wav"
    }
    audio_manager.load_sounds(sfx_map)

    # 5. 모든 씬(Scene) 생성
    scenes = {
        "MENU": MainMenuScene(cap, audio_manager, CONFIG),
        "GAME": GameScene(cap, audio_manager, CONFIG),
        "RESULT": ResultScene(cap, audio_manager, CONFIG)
    }
    
    active_scene = scenes["MENU"] # 시작 씬
    active_scene.startup({})
    
    print("메인 루프를 시작합니다. (첫 씬: MENU)")
    print("--- 키 안내 ---")
    print("  Q / ESC : 즉시 종료")
    print("  SPACE (메뉴) : 게임 시작")
    print("  M (게임/결과) : 메뉴로")
    print("---------------")

    # 6. 메인 게임 루프 (씬 매니저)
    try:
        while True:
            # (1) Pygame 이벤트 처리 (창 종료 버튼 'X' 감지용)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("종료 이벤트 (pygame.QUIT)")
                    return

            # (2) 카메라 프레임 읽기
            ret, frame = cap.read()
            if not ret:
                print("오류: 프레임 읽기 실패")
                break
            frame = cv2.flip(frame, 1) # 좌우 반전
            
            # (3) 현재 씬 로직 업데이트
            active_scene.update(frame, time.time())
            
            # (4) 현재 씬 그리기
            active_scene.draw(frame)
            
            # (5) 화면 표시
            cv2.imshow("Beat Boxer", frame)

            # (6) OpenCV 키보드 입력 처리
            # (6) OpenCV 키보드 입력 처리
            key = cv2.waitKey(1) & 0xFF

            if key != 255:
                try:
                    print(f"[DEBUG] Key pressed. ASCII: {key}, Char: '{chr(key)}'")
                except:
                    print(f"[DEBUG] Key pressed. ASCII: {key} (Non-printable char)")

            # (7) 전역 키 처리 (종료)
            if key == 27:  # ESC only
                print("'ESC' 키 입력. 프로그램 종료.")
                return 

            # (8) 씬에 키 이벤트 전달
            active_scene.handle_event(key)

            # (9) 씬 전환 확인
            next_scene_name = active_scene.next_scene_name
            if next_scene_name:
                print(f"씬 전환: {active_scene.__class__.__name__} -> {next_scene_name}")
                persistent_data = active_scene.cleanup() 
                active_scene = scenes.get(next_scene_name)
                if not active_scene:
                    print(f"오류: {next_scene_name} 씬을 찾을 수 없습니다. 종료합니다.")
                    break
                active_scene.startup(persistent_data)
                
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