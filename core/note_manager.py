"""
노트 관리 모듈
노트의 스폰, 업데이트, 정리를 담당합니다.
"""
from typing import Dict, List, Optional, Tuple

from core.note import Note


class NoteManager:
    """노트 생명주기를 관리하는 클래스"""
    
    def __init__(
        self,
        source_width: int,
        source_height: int,
        pre_spawn_time: float,
        config_colors: Dict,
        judge_timing: Dict[str, float],
        test_mode: bool,
        config_note_styles: Optional[Dict] = None
    ):
        self.source_width = source_width
        self.source_height = source_height
        self.pre_spawn_time = pre_spawn_time
        self.config_colors = config_colors
        self.judge_timing = judge_timing
        self.test_mode = test_mode
        self.config_note_styles = config_note_styles or {}
        
        self.active_notes: List[Note] = []
    
    def spawn_note(
        self,
        item: Dict,
        window_width: int,
        window_height: int,
        hit_zone_camera: Tuple[int, int]
    ) -> Note:
        """
        새로운 노트를 생성합니다.
        
        Args:
            item: 비트맵 아이템 (t, type, lane 포함)
            window_width: 윈도우 너비
            window_height: 윈도우 높이
            hit_zone_camera: 히트존 카메라 좌표
            
        Returns:
            생성된 Note 객체
        """
        note = Note(
            item,
            max(1, self.source_width or window_width),
            max(1, self.source_height or window_height),
            int((self.source_height or window_height) * 0.7),
            self.pre_spawn_time,
            self.config_colors.get("notes", {}),
            self.judge_timing,
            self.test_mode,
            self.config_note_styles,
        )
        self.active_notes.append(note)
        return note
    
    def update_notes(self, now: float, song_start_time: Optional[float], hit_zone_camera: Tuple[int, int]) -> None:
        """모든 활성 노트를 업데이트합니다."""
        if song_start_time is None:
            return
        for note in self.active_notes:
            note.update(now, song_start_time, hit_zone_camera)
    
    def cleanup_hit_notes(self) -> None:
        """히트되거나 미스된 노트를 제거합니다."""
        self.active_notes = [
            note for note in self.active_notes 
            if not note.hit and not note.missed
        ]
    
    def get_active_notes(self) -> List[Note]:
        """활성 노트 리스트를 반환합니다."""
        return self.active_notes
    
    def is_chart_completed(self, beatmap_index: int, beatmap_length: int) -> bool:
        """차트가 완료되었는지 확인합니다."""
        if beatmap_index < beatmap_length:
            return False
        return not any(not note.hit and not note.missed for note in self.active_notes)

