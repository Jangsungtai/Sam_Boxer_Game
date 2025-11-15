"""
게임 상태 관리 모듈
게임의 상태를 중앙에서 관리합니다.
"""
import time
from dataclasses import dataclass, field
from typing import Deque, Optional
from collections import deque


@dataclass
class GameState:
    """게임 상태를 담는 데이터 클래스"""
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    song_start_time: Optional[float] = None
    game_finished: bool = False
    test_mode: bool = False
    last_judgement_type: Optional[str] = None
    last_judgement_time: float = 0.0
    judge_log: Deque[str] = field(default_factory=lambda: deque(maxlen=10))
    status_text: str = "Ready!"
    countdown_start: Optional[float] = None
    finish_trigger_time: Optional[float] = None
    
    def reset(self) -> None:
        """상태를 초기화합니다."""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.song_start_time = None
        self.game_finished = False
        self.last_judgement_type = None
        self.last_judgement_time = 0.0
        self.judge_log.clear()
        self.status_text = "Ready!"
        self.countdown_start = None
        self.finish_trigger_time = None
    
    def update_combo(self, judgement: str) -> None:
        """판정에 따라 콤보를 업데이트합니다."""
        if judgement == "MISS":
            self.combo = 0
        else:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
    
    def record_judgement(self, judgement: str, note_type: str, delta: float, now: float = 0.0) -> None:
        """판정을 기록합니다."""
        self.last_judgement_type = judgement
        self.last_judgement_time = now if now > 0 else time.time()
        self.judge_log.appendleft(f"{judgement} ({note_type}) Δ={delta:0.3f}")

