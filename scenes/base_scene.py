# scenes/base_scene.py

class BaseScene:
    """
    모든 씬의 부모가 되는 기본 클래스.
    이 클래스를 상속받는 모든 씬은
    handle_event, update, draw 메서드를 구현해야 합니다.
    """
    def __init__(self, screen, audio_manager, config):
        self.screen = screen # OpenCV 프레임 (영상)
        self.audio_manager = audio_manager
        self.config = config # config 딕셔너리
        self.next_scene_name = None # 다음 씬으로 전환할 때 사용
        self.persistent_data = {} # 씬 간에 전달할 데이터 (예: 최종 점수)

    # --- (수정) 'event' 객체 대신 'key' (정수)를 받음 ---
    def handle_event(self, key):
        """키보드 입력을 처리합니다 (OpenCV key code)."""
        pass
    # --- (수정 끝) ---

    def update(self, frame, now):
        """매 프레임 게임 로직을 업데이트합니다."""
        pass

    def draw(self, frame):
        """화면에 UI를 그립니다."""
        pass

    def startup(self, persistent_data):
        """씬이 시작될 때 이전 씬에서 데이터를 받습니다."""
        self.persistent_data = persistent_data
        # 씬 시작 시 next_scene_name 초기화
        self.next_scene_name = None 

    def cleanup(self):
        """씬이 종료될 때 데이터를 반환합니다."""
        self.next_scene_name = None # 다음 씬 이름 초기화
        return self.persistent_data