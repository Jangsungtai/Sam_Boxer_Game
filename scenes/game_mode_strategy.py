# scenes/game_mode_strategy.py

import cv2
from abc import ABC, abstractmethod

class GameModeStrategy(ABC):
    """게임 모드 전략 추상 클래스 (Phase 2: 리팩토링)"""
    
    def __init__(self, game_scene):
        self.game_scene = game_scene
    
    @abstractmethod
    def handle_hits(self, hit_events, t_game, now, **kwargs):
        """감지된 히트 이벤트를 해당 노트와 매칭하여 판정합니다 (Phase 2: kwargs 추가).
        
        Args:
            hit_events: 히트 이벤트 리스트
            t_game: 게임 시간
            now: 현재 시간
            **kwargs: 추가 데이터 (smoothed_landmarks, left_fist_center, right_fist_center 등)
        """
        pass
    
    def draw_hud(self, frame):
        """HUD 그리기 템플릿 메서드 (Phase 2: 공통 로직 통합)."""
        # 공통 부분: 히트존, 덕 라인, 점수/콤보, 판정 통계
        self._draw_common_hud(frame)
        
        # 모드별 추가 로직
        self._draw_mode_specific_hud(frame)
    
    def _draw_common_hud(self, frame):
        """공통 HUD 요소 그리기 (Phase 2: 공통 로직 통합)."""
        ui_cfg = self.game_scene.config_ui
        pos_cfg = ui_cfg["positions"]
        col_cfg = ui_cfg["colors"]["hud"]
        hud_styles = ui_cfg.get("styles", {}).get("hud", {})
        hit_zone_radius = int(getattr(self.game_scene, "hit_zone_radius", hud_styles.get("hit_zone_radius", 30)))
        hit_zone_thickness = int(hud_styles.get("hit_zone_thickness", 6))
        
        duck_y = self.game_scene.duck_line_y
        cv2.line(frame, (0, duck_y), (self.game_scene.width, duck_y), tuple(col_cfg["duck_line"]), 2)
        cv2.putText(frame, "DUCK LINE", (10, duck_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, tuple(col_cfg["duck_line"]), 2)
        
        hz_x, hz_y = self.game_scene.hit_zone
        
        # 판정 결과에 따라 히트존 색상 및 두께 변경
        last_judgement = self.game_scene.last_judgement
        base_thickness = hit_zone_thickness
        
        if last_judgement == "PERFECT":
            hit_zone_color = (0, 255, 255)  # 노란색 (BGR)
            hit_zone_thickness = base_thickness * 2
        elif last_judgement == "GREAT":
            hit_zone_color = (0, 255, 0)  # 녹색 (BGR)
        elif last_judgement == "GOOD":
            hit_zone_color = (255, 0, 0)  # 파란색 (BGR)
        elif last_judgement == "MISS":
            hit_zone_color = (0, 0, 255)  # 빨간색 (BGR)
        else:
            hit_zone_color = (128, 128, 128)  # 회색 (BGR) - 평상시
        
        cv2.circle(frame, (hz_x, hz_y), hit_zone_radius, hit_zone_color, hit_zone_thickness)
        
        # 히트존 원 위에 최근 판정 결과 하나만 표시
        if self.game_scene.floating_judgement_logs:
            text, color, _ = self.game_scene.floating_judgement_logs[0]
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = hz_x - (text_size[0] // 2)
            text_y = hz_y - (hit_zone_radius + 40)
            cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        
        # Score, Combo 표시
        score_pos = tuple(pos_cfg["score"])
        score_text = f"Score: {self.game_scene.state['score']}"
        combo_text = f"Combo: {self.game_scene.state['combo']}"
        cv2.putText(frame, score_text, score_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["score_text"]), 3)
        (text_width, _), _ = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)
        combo_pos = (self.game_scene.width - text_width - 20, score_pos[1])
        cv2.putText(frame, combo_text, combo_pos, cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(col_cfg["combo_text"]), 3)
        
        # 판정 통계 표시
        judgement_colors = ui_cfg.get("colors", {}).get("judgement", {})
        stats_y = score_pos[1] + 50
        font_scale = 0.7
        thickness = 2
        line_spacing = 30
        
        for i, judge_type in enumerate(["PERFECT", "GREAT", "GOOD", "MISS"]):
            count = self.game_scene.judgement_stats.get(judge_type, 0)
            text = f"{judge_type}: {count}"
            color = tuple(judgement_colors.get(judge_type, [255, 255, 255]))
            y_pos = stats_y + (i * line_spacing)
            cv2.putText(frame, text, (score_pos[0], y_pos), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    
    @abstractmethod
    def _draw_mode_specific_hud(self, frame):
        """모드별 추가 HUD 요소 (랜드마크 시각화 등)."""
        pass
    
    @abstractmethod
    def draw_additional(self, frame, now):
        """모드별 추가 시각화 요소를 그립니다 (이벤트 히스토리 등)."""
        pass
    
    @abstractmethod
    def on_hit_events(self, hit_events, now):
        """히트 이벤트 발생 시 모드별 처리 (이벤트 히스토리 저장 등)."""
        pass
    
    # Phase 2: calculate_debug_info 제거 (GameScene에서 계산 후 값만 전달)
    
    @abstractmethod
    def format_judgement_text(self, judge_text, dt):
        """판정 텍스트를 포맷팅합니다."""
        pass

