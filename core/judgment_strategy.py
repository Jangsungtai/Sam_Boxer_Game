"""
판정 전략 모듈
판정 로직을 전략 패턴으로 분리합니다.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional

from core.note import Note


class JudgmentStrategy(ABC):
    """판정 로직을 위한 추상 전략 클래스"""
    
    @abstractmethod
    def judge(
        self,
        note: Note,
        event: Dict,
        game_time: float,
        judge_timing: Dict[str, float]
    ) -> Optional[str]:
        """
        노트와 이벤트를 기반으로 판정을 수행합니다.
        
        Args:
            note: 판정할 노트
            event: 히트 이벤트
            game_time: 게임 시간
            judge_timing: 판정 타이밍 설정
            
        Returns:
            판정 결과 (PERFECT, GREAT, GOOD, MISS) 또는 None
        """
        pass


class JabJudgmentStrategy(JudgmentStrategy):
    """JAB 판정 전략"""
    
    def judge(
        self,
        note: Note,
        event: Dict,
        game_time: float,
        judge_timing: Dict[str, float]
    ) -> Optional[str]:
        """JAB 노트에 대한 판정을 수행합니다."""
        if note.typ not in ["JAB_L", "JAB_R"]:
            return None
        
        # 이벤트 시간과 노트 시간의 차이 계산
        event_time = event.get("t_hit", game_time)
        delta = abs(game_time - note.t)
        
        # 판정 창 확인
        thresholds = [
            ("PERFECT", judge_timing.get("perfect", 0.2)),
            ("GREAT", judge_timing.get("great", 0.35)),
            ("GOOD", judge_timing.get("good", 0.5)),
        ]
        
        for judge, window in thresholds:
            if delta <= window:
                return judge
        
        return None


class WeaveJudgmentStrategy(JudgmentStrategy):
    """WEAVE 판정 전략"""
    
    def __init__(self, judgment_logic, pose_tracker, window_width: int, window_height: int):
        self.judgment_logic = judgment_logic
        self.pose_tracker = pose_tracker
        self.window_width = window_width
        self.window_height = window_height
    
    def judge(
        self,
        note: Note,
        event: Dict,
        game_time: float,
        judge_timing: Dict[str, float]
    ) -> Optional[str]:
        """WEAVE 노트에 대한 판정을 수행합니다."""
        if note.typ not in ["WEAVE_L", "WEAVE_R"]:
            return None
        
        from core.constants import JUDGMENT_WINDOW
        
        # 시간 판정
        time_diff = abs(game_time - note.t)
        if time_diff > JUDGMENT_WINDOW:
            return None
        
        # JudgmentLogic을 사용하여 위치 판정
        judgment = self.judgment_logic.check_hit(
            note,
            self.pose_tracker,
            game_time,
            self.window_width,
            self.window_height
        )
        
        if judgment == 'HIT':
            # 시간 차이에 따라 판정 등급 결정
            thresholds = [
                ("PERFECT", judge_timing.get("perfect", 0.2)),
                ("GREAT", judge_timing.get("great", 0.35)),
                ("GOOD", judge_timing.get("good", 0.5)),
            ]
            for judge, window in thresholds:
                if time_diff <= window:
                    return judge
            return "GOOD"  # 기본값
        elif judgment == 'MISS':
            return "MISS"
        
        return None

