"""
실루엣 렌더러 모듈
MediaPipe 세그멘테이션 마스크를 사용하여 실루엣 외곽선을 그립니다.
"""
from typing import Callable, Optional, Tuple

import arcade
import cv2
import numpy as np


class SilhouetteRenderer:
    """실루엣 외곽선을 그리는 클래스"""
    
    @staticmethod
    def draw_silhouette(
        mask: Optional[np.ndarray],
        coord_converter: Callable[[Tuple[float, float]], Tuple[float, float]],
        window_width: int,
        window_height: int,
        color: Tuple[int, int, int] = arcade.color.WHITE,
        line_width: int = 3
    ) -> None:
        """
        세그멘테이션 마스크에서 실루엣 외곽선을 추출하여 그립니다.
        
        Args:
            mask: MediaPipe 세그멘테이션 마스크 (0.0~1.0 범위)
            coord_converter: 카메라 좌표를 Arcade 좌표로 변환하는 함수
            window_width: 윈도우 너비
            window_height: 윈도우 높이
            color: 외곽선 색상
            line_width: 외곽선 두께
        """
        if mask is None:
            return
        
        try:
            # 마스크를 8비트 단일 채널로 변환
            mask_8bit = (mask * 255).astype(np.uint8)
            
            # 가우시안 블러 적용 (부드러운 외곽선)
            blurred = cv2.GaussianBlur(mask_8bit, (15, 15), 0)
            
            # 이진화
            _, binary = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
            
            # 모폴로지 연산 (닫힘 후 열림)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
            
            # 외곽선 추출 (모든 점 유지)
            contours, _ = cv2.findContours(
                opened, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_NONE
            )
            
            if not contours:
                return
            
            # 가장 큰 외곽선 선택 (인물 전체 실루엣)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # OpenCV 좌표를 Arcade 좌표로 변환
            arcade_points = []
            for point in largest_contour:
                x_cam, y_cam = point[0]
                x_arc, y_arc = coord_converter((x_cam, y_cam))
                arcade_points.append((x_arc, y_arc))
            
            # 외곽선 그리기
            if len(arcade_points) > 1:
                # 외곽선이 닫힌 형태로 보이도록 첫 점을 다시 추가
                arcade_points.append(arcade_points[0])
                arcade.draw_line_strip(arcade_points, color, line_width)
                
        except Exception as e:
            # 실루엣 렌더링 실패는 게임에 치명적이지 않으므로 조용히 처리
            pass

