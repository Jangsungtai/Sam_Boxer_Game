"""
판정 처리 모듈
노트 판정 로직을 통합 관리합니다.
"""
from typing import Any, Dict, List, Optional, Tuple

from core.note import Note
from core.score_manager import ScoreManager
from core.hit_effect import HitEffectSystem
from core.judgment_logic import JudgmentLogic
from core.constants import JUDGMENT_WINDOW


class JudgmentProcessor:
    """판정 처리를 담당하는 클래스"""
    
    def __init__(
        self,
        judge_timing: Dict[str, float],
        score_manager: ScoreManager,
        hit_effect_system: HitEffectSystem,
        audio_manager,
        pose_tracker,
        window_width: int,
        window_height: int,
        coord_converter,
        color_converter,
        config_colors: Dict,
        hit_zone_camera: Tuple[int, int],
        test_mode: bool = False
    ):
        self.judge_timing = judge_timing
        self.score_manager = score_manager
        self.hit_effect_system = hit_effect_system
        self.audio_manager = audio_manager
        self.pose_tracker = pose_tracker
        self.window_width = window_width
        self.window_height = window_height
        self.coord_converter = coord_converter
        self.color_converter = color_converter
        self.config_colors = config_colors
        self.hit_zone_camera = hit_zone_camera
        self.test_mode = test_mode
        
        self.judgment_logic = JudgmentLogic()
    
    def process_hit_events(
        self,
        game_time: float,
        hit_events: List[Dict[str, Any]],
        active_notes: List[Note],
        song_start_time: Optional[float],
        timing_offset: float,
        now: float
    ) -> None:
        """
        히트 이벤트를 처리하고 노트와 매칭합니다.
        
        Args:
            game_time: 게임 시간
            hit_events: 히트 이벤트 리스트
            active_notes: 활성 노트 리스트
            song_start_time: 곡 시작 시간
            timing_offset: 타이밍 오프셋
            now: 현재 시간
        """
        if not hit_events:
            return
        
        for event in hit_events:
            # 이미 사용된 이벤트는 건너뛰기
            if event.get("used", False):
                continue
            
            note_type = event.get("type")
            event_time = event.get("t_hit", now)
            
            # 이벤트 시간을 게임 시간으로 변환
            if song_start_time:
                adjusted_time = (event_time - song_start_time) + timing_offset
            else:
                adjusted_time = 0.0
                if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                    from core.logger import get_logger
                    logger = get_logger()
                    logger.warning(f"song_start_time is None for {note_type}, adjusted_time=0.0")
                continue
            
            # 노트 매칭
            candidate = self._find_best_matching_note(note_type, adjusted_time, active_notes)
            if not candidate:
                if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                    self._log_matching_failure(note_type, adjusted_time, active_notes)
                continue
            
            # 판정 등급 결정
            delta = abs(adjusted_time - candidate.t)
            judgement = self._determine_judgement(delta)
            if judgement is None:
                if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                    from core.logger import get_logger
                    logger = get_logger()
                    logger.debug(f"No judgement for {note_type}: delta={delta:.3f}, thresholds={self.judge_timing}")
                continue
            
            # 판정 등록
            self._register_hit(candidate, judgement, delta, now)
            
            if self.test_mode and note_type in ["JAB_L", "JAB_R"]:
                from core.logger import get_logger
                logger = get_logger()
                logger.info(f"{note_type} -> {judgement} (delta={delta:.3f}s)")
            
            # 이벤트 소비
            event["used"] = True
    
    def process_weave_judgments(
        self,
        game_time: float,
        active_notes: List[Note],
        now: float
    ) -> None:
        """
        위빙 노트에 대한 판정을 처리합니다.
        
        Args:
            game_time: 게임 시간
            active_notes: 활성 노트 리스트
            now: 현재 시간
        """
        if not self.pose_tracker:
            return
        
        # 위빙 타입 노트만 필터링
        weave_notes = [
            note for note in active_notes
            if note.typ in ["WEAVE_L", "WEAVE_R"] and not note.hit and not note.missed
        ]
        
        for note in weave_notes:
            # 시간 판정
            time_diff = abs(game_time - note.t)
            if time_diff > JUDGMENT_WINDOW:
                continue
            
            # JudgmentLogic을 사용하여 판정
            judgment = self.judgment_logic.check_hit(
                note,
                self.pose_tracker,
                game_time,
                self.window_width,
                self.window_height
            )
            
            if judgment == 'HIT':
                delta = time_diff
                judgement = self._determine_judgement(delta)
                if judgement:
                    self._register_hit(note, judgement, delta, now)
            elif judgment == 'MISS':
                self._register_miss(note, now)
    
    def process_misses(
        self,
        game_time: float,
        active_notes: List[Note],
        now: float
    ) -> None:
        """
        미스 판정을 처리합니다.
        
        Args:
            game_time: 게임 시간
            active_notes: 활성 노트 리스트
            now: 현재 시간
        """
        # MISS 판정 창을 good 창보다 약간 더 크게 설정 (1.2배)
        miss_window = self.judge_timing.get("good", 0.5) * 1.2
        
        for note in active_notes:
            if note.hit or note.missed:
                continue
            # 위빙 노트는 별도 처리하므로 제외
            if note.typ in ["WEAVE_L", "WEAVE_R"]:
                continue
            if game_time > note.t + miss_window:
                self._register_miss(note, now)
    
    def _find_best_matching_note(
        self,
        note_type: Optional[str],
        adjusted_time: float,
        active_notes: List[Note]
    ) -> Optional[Note]:
        """이벤트 시간에 가장 가까운 미판정 노트를 찾습니다."""
        if note_type is None:
            return None
        
        candidates = [
            note for note in active_notes 
            if note.typ == note_type and not note.hit and not note.missed
        ]
        
        if not candidates:
            return None
        
        # 판정 창 내의 노트만 필터링
        max_window = max(
            self.judge_timing.get("perfect", 0.2),
            self.judge_timing.get("great", 0.35),
            self.judge_timing.get("good", 0.5)
        ) + 0.1
        
        valid_candidates = [
            note for note in candidates 
            if abs(note.t - adjusted_time) <= max_window
        ]
        
        if not valid_candidates:
            return None
        
        return min(valid_candidates, key=lambda note: abs(note.t - adjusted_time))
    
    def _determine_judgement(self, delta: float) -> Optional[str]:
        """시간 차이에 따라 판정 등급을 결정합니다."""
        thresholds = [
            ("PERFECT", self.judge_timing.get("perfect", 0.2)),
            ("GREAT", self.judge_timing.get("great", 0.35)),
            ("GOOD", self.judge_timing.get("good", 0.5)),
        ]
        for judge, window in thresholds:
            if delta <= window:
                return judge
        return None
    
    def _register_hit(self, note: Note, judgement: str, delta: float, now: float) -> None:
        """히트 판정을 등록합니다."""
        note.hit = True
        note.judge_result = judgement
        
        # 점수 및 콤보 업데이트
        self.score_manager.register_hit(judgement, note.typ, delta, now)
        
        # 히트 이펙트 생성
        hit_zone_arcade = self.coord_converter(self.hit_zone_camera)
        judgement_color_bgr = self.config_colors.get("judgement", {}).get(judgement, (255, 255, 255))
        judgement_color_rgb = self.color_converter(tuple(judgement_color_bgr))
        self.hit_effect_system.spawn_effect(
            hit_zone_arcade[0],
            hit_zone_arcade[1],
            judgement,
            judgement_color_rgb,
            now,
        )
        
        # 사운드 재생
        if self.audio_manager:
            sfx_key = judgement if judgement in self.score_manager.score_values else "MISS"
            self.audio_manager.play_sfx(sfx_key)
    
    def _register_miss(self, note: Note, now: float) -> None:
        """미스 판정을 등록합니다."""
        note.missed = True
        note.judge_result = "MISS"
        
        # 점수 및 콤보 업데이트
        self.score_manager.register_miss(note.typ, now)
        
        # 미스 이펙트 생성
        note_pos_arcade = self.coord_converter((note.x, note.y))
        miss_color_bgr = self.config_colors.get("judgement", {}).get("MISS", (255, 255, 255))
        miss_color_rgb = self.color_converter(tuple(miss_color_bgr))
        self.hit_effect_system.spawn_effect(
            note_pos_arcade[0],
            note_pos_arcade[1],
            "MISS",
            miss_color_rgb,
            now,
        )
        
        # 사운드 재생
        if self.audio_manager:
            self.audio_manager.play_sfx("MISS")
    
    def _log_matching_failure(
        self,
        note_type: str,
        adjusted_time: float,
        active_notes: List[Note]
    ) -> None:
        """매칭 실패 시 디버깅 로그를 출력합니다."""
        from core.logger import get_logger
        logger = get_logger()
        
        candidates_all = [
            n for n in active_notes 
            if n.typ == note_type and not n.hit and not n.missed
        ]
        logger.debug(f"No candidate for {note_type}: adjusted_time={adjusted_time:.2f}, all_candidates={len(candidates_all)}")
        
        if candidates_all:
            closest = min(candidates_all, key=lambda n: abs(n.t - adjusted_time))
            delta_closest = abs(closest.t - adjusted_time)
            max_window = max(
                self.judge_timing.get("perfect", 0.2),
                self.judge_timing.get("great", 0.35),
                self.judge_timing.get("good", 0.5)
            ) + 0.1
            logger.debug(f"Closest note: t={closest.t:.2f}, delta={delta_closest:.2f}, max_window={max_window:.2f}")

