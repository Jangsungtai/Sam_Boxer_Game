"""
비트맵 로더 모듈
비트맵 파일을 로드하고 파싱합니다.
"""
import json
import os
from typing import Any, Dict, List


class BeatmapLoader:
    """비트맵 파일을 로드하고 파싱하는 클래스"""
    
    def __init__(self, config_difficulty: Dict[str, Any]):
        self.config_difficulty = config_difficulty
    
    def load_beatmap(self, beatmap_dir: str) -> List[Dict[str, Any]]:
        """
        비트맵 파일을 로드합니다.
        
        Args:
            beatmap_dir: 비트맵 디렉토리 경로
            
        Returns:
            비트맵 아이템 리스트
        """
        text_path = os.path.join(beatmap_dir, "beatmap.txt")
        json_path = os.path.join(beatmap_dir, "beatmap.json")
        
        if os.path.exists(text_path):
            beatmap_items = self._parse_text_beatmap(text_path)
        else:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    beatmap_items = json.load(f)
            except FileNotFoundError:
                from core.logger import get_logger
                logger = get_logger()
                logger.warning(f"비트맵 파일을 찾을 수 없습니다. ({beatmap_dir})")
                beatmap_items = []
        
        # END 타입 제거 및 정렬
        beatmap_items = [
            item for item in beatmap_items 
            if item.get("type") != "END"
        ]
        beatmap_items.sort(key=lambda item: item.get("t", 0.0))
        
        return beatmap_items
    
    def _parse_text_beatmap(self, text_path: str) -> List[Dict[str, Any]]:
        """
        텍스트 비트맵 파일을 파싱합니다.
        
        Args:
            text_path: 텍스트 비트맵 파일 경로
            
        Returns:
            비트맵 아이템 리스트
        """
        mapping = {
            "0": "GUARD",  # GUARD 노트 추가
            "1": "JAB_L", 
            "2": "JAB_R", 
            "3": "WEAVE_L", 
            "4": "WEAVE_R"
        }
        
        song_info = self.config_difficulty.get("song_info", {})
        bpm = float(song_info.get("bpm", 120))
        division = int(song_info.get("division", 4))
        start_delay = float(song_info.get("start_delay", 0.0))
        
        seconds_per_step = 60.0 / max(1e-6, bpm) / max(1, division)
        step_index = 0
        beatmap: List[Dict[str, Any]] = []
        
        with open(text_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # 주석 제거 (# 이후 부분 제거)
                if "#" in line:
                    line = line.split("#")[0].strip()
                
                # 주석 제거 후 빈 줄이면 건너뛰기
                if not line:
                    continue
                
                for ch in line:
                    note_type = mapping.get(ch)
                    if note_type:
                        beatmap.append({
                            "t": start_delay + step_index * seconds_per_step,
                            "type": note_type
                        })
                    step_index += 1
        
        return beatmap

