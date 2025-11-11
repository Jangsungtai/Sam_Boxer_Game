from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

import arcade


class GameModeStrategy(ABC):
    """게임 모드 전략의 Arcade 버전 추상 클래스."""

    def __init__(self, game_scene) -> None:
        self.game_scene = game_scene

    @abstractmethod
    def handle_hits(self, hit_events, t_game: float, now: float, **kwargs) -> None:
        """감지된 히트 이벤트를 처리합니다."""

    def draw_hud(self) -> None:
        self._draw_mode_specific_hud()

    @abstractmethod
    def _draw_mode_specific_hud(self) -> None:
        """모드별 추가 HUD 요소를 그립니다."""

    def get_hit_zone_color(self, default_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """히트존 색상을 결정합니다."""
        return default_color

    def draw_additional(self, now: float) -> None:  # pragma: no cover - optional override
        pass

    def on_hit_events(self, hit_events, now: float) -> None:  # pragma: no cover - optional override
        pass

    def format_judgement_text(self, judge_text: str, dt: float | None) -> str:
        return judge_text
