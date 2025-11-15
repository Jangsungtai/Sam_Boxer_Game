# beat_boxer_game/beat_manager.py

import random
import time
from typing import List, Optional

import arcade

from constants import (
    ALL_BEAT_TYPES, BEAT_JAB_L, BEAT_JAB_R, BEAT_TIME, BEAT_WEAVE_L, BEAT_WEAVE_R,
    BEAT_START_Y, SCREEN_WIDTH, SCREEN_HEIGHT, BEAT_JUDGMENT_Y
)
from core.note import Note  # 기존 Note 클래스 사용


class BeatManager:
    """게임 내 비트 생성 및 관리를 담당하는 클래스"""

    def __init__(self, config_colors: dict, judge_timing: dict, test_mode: bool, config_note_styles: Optional[dict] = None):
        self.beat_list: List[Note] = []
        self.next_beat_time: float = 0.0
        self.beat_interval: float = 1.5  # 비트 생성 간격 (초)
        self.beats_per_minute: int = 60  # BPM
        
        # Note 생성에 필요한 설정
        self.config_colors = config_colors
        self.judge_timing = judge_timing
        self.test_mode = test_mode
        self.config_note_styles = config_note_styles or {}
        
        # 비트 타입 매핑 (상수 -> Note 타입 문자열)
        self.beat_type_map = {
            BEAT_JAB_L: "JAB_L",
            BEAT_JAB_R: "JAB_R",
            BEAT_WEAVE_L: "WEAVE_L",
            BEAT_WEAVE_R: "WEAVE_R"
        }

    def setup(self, start_time: float = None):
        """매니저 초기 설정"""
        self.beat_list = []
        if start_time is None:
            start_time = time.time()
        self.next_beat_time = start_time + self.beat_interval

    def update_bpm(self, bpm: int):
        """BPM에 따라 비트 생성 간격 업데이트"""
        self.beats_per_minute = bpm
        if bpm > 0:
            self.beat_interval = 60 / bpm
        else:
            self.beat_interval = 1.5

    def update(self, delta_time: float, current_time: float, song_start_time: float, hit_zone_camera: tuple):
        """비트를 이동시키고 새 비트를 생성"""
        # 기존 Note 업데이트
        for note in self.beat_list:
            note.update(current_time, song_start_time, hit_zone_camera)

        # 비트 생성
        if current_time >= self.next_beat_time:
            self.create_new_beat(song_start_time)
            self.next_beat_time += self.beat_interval

        # 화면 밖으로 나간 비트 제거
        self.clean_up_beats()

    def create_new_beat(self, song_start_time: float):
        """랜덤한 유형의 새 비트를 생성"""
        beat_type_const = random.choice(ALL_BEAT_TYPES)
        beat_type_str = self.beat_type_map.get(beat_type_const, "JAB_L")
        
        # Note 객체 생성에 필요한 item 딕셔너리
        # Note는 self.t를 기준으로 시간을 계산하므로, 현재 시간 기준으로 생성
        current_time = time.time()
        beat_item = {
            "t": current_time - song_start_time,  # 게임 시간 기준
            "type": beat_type_str,
            "lane": "C"  # 기본 레인
        }
        
        # 펀치 (JAB) 비트: 중앙으로 내려옴
        if beat_type_const in [BEAT_JAB_L, BEAT_JAB_R]:
            # Note 클래스가 자동으로 위치를 계산하므로 기본 설정만 전달
            new_beat = Note(
                beat_item,
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
                int(SCREEN_HEIGHT * 0.6),  # duck_line_y (사용 안 함)
                1.0,  # pre_spawn_time
                self.config_colors,
                self.judge_timing,
                self.test_mode,
                self.config_note_styles
            )

        # 위빙 (WEAVE) 비트: 아래에서 위로 올라오며 중앙선까지 와야함
        elif beat_type_const in [BEAT_WEAVE_L, BEAT_WEAVE_R]:
            # 위빙은 플레이어의 몸통을 향해 오는 상대방 펀치이므로, 중앙선 근처에서 생성
            # Note 클래스를 사용하되, 타입만 WEAVE로 설정
            new_beat = Note(
                beat_item,
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
                int(SCREEN_HEIGHT * 0.6),  # duck_line_y
                1.0,  # pre_spawn_time
                self.config_colors,
                self.judge_timing,
                self.test_mode,
                self.config_note_styles
            )

        self.beat_list.append(new_beat)

    def clean_up_beats(self):
        """판정 위치를 지나간 비트 제거"""
        # Note 객체는 hit 또는 missed 상태로 관리되므로, 여기서는 제거하지 않음
        # 대신 화면 밖으로 완전히 나간 비트만 제거
        beats_to_remove = [
            beat for beat in self.beat_list
            if (beat.hit or beat.missed) and beat.y > SCREEN_HEIGHT + 100
        ]
        for beat in beats_to_remove:
            if beat in self.beat_list:
                self.beat_list.remove(beat)

    def draw(self, screen_height: int, color_converter, coord_converter):
        """현재 활성화된 모든 비트를 그림"""
        for beat in self.beat_list:
            beat.draw(screen_height, color_converter, coord_converter)

    def get_judgable_beats(self, current_time: float, song_start_time: float) -> List[Note]:
        """판정 가능한 위치에 도달한 비트 목록을 반환"""
        judgable_beats = []
        for beat in self.beat_list:
            if beat.hit or beat.missed:
                continue
            # 현재 비트의 위치가 판정선 근처인지 확인
            # Note는 self.t를 기준으로 시간을 계산
            game_time = current_time - song_start_time
            time_diff = abs(game_time - beat.t)
            # JUDGMENT_WINDOW는 constants에서 import 필요
            from constants import JUDGMENT_WINDOW
            if time_diff < JUDGMENT_WINDOW:
                judgable_beats.append(beat)
        return judgable_beats

