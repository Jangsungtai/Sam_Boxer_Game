import cv2
import numpy as np

# --- (수정) 하드코딩된 COLORS 딕셔너리 삭제 ---

class Note:
    # --- (수정) __init__에서 hit_zone 제거 ---
    def __init__(self, item, width, height, duck_line_y, pre_spawn_time, config_colors, judge_timing, test_mode, config_note_styles=None):
        self.t = item["t"]
        self.typ = item["type"]
        self.lane = item.get("lane", "C")
        self.pre_spawn = pre_spawn_time
        
        self.hit = False
        self.missed = False
        self.judge_result = None  # 판정 결과 저장 (timing, area, area/timing, PERFECT, GREAT, GOOD 등)
        
        self.width = width
        self.height = height
        # self.hit_zone = hit_zone # (제거)
        self.duck_line_y = duck_line_y
        
        # --- (수정) config에서 색상 가져오기 ---
        self.color = tuple(config_colors.get(self.typ, [255, 255, 255]))
        # --- (수정 끝) ---

        # 표시용 숫자 라벨 (리듬 맵핑: 1=JAB_L, 2=JAB_R, 3=DUCK, 4=BOMB)
        type_to_label = {"JAB_L": "1", "JAB_R": "2", "DUCK": "3", "BOMB": "4"}
        self.label = type_to_label.get(self.typ)

        # --- (추가) 스타일 설정 (ui.json의 styles.notes) ---
        styles = config_note_styles or {}
        self.circle_radius = int(styles.get("circle_radius", 30))
        self.circle_outline_thickness = int(styles.get("circle_outline_thickness", 3))
        self.duck_half_width = int(styles.get("duck_half_width", 200))
        self.duck_half_height = int(styles.get("duck_half_height", 15))
        self.duck_outline_thickness = int(styles.get("duck_outline_thickness", 2))
        self.label_font_scale_circle = float(styles.get("label_font_scale_circle", 0.9))
        self.label_font_scale_duck = float(styles.get("label_font_scale_duck", 0.8))
        self.label_outline_thickness = int(styles.get("label_outline_thickness", 3))
        self.label_fill_thickness = int(styles.get("label_fill_thickness", 2))
        
        # --- (추가) 판정 시간과 테스트 모드 저장 ---
        self.judge_timing = judge_timing
        self.test_mode = test_mode

        # (시작 위치 설정)
        # (참고: 시작 위치는 여전히 고정된 값을 기준으로 함)
        temp_tx, temp_ty = int(width * 0.5), int(height * 0.6) # 임시 타겟 (스폰 위치 계산용)
        
        if self.typ == "JAB_L": self.x0, self.y0 = -100, temp_ty
        elif self.typ == "JAB_R": self.x0, self.y0 = width + 100, temp_ty
        elif self.typ == "DUCK": self.x0, self.y0 = temp_tx, -100
        elif self.typ == "BOMB":
            self.x0, self.y0 = -100 if self.lane == "L" else width + 100, temp_ty
        else: self.x0, self.y0 = temp_tx, temp_ty
        self.x, self.y = self.x0, self.y0

    def get_progress(self, now, start_time):
        # (2단계와 동일)
        spawn_time = start_time + self.t - self.pre_spawn
        if now < spawn_time: return 0.0
        prog = (now - spawn_time) / self.pre_spawn
        return np.clip(prog, 0.0, 1.0)

    # --- (수정) update_and_draw가 동적 hit_zone을 인자로 받음 ---
    def update_and_draw(self, frame, now, start_time, dynamic_hit_zone):
        # 판정 결과가 있는 경우 노트 위치 계산 및 판정 결과 표시
        if self.hit or self.missed:
            # 판정 결과 표시를 위해 위치 계산
            prog = self.get_progress(now, start_time)
            tx, ty = dynamic_hit_zone
            if self.typ == "DUCK":
                self.x = int((1 - prog) * self.x0 + prog * tx)
                self.y = int((1 - prog) * self.y0 + prog * self.duck_line_y)
            else:
                self.x = int((1 - prog) * self.x0 + prog * tx)
                self.y = int((1 - prog) * self.y0 + prog * ty)
            
            # 판정 결과 표시 (timing, area, area/timing만 표시)
            if self.judge_result and self.judge_result in ["timing", "area", "area/timing"]:
                font = cv2.FONT_HERSHEY_SIMPLEX
                text = self.judge_result
                font_scale = 0.6
                thickness = 2
                (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
                text_x = int(self.x - text_w / 2)
                text_y = int(self.y - self.circle_radius - 10) if self.typ != "DUCK" else int(self.y - self.duck_half_height - 10)
                
                # 판정 결과 색상 (기본 빨간색)
                color = (0, 0, 255)
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)
            
            return

        prog = self.get_progress(now, start_time)
        
        # (수정) self.hit_zone 대신 dynamic_hit_zone 사용
        tx, ty = dynamic_hit_zone 
        
        if self.typ == "DUCK":
            self.x = int((1 - prog) * self.x0 + prog * tx) # DUCK 노트도 X좌표는 타겟을 따라감
            self.y = int((1 - prog) * self.y0 + prog * self.duck_line_y)
        else:
            self.x = int((1 - prog) * self.x0 + prog * tx)
            self.y = int((1 - prog) * self.y0 + prog * ty)

        # --- (수정) 하드코딩 대신 self.color 사용 ---
        outline_color = (255, 255, 255)  # 기본 흰색
        
        if self.test_mode:
            t_game = now - start_time
            dt = t_game - self.t
            if abs(dt) <= self.judge_timing.get("good", 1.0):
                outline_color = (0, 0, 255)  # 빨간색
        
        if self.typ == "DUCK":
            cv2.rectangle(frame, (self.x - self.duck_half_width, self.y - self.duck_half_height), (self.x + self.duck_half_width, self.y + self.duck_half_height), self.color, -1)
            cv2.rectangle(frame, (self.x - self.duck_half_width, self.y - self.duck_half_height), (self.x + self.duck_half_width, self.y + self.duck_half_height), outline_color, self.duck_outline_thickness)
        else:
            cv2.circle(frame, (self.x, self.y), self.circle_radius, self.color, -1)
            cv2.circle(frame, (self.x, self.y), self.circle_radius, outline_color, self.circle_outline_thickness)
        
        # 숫자 라벨 그리기 (노트 중앙 정렬)
        if self.label:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = self.label_font_scale_circle if self.typ != "DUCK" else self.label_font_scale_duck
            thickness_outline = self.label_outline_thickness
            thickness_fill = self.label_fill_thickness
            (text_w, text_h), _ = cv2.getTextSize(self.label, font, font_scale, thickness_fill)
            text_x = int(self.x - text_w / 2)
            # baseline 보정: 텍스트는 기준선 기준으로 그려지므로 약간 아래로 이동
            text_y = int(self.y + text_h / 2) 
            # 외곽선
            cv2.putText(frame, self.label, (text_x, text_y), font, font_scale, (255, 255, 255), thickness_outline, cv2.LINE_AA)
            # 내부 채움
            cv2.putText(frame, self.label, (text_x, text_y), font, font_scale, (0, 0, 0), thickness_fill, cv2.LINE_AA)
    # --- (수정 끝) ---