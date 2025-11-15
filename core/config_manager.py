"""
설정 관리 모듈
모든 설정을 중앙에서 관리합니다.
"""
import json
import os
from typing import Any, Dict, Optional


class ConfigManager:
    """게임 설정을 중앙에서 관리하는 클래스"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.constants: Dict[str, Any] = {}
        self.rules: Dict[str, Any] = {}
        self.difficulty: Dict[str, Any] = {}
        self.ui: Dict[str, Any] = {}
        
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """모든 설정 파일을 로드합니다."""
        try:
            self.rules = self._load_json("rules.json")
            self.difficulty = self._load_json("difficulty.json")
            self.ui = self._load_json("ui.json")
        except FileNotFoundError as e:
            from core.logger import get_logger
            logger = get_logger()
            logger.error(f"설정 파일을 찾을 수 없습니다: {e}")
            raise
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """JSON 파일을 로드합니다."""
        filepath = os.path.join(self.config_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_judge_timing(self, level: str = "Normal") -> Dict[str, float]:
        """
        난이도별 판정 타이밍을 반환합니다.
        
        Args:
            level: 난이도 (Easy, Normal, Hard)
            
        Returns:
            판정 타이밍 딕셔너리
        """
        levels = self.difficulty.get("levels", {})
        default_level = self.difficulty.get("default", "Normal")
        difficulty = levels.get(level) or levels.get(default_level) or next(iter(levels.values()), {})
        
        base_timing = self.difficulty.get(
            "judge_timing_base",
            {"perfect": 0.25, "great": 0.4, "good": 0.6}
        )
        scale = float(difficulty.get("judge_timing_scale", 1.0))
        
        return {key: float(value) * scale for key, value in base_timing.items()}
    
    def get_difficulty_settings(self, level: str = "Normal") -> Dict[str, Any]:
        """
        난이도별 설정을 반환합니다.
        
        Args:
            level: 난이도 (Easy, Normal, Hard)
            
        Returns:
            난이도 설정 딕셔너리
        """
        levels = self.difficulty.get("levels", {})
        default_level = self.difficulty.get("default", "Normal")
        return levels.get(level) or levels.get(default_level) or {}
    
    def get_config(self) -> Dict[str, Any]:
        """전체 설정을 반환합니다."""
        return {
            "rules": self.rules,
            "difficulty": self.difficulty,
            "ui": self.ui
        }

