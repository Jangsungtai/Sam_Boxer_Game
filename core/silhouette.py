"""
실시간 실루엣 윤곽선 추출 및 렌더링 모듈 (최대 부드러움 및 네온 효과 적용)

MediaPipe Selfie Segmentation과 Pose 랜드마크를 함께 사용하여 실루엣 외곽선과 인체 뼈대 와이어프레임을 그립니다.
고품질 후처리(블러, 모폴로지 연산)와 네온 효과를 통해 시각적 퀄리티를 극대화합니다.

**수정 사항:** 윤곽선 부드러움을 극대화하기 위해 cv2.CHAIN_APPROX_NONE이 사용되었고, draw_outline 함수에 네온 효과가 추가되었습니다. Pose 기능이 추가되어 뼈대도 함께 표시됩니다.
"""

import cv2
import numpy as np
import mediapipe as mp
import time

# ============================================================================
# 조정 가능한 파라미터
# ============================================================================

# 비디오 캡처 설정
CAMERA_INDEX = None  # None이면 자동으로 Mac 기본 카메라 탐색
CAPTURE_WIDTH = 1280  # 캡처 해상도 너비
CAPTURE_HEIGHT = 720  # 캡처 해상도 높이

# 내부 처리 해상도 (성능 최적화)
PROCESS_WIDTH = 960  # 처리 너비 (원본 비율 유지)
PROCESS_HEIGHT = None  # None이면 비율에 맞게 자동 계산

# MediaPipe 설정
SEGMENTATION_MODEL = 1  # Selfie Segmentation: 0: 일반, 1: 고품질
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

# 후처리 파라미터
BLUR_KERNEL = (15, 15)  # Gaussian 블러 커널 크기 (홀수여야 함)
THRESHOLD_VALUE = 127  # 이진화 임계값 (0-255)
MORPH_KERNEL_SIZE = 5  # 모폴로지 연산 커널 크기
MORPH_ITERATIONS = 2  # 모폴로지 연산 반복 횟수

# 렌더링 설정
OUTLINE_COLOR = (255, 255, 255)  # 윤곽선 핵심 색상 (BGR 형식, 흰색)
OUTLINE_THICKNESS = 2  # 윤곽선 두께
BACKGROUND_COLOR = (0, 0, 0)  # 배경 색상 (BGR 형식, 검은색)
GLOW_COLOR = (180, 255, 255)  # 네온 글로우 색상 (시안/파랑 계열)
POSE_COLOR = (255, 0, 255)  # 포즈 와이어프레임 색상 (마젠타)
POSE_THICKNESS = 3  # 포즈 선 두께

# 윈도우 설정
WINDOW_NAME = "실루엣 및 포즈 모듈"

# 성능 모니터링
SHOW_FPS = True  # FPS 표시 여부
FPS_UPDATE_INTERVAL = 1.0  # FPS 업데이트 간격 (초)


# ============================================================================
# 카메라 선택 함수
# ============================================================================

def get_best_camera_index() -> int:
    """
    Mac의 기본 카메라를 찾아 인덱스를 반환합니다.
    """
    print("사용 가능한 카메라를 찾는 중...")
    for index in range(4, -1, -1):
        # cv2.CAP_AVFOUNDATION 사용
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            print(f"카메라 발견: 인덱스 {index}")
            cap.release()
            return index
    print("사용 가능한 카메라가 없습니다. 0번 인덱스로 시도합니다.")
    return 0


# ============================================================================
# MediaPipe 초기화
# ============================================================================

def initialize_mediapipe():
    """
    MediaPipe Selfie Segmentation 및 Pose 모델을 초기화합니다.
    """
    mp_selfie_segmentation = mp.solutions.selfie_segmentation
    segmentation = mp_selfie_segmentation.SelfieSegmentation(
        model_selection=SEGMENTATION_MODEL
    )
    
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE
    )
    
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    return segmentation, pose, mp_drawing, mp_drawing_styles


# ============================================================================
# 프레임 처리 및 윤곽선 추출
# ============================================================================

def resize_for_processing(frame: np.ndarray) -> tuple[np.ndarray, float]:
    """
    성능 최적화를 위해 프레임을 처리 해상도로 리사이즈합니다.
    """
    original_height, original_width = frame.shape[:2]
    
    if PROCESS_HEIGHT is None:
        scale = PROCESS_WIDTH / original_width
        process_height = int(original_height * scale)
    else:
        process_height = PROCESS_HEIGHT
        scale = PROCESS_WIDTH / original_width
    
    resized_frame = cv2.resize(
        frame, 
        (PROCESS_WIDTH, process_height), 
        interpolation=cv2.INTER_LINEAR
    )
    
    return resized_frame, scale


def process_frame(frame: np.ndarray, segmentation, pose):
    """
    프레임에서 실루엣 마스크와 포즈 랜드마크를 모두 추출하고 마스크 후처리를 적용합니다.
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 세그멘테이션 및 포즈 수행
    seg_results = segmentation.process(rgb_frame)
    pose_results = pose.process(rgb_frame)
    
    # 마스크 후처리
    mask = None
    if seg_results.segmentation_mask is not None:
        mask = seg_results.segmentation_mask
        mask_8bit = (mask * 255).astype(np.uint8)
        
        # 1. Gaussian 블러 적용
        smoothed_mask = cv2.GaussianBlur(mask_8bit, BLUR_KERNEL, 0)
        
        # 2. 이진화 적용
        _, binary_mask = cv2.threshold(
            smoothed_mask, 
            THRESHOLD_VALUE, 
            255, 
            cv2.THRESH_BINARY
        )
        
        # 3. 모폴로지 연산
        kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)
        mask = cv2.morphologyEx(
            binary_mask, 
            cv2.MORPH_CLOSE, 
            kernel, 
            iterations=MORPH_ITERATIONS
        )
    
    return mask, pose_results


def extract_silhouette(mask: np.ndarray) -> np.ndarray:
    """
    이진 마스크에서 실루엣 외곽선을 추출합니다. (CHAIN_APPROX_NONE으로 최대 부드러움 유지)
    """
    if mask is None:
        return None
    
    # CHAIN_APPROX_NONE: 모든 윤곽선 점을 저장하여 부드러운 곡선 유지 (각짐 방지)
    contours, _ = cv2.findContours(
        mask, 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_NONE
    )
    
    if not contours:
        return None
    
    # 가장 큰 윤곽선 선택
    largest_contour = max(contours, key=cv2.contourArea)
    return largest_contour


def draw_pose_and_silhouette(
    frame: np.ndarray, 
    contour: np.ndarray, 
    pose_results,
    mp_drawing,
    mp_drawing_styles,
    scale: float = 1.0,
    source_width: int = None,
    source_height: int = None,
    window_width: int = None,
    window_height: int = None
) -> np.ndarray:
    """
    검은 배경에 네온 효과를 적용한 윤곽선과 포즈 와이어프레임을 그립니다.
    """
    # 1. 검은 배경 생성
    height, width = frame.shape[:2]
    output = np.zeros((height, width, 3), dtype=np.uint8)
    output[:] = BACKGROUND_COLOR
    
    # 2. 윤곽선 스케일링 및 네온 효과 적용 (활성화 경계선)
    if contour is not None and len(contour) >= 3:
        # a) 처리 해상도 -> 원본 캡처 해상도로 복원
        if scale != 1.0 and scale > 0:
            scaled_contour = (contour.astype(np.float32) / scale).astype(np.int32)
        else:
            scaled_contour = contour.astype(np.int32)
        
        # b) 원본 캡처 해상도 -> 최종 표시 윈도우 해상도로 스케일링
        if source_width and source_height and window_width and window_height:
            x_scale = window_width / source_width if source_width > 0 else 1.0
            y_scale = window_height / source_height if source_height > 0 else 1.0
        else:
            x_scale = 1.0
            y_scale = 1.0
        
        # c) 좌표 변환 적용 (Arcade-like scaling)
        transformed_contour = scaled_contour.copy()
        for i in range(len(transformed_contour)):
            x_cam, y_cam = transformed_contour[i, 0]
            transformed_contour[i, 0] = [int(x_cam * x_scale), int(y_cam * y_scale)]
        
        contours_to_draw = [transformed_contour]
        
        # 네온 글로우 효과 적용
        # 1단계: 가장 넓고 흐릿한 글로우
        cv2.drawContours(output, contours_to_draw, -1, GLOW_COLOR, OUTLINE_THICKNESS * 6, cv2.LINE_AA)
        # 2단계: 중간 글로우
        cv2.drawContours(output, contours_to_draw, -1, GLOW_COLOR, OUTLINE_THICKNESS * 4, cv2.LINE_AA)
        # 3단계: 선명한 하이라이트
        cv2.drawContours(output, contours_to_draw, -1, OUTLINE_COLOR, OUTLINE_THICKNESS * 2, cv2.LINE_AA)
        # 4단계: 가장 얇고 선명한 핵심 선
        cv2.drawContours(output, contours_to_draw, -1, OUTLINE_COLOR, OUTLINE_THICKNESS, cv2.LINE_AA)
    
    # 3. 포즈 와이어프레임 그리기 (와이어프레임 코어)
    if pose_results.pose_landmarks:
        # 포즈 랜드마크를 현재 출력 해상도(width, height)에 맞게 스케일링하여 그립니다.
        mp_drawing.draw_landmarks(
            output,
            pose_results.pose_landmarks,
            mp.solutions.pose.POSE_CONNECTIONS,
            # 포즈 랜드마크 스타일: 점이 아닌 선만 그리도록 커스터마이징
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=POSE_COLOR, thickness=0, circle_radius=0),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=POSE_COLOR, thickness=POSE_THICKNESS, circle_radius=0)
        )
    
    # Note: 포즈 랜드마크는 MediaPipe의 DrawingUtil이 직접 그리기 때문에, 
    # 별도의 복잡한 Arcade 스케일링 로직을 적용할 필요 없이 바로 output 프레임에 그립니다.
    
    return output


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    """
    메인 실행 함수: 실시간 비디오 캡처 및 실루엣/포즈 렌더링
    """
    # MediaPipe 초기화
    print("MediaPipe Segmentation 및 Pose 초기화 중...")
    segmentation, pose, mp_drawing, mp_drawing_styles = initialize_mediapipe()
    
    # 카메라 인덱스 결정
    camera_index = CAMERA_INDEX if CAMERA_INDEX is not None else get_best_camera_index()
    
    # 비디오 캡처 초기화
    print(f"카메라 초기화 중... (인덱스: {camera_index}, 해상도: {CAPTURE_WIDTH}x{CAPTURE_HEIGHT})")
    cap = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
    
    if not cap.isOpened():
        print(f"오류: 카메라를 열 수 없습니다 (인덱스: {camera_index})")
        return
    
    # 카메라 해상도 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
    
    # 실제 설정된 해상도 확인
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"실제 캡처 해상도: {actual_width}x{actual_height}")
    print(f"처리 해상도: {PROCESS_WIDTH}x{PROCESS_HEIGHT or '자동'}")
    print(f"윈도우 이름: {WINDOW_NAME}")
    
    # 카메라가 준비될 때까지 대기
    print("카메라 준비 중...")
    ret = False
    for _ in range(5):
        ret, _ = cap.read()
        if ret:
            break
        time.sleep(0.1)
    
    if not ret:
        print("오류: 카메라에서 프레임을 읽을 수 없습니다. 카메라가 다른 프로그램에서 사용 중일 수 있습니다.")
        cap.release()
        return
    
    print("\n'q' 또는 ESC 키를 눌러 종료하세요.\n")
    
    # FPS 계산 변수
    fps_counter = 0
    fps_start_time = time.time()
    current_fps = 0.0
    
    try:
        while True:
            # 프레임 읽기
            ret, frame = cap.read()
            if not ret:
                print("경고: 프레임을 읽을 수 없습니다. 재시도 중...")
                time.sleep(0.1)
                continue
            
            # 좌우 반전 (거울 모드)
            frame = cv2.flip(frame, 1)
            
            # 성능 최적화를 위한 리사이즈
            resized_frame, scale = resize_for_processing(frame)
            
            # 실루엣 마스크 및 포즈 랜드마크 추출
            mask, pose_results = process_frame(resized_frame, segmentation, pose)
            
            # 윤곽선 추출
            contour = extract_silhouette(mask)
            
            # 렌더링: 실루엣 외곽선 (네온) + 포즈 와이어프레임 (뼈대)
            frame_height, frame_width = frame.shape[:2]
            output = draw_pose_and_silhouette(
                frame, 
                contour, 
                pose_results,
                mp_drawing,
                mp_drawing_styles,
                scale,
                source_width=actual_width,   # 카메라 해상도
                source_height=actual_height,  # 카메라 해상도
                window_width=frame_width,    # 프레임/화면 너비
                window_height=frame_height    # 프레임/화면 높이
            )
            
            # FPS 표시
            if SHOW_FPS:
                fps_counter += 1
                elapsed = time.time() - fps_start_time
                if elapsed >= FPS_UPDATE_INTERVAL:
                    current_fps = fps_counter / elapsed
                    fps_counter = 0
                    fps_start_time = time.time()
                
                # FPS 텍스트 표시
                cv2.putText(
                    output,
                    f"FPS: {current_fps:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2
                )
            
            # 결과 표시
            cv2.imshow(WINDOW_NAME, output)
            
            # 'q' 또는 ESC 키로 종료
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' 또는 ESC (27)
                break
            
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    finally:
        # 리소스 정리
        cap.release()
        cv2.destroyAllWindows()
        print("리소스 정리 완료.")


if __name__ == "__main__":
    main()
