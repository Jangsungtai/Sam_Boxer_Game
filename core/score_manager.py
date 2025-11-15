"""
점수 관리 모듈
점수, 콤보, 판정 점수를 관리합니다.
"""
from typing import Dict, Optional

from core.game_state import GameState


class ScoreManager:
    """점수 및 콤보를 관리하는 클래스"""
    
    def __init__(
        self,
        score_values: Dict[str, int],
        score_multiplier: float,
        game_state: GameState
    ):
        self.score_values = score_values
        self.score_multiplier = score_multiplier
        self.game_state = game_state
    
    def register_hit(
        self,
        judgement: str,
        note_type: str,
        delta: float,
        now: float
    ) -> int:
        """
        히트 판정을 등록하고 점수를 계산합니다.
        
        Args:
            judgement: 판정 등급 (PERFECT, GREAT, GOOD, MISS)
            note_type: 노트 타입
            delta: 시간 차이
            now: 현재 시간
            
        Returns:
            획득한 점수
        """
        # 판정 기록
        self.game_state.record_judgement(judgement, note_type, delta, now)
        
        # 콤보 업데이트
        self.game_state.update_combo(judgement)
        
        # 점수 계산
        base_score = self.score_values.get(judgement, 0)
        gained = int(base_score * self.score_multiplier)
        self.game_state.score += gained
        
        return gained
    
    def register_miss(self, note_type: str, now: float) -> None:
        """
        미스 판정을 등록합니다.
        
        Args:
            note_type: 노트 타입
            now: 현재 시간
        """
        self.game_state.record_judgement("MISS", note_type, 0.0, now)
        self.game_state.update_combo("MISS")

