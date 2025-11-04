import sys
import pygame
import cv2
import json
import time
import os
import numpy as np # (추가)

# 씬(Scene) 임포트
from scenes.main_menu_scene import MainMenuScene
from scenes.game_scene import GameScene
from scenes.result_scene import ResultScene
from core.audio_manager import AudioManager
from core.pose_tracker import PoseTracker # (추가)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_best_camera_index():
    """ 사용 가능한 카메라 인덱스를 역순으로 (e.g., 3, 2, 1, 0) 탐색합니다. """
    print("사용 가능한 카메라를 찾는 중...")
    for index in range(4, -1, -1):
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            print(f"카메라 발견: 인덱스 {index}")
            cap.release()
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
    
    # (추가) 카메라 해상도 가져오기
    CAM_WIDTH = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    CAM_HEIGHT = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"카메라 초기화 성공 (인덱스: {camera_index}, {CAM_WIDTH}x{CAM_HEIGHT})")


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

    # --- (추가) 5. PoseTracker 생성 (main에서) ---
    print("Initializing Pose Tracker...")
    pose_tracker = PoseTracker(CAM_WIDTH, CAM_HEIGHT, CONFIG["rules"], CONFIG["ui"])
    # --- (추가 끝) ---

    # --- (수정) 6. 모든 씬(Scene) 생성 (pose_tracker 전달) ---
    scenes = {
        "MENU": MainMenuScene(cap, audio_manager, CONFIG, pose_tracker),
        "GAME": GameScene(cap, audio_manager, CONFIG, pose_tracker),
        "RESULT": ResultScene(cap, audio_manager, CONFIG, pose_tracker)
    }
    # --- (수정 끝) ---
    
    active_scene = scenes["MENU"] # 시작 씬
    active_scene.startup({})
    
    print("메인 루프를 시작합니다. (첫 씬: MENU)")
    print("--- 키 안내 ---")
    print("  ESC : 즉시 종료")
    print("  0 (캘리브레이션) : 캘리브레이션 스킵")
    print("  SPACE (메뉴) : 게임 시작")
    print("  SPACE (결과) : 게임 재시작")
    print("---------------")
    
    # (추가) 블러 처리를 위한 배경 이미지 (초기화)
    blurred_bg = np.zeros((CAM_HEIGHT, CAM_WIDTH, 3), dtype=np.uint8)

    # 7. 메인 게임 루프 (씬 매니저)
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
            
            # --- (추가) 3. Pose-Tracking 및 배경 블러 (main에서) ---
            now = time.time()
            
            # (수정) 원본 프레임(frame)을 복사하여 포즈 트래커에 전달 (랜드마크가 원본에 그려지는 것을 방지)
            frame_for_pose = frame.copy()
            hit_events, landmarks, mask = pose_tracker.process_frame(frame_for_pose, now)
            
            if mask is not None:
                # 배경 블러 생성
                blurred_bg = cv2.GaussianBlur(frame, (21, 21), 0)
                
                # 마스크를 3채널로 확장 (B, G, R)
                mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                
                # 마스크(사람) 부분은 원본(frame)을, 아닌 부분은 블러(blurred_bg)를 합성
                display_frame = np.where(mask_3ch > 0.1, frame, blurred_bg)
            else:
                # 마스크가 없으면 (아직 로딩 중이거나 감지 실패 시) 원본 프레임 표시
                display_frame = frame
            # --- (추가 끝) ---

            # (수정) 4. 현재 씬 로직 업데이트
            # (원본 frame과 랜드마크 정보를 전달)
            active_scene.update(frame, hit_events, landmarks, now)
            
            # (수정) 5. 현재 씬 그리기
            # (블러 처리된 display_frame에 UI를 그리도록 전달)
            active_scene.draw(display_frame)
            
            # (수정) 6. 화면 표시
            # (최종 합성된 display_frame을 표시)
            cv2.imshow("Beat Boxer", display_frame)

            # (7) OpenCV 키보드 입력 처리
            key = cv2.waitKey(1) & 0xFF

            # (8) 전역 키 처리 (종료)
            if key == 27:  # ESC only
                print("'ESC' 키 입력. 프로그램 종료.")
                return 

            # (9) 씬에 키 이벤트 전달
            active_scene.handle_event(key)

            # (10) 씬 전환 확인
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
        # 8. 종료
        print("모든 리소스를 정리합니다...")
        cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        print("프로그램을 종료합니다.")

if __name__ == "__main__":
    main()