# beat_boxer_game/constants.py

# ============================================================================
# 게임 해상도 및 화면 설정
# ============================================================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Beat Boxer"

# ============================================================================
# 비트 및 판정 시간 설정 (초)
# ============================================================================

BEAT_TIME = 0.5  # 비트가 생성되어 판정선에 도달하는 데 걸리는 시간
JUDGMENT_WINDOW = 0.2  # HIT 판정 시간 범위 (예: 0.2초)

# ============================================================================
# UI 위치 및 크기 설정
# ============================================================================

# 기본 원형 비트 위치
CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2

# Dodge 라인 관련 UI 위치 (수직선 3개)
# Dodge 라인은 중앙선을 중심으로 좌우에 위치하며, 중앙선은 판정선(JUDGMENT_Y)에 대응
DODGE_CENTER_LINE_X = CENTER_X  # 중앙 센터 라인 (빨간색)
DODGE_LINE_OFFSET = 180         # 중앙선으로부터 좌우 위빙 라인까지의 거리
DODGE_LEFT_LINE_X = CENTER_X - DODGE_LINE_OFFSET  # 위빙 R 판정 영역의 좌측 경계
DODGE_RIGHT_LINE_X = CENTER_X + DODGE_LINE_OFFSET  # 위빙 L 판정 영역의 우측 경계

DODGE_LINE_Y_TOP = SCREEN_HEIGHT * 0.9    # Dodge 라인이 시작되는 상단 Y 좌표
DODGE_LINE_Y_BOTTOM = SCREEN_HEIGHT * 0.1  # Dodge 라인이 끝나는 하단 Y 좌표

# 비트 생성 시작 및 판정 위치
BEAT_START_Y = DODGE_LINE_Y_BOTTOM * 0.8  # 펀치 비트가 생성되는 화면 하단 Y 좌표
BEAT_JUDGMENT_Y = SCREEN_HEIGHT * 0.45    # 펀치 비트의 최종 판정 위치 (기존 센터 원 위치)

# ============================================================================
# BEAT 유형 및 포즈 랜드마크 매핑
# ============================================================================

# 새로운 비트 유형 정의 (상대방 펀치 회피용)
BEAT_JAB_L = 1  # 잽 (왼손)
BEAT_JAB_R = 2  # 잽 (오른손)
BEAT_WEAVE_L = 3  # 위빙 (왼쪽으로 피하기)
BEAT_WEAVE_R = 4  # 위빙 (오른쪽으로 피하기)

ALL_BEAT_TYPES = [BEAT_JAB_L, BEAT_JAB_R, BEAT_WEAVE_L, BEAT_WEAVE_R]

# 포즈 랜드마크 인덱스 (MediaPipe Pose 기준)
NOSE_LANDMARK = 0
LEFT_HAND_LANDMARK = 15  # Left Wrist
RIGHT_HAND_LANDMARK = 16  # Right Wrist

# ============================================================================
# 색상 정의 (RGB)
# ============================================================================

COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_BACKGROUND = (0, 0, 0)
COLOR_DODGE_LINE = COLOR_RED  # Dodge 라인 색상 (빨간색)
COLOR_WEAVE_AREA = (255, 0, 0, 60)  # 위빙 판정 영역의 투명한 빨간색

