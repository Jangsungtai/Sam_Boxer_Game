# scenes/game_mode_strategy.py

from abc import ABC, abstractmethod

class GameModeStrategy(ABC):
    """게임 모드 전략 추상 클래스"""
    
    def __init__(self, game_scene):
        self.game_scene = game_scene
    
    @abstractmethod
    def handle_hits(self, hit_events, t_game, now):
        """감지된 히트 이벤트를 해당 노트와 매칭하여 판정합니다."""
        pass
    
    @abstractmethod
    def draw_hud(self, frame):
        """점수/콤보/히트존/덕 라인 등 HUD 요소를 그립니다."""
        pass
    
    @abstractmethod
    def draw_additional(self, frame, now):
        """모드별 추가 시각화 요소를 그립니다 (이벤트 히스토리 등)."""
        pass
    
    @abstractmethod
    def on_hit_events(self, hit_events, now):
        """히트 이벤트 발생 시 모드별 처리 (이벤트 히스토리 저장 등)."""
        pass
    
    @abstractmethod
    def calculate_debug_info(self, active_notes, hit_zone, smoothed_landmark_pos, start_time, now):
        """디버그 정보 계산 (다음 노트의 시간/공간 정보 등)."""
        pass
    
    @abstractmethod
    def format_judgement_text(self, judge_text, dt):
        """판정 텍스트를 포맷팅합니다."""
        pass

