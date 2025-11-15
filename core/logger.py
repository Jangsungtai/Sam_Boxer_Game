"""
로깅 시스템 모듈
게임 전체에서 일관된 로깅을 제공합니다.
"""
import logging
import sys
from typing import Optional


class GameLogger:
    """게임 로깅을 위한 싱글톤 클래스"""
    
    _instance: Optional['GameLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._logger = logging.getLogger("beat_boxer")
            self._logger.setLevel(logging.DEBUG)
            
            # 콘솔 핸들러 설정
            if not self._logger.handlers:
                handler = logging.StreamHandler(sys.stdout)
                handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter(
                    '[%(levelname)s] %(message)s'
                )
                handler.setFormatter(formatter)
                self._logger.addHandler(handler)
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """로거 인스턴스를 반환합니다."""
        instance = cls()
        if instance._logger is None:
            instance.__init__()
        return instance._logger


# 편의 함수
def get_logger() -> logging.Logger:
    """로거를 반환하는 편의 함수"""
    return GameLogger.get_logger()

