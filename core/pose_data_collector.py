"""포즈 데이터 수집 및 CSV 저장 모듈 (테스트 모드 전용)"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class PoseDataCollector:
    """테스트 모드에서 포즈 데이터를 수집하고 CSV 파일로 저장하는 클래스."""

    def __init__(self, test_mode: bool = False) -> None:
        """
        Args:
            test_mode: 테스트 모드 활성화 여부
        """
        self.test_mode = test_mode
        self.collected_data: List[Dict[str, Any]] = []
        self.output_dir = "data/pose_data"
        self._saved: bool = False  # 저장 완료 플래그 (중복 저장 방지)
        
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)

    def collect_data(self, note_type: str, pose_data: Dict[str, Any]) -> None:
        """
        노트 타입과 포즈 데이터를 수집합니다.
        
        Args:
            note_type: 노트 타입 (GUARD, JAB_L, JAB_R, WEAVE_L, WEAVE_R)
            pose_data: 포즈 판정 데이터 딕셔너리
        """
        if not self.test_mode:
            return
        
        # 노트 타입 매핑 (표시용)
        note_type_mapping = {
            "GUARD": "GUARD",
            "JAB_L": "JAB_L",
            "JAB_R": "STRAIGHT_R",
            "WEAVE_L": "WEAVE_L",
            "WEAVE_R": "WEAVE_R",
        }
        
        # 데이터 행 생성 (각 필드를 개별 컬럼으로 저장)
        row_data = {
            "Note_Type": note_type_mapping.get(note_type, note_type),
            "left_fist_dist": pose_data.get("left_fist_dist", ""),
            "left_fist_angle": pose_data.get("left_fist_angle", ""),
            "right_fist_dist": pose_data.get("right_fist_dist", ""),
            "right_fist_angle": pose_data.get("right_fist_angle", ""),
            "left_arm_angle": pose_data.get("left_arm_angle", ""),
            "right_arm_angle": pose_data.get("right_arm_angle", ""),
            "nose_position": pose_data.get("nose_position", ""),
            "nose_above_shoulder": 1 if pose_data.get("nose_above_shoulder", False) else 0,
        }
        
        self.collected_data.append(row_data)

    def save_to_csv(self) -> Optional[str]:
        """
        수집된 데이터를 CSV 파일로 저장합니다.
        
        Returns:
            저장된 파일 경로, 실패 시 None
        """
        # 이미 저장되었으면 중복 저장 방지
        if self._saved:
            print(f"[PoseDataCollector] 이미 저장된 데이터입니다. 중복 저장을 건너뜁니다.")
            return None
        
        if not self.test_mode or not self.collected_data:
            if not self.test_mode:
                print(f"[PoseDataCollector] 테스트 모드가 아닙니다.")
            if not self.collected_data:
                print(f"[PoseDataCollector] 저장할 데이터가 없습니다.")
            return None
        
        # 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pose_data_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # CSV 컬럼 순서
            fieldnames = [
                "Note_Type",
                "left_fist_dist",
                "left_fist_angle",
                "right_fist_dist",
                "right_fist_angle",
                "left_arm_angle",
                "right_arm_angle",
                "nose_position",
                "nose_above_shoulder",
            ]
            
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.collected_data)
            
            self._saved = True  # 저장 완료 플래그 설정
            print(f"[PoseDataCollector] 데이터 저장 완료: {filepath} ({len(self.collected_data)}개 행)")
            return filepath
        except Exception as e:
            print(f"[PoseDataCollector] CSV 저장 실패: {e}")
            return None

    def clear_data(self) -> None:
        """수집된 데이터를 초기화합니다."""
        self.collected_data = []
        self._saved = False  # 저장 플래그도 초기화

