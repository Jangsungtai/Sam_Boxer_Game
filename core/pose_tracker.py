#MediaPipe 로직, 캘리브레이션, 동작 감지(펀치/더킹)를 모두 캡슐화한 클래스
import cv2
import time
import math
import numpy as np
import mediapipe as mp
from collections import deque

# MediaPipe 포즈 솔루션 초기화
mp_pose = mp.solutions.pose

class PoseTracker:
    def __init__(self, width, height, config_rules, config_ui):
        self.pose = mp_pose.Pose(
            model_complexity=2,  # 정확도 개선을 위해 1 -> 2로 변경
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            enable_segmentation=True # --- (수정) 배경 분리 기능 활성화 ---
        )
        
        self.width = width
        self.height = height
        
        # (기록용 deque들...)
        self.hist_t = deque(maxlen=5)
        self.hist_lw = deque(maxlen=5); self.hist_rw = deque(maxlen=5)
        self.hist_ls = deque(maxlen=5); self.hist_rs = deque(maxlen=5)
        self.hist_le = deque(maxlen=5); self.hist_re = deque(maxlen=5)

        # 캘리브레이션 데이터 (기본값)
        self.calib_data = {
            "shoulder_w": 300,
            "head_center": (int(width * 0.5), int(height * 0.35)),
            "head_radius": int(width * 0.08),
            "duck_line_y": int(height * 0.5)
        }
        
        rules = config_rules["action_thresholds"]
        self.REFRACTORY = rules["action_refractory"]
        self.V_THRESH = rules["action_v_thresh"]
        self.ANG_THRESH = rules["action_ang_thresh"]
        
        self.test_mode = False
        self.last_hit_t = {"L": 0.0, "R": 0.0}
        
        # config_rules 저장 (spatial_judge_mode 접근용)
        self.config_rules = config_rules
        
        # 테스트 모드: 손이 히트존 밖에 있었는지 추적
        self.left_was_outside_hit_zone = False
        self.right_was_outside_hit_zone = False
        
        # 히트존 정보 가져오기
        hud_styles = config_ui.get("styles", {}).get("hud", {})
        hit_zone_pos_ratio = config_ui.get("positions", {}).get("hit_zone", {}).get("pos_ratio", [0.5, 0.3])
        self.hit_zone_x = int(width * hit_zone_pos_ratio[0])
        self.hit_zone_y = int(height * hit_zone_pos_ratio[1])
        self.hit_zone_radius = int(hud_styles.get("hit_zone_radius", 100))
        
        # 랜드마크 스무딩 데이터 (Phase 1: 역할 확장)
        self.smoothing_alpha = 0.7  # 스무딩 계수
        self.calib_landmark_pos = {
            "head_center": None, "nose": None, "left_eye_inner": None, "right_eye_inner": None,
            "left_wrist": None, "right_wrist": None, 
            "left_elbow": None, "right_elbow": None,
            "shoulders": (None, None),
            "left_ear": None, "right_ear": None,
            "left_mouth": None, "right_mouth": None,
            "left_index": None, "right_index": None,
            "left_pinky": None, "right_pinky": None,
            "left_thumb": None, "right_thumb": None
        }
        self.smoothed_landmark_pos = self.calib_landmark_pos.copy()
        
        # 주먹 중심점 (계산된 값)
        self.left_fist_center = None
        self.right_fist_center = None

    def _angle(self, a, b, c):
        # (1단계와 동일)
        a = np.array(a); b = np.array(b); c = np.array(c)
        ab = a - b; cb = c - b
        denom = (np.linalg.norm(ab) * np.linalg.norm(cb) + 1e-6)
        cosang = np.dot(ab, cb) / denom
        return math.degrees(math.acos(np.clip(cosang, -1.0, 1.0)))

    def calibrate_from_pose(self, pose_landmarks):
        """
        안정화된 단일 포즈(landmarks)를 기반으로 캘리브레이션을 수행합니다.
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
            
            shoulder_w = np.linalg.norm(np.array(L_SH) - np.array(R_SH))
            head_center = (int(NOSE[0]), int(NOSE[1]))
            head_radius = int(shoulder_w * 0.4) 
            duck_line_y = head_center[1] + head_radius
            
            self.calib_data["shoulder_w"] = shoulder_w
            self.calib_data["head_center"] = head_center
            self.calib_data["head_radius"] = head_radius
            self.calib_data["duck_line_y"] = duck_line_y
            
            print(f"Calibration Done: ShoulderWidth={shoulder_w:.1f}px, Head=({head_center}, r={head_radius}), DuckLineY={duck_line_y}px")

        except Exception as e:
            print(f"Calibration Error: {e}. Using default values.")

    def process_frame(self, frame, now):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)
        hit_events = []
        
        # --- (수정) 마스크가 없을 때도 None 반환 ---
        if not res.pose_landmarks:
            return hit_events, None, None
        # --- (수정 끝) ---
        
        lm = res.pose_landmarks.landmark
        def P(i): return (lm[i].x * self.width, lm[i].y * self.height)
        
        try:
            LW, RW = P(mp_pose.PoseLandmark.LEFT_WRIST),  P(mp_pose.PoseLandmark.RIGHT_WRIST)
            LS, RS = P(mp_pose.PoseLandmark.LEFT_SHOULDER),P(mp_pose.PoseLandmark.RIGHT_SHOULDER)
            LE, RE = P(mp_pose.PoseLandmark.LEFT_ELBOW),   P(mp_pose.PoseLandmark.RIGHT_ELBOW)
            NOSE   = P(mp_pose.PoseLandmark.NOSE)
        except Exception:
            # --- (수정) 마스크 함께 반환 ---
            return hit_events, res.pose_landmarks, res.segmentation_mask
            # --- (수정 끝) ---

        self.hist_t.append(now)
        for h, v in [(self.hist_lw, LW), (self.hist_rw, RW), (self.hist_ls, LS), (self.hist_rs, RS), (self.hist_le, LE), (self.hist_re, RE)]:
            h.append(v)
            
        if len(self.hist_t) < 2:
            # --- (수정) 마스크 함께 반환 ---
            return hit_events, res.pose_landmarks, res.segmentation_mask
            # --- (수정 끝) ---

        dt = self.hist_t[-1] - self.hist_t[-2]
        sw = self.calib_data["shoulder_w"]

        def radial_speed(S, W, prevW):
            r_now = np.linalg.norm(np.array(W) - np.array(S)) / sw
            r_prv = np.linalg.norm(np.array(prevW) - np.array(S)) / sw
            return (r_now - r_prv) / max(1e-6, dt)
            
        vL = radial_speed(LS, LW, self.hist_lw[-2])
        vR = radial_speed(RS, RW, self.hist_rw[-2])
        angL = self._angle(LS, LE, LW); angR = self._angle(RS, RE, RW)
        
        hit_zone_x = self.width // 2
        # MediaPipe는 반전된 프레임을 처리하므로, 랜드마크 좌표도 반전된 프레임 기준입니다.
        # 화면에서 보이는 위치:
        # - 화면 왼쪽에 보이는 손 = 사용자의 오른손 = RIGHT_WRIST
        # - 화면 오른쪽에 보이는 손 = 사용자의 왼손 = LEFT_WRIST
        # MediaPipe 좌표 기준으로는 (반전된 프레임 기준):
        # - RIGHT_WRIST가 화면 왼쪽에 있으면 RW[0] < hit_zone_x
        # - LEFT_WRIST가 화면 오른쪽에 있으면 LW[0] > hit_zone_x
        left_zone_for_jab_l = RW[0] < hit_zone_x  # RIGHT_WRIST가 화면 왼쪽에 있으면
        right_zone_for_jab_r = LW[0] > hit_zone_x  # LEFT_WRIST가 화면 오른쪽에 있으면

        if self.test_mode:
            # 테스트 모드: 손의 중심점이 히트존을 나갔다가 다시 들어온 것을 감지
            # spatial_judge_mode에 따라 손의 중심점 계산
            spatial_mode = self.config_rules.get("spatial_judge_mode", 2)
            
            # cv2.flip 고려: 화면 왼쪽 펀치(JAB_L)는 RIGHT_WRIST 사용, 화면 오른쪽 펀치(JAB_R)는 LEFT_WRIST 사용
            # RIGHT_WRIST 중심점 계산 (JAB_L에 사용 - 화면 왼쪽에 보이는 손)
            right_wrist = RW
            right_pinky = P(mp_pose.PoseLandmark.RIGHT_PINKY) if spatial_mode == 2 else None
            right_index = P(mp_pose.PoseLandmark.RIGHT_INDEX) if spatial_mode == 2 else None
            right_thumb = P(mp_pose.PoseLandmark.RIGHT_THUMB) if spatial_mode == 2 else None
            
            if spatial_mode == 1:
                right_center_for_jab_l = right_wrist
            else:
                right_points = [p for p in [right_wrist, right_pinky, right_index, right_thumb] if p is not None]
                if right_points:
                    right_center_for_jab_l = (np.mean([p[0] for p in right_points]), np.mean([p[1] for p in right_points]))
                else:
                    right_center_for_jab_l = None
            
            # LEFT_WRIST 중심점 계산 (JAB_R에 사용 - 화면 오른쪽에 보이는 손)
            left_wrist = LW
            left_pinky = P(mp_pose.PoseLandmark.LEFT_PINKY) if spatial_mode == 2 else None
            left_index = P(mp_pose.PoseLandmark.LEFT_INDEX) if spatial_mode == 2 else None
            left_thumb = P(mp_pose.PoseLandmark.LEFT_THUMB) if spatial_mode == 2 else None
            
            if spatial_mode == 1:
                left_center_for_jab_r = left_wrist
            else:
                left_points = [p for p in [left_wrist, left_pinky, left_index, left_thumb] if p is not None]
                if left_points:
                    left_center_for_jab_r = (np.mean([p[0] for p in left_points]), np.mean([p[1] for p in left_points]))
                else:
                    left_center_for_jab_r = None
            
            # 히트존 안에 있는지 확인
            def is_inside_hit_zone(center):
                if center is None:
                    return False
                # MediaPipe 좌표는 이미 반전된 프레임 기준이므로 추가 반전 불필요
                dist = np.sqrt((center[0] - self.hit_zone_x)**2 + (center[1] - self.hit_zone_y)**2)
                return dist <= self.hit_zone_radius
            
            # JAB_L: RIGHT_WRIST(화면 왼쪽에 보이는 손)가 히트존을 나갔다가 다시 들어온 경우
            if right_center_for_jab_l:
                right_inside = is_inside_hit_zone(right_center_for_jab_l)
                if not self.right_was_outside_hit_zone and not right_inside:
                    # 히트존 밖으로 나감
                    self.right_was_outside_hit_zone = True
                elif self.right_was_outside_hit_zone and right_inside and left_zone_for_jab_l:
                    # 히트존 밖에 있다가 다시 안으로 들어옴 (펀치 감지)
                    if (now - self.last_hit_t["L"] > self.REFRACTORY):
                        hit_events.append({"type": "JAB_L", "t_hit": now})
                        self.last_hit_t["L"] = now
                        self.right_was_outside_hit_zone = False
            
            # JAB_R: LEFT_WRIST(화면 오른쪽에 보이는 손)가 히트존을 나갔다가 다시 들어온 경우
            if left_center_for_jab_r:
                left_inside = is_inside_hit_zone(left_center_for_jab_r)
                if not self.left_was_outside_hit_zone and not left_inside:
                    # 히트존 밖으로 나감
                    self.left_was_outside_hit_zone = True
                elif self.left_was_outside_hit_zone and left_inside and right_zone_for_jab_r:
                    # 히트존 밖에 있다가 다시 안으로 들어옴 (펀치 감지)
                    if (now - self.last_hit_t["R"] > self.REFRACTORY):
                        hit_events.append({"type": "JAB_R", "t_hit": now})
                        self.last_hit_t["R"] = now
                        self.left_was_outside_hit_zone = False
        else:
            # 일반 모드: 속도, hit zone 내부, 쿨타임 체크
            # cv2.flip 고려: JAB_L은 RIGHT_WRIST(화면 왼쪽)의 속도 사용, JAB_R은 LEFT_WRIST(화면 오른쪽)의 속도 사용
            # 주먹 중심점이 hit zone 안에 있는지 확인
            spatial_mode = self.config_rules.get("spatial_judge_mode", 2)
            
            # JAB_L: RIGHT_WRIST 중심점 계산
            right_wrist = RW
            right_pinky = P(mp_pose.PoseLandmark.RIGHT_PINKY) if spatial_mode == 2 else None
            right_index = P(mp_pose.PoseLandmark.RIGHT_INDEX) if spatial_mode == 2 else None
            right_thumb = P(mp_pose.PoseLandmark.RIGHT_THUMB) if spatial_mode == 2 else None
            
            if spatial_mode == 1:
                right_center_for_jab_l = right_wrist
            else:
                right_points = [p for p in [right_wrist, right_pinky, right_index, right_thumb] if p is not None]
                if right_points:
                    right_center_for_jab_l = (np.mean([p[0] for p in right_points]), np.mean([p[1] for p in right_points]))
                else:
                    right_center_for_jab_l = None
            
            # JAB_R: LEFT_WRIST 중심점 계산
            left_wrist = LW
            left_pinky = P(mp_pose.PoseLandmark.LEFT_PINKY) if spatial_mode == 2 else None
            left_index = P(mp_pose.PoseLandmark.LEFT_INDEX) if spatial_mode == 2 else None
            left_thumb = P(mp_pose.PoseLandmark.LEFT_THUMB) if spatial_mode == 2 else None
            
            if spatial_mode == 1:
                left_center_for_jab_r = left_wrist
            else:
                left_points = [p for p in [left_wrist, left_pinky, left_index, left_thumb] if p is not None]
                if left_points:
                    left_center_for_jab_r = (np.mean([p[0] for p in left_points]), np.mean([p[1] for p in left_points]))
                else:
                    left_center_for_jab_r = None
            
            # 히트존 안에 있는지 확인하는 함수
            def is_inside_hit_zone(center):
                if center is None:
                    return False
                # MediaPipe 좌표는 이미 반전된 프레임 기준이므로 추가 반전 불필요
                dist = np.sqrt((center[0] - self.hit_zone_x)**2 + (center[1] - self.hit_zone_y)**2)
                return dist <= self.hit_zone_radius
            
            # JAB_L 판정 (각도 조건 제거, hit zone 체크 추가)
            jab_l_conditions = {
                "vR": vR >= self.V_THRESH,
                "in_hit_zone": right_center_for_jab_l is not None and is_inside_hit_zone(right_center_for_jab_l),
                "cooldown": (now - self.last_hit_t["L"] > self.REFRACTORY)
            }
            if all(jab_l_conditions.values()):
                hit_events.append({"type": "JAB_L", "t_hit": now})
                self.last_hit_t["L"] = now
                if self.test_mode:
                    print(f"[JAB_L HIT] vR={vR:.2f}, angR={angR:.1f}, RW[0]={RW[0]:.1f}, hit_zone_x={hit_zone_x}, in_zone=True")
            elif self.test_mode and vR > 0.3:  # test mode에서만 조건이 거의 충족될 때 로그
                failed = [k for k, v in jab_l_conditions.items() if not v]
                in_zone = right_center_for_jab_l is not None and is_inside_hit_zone(right_center_for_jab_l)
                print(f"[JAB_L FAIL] {failed} | vR={vR:.2f}/{self.V_THRESH}, angR={angR:.1f}, in_zone={in_zone}, RW[0]={RW[0]:.1f}, cooldown={(now-self.last_hit_t['L']):.2f}s")

            # JAB_R 판정 (각도 조건 제거, hit zone 체크 추가)
            jab_r_conditions = {
                "vL": vL >= self.V_THRESH,
                "in_hit_zone": left_center_for_jab_r is not None and is_inside_hit_zone(left_center_for_jab_r),
                "cooldown": (now - self.last_hit_t["R"] > self.REFRACTORY)
            }
            if all(jab_r_conditions.values()):
                hit_events.append({"type": "JAB_R", "t_hit": now})
                self.last_hit_t["R"] = now
                if self.test_mode:
                    print(f"[JAB_R HIT] vL={vL:.2f}, angL={angL:.1f}, LW[0]={LW[0]:.1f}, hit_zone_x={hit_zone_x}, in_zone=True")
            elif self.test_mode and vL > 0.3:  # test mode에서만 조건이 거의 충족될 때 로그
                failed = [k for k, v in jab_r_conditions.items() if not v]
                in_zone = left_center_for_jab_r is not None and is_inside_hit_zone(left_center_for_jab_r)
                print(f"[JAB_R FAIL] {failed} | vL={vL:.2f}/{self.V_THRESH}, angL={angL:.1f}, in_zone={in_zone}, LW[0]={LW[0]:.1f}, cooldown={(now-self.last_hit_t['R']):.2f}s")

        if NOSE[1] > self.calib_data["duck_line_y"]: 
             hit_events.append({"type": "DUCK", "t_hit": now})

        # Phase 1: 랜드마크 스무딩 및 주먹 중심점 계산
        if res.pose_landmarks:
            self.update_landmark_smoothing(res.pose_landmarks)
            self.calculate_fist_centroids()

        # --- (수정) 마스크 함께 반환 ---
        return hit_events, res.pose_landmarks, res.segmentation_mask

    def set_test_mode(self, enabled: bool) -> None:
        """테스트 모드 토글 (실시간 디버그 용)."""
        self.test_mode = bool(enabled)
        # --- (수정 끝) ---
    
    def get_smoothed_landmarks(self):
        """현재 스무딩된 모든 랜드마크를 반환합니다 (Phase 1)."""
        return self.smoothed_landmark_pos.copy()
    
    def get_fist_centroids(self):
        """주먹 중심점을 계산하여 반환합니다 (Phase 1).
        
        Returns:
            (left_fist_center, right_fist_center): 
            - left_fist_center: (x, y) 또는 None
            - right_fist_center: (x, y) 또는 None
        """
        return (self.left_fist_center, self.right_fist_center)
    
    def update_landmark_smoothing(self, pose_landmarks):
        """랜드마크 스무딩을 업데이트합니다 (Phase 1)."""
        if not pose_landmarks:
            return
        
        lm = pose_landmarks.landmark
        def P(i): return (lm[i].x * self.width, lm[i].y * self.height)
        
        try:
            # 랜드마크 좌표 추출
            raw_landmark_pos = {
                "head_center": None, "nose": None, "left_eye_inner": None, "right_eye_inner": None,
                "left_wrist": None, "right_wrist": None, 
                "left_elbow": None, "right_elbow": None,
                "shoulders": (None, None),
                "left_ear": None, "right_ear": None,
                "left_mouth": None, "right_mouth": None,
                "left_index": None, "right_index": None,
                "left_pinky": None, "right_pinky": None,
                "left_thumb": None, "right_thumb": None
            }
            
            NOSE = P(mp_pose.PoseLandmark.NOSE)
            L_EYE_INNER = P(mp_pose.PoseLandmark.LEFT_EYE_INNER)
            R_EYE_INNER = P(mp_pose.PoseLandmark.RIGHT_EYE_INNER)
            HEAD_CENTER = ((L_EYE_INNER[0] + R_EYE_INNER[0]) / 2, (L_EYE_INNER[1] + R_EYE_INNER[1]) / 2)
            
            L_WRIST = P(mp_pose.PoseLandmark.LEFT_WRIST)
            R_WRIST = P(mp_pose.PoseLandmark.RIGHT_WRIST)
            L_ELBOW = P(mp_pose.PoseLandmark.LEFT_ELBOW)
            R_ELBOW = P(mp_pose.PoseLandmark.RIGHT_ELBOW)
            L_SHOULDER = P(mp_pose.PoseLandmark.LEFT_SHOULDER)
            R_SHOULDER = P(mp_pose.PoseLandmark.RIGHT_SHOULDER)
            LEFT_EAR = P(mp_pose.PoseLandmark.LEFT_EAR)
            RIGHT_EAR = P(mp_pose.PoseLandmark.RIGHT_EAR)
            LEFT_MOUTH = P(mp_pose.PoseLandmark.MOUTH_LEFT)
            RIGHT_MOUTH = P(mp_pose.PoseLandmark.MOUTH_RIGHT)
            L_PINKY = P(mp_pose.PoseLandmark.LEFT_PINKY)
            R_PINKY = P(mp_pose.PoseLandmark.RIGHT_PINKY)
            L_INDEX = P(mp_pose.PoseLandmark.LEFT_INDEX)
            R_INDEX = P(mp_pose.PoseLandmark.RIGHT_INDEX)
            L_THUMB = P(mp_pose.PoseLandmark.LEFT_THUMB)
            R_THUMB = P(mp_pose.PoseLandmark.RIGHT_THUMB)
            
            raw_landmark_pos = {
                "head_center": HEAD_CENTER, "nose": NOSE,
                "left_eye_inner": L_EYE_INNER, "right_eye_inner": R_EYE_INNER,
                "left_wrist": L_WRIST, "right_wrist": R_WRIST,
                "left_elbow": L_ELBOW, "right_elbow": R_ELBOW,
                "shoulders": (L_SHOULDER, R_SHOULDER),
                "left_ear": LEFT_EAR, "right_ear": RIGHT_EAR,
                "left_mouth": LEFT_MOUTH, "right_mouth": RIGHT_MOUTH,
                "left_index": L_INDEX, "right_index": R_INDEX,
                "left_pinky": L_PINKY, "right_pinky": R_PINKY,
                "left_thumb": L_THUMB, "right_thumb": R_THUMB
            }
        except Exception:
            return
        
        # 스무딩 적용
        for key in self.smoothed_landmark_pos.keys():
            raw_pos = raw_landmark_pos.get(key)
            prev_pos = self.smoothed_landmark_pos.get(key)
            
            if key == "shoulders":
                raw_l, raw_r = raw_pos if raw_pos and None not in raw_pos else (None, None)
                prev_l, prev_r = prev_pos if prev_pos and None not in prev_pos else (None, None)
                
                def smooth_point(raw, prev):
                    if raw:
                        if prev:
                            x = prev[0] * (1.0 - self.smoothing_alpha) + raw[0] * self.smoothing_alpha
                            y = prev[1] * (1.0 - self.smoothing_alpha) + raw[1] * self.smoothing_alpha
                            return (x, y)
                        return raw
                    return None
                    
                self.smoothed_landmark_pos[key] = (smooth_point(raw_l, prev_l), smooth_point(raw_r, prev_r))
                continue
            
            if raw_pos:
                if prev_pos:
                    new_x = prev_pos[0] * (1.0 - self.smoothing_alpha) + raw_pos[0] * self.smoothing_alpha
                    new_y = prev_pos[1] * (1.0 - self.smoothing_alpha) + raw_pos[1] * self.smoothing_alpha
                    self.smoothed_landmark_pos[key] = (new_x, new_y)
                else:
                    self.smoothed_landmark_pos[key] = raw_pos
            else:
                self.smoothed_landmark_pos[key] = None
    
    def calculate_fist_centroids(self):
        """주먹 중심점을 계산합니다 (Phase 1)."""
        mode = int(self.config_rules.get("spatial_judge_mode", 2))
        if mode == 1:
            left_keys = ["left_wrist"]
            right_keys = ["right_wrist"]
        else:
            left_keys = ["left_wrist", "left_pinky", "left_index", "left_thumb"]
            right_keys = ["right_wrist", "right_pinky", "right_index", "right_thumb"]
        
        def calc_centroid(keys):
            pts = [self.smoothed_landmark_pos.get(k) for k in keys]
            valid_points = [p for p in pts if p is not None]
            if not valid_points:
                return None
            xs = [p[0] for p in valid_points]
            ys = [p[1] for p in valid_points]
            return (int(np.mean(xs)), int(np.mean(ys)))
        
        self.left_fist_center = calc_centroid(left_keys)
        self.right_fist_center = calc_centroid(right_keys)
    
    def check_calibration_position(self, calib_targets):
        """캘리브레이션 위치 확인 (Phase 4).
        
        Args:
            calib_targets: 캘리브레이션 타겟 정보 (head, left_fist, right_fist)
        
        Returns:
            (all_ok, (head_ok, left_fist_ok, right_fist_ok), raw_landmark_pos): 
            - all_ok: 모든 타겟 달성 여부
            - (head_ok, left_fist_ok, right_fist_ok): 각 타겟 달성 여부
            - raw_landmark_pos: 원본 랜드마크 위치 딕셔너리
        """
        import mediapipe as mp
        mp_pose = mp.solutions.pose
        
        positions = {
            "head_center": None, "nose": None, "left_eye_inner": None, "right_eye_inner": None,
            "left_wrist": None, "right_wrist": None, 
            "left_elbow": None, "right_elbow": None,
            "shoulders": (None, None),
            "left_ear": None, "right_ear": None,
            "left_mouth": None, "right_mouth": None,
            "left_index": None, "right_index": None,
            "left_pinky": None, "right_pinky": None,
            "left_thumb": None, "right_thumb": None
        }
        
        if not hasattr(self, 'smoothed_landmark_pos') or not self.smoothed_landmark_pos:
            return False, (False, False, False), positions
        
        # 스무딩된 랜드마크를 사용하여 캘리브레이션 확인
        smoothed = self.smoothed_landmark_pos
        
        def dist(p1, p2):
            return np.linalg.norm(np.array(p1) - np.array(p2))
        
        target_h = calib_targets["head"]
        target_l = calib_targets["left_fist"]
        target_r = calib_targets["right_fist"]
        
        # 머리 확인
        nose_pos = smoothed.get("nose")
        head_ok = False
        if nose_pos:
            head_ok = dist(nose_pos, target_h["pos"]) < target_h["radius"]
        
        # 손의 중앙점을 사용하여 캘리브레이션 확인
        mode = int(self.config_rules.get("spatial_judge_mode", 2))
        if mode == 1:
            left_keys = ["left_wrist"]
            right_keys = ["right_wrist"]
        else:
            left_keys = ["left_wrist", "left_pinky", "left_index", "left_thumb"]
            right_keys = ["right_wrist", "right_pinky", "right_index", "right_thumb"]
        
        def calc_centroid(keys):
            pts = [smoothed.get(k) for k in keys]
            valid_points = [p for p in pts if p is not None]
            if not valid_points:
                return None
            xs = [p[0] for p in valid_points]
            ys = [p[1] for p in valid_points]
            return (np.mean(xs), np.mean(ys))
        
        left_fist_center = calc_centroid(left_keys)
        right_fist_center = calc_centroid(right_keys)
        
        # 왼쪽 펀치 타겟은 실제 왼손으로, 오른쪽 펀치 타겟은 실제 오른손으로 확인
        lw_ok = False
        rw_ok = False
        
        if left_fist_center:  # 왼쪽 펀치 타겟 -> 실제 왼손 사용
            lw_ok = dist(left_fist_center, target_l["pos"]) < target_l["radius"]
        
        if right_fist_center:  # 오른쪽 펀치 타겟 -> 실제 오른손 사용
            rw_ok = dist(right_fist_center, target_r["pos"]) < target_r["radius"]
        
        all_ok = head_ok and lw_ok and rw_ok
        
        # raw_landmark_pos는 smoothed_landmark_pos를 사용 (실제로는 스무딩된 값)
        raw_landmark_pos = smoothed.copy()
        
        return all_ok, (head_ok, lw_ok, rw_ok), raw_landmark_pos