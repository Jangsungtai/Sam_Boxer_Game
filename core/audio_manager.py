#모든 사운드 로딩과 재생을 전담할 AudioManager 클래스

import pygame
import os

class AudioManager:
    def __init__(self):
        # 믹서 초기화 (main.py에서 pygame.init()을 먼저 호출해야 함)
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512) # 레이턴시 감소 설정
            pygame.mixer.init()
            print("Audio Manager: Pygame Mixer 초기화 성공")
        except Exception as e:
            print(f"오류: Pygame Mixer 초기화 실패. 사운드 없이 진행합니다. {e}")
            self.mixer_loaded = False
            return
            
        self.mixer_loaded = True
        self.sounds = {} # 효과음 캐시

    def load_sounds(self, sound_map):
        """
        sound_map: {"판정이름": "파일이름.wav", ...}
        예: {"PERFECT": "hit_perfect.wav", "MISS": "miss.wav"}
        """
        if not self.mixer_loaded:
            return
            
        print("Loading sounds...")
        for name, filename in sound_map.items():
            path = os.path.join("assets/sounds", filename)
            if not os.path.exists(path):
                print(f"  [경고] 효과음 파일 없음: {path}")
                continue
                
            try:
                self.sounds[name] = pygame.mixer.Sound(path)
                print(f"  [성공] {name} -> {filename}")
            except Exception as e:
                print(f"  [실패] {name} 로드 실패: {e}")

    def play_sfx(self, name):
        """효과음을 재생합니다."""
        if not self.mixer_loaded or name not in self.sounds:
            return
            
        try:
            # 기존 소리가 나고 있으면 중지하고 새로 재생 (타격감 향상)
            self.sounds[name].stop() 
            self.sounds[name].play()
        except Exception as e:
            print(f"SFX 재생 오류: {name}, {e}")

    def load_music(self, music_path):
        """배경 음악을 로드합니다."""
        if not self.mixer_loaded or not os.path.exists(music_path):
            print(f"[경고] 음악 파일 없음: {music_path}")
            return False
            
        try:
            pygame.mixer.music.load(music_path)
            print(f"Music loaded: {music_path}")
            return True
        except Exception as e:
            print(f"음악 로드 실패: {e}")
            return False

    def play_music(self):
        """배경 음악을 1회 재생합니다."""
        if not self.mixer_loaded:
            return
        try:
            pygame.mixer.music.play(0) # 0 = 1번만 재생
        except Exception as e:
            print(f"음악 재생 실패: {e}")

    def stop_music(self):
        """배경 음악을 정지합니다."""
        if not self.mixer_loaded:
            return
        pygame.mixer.music.stop()