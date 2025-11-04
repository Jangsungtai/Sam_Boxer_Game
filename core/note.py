import cv2
import numpy as np

# --- (수정) 하드코딩된 COLORS 딕셔너리 삭제 ---

class Note:
    # --- (수정) __init__에서 hit_zone 제거 ---
    def __init__(self, item, width, height, duck_line_y, pre_spawn_time, config_colors):
        self.t = item["t"]
        self.typ = item["type"]
        self.lane = item.get("lane", "C")
        self.pre_spawn = pre_spawn_time
        
        self.hit = False
        self.missed = False
        
        self.width = width
        self.height = height
        # self.hit_zone = hit_zone # (제거)
        self.duck_line_y = duck_line_y
        
        # --- (수정) config에서 색상 가져오기 ---
        self.color = tuple(config_colors.get(self.typ, [255, 255, 255]))
        # --- (수정 끝) ---

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
        if self.hit or self.missed:
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
        if self.typ == "DUCK":
            cv2.rectangle(frame, (self.x - 200, self.y - 15), (self.x + 200, self.y + 15), self.color, -1)
            cv2.rectangle(frame, (self.x - 200, self.y - 15), (self.x + 200, self.y + 15), (255,255,255), 2)
        else:
            cv2.circle(frame, (self.x, self.y), 30, self.color, -1)
            cv2.circle(frame, (self.x, self.y), 30, (255, 255, 255), 3)
    # --- (수정 끝) ---