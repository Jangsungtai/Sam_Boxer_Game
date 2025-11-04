#MediaPipe 로직, 캘리브레이션, 동작 감지(펀치/더킹)를 모두 캡슐화한 클래스
import cv2
import time
import math
import numpy as np
import mediapipe as mp
from collections import deque

# MediaPipe 포즈 솔루션 초기화
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class PoseTracker:
    def __init__(self, width, height, config_rules, config_ui):
        self.pose = mp_pose.Pose(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.width = width
        self.height = height
        
        # (기록용 deque들)
        self.hist_t = deque(maxlen=5)
        self.hist_lw = deque(maxlen=5); self.hist_rw = deque(maxlen=5)
        self.hist_ls = deque(maxlen=5); self.hist_rs = deque(maxlen=5)
        self.hist_le = deque(maxlen=5); self.hist_re = deque(maxlen=5)

        # --- (수정) calib_data 구조 및 기본값 변경 ---
        self.calib_data = {
            "shoulder_w": 300,
            "head_center": (int(width * 0.5), int(height * 0.35)),
            "head_radius": int(width * 0.08),
            "duck_line_y": int(height * 0.5)
        }
        # --- (수정 끝) ---
        
        # --- (수정) config 값 로드 방식 변경 ---
        rules = config_rules["action_thresholds"]
        self.REFRACTORY = rules["action_refractory"]
        self.V_THRESH = rules["action_v_thresh"]
        self.ANG_THRESH = rules["action_ang_thresh"]
        # (참고) DUCK_LINE_OFFSET_RATIO는 더 이상 여기서 사용 안 함
        # --- (수정 끝) ---
        
        self.last_hit_t = {"L": 0.0, "R": 0.0}

    def _angle(self, a, b, c):
        # (3점 사이의 각도 계산)
        a = np.array(a); b = np.array(b); c = np.array(c)
        ab = a - b; cb = c - b
        denom = (np.linalg.norm(ab) * np.linalg.norm(cb) + 1e-6)
        cosang = np.dot(ab, cb) / denom
        return math.degrees(math.acos(np.clip(cosang, -1.0, 1.0)))

    # --- (수정) 캘리브레이션 메서드 전체 변경 ---
    def calibrate_from_pose(self, pose_landmarks):
        """
        안정화된 단일 포즈(landmarks)를 기반으로 캘리브레이션을 수행합니다.
        (기존: calibrate_from_frames)
        """
        print("Calibrating from stable pose...")
        if not pose_landmarks:
            print("Calibration Failed: No pose data provided. Using defaults.")
            return

        lm = pose_landmarks.landmark
        def P(i): return (lm[i].x * self.width, lm[i].y * self.height)

        try:
            L_SH = P(mp_pose.PoseLandmark.LEFT_SHOULDER)
            R_SH = P(mp_pose.PoseLandmark.RIGHT_SHOULDER)
            NOSE = P(mp_pose.PoseLandmark.NOSE)
            
            # 1. 평균 어깨 너비 계산
            shoulder_w = np.linalg.norm(np.array(L_SH) - np.array(R_SH))
            
            # 2. 헤드 서클 (코 기준)
            head_center = (int(NOSE[0]), int(NOSE[1]))
            
            # 3. 헤드 반지름 (어깨 너비의 40%로 유추)
            # (요구사항: "얼굴 사이즈를 유추한 원", "추후 얼굴 모양")
            head_radius = int(shoulder_w * 0.4) 
            
            # 4. 더킹 라인 (캘리브레이션된 머리 '바닥' 기준)
            # (head_circle의 y + radius)
            duck_line_y = head_center[1] + head_radius
            
            # 계산된 값 저장
            self.calib_data["shoulder_w"] = shoulder_w
            self.calib_data["head_center"] = head_center
            self.calib_data["head_radius"] = head_radius
            self.calib_data["duck_line_y"] = duck_line_y
            
            print(f"Calibration Done: ShoulderWidth={shoulder_w:.1f}px, Head=({head_center}, r={head_radius}), DuckLineY={duck_line_y}px")

        except Exception as e:
            print(f"Calibration Error: {e}. Using default values.")
    # --- (수정 끝) ---

    def process_frame(self, frame, now):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)
        hit_events = []
        if not res.pose_landmarks:
            return hit_events, None
        
        lm = res.pose_landmarks.landmark
        def P(i): return (lm[i].x * self.width, lm[i].y * self.height)
        
        try:
            LW, RW = P(mp_pose.PoseLandmark.LEFT_WRIST),  P(mp_pose.PoseLandmark.RIGHT_WRIST)
            LS, RS = P(mp_pose.PoseLandmark.LEFT_SHOULDER),P(mp_pose.PoseLandmark.RIGHT_SHOULDER)
            LE, RE = P(mp_pose.PoseLandmark.LEFT_ELBOW),   P(mp_pose.PoseLandmark.RIGHT_ELBOW)
            NOSE   = P(mp_pose.PoseLandmark.NOSE)
        except Exception:
            return hit_events, res.pose_landmarks

        mp_drawing.draw_landmarks(
            frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )

        self.hist_t.append(now)
        for h, v in [(self.hist_lw, LW), (self.hist_rw, RW), (self.hist_ls, LS), (self.hist_rs, RS), (self.hist_le, LE), (self.hist_re, RE)]:
            h.append(v)
            
        if len(self.hist_t) < 2:
            return hit_events, res.pose_landmarks

        dt = self.hist_t[-1] - self.hist_t[-2]
        
        # --- (수정) 캘리브레이션된 어깨너비 사용 ---
        sw = self.calib_data["shoulder_w"]
        # --- (수정 끝) ---

        def radial_speed(S, W, prevW):
            r_now = np.linalg.norm(np.array(W) - np.array(S)) / sw
            r_prv = np.linalg.norm(np.array(prevW) - np.array(S)) / sw
            return (r_now - r_prv) / max(1e-6, dt)
            
        vL = radial_speed(LS, LW, self.hist_lw[-2])
        vR = radial_speed(RS, RW, self.hist_rw[-2])
        angL = self._angle(LS, LE, LW); angR = self._angle(RS, RE, RW)
        
        hit_zone_x = self.width // 2
        left_zone = LW[0] < hit_zone_x; right_zone = RW[0] > hit_zone_x

        if (vL >= self.V_THRESH and angL >= self.ANG_THRESH and left_zone and (now - self.last_hit_t["L"] > self.REFRACTORY)):
            hit_events.append({"type": "JAB_L", "t_hit": now})
            self.last_hit_t["L"] = now

        if (vR >= self.V_THRESH and angR >= self.ANG_THRESH and right_zone and (now - self.last_hit_t["R"] > self.REFRACTORY)):
            hit_events.append({"type": "JAB_R", "t_hit": now})
            self.last_hit_t["R"] = now

        # --- (수정) 더킹 기준선 변경 ---
        # 캘리브레이션된 'duck_line_y' (머리 바닥)을 기준으로 함
        if NOSE[1] > self.calib_data["duck_line_y"]: 
             hit_events.append({"type": "DUCK", "t_hit": now})
        # --- (수정 끝) ---

        return hit_events, res.pose_landmarks