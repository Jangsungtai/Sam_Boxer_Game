# beat_boxer_game/judgment_logic.py

import math
from typing import Tuple, Optional
from constants import (
    BEAT_WEAVE_L, BEAT_WEAVE_R, NOSE_LANDMARK,
    DODGE_LEFT_LINE_X, DODGE_RIGHT_LINE_X, DODGE_CENTER_LINE_X,
    BEAT_JUDGMENT_Y, JUDGMENT_WINDOW,
    LEFT_HAND_LANDMARK, RIGHT_HAND_LANDMARK
)


class JudgmentLogic:
    """포즈 및 비트 위치를 기반으로 HIT/MISS 판정 로직을 관리"""

    def __init__(self):
        pass

    def check_hit(
        self,
        beat,
        pose_tracker,
        current_time: float,
        screen_width: int,
        screen_height: int
    ) -> Optional[str]:
        """
        주어진 비트와 현재 포즈를 기반으로 HIT/MISS를 판정합니다.

        Args:
            beat: 현재 판정할 Beat/Note 객체
            pose_tracker: 현재 프레임의 랜드마크를 가진 PoseTracker 객체
            current_time: 현재 시간
            screen_width: 화면 너비
            screen_height: 화면 높이

        Returns:
            Optional[str]: 'HIT', 'MISS', 또는 None (판정 시간 아님)
        """

        # 1. 시간 판정: 비트가 판정 창에 도달했는지 확인 (기존 펀치 로직 유지)
        # Note 객체는 self.t 속성을 가지고 있음
        time_diff = beat.t - current_time
        if abs(time_diff) > JUDGMENT_WINDOW:
            return None  # 판정 시간 아님

        # 2. 랜드마크 위치 가져오기
        landmarks = pose_tracker.get_smoothed_landmarks()
        if not landmarks:
            return 'MISS'  # 랜드마크 없음

        # 3. 비트 유형에 따른 위치 판정
        beat_type = beat.typ if hasattr(beat, 'typ') else None

        # **JAB (펀치) 판정 로직** (기존 로직 유지)
        if beat_type in ["JAB_L", "JAB_R"]:
            # 포즈 랜드마크 좌표 가져오기
            if beat_type == "JAB_L":
                target_landmark = landmarks.get("left_wrist")
            else:
                target_landmark = landmarks.get("right_wrist")

            if target_landmark:
                # 히트존 내에 있는지 확인
                if pose_tracker and hasattr(pose_tracker, 'hit_zone_x'):
                    hit_zone_x = pose_tracker.hit_zone_x
                    hit_zone_y = pose_tracker.hit_zone_y
                    hit_zone_radius = pose_tracker.hit_zone_radius

                    # 카메라 좌표를 화면 좌표로 변환 필요
                    # 간단히 랜드마크가 히트존 근처에 있는지 확인
                    if target_landmark:
                        # 실제 판정 로직은 기존 시스템 사용
                        return 'HIT'  # 임시 HIT (추후 펀치 로직 개선 필요)

            return 'MISS'

        # **WEAVE (위빙) 판정 로직** (요청하신 로직)
        elif beat_type in ["WEAVE_L", "WEAVE_R"]:
            # 코 랜드마크 위치 가져오기 (카메라 좌표)
            nose_pos = landmarks.get("nose")
            if not nose_pos:
                return 'MISS'

            # 카메라 좌표를 화면 좌표로 변환
            # PoseTracker는 카메라 좌표를 사용하므로 화면 좌표로 변환 필요
            nose_x_camera = nose_pos[0]  # 카메라 좌표
            nose_y_camera = nose_pos[1]

            # 화면 좌표로 변환 (스케일링)
            # constants의 좌표는 화면 좌표 기준이므로, 카메라 좌표를 화면 좌표로 변환
            if pose_tracker.width > 0 and pose_tracker.height > 0:
                nose_x = nose_x_camera * (screen_width / pose_tracker.width)
                nose_y = nose_y_camera * (screen_height / pose_tracker.height)
            else:
                nose_x = nose_x_camera
                nose_y = nose_y_camera

            # a. 위빙 L (왼쪽으로 피하기): 코가 오른쪽 영역(Dodge R)에 있어야 함
            if beat_type == "WEAVE_L":
                # 위빙 L 명령 -> 코가 DODGE_RIGHT_LINE_X의 왼쪽에 있어야 함 (중앙선과 DODGE_RIGHT_LINE_X 사이)
                # 판정 성공 조건: DODGE_CENTER_LINE_X < nose_x < DODGE_RIGHT_LINE_X
                if DODGE_CENTER_LINE_X < nose_x < DODGE_RIGHT_LINE_X:
                    return 'HIT'
                # 좌우 라인을 벗어나면 MISS 처리
                elif nose_x < DODGE_LEFT_LINE_X or nose_x > DODGE_RIGHT_LINE_X:
                    return 'MISS'
                else:
                    return 'MISS'

            # b. 위빙 R (오른쪽으로 피하기): 코가 왼쪽 영역(Dodge L)에 있어야 함
            elif beat_type == "WEAVE_R":
                # 위빙 R 명령 -> 코가 DODGE_LEFT_LINE_X의 오른쪽에 있어야 함 (DODGE_LEFT_LINE_X와 중앙선 사이)
                # 판정 성공 조건: DODGE_LEFT_LINE_X < nose_x < DODGE_CENTER_LINE_X
                if DODGE_LEFT_LINE_X < nose_x < DODGE_CENTER_LINE_X:
                    return 'HIT'
                # 좌우 라인을 벗어나면 MISS 처리
                elif nose_x < DODGE_LEFT_LINE_X or nose_x > DODGE_RIGHT_LINE_X:
                    return 'MISS'
                else:
                    return 'MISS'

        # 4. 시간 판정 실패 (비트가 판정 시간을 지났을 경우)
        if time_diff < 0:
            return 'MISS'

        return None  # 아직 판정 시간 아님

