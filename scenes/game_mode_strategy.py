# scenes/game_mode_strategy.py

import cv2
import time
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
        
        # --- 판정 이펙트 로직 시작 (Arcade 컨셉 시각화) ---
        now = time.time()
        effect_duration = hud_styles.get("hit_zone_effect_duration", 0.15)
        
        last_type = self.game_scene.last_judgement_type
        # hit_effect_timer가 0.0이면 아직 판정이 없었던 것이므로 이펙트 비활성화
        if self.game_scene.hit_effect_timer > 0:
            elapsed = now - self.game_scene.hit_effect_timer
        else:
            elapsed = effect_duration + 1  # 이펙트 비활성화를 위한 큰 값
        
        # 기본값 설정: BGR 색상을 유지
        hit_zone_color_bgr = tuple(col_cfg.get("hit_zone", [255, 255, 255]))
        current_radius = hit_zone_radius
        
        # 이펙트 시간 내에 있으면
        if elapsed < effect_duration and last_type and self.game_scene.hit_effect_timer > 0:
            col_cfg_hud = self.game_scene.config_ui["colors"]["hud"]
            
            color_map_bgr = {
                "PERFECT": tuple(col_cfg_hud.get("hit_zone_perfect_color", [0, 255, 255])),
                "GREAT": tuple(col_cfg_hud.get("hit_zone_great_color", [255, 165, 0])),
                "GOOD": tuple(col_cfg_hud.get("hit_zone_good_color", [0, 128, 0])),
                "MISS": tuple(col_cfg_hud.get("hit_zone_miss_color", [0, 0, 255])),
                "timing": tuple(col_cfg_hud.get("hit_zone_miss_color", [0, 0, 255])),
                "area": tuple(col_cfg_hud.get("hit_zone_miss_color", [0, 0, 255])),
                "area/timing": tuple(col_cfg_hud.get("hit_zone_miss_color", [0, 0, 255])),
                "BOMB!": (128, 0, 255)  # BGR 보라색
            }
            
            # 색상 적용 (BGR 순서)
            hit_zone_color_bgr = color_map_bgr.get(last_type, hit_zone_color_bgr)
            
            # Perfect일 때만 순간적으로 확장 (타격감 구현)
            if last_type == "PERFECT":
                max_expansion = hit_zone_radius * 0.15
                half_duration = effect_duration / 2
                
                if elapsed < half_duration:
                    # 확장 페이즈: 0 -> max
                    expansion_ratio = elapsed / half_duration
                    current_radius += max_expansion * expansion_ratio
                else:
                    # 축소 페이즈: max -> 0
                    shrink_ratio = (elapsed - half_duration) / half_duration
                    current_radius += max_expansion * (1.0 - shrink_ratio)
            
            current_radius = int(current_radius)
        
        # cv2.circle 호출 시 동적으로 계산된 값 사용
        cv2.circle(frame, (hz_x, hz_y), current_radius, hit_zone_color_bgr, hit_zone_thickness)
        # --- 판정 이펙트 로직 끝 ---
        
        # 히트존 원 위에 최근 판정 결과 하나만 표시
        if self.game_scene.floating_judgement_logs:
            text, color_rgb, _ = self.game_scene.floating_judgement_logs[0]
            # color는 RGB 튜플이므로 OpenCV에 그릴 때는 BGR로 변환
            bgr_color = self.game_scene._rgb_to_bgr(color_rgb) if hasattr(self.game_scene, '_rgb_to_bgr') else (color_rgb[2], color_rgb[1], color_rgb[0])
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = hz_x - (text_size[0] // 2)
            text_y = hz_y - (hit_zone_radius + 40)
            cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, bgr_color, 2)
        
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

