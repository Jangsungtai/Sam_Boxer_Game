from __future__ import annotations

import arcade

from scenes.game_mode_strategy import GameModeStrategy


class NormalModeStrategy(GameModeStrategy):
    """일반 게임 모드 전략 (Arcade 버전)."""

    def handle_hits(self, hit_events, t_game, now, **kwargs) -> None:
        # 플레이어 입력을 사용한 판정 로직은 추후 단계에서 복구합니다.
        pass

    def _draw_mode_specific_hud(self) -> None:
        # Normal Mode 텍스트 제거
        pass
