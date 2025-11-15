"""
게임 팩토리 모듈
게임 컴포넌트 생성 및 의존성 주입을 담당합니다.
"""
import os
import sys
from typing import Any, Dict, Optional

import cv2
import pygame

from core.audio_manager import AudioManager
from core.pose_tracker import PoseTracker
from core.config_manager import ConfigManager
from core.logger import get_logger


logger = get_logger()


def resource_path(relative_path: str) -> str:
    """PyInstaller 지원을 위한 자원 경로 헬퍼."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_best_camera_index() -> int:
    """사용 가능한 카메라 인덱스를 탐색하여 반환합니다."""
    logger.info("사용 가능한 카메라를 찾는 중...")
    for index in range(4, -1, -1):
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if cap.isOpened():
            logger.info(f"카메라 발견: 인덱스 {index}")
            cap.release()
            return index
    logger.warning("사용 가능한 카메라가 없습니다. 0번 인덱스로 시도합니다.")
    return 0


class GameFactory:
    """게임 컴포넌트 생성 및 의존성 주입"""
    
    @staticmethod
    def create_audio_manager() -> Optional[AudioManager]:
        """오디오 매니저를 생성합니다."""
        try:
            pygame.init()
            logger.info("Pygame 모듈 초기화 성공")
            audio_manager = AudioManager()
            sfx_map = {
                "PERFECT": "hit_perfect.wav",
                "GREAT": "hit_good.wav",
                "GOOD": "hit_good.wav",
                "MISS": "miss.wav",
                "BOMB!": "bomb.wav",
            }
            audio_manager.load_sounds(sfx_map)
            return audio_manager
        except Exception as exc:
            logger.error(f"오디오 초기화 실패: {exc}")
            return None
    
    @staticmethod
    def create_camera() -> tuple[Optional[cv2.VideoCapture], int, int]:
        """카메라를 초기화합니다."""
        camera_index = get_best_camera_index()
        capture = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
        
        if capture is not None and capture.isOpened():
            source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
            source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
            logger.info(f"카메라 초기화 성공 (인덱스: {camera_index}, {source_width}x{source_height})")
            return capture, source_width, source_height
        else:
            logger.warning(f"카메라(인덱스 {camera_index})를 열 수 없습니다. 카메라 없이 실행합니다.")
            if capture is not None:
                capture.release()
            return None, 1280, 720
    
    @staticmethod
    def create_config_manager(config_dir: str = "config") -> ConfigManager:
        """설정 매니저를 생성합니다."""
        try:
            logger.info("Loading config files...")
            return ConfigManager(config_dir)
        except FileNotFoundError as exc:
            logger.error(f"필수 config 파일을 찾을 수 없습니다: {exc}")
            raise
    
    @staticmethod
    def create_pose_tracker(
        source_width: int,
        source_height: int,
        config: Dict[str, Any]
    ) -> Optional[PoseTracker]:
        """포즈 트래커를 생성합니다."""
        try:
            logger.info("Initializing Pose Tracker...")
            return PoseTracker(
                source_width,
                source_height,
                config["rules"],
                config["ui"]
            )
        except Exception as exc:
            logger.error(f"PoseTracker 초기화 실패: {exc}")
            return None

