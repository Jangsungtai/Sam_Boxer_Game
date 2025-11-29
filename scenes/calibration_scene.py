from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import arcade

from scenes.base_scene import BaseScene


class CalibrationScene(BaseScene):
    """사용자 포즈 캘리브레이션을 위한 안내 씬."""

    def __init__(self, window, audio_manager, config, pose_tracker) -> None:
        super().__init__(window, audio_manager, config, pose_tracker)
        self.hold_requirement = float(self.config.get("rules", {}).get("calibration_hold_time", 3.0))
        self.targets: Dict[str, Dict[str, float]] = {}
        self.hold_start: Optional[float] = None
        self.last_status: Tuple[bool, bool, bool] = (False, False, False)
        self.status_text: str = "카메라 앞에 서서 지시에 맞춰 주세요."
        self.last_nose_pos: Optional[Tuple[float, float]] = None
        self.last_left_fist: Optional[Tuple[float, float]] = None
        self.last_right_fist: Optional[Tuple[float, float]] = None
        self.countdown_remaining: Optional[float] = None

    def startup(self, persistent_data):
        super().startup(persistent_data)
        self._build_targets()
        self.hold_start = None
        self.last_status = (False, False, False)
        self.status_text = "카메라 앞에 서서 지시에 맞춰 주세요."
        self.last_nose_pos = None
        self.last_left_fist = None
        self.last_right_fist = None
        self.countdown_remaining = None
        # next_scene_name 초기화 (startup에서 None으로 설정됨)
        print(f"[CalibrationScene] Startup: next_scene_name={self.next_scene_name}")

    def _build_targets(self) -> None:
        if not self.source_width or not self.source_height:
            return
        positions = self.config.get("ui", {}).get("positions", {})
        calib_cfg = positions.get("calibration_targets", {})

        def build_target(name: str) -> Dict[str, float]:
            data = calib_cfg.get(name, {})
            ratio_x, ratio_y = data.get("pos_ratio", [0.5, 0.5])
            radius = data.get("radius_ratio_w", 0.08) * self.source_width
            return {
                "pos": (
                    ratio_x * self.source_width,
                    ratio_y * self.source_height,
                ),
                "radius": radius,
            }

        self.targets = {
            "head": build_target("head"),
            "left_fist": build_target("left_fist"),
            "right_fist": build_target("right_fist"),
        }

    def update(self, delta_time: float, **kwargs):
        super().update(delta_time, **kwargs)
        
        # next_scene_name이 설정되어 있으면 씬 전환 대기 (키 입력으로 설정된 경우)
        if self.next_scene_name:
            print(f"[CalibrationScene] update: next_scene_name={self.next_scene_name}, waiting for scene switch")
            return
        
        if self.pose_tracker is None:
            # 포즈 트래커가 없으면 바로 게임으로 이동
            self.persistent_data["calibrated"] = False
            self.next_scene_name = "GAME"
            return

        landmarks = kwargs.get("landmarks")
        if not landmarks:
            self.status_text = "신체 전체가 프레임 안에 들어오도록 서 주세요."
            self.hold_start = None
            self.last_nose_pos = None
            self.last_left_fist = None
            self.last_right_fist = None
            self.countdown_remaining = None
            return

        if not self.targets:
            self._build_targets()
            if not self.targets:
                return

        if self.pose_tracker:
            smoothed = self.pose_tracker.get_smoothed_landmarks()
            if smoothed:
                self.last_nose_pos = smoothed.get("nose")
            left_fist, right_fist = self.pose_tracker.get_fist_centroids()
            self.last_left_fist = left_fist
            self.last_right_fist = right_fist

        all_ok, status_tuple, _ = self.pose_tracker.check_calibration_position(self.targets)
        self.last_status = status_tuple

        if all_ok:
            if self.hold_start is None:
                self.hold_start = kwargs.get("now", time.time())
            held_for = kwargs.get("now", time.time()) - self.hold_start
            self.status_text = f"좋아요! 유지하세요... ({held_for:0.1f}s)"
            self.countdown_remaining = max(0.0, self.hold_requirement - held_for)
            if held_for >= self.hold_requirement:
                self.pose_tracker.calibrate_from_pose(landmarks)
                self.persistent_data["calibrated"] = True
                self.countdown_remaining = 0.0
                self.next_scene_name = "GAME"
        else:
            cues = []
            head_ok, left_ok, right_ok = status_tuple
            if not head_ok:
                cues.append("머리를 원 안에 맞춰 주세요.")
            if not left_ok:
                cues.append("화면 왼쪽 손을 표시된 위치에 맞춰 주세요.")
            if not right_ok:
                cues.append("화면 오른쪽 손을 표시된 위치에 맞춰 주세요.")
            self.status_text = " / ".join(cues) if cues else "자세를 다시 맞춰 주세요."
            self.hold_start = None
            self.countdown_remaining = None

    def draw_scene(self) -> None:
        width = max(1, int(self.window.width))
        height = max(1, int(self.window.height))
        center_x = width / 2
        center_y = height - 80

        arcade.draw_text(
            "CALIBRATION",
            center_x,
            center_y,
            arcade.color.WHITE,
            font_size=32,
            anchor_x="center",
        )

        arcade.draw_text(
            "",
            center_x,
            center_y - 60,
            arcade.color.AQUA,
            font_size=18,
            anchor_x="center",
        )

        if not self.targets:
            return

        def draw_target(target_name: str, color: Tuple[int, int, int], ok: bool, label: str) -> None:
            target = self.targets.get(target_name)
            if not target:
                return
            cx, cy = self.to_arcade_xy(target["pos"])
            radius = target["radius"] * self.x_scale
            arcade.draw_circle_outline(cx, cy, radius, color, 4)
            if ok:
                arcade.draw_circle_filled(cx, cy, radius * 0.6, color)
            arcade.draw_text(label, cx, cy - radius - 30, color, font_size=16, anchor_x="center")

        head_ok, left_ok, right_ok = self.last_status
        head_color = arcade.color.WHITE
        left_color = arcade.color.ORANGE_RED
        right_color = arcade.color.DODGER_BLUE

        draw_target("head", head_color, head_ok, "머리를 원 안에 맞춰 주세요.")
        # 좌우 반전: 화면 왼쪽 = 실제 왼손, 화면 오른쪽 = 실제 오른손
        draw_target("left_fist", left_color, left_ok, "화면 왼쪽 손을 표시된 위치에 맞춰 주세요.")
        draw_target("right_fist", right_color, right_ok, "화면 오른쪽 손을 표시된 위치에 맞춰 주세요.")

        self._draw_pose_markers()

        if self.countdown_remaining is not None:
            arcade.draw_text(
                f"{self.countdown_remaining:0.2f}",
                width * 0.5,
                height * 0.4,
                arcade.color.WHITE,
                font_size=72,
                anchor_x="center",
                anchor_y="center",
            )

    def _draw_pose_markers(self) -> None:
        marker_radius = 8 * max(self.x_scale, self.y_scale, 1.0)

        if self.last_nose_pos:
            self._draw_marker(self.last_nose_pos, arcade.color.GOLD, marker_radius)

        # 화면 기준 왼쪽 = 실제 오른손 (right_fist)
        if self.last_right_fist:
            self._draw_marker(self.last_right_fist, arcade.color.LIGHT_SKY_BLUE, marker_radius)

        if self.last_left_fist:
            self._draw_marker(self.last_left_fist, arcade.color.SALMON, marker_radius)

    def _draw_marker(self, pos: Tuple[float, float], color: Tuple[int, int, int], radius: float) -> None:
        cx, cy = self.to_arcade_xy(pos)
        arcade.draw_circle_filled(cx, cy, radius, color)
        arcade.draw_circle_outline(cx, cy, radius + 2, arcade.color.WHITE, 2)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        # 디버깅: 모든 키 입력 로그 출력
        print(f"[CalibrationScene] Key pressed: symbol={symbol}, modifiers={modifiers}, char={chr(symbol) if 32 <= symbol <= 126 else 'N/A'}")
        
        # 0 키 처리 (여러 방법으로 체크)
        is_zero = (
            symbol == arcade.key.KEY_0 or 
            symbol == arcade.key.NUM_0 or 
            symbol == ord('0') or
            symbol == 48  # ASCII 코드 직접 체크
        )
        
        # 9 키 처리 (여러 방법으로 체크)
        is_nine = (
            symbol == arcade.key.KEY_9 or 
            symbol == arcade.key.NUM_9 or 
            symbol == ord('9') or
            symbol == 57  # ASCII 코드 직접 체크
        )
        
        if is_zero:
            print(f"[CalibrationScene] '0' detected (symbol={symbol}) – skipping calibration (normal mode).")
            self.persistent_data["calibrated"] = False
            self.persistent_data["test_mode"] = False
            if self.pose_tracker:
                self.pose_tracker.set_test_mode(False)
            self.next_scene_name = "GAME"
            print(f"[CalibrationScene] Setting next_scene_name to: {self.next_scene_name}")
        elif is_nine:
            print(f"[CalibrationScene] '9' detected (symbol={symbol}) – skipping calibration (test mode).")
            self.persistent_data["calibrated"] = False
            self.persistent_data["test_mode"] = True
            if self.pose_tracker:
                self.pose_tracker.set_test_mode(True)
            self.next_scene_name = "GAME"
            print(f"[CalibrationScene] Setting next_scene_name to: {self.next_scene_name}")

