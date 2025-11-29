#!/usr/bin/env python3
"""
1단계: 고급자세 기준 정의
상급자 데이터를 분석하여 각 포즈 타입별 기준 포즈 벡터(Centroid)를 추출합니다.
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import matplotlib
from math import pi
matplotlib.use('Agg')  # GUI 없이 사용

# 한글 폰트 설정 (macOS)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
POSE_DATA_FILE = DATA_DIR / "pose_data" / "상급자 Sample1.csv"
BEGINNER_DATA_FILE = DATA_DIR / "pose_data" / "초심자 Sample1.csv"
OUTPUT_JSON = DATA_DIR / "pose_standards.json"
OUTPUT_PLOT = REPORTS_DIR / "pose_analysis.png"
OUTPUT_RADAR = REPORTS_DIR / "1.0_pose_radar_chart.png"
OUTPUT_BEGINNER_RADAR = REPORTS_DIR / "2.0_pose_radar_chart.png"

# 포즈 타입
POSE_TYPES = ["GUARD", "JAB_L", "STRAIGHT_R", "WEAVE_L", "WEAVE_R"]

# 8개 변수
VARIABLES = [
    "left_fist_dist",
    "left_fist_angle",
    "right_fist_dist",
    "right_fist_angle",
    "left_arm_angle",
    "right_arm_angle",
    "nose_position",
    "nose_above_shoulder"
]

# 변수 한글 레이블
VARIABLE_LABELS = {
    "left_fist_dist": "왼손 거리",
    "left_fist_angle": "왼손 각도",
    "right_fist_dist": "오른손 거리",
    "right_fist_angle": "오른손 각도",
    "left_arm_angle": "왼팔 각도",
    "right_arm_angle": "오른팔 각도",
    "nose_position": "코 위치",
    "nose_above_shoulder": "코가 어깨 위"
}


def remove_outliers_iqr(df, columns):
    """IQR 기반 이상치 제거"""
    df_clean = df.copy()
    for col in columns:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df_clean = df_clean[(df_clean[col] >= lower_bound) & (df_clean[col] <= upper_bound)]
    return df_clean


def find_optimal_k(data, k_range=[1, 2, 3]):
    """Silhouette Score를 사용하여 최적 K 탐색"""
    if len(data) < 2:
        return 1, {}
    
    results = {}
    best_k = 1
    best_score = -1
    
    for k in k_range:
        if len(data) < k:
            continue
        
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(data)
            
            if k == 1:
                # K=1일 때는 Silhouette Score를 계산할 수 없으므로 0으로 설정
                score = 0.0
            else:
                score = silhouette_score(data, labels)
            
            results[k] = {
                "silhouette_score": float(score),
                "centroid": kmeans.cluster_centers_[0].tolist() if k == 1 else kmeans.cluster_centers_.tolist(),
                "inertia": float(kmeans.inertia_)
            }
            
            if score > best_score:
                best_score = score
                best_k = k
        except Exception as e:
            print(f"K={k} 처리 중 오류: {e}")
            continue
    
    return best_k, results


def create_visualizations(pose_data_dict, centroids_dict):
    """포즈 타입별 변수 분포 시각화 (박스플롯 + 히스토그램)"""
    n_poses = len(POSE_TYPES)
    n_vars = len(VARIABLES)
    
    # 전체 그림 크기 설정
    fig = plt.figure(figsize=(20, 4 * n_poses))
    
    for pose_idx, pose_type in enumerate(POSE_TYPES):
        if pose_type not in pose_data_dict:
            continue
        
        data = pose_data_dict[pose_type]
        centroid = centroids_dict.get(pose_type, {})
        
        # 각 변수에 대해 박스플롯과 히스토그램 생성
        for var_idx, var in enumerate(VARIABLES):
            if var not in data.columns:
                continue
            
            # 박스플롯
            ax1 = plt.subplot(n_poses, n_vars * 2, pose_idx * n_vars * 2 + var_idx * 2 + 1)
            bp = ax1.boxplot(data[var].values, vert=True, patch_artist=True)
            bp['boxes'][0].set_facecolor('lightblue')
            bp['boxes'][0].set_alpha(0.7)
            
            # Centroid 값 표시
            has_centroid = False
            if pose_type in centroid and var in centroid[pose_type]:
                centroid_value = centroid[pose_type][var]
                ax1.axhline(y=centroid_value, color='red', linestyle='--', linewidth=2, label='Centroid')
                ax1.scatter([1], [centroid_value], color='red', s=100, zorder=5, marker='*')
                has_centroid = True
            
            ax1.set_title(f'{pose_type} - {var}', fontsize=10, fontweight='bold')
            ax1.set_ylabel('값', fontsize=9)
            ax1.grid(True, alpha=0.3)
            if var_idx == 0 and has_centroid:
                ax1.legend(fontsize=8)
            
            # 히스토그램
            ax2 = plt.subplot(n_poses, n_vars * 2, pose_idx * n_vars * 2 + var_idx * 2 + 2)
            ax2.hist(data[var].values, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
            
            # Centroid 값 표시
            has_centroid = False
            if pose_type in centroid and var in centroid[pose_type]:
                centroid_value = centroid[pose_type][var]
                ax2.axvline(x=centroid_value, color='red', linestyle='--', linewidth=2, label='Centroid')
                has_centroid = True
            
            ax2.set_xlabel('값', fontsize=9)
            ax2.set_ylabel('빈도', fontsize=9)
            ax2.grid(True, alpha=0.3)
            if var_idx == 0 and has_centroid:
                ax2.legend(fontsize=8)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT, dpi=300, bbox_inches='tight')
    print(f"시각화 저장: {OUTPUT_PLOT}")
    plt.close()


def normalize_value(value, min_val, max_val):
    """Min-Max 정규화 (0-1 범위)"""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def create_radar_chart(centroids_dict, all_data_dict, output_file=None):
    """정규화된 Centroid 패턴을 레이더 차트로 시각화"""
    if output_file is None:
        output_file = OUTPUT_RADAR
    # 모든 데이터에서 각 변수의 최소/최대값 계산 (정규화용)
    min_max_values = {}
    for var in VARIABLES:
        all_values = []
        for pose_type in POSE_TYPES:
            if pose_type in all_data_dict:
                if var in all_data_dict[pose_type].columns:
                    all_values.extend(all_data_dict[pose_type][var].values)
        if all_values:
            min_max_values[var] = {
                'min': min(all_values),
                'max': max(all_values)
            }
    
    # 레이더 차트 설정
    angles = [n / float(len(VARIABLES)) * 2 * pi for n in range(len(VARIABLES))]
    angles += angles[:1]  # 닫힌 형태로 만들기
    
    # 변수 레이블 (레이더 차트용 순서 조정)
    # 12시부터 시계방향: 오른손 각도 -> 오른손 거리 -> 왼손 각도 -> 왼손 거리 -> 코가 어깨 위 -> 코 위치 -> 오른팔 각도 -> 왼팔 각도
    radar_variables = [
        "right_fist_angle",      # 오른손 각도 (12시 방향)
        "right_fist_dist",       # 오른손 거리 (1-2시 방향)
        "left_fist_angle",       # 왼손 각도 (3시 방향)
        "left_fist_dist",        # 왼손 거리 (4-5시 방향)
        "nose_above_shoulder",   # 코가 어깨 위 (6시 방향)
        "nose_position",         # 코 위치 (7-8시 방향)
        "right_arm_angle",       # 오른팔 각도 (9시 방향)
        "left_arm_angle"         # 왼팔 각도 (10-11시 방향)
    ]
    
    # 한글 레이블
    radar_labels = [VARIABLE_LABELS[var] for var in radar_variables]
    
    # 그림 생성
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection='polar'))
    
    # 색상 설정
    colors = {
        'GUARD': 'red',
        'JAB_L': 'blue',
        'STRAIGHT_R': 'green',
        'WEAVE_L': 'purple',
        'WEAVE_R': 'orange'
    }
    
    # 각 포즈 타입별로 레이더 차트 그리기
    for pose_type in POSE_TYPES:
        if pose_type not in centroids_dict:
            continue
        
        centroid = centroids_dict[pose_type]
        values = []
        
        for var in radar_variables:
            if var in centroid:
                # 정규화
                if var in min_max_values:
                    norm_value = normalize_value(
                        centroid[var],
                        min_max_values[var]['min'],
                        min_max_values[var]['max']
                    )
                else:
                    norm_value = 0.5
                values.append(norm_value)
            else:
                values.append(0.0)
        
        values += values[:1]  # 닫힌 형태로 만들기
        
        # 레이더 차트 그리기
        ax.plot(angles, values, 'o-', linewidth=2, label=pose_type, color=colors[pose_type])
        ax.fill(angles, values, alpha=0.25, color=colors[pose_type])
    
    # 축 레이블 설정
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_labels, fontsize=10)
    
    # y축 설정 (0-1 범위)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(['0.25', '0.5', '0.75', '1.0'], fontsize=8)
    ax.grid(True)
    
    # 제목 및 범례
    plt.title('Normalized Centroid Pattern (Radar Chart)', size=16, fontweight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"레이더 차트 저장: {output_file}")
    plt.close()


def create_individual_radar_charts(centroids_dict, all_data_dict, prefix="1"):
    """각 포즈 타입별로 개별 레이더 차트 생성"""
    # 모든 데이터에서 각 변수의 최소/최대값 계산 (정규화용)
    min_max_values = {}
    for var in VARIABLES:
        all_values = []
        for pose_type in POSE_TYPES:
            if pose_type in all_data_dict:
                if var in all_data_dict[pose_type].columns:
                    all_values.extend(all_data_dict[pose_type][var].values)
        if all_values:
            min_max_values[var] = {
                'min': min(all_values),
                'max': max(all_values)
            }
    
    # 변수 레이블 (레이더 차트용 순서)
    # 12시부터 시계방향: 오른손 각도 -> 오른손 거리 -> 왼손 각도 -> 왼손 거리 -> 코가 어깨 위 -> 코 위치 -> 오른팔 각도 -> 왼팔 각도
    radar_variables = [
        "right_fist_angle",      # 오른손 각도 (12시 방향)
        "right_fist_dist",       # 오른손 거리 (1-2시 방향)
        "left_fist_angle",       # 왼손 각도 (3시 방향)
        "left_fist_dist",        # 왼손 거리 (4-5시 방향)
        "nose_above_shoulder",   # 코가 어깨 위 (6시 방향)
        "nose_position",         # 코 위치 (7-8시 방향)
        "right_arm_angle",       # 오른팔 각도 (9시 방향)
        "left_arm_angle"         # 왼팔 각도 (10-11시 방향)
    ]
    
    # 포즈 타입별 파일명 매핑
    pose_file_mapping = {
        'GUARD': f'{prefix}.1_pose_radar_chart_guard.png',
        'JAB_L': f'{prefix}.2_pose_radar_chart_jab_l.png',
        'STRAIGHT_R': f'{prefix}.3_pose_radar_chart_straight_r.png',
        'WEAVE_L': f'{prefix}.4_pose_radar_chart_weave_l.png',
        'WEAVE_R': f'{prefix}.5_pose_radar_chart_weave_r.png'
    }
    
    # 색상 설정
    colors = {
        'GUARD': 'red',
        'JAB_L': 'blue',
        'STRAIGHT_R': 'green',
        'WEAVE_L': 'purple',
        'WEAVE_R': 'orange'
    }
    
    # 각 포즈 타입별로 개별 레이더 차트 생성
    for pose_type in POSE_TYPES:
        if pose_type not in centroids_dict:
            continue
        
        centroid = centroids_dict[pose_type]
        
        # 레이더 차트 설정
        angles = [n / float(len(radar_variables)) * 2 * pi for n in range(len(radar_variables))]
        angles += angles[:1]  # 닫힌 형태로 만들기
        
        values = []
        for var in radar_variables:
            if var in centroid:
                # 정규화
                if var in min_max_values:
                    norm_value = normalize_value(
                        centroid[var],
                        min_max_values[var]['min'],
                        min_max_values[var]['max']
                    )
                else:
                    norm_value = 0.5
                values.append(norm_value)
            else:
                values.append(0.0)
        
        values += values[:1]  # 닫힌 형태로 만들기
        
        # 그림 생성
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # 레이더 차트 그리기
        ax.plot(angles, values, 'o-', linewidth=3, label=pose_type, color=colors[pose_type])
        ax.fill(angles, values, alpha=0.3, color=colors[pose_type])
        
        # 한글 레이블
        radar_labels = [VARIABLE_LABELS[var] for var in radar_variables]
        
        # 축 레이블 설정
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(radar_labels, fontsize=11)
        
        # y축 설정 (0-1 범위)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(['0.25', '0.5', '0.75', '1.0'], fontsize=9)
        ax.grid(True, alpha=0.5)
        
        # 제목
        plt.title(f'{pose_type} - Normalized Centroid Pattern', size=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 파일 저장
        output_file = REPORTS_DIR / pose_file_mapping[pose_type]
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  {pose_type} 레이더 차트 저장: {output_file}")
        plt.close()


def create_comparison_radar_charts(expert_centroids_dict, beginner_centroids_dict, 
                                   expert_data_dict, beginner_data_dict):
    """상급자와 초심자의 Centroid를 같은 레이더 차트에 비교"""
    # 모든 데이터에서 각 변수의 최소/최대값 계산 (정규화용)
    min_max_values = {}
    for var in VARIABLES:
        all_values = []
        for pose_type in POSE_TYPES:
            if pose_type in expert_data_dict:
                if var in expert_data_dict[pose_type].columns:
                    all_values.extend(expert_data_dict[pose_type][var].values)
            if pose_type in beginner_data_dict:
                if var in beginner_data_dict[pose_type].columns:
                    all_values.extend(beginner_data_dict[pose_type][var].values)
        if all_values:
            min_max_values[var] = {
                'min': min(all_values),
                'max': max(all_values)
            }
    
    # 변수 레이블 (레이더 차트용 순서)
    # 12시부터 시계방향: 오른손 각도 -> 오른손 거리 -> 왼손 각도 -> 왼손 거리 -> 코가 어깨 위 -> 코 위치 -> 오른팔 각도 -> 왼팔 각도
    radar_variables = [
        "right_fist_angle",      # 오른손 각도 (12시 방향)
        "right_fist_dist",       # 오른손 거리 (1-2시 방향)
        "left_fist_angle",       # 왼손 각도 (3시 방향)
        "left_fist_dist",        # 왼손 거리 (4-5시 방향)
        "nose_above_shoulder",   # 코가 어깨 위 (6시 방향)
        "nose_position",         # 코 위치 (7-8시 방향)
        "right_arm_angle",       # 오른팔 각도 (9시 방향)
        "left_arm_angle"         # 왼팔 각도 (10-11시 방향)
    ]
    
    # 포즈 타입별 파일명 매핑
    pose_file_mapping = {
        'GUARD': '3.1_pose_radar_chart_comparison_guard.png',
        'JAB_L': '3.2_pose_radar_chart_comparison_jab_l.png',
        'STRAIGHT_R': '3.3_pose_radar_chart_comparison_straight_r.png',
        'WEAVE_L': '3.4_pose_radar_chart_comparison_weave_l.png',
        'WEAVE_R': '3.5_pose_radar_chart_comparison_weave_r.png'
    }
    
    # 각 포즈 타입별로 비교 레이더 차트 생성
    for pose_type in POSE_TYPES:
        if pose_type not in expert_centroids_dict and pose_type not in beginner_centroids_dict:
            continue
        
        # 레이더 차트 설정
        angles = [n / float(len(radar_variables)) * 2 * pi for n in range(len(radar_variables))]
        angles += angles[:1]  # 닫힌 형태로 만들기
        
        # 그림 생성
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # 상급자 데이터 그리기
        if pose_type in expert_centroids_dict:
            expert_centroid = expert_centroids_dict[pose_type]
            expert_values = []
            
            for var in radar_variables:
                if var in expert_centroid:
                    if var in min_max_values:
                        norm_value = normalize_value(
                            expert_centroid[var],
                            min_max_values[var]['min'],
                            min_max_values[var]['max']
                        )
                    else:
                        norm_value = 0.5
                    expert_values.append(norm_value)
                else:
                    expert_values.append(0.0)
            
            expert_values += expert_values[:1]  # 닫힌 형태로 만들기
            
            # 상급자는 빨간색
            ax.plot(angles, expert_values, 'o-', linewidth=3, label=f'{pose_type} (상급자)', color='red')
            ax.fill(angles, expert_values, alpha=0.2, color='red')
        
        # 초심자 데이터 그리기
        if pose_type in beginner_centroids_dict:
            beginner_centroid = beginner_centroids_dict[pose_type]
            beginner_values = []
            
            for var in radar_variables:
                if var in beginner_centroid:
                    if var in min_max_values:
                        norm_value = normalize_value(
                            beginner_centroid[var],
                            min_max_values[var]['min'],
                            min_max_values[var]['max']
                        )
                    else:
                        norm_value = 0.5
                    beginner_values.append(norm_value)
                else:
                    beginner_values.append(0.0)
            
            beginner_values += beginner_values[:1]  # 닫힌 형태로 만들기
            
            # 초심자는 파란색
            ax.plot(angles, beginner_values, 's-', linewidth=3, label=f'{pose_type} (초심자)', color='blue')
            ax.fill(angles, beginner_values, alpha=0.2, color='blue')
        
        # 한글 레이블
        radar_labels = [VARIABLE_LABELS[var] for var in radar_variables]
        
        # 축 레이블 설정
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(radar_labels, fontsize=11)
        
        # y축 설정 (0-1 범위)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(['0.25', '0.5', '0.75', '1.0'], fontsize=9)
        ax.grid(True, alpha=0.5)
        
        # 제목
        plt.title(f'{pose_type} - 상급자 vs 초심자 비교', size=16, fontweight='bold', pad=20)
        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
        
        plt.tight_layout()
        
        # 파일 저장
        output_file = REPORTS_DIR / pose_file_mapping[pose_type]
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  {pose_type} 비교 레이더 차트 저장: {output_file}")
        plt.close()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("1단계: 고급자세 기준 정의")
    print("=" * 60)
    
    # 디렉토리 생성
    REPORTS_DIR.mkdir(exist_ok=True)
    
    # 1. 데이터 로드
    print(f"\n[1] 데이터 로드: {POSE_DATA_FILE}")
    if not POSE_DATA_FILE.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {POSE_DATA_FILE}")
    
    df = pd.read_csv(POSE_DATA_FILE)
    print(f"   전체 데이터: {len(df)}개 행")
    
    # 2. 포즈 타입별 데이터 분리 및 전처리
    print("\n[2] 포즈 타입별 데이터 분리 및 IQR 이상치 제거")
    pose_data_dict = {}
    pose_data_clean_dict = {}
    
    for pose_type in POSE_TYPES:
        pose_df = df[df['Note_Type'] == pose_type].copy()
        print(f"   {pose_type}: {len(pose_df)}개 (이상치 제거 전)")
        
        if len(pose_df) == 0:
            continue
        
        # IQR 기반 이상치 제거
        pose_df_clean = remove_outliers_iqr(pose_df, VARIABLES)
        print(f"   {pose_type}: {len(pose_df_clean)}개 (이상치 제거 후)")
        
        pose_data_dict[pose_type] = pose_df
        pose_data_clean_dict[pose_type] = pose_df_clean
    
    # 3. 최적 K 탐색 및 Centroid 계산
    print("\n[3] 최적 K 탐색 (Silhouette Score 비교)")
    results_dict = {}
    centroids_dict = {}
    
    for pose_type in POSE_TYPES:
        if pose_type not in pose_data_clean_dict:
            continue
        
        data = pose_data_clean_dict[pose_type][VARIABLES].values
        
        if len(data) == 0:
            print(f"   {pose_type}: 데이터 없음")
            continue
        
        print(f"\n   {pose_type} 분석 중...")
        best_k, k_results = find_optimal_k(data, k_range=[1, 2, 3])
        
        print(f"   최적 K: {best_k}")
        for k, result in k_results.items():
            print(f"     K={k}: Silhouette Score = {result['silhouette_score']:.4f}")
        
        # 최적 K의 Centroid 추출
        if best_k in k_results:
            if best_k == 1:
                centroid_values = k_results[best_k]['centroid']
            else:
                # K>1일 때는 가장 큰 클러스터의 중심을 사용
                centroid_values = k_results[best_k]['centroid'][0]
            
            centroids_dict[pose_type] = {
                var: float(val) for var, val in zip(VARIABLES, centroid_values)
            }
        
        results_dict[pose_type] = {
            "optimal_k": best_k,
            "k_results": k_results,
            "data_count": len(data),
            "centroid": centroids_dict.get(pose_type, {})
        }
    
    # 4. JSON 저장
    print(f"\n[4] 결과 저장: {OUTPUT_JSON}")
    output_data = {
        "metadata": {
            "description": "상급자 데이터 기반 포즈 타입별 기준 포즈 벡터 (Centroid)",
            "data_source": str(POSE_DATA_FILE),
            "variables": VARIABLES,
            "pose_types": POSE_TYPES
        },
        "results": results_dict
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"   저장 완료: {len(results_dict)}개 포즈 타입")
    
    # 5. 시각화 생성
    print(f"\n[5] 시각화 생성")
    print(f"   박스플롯/히스토그램: {OUTPUT_PLOT}")
    create_visualizations(pose_data_clean_dict, centroids_dict)
    
    print(f"   전체 레이더 차트: {OUTPUT_RADAR}")
    create_radar_chart(centroids_dict, pose_data_clean_dict)
    
    print(f"   포즈별 개별 레이더 차트:")
    create_individual_radar_charts(centroids_dict, pose_data_clean_dict)
    
    # 6. 초심자 데이터 분석 및 레이더 차트 생성
    print(f"\n[6] 초심자 데이터 분석 및 레이더 차트 생성")
    if BEGINNER_DATA_FILE.exists():
        print(f"   초심자 데이터 로드: {BEGINNER_DATA_FILE}")
        beginner_df = pd.read_csv(BEGINNER_DATA_FILE)
        print(f"   전체 데이터: {len(beginner_df)}개 행")
        
        # 초심자 데이터에서도 Centroid 계산
        beginner_pose_data_dict = {}
        beginner_pose_data_clean_dict = {}
        beginner_centroids_dict = {}
        
        print(f"   포즈 타입별 데이터 분리 및 IQR 이상치 제거")
        for pose_type in POSE_TYPES:
            pose_df = beginner_df[beginner_df['Note_Type'] == pose_type].copy()
            if len(pose_df) == 0:
                continue
            
            print(f"   {pose_type}: {len(pose_df)}개 (이상치 제거 전)")
            pose_df_clean = remove_outliers_iqr(pose_df, VARIABLES)
            print(f"   {pose_type}: {len(pose_df_clean)}개 (이상치 제거 후)")
            
            beginner_pose_data_dict[pose_type] = pose_df
            beginner_pose_data_clean_dict[pose_type] = pose_df_clean
            
            # Centroid 계산 (K-Means 사용)
            if len(pose_df_clean) > 0:
                data = pose_df_clean[VARIABLES].values
                best_k, k_results = find_optimal_k(data, k_range=[1, 2, 3])
                
                if best_k in k_results:
                    if best_k == 1:
                        centroid_values = k_results[best_k]['centroid']
                    else:
                        centroid_values = k_results[best_k]['centroid'][0]
                    
                    beginner_centroids_dict[pose_type] = {
                        var: float(val) for var, val in zip(VARIABLES, centroid_values)
                    }
        
        # 초심자 레이더 차트 생성
        if beginner_centroids_dict:
            print(f"   초심자 전체 레이더 차트: {OUTPUT_BEGINNER_RADAR}")
            create_radar_chart(beginner_centroids_dict, beginner_pose_data_clean_dict, OUTPUT_BEGINNER_RADAR)
            
            print(f"   초심자 포즈별 개별 레이더 차트:")
            create_individual_radar_charts(beginner_centroids_dict, beginner_pose_data_clean_dict, prefix="2")
            
            # 7. 상급자 vs 초심자 비교 레이더 차트 생성
            print(f"\n[7] 상급자 vs 초심자 비교 레이더 차트 생성")
            create_comparison_radar_charts(
                centroids_dict, 
                beginner_centroids_dict,
                pose_data_clean_dict,
                beginner_pose_data_clean_dict
            )
        else:
            print(f"   초심자 데이터에서 Centroid를 계산할 수 없습니다.")
    else:
        print(f"   초심자 데이터 파일을 찾을 수 없습니다: {BEGINNER_DATA_FILE}")
    
    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"결과 파일:")
    print(f"  - {OUTPUT_JSON}")
    print(f"  - {OUTPUT_PLOT}")
    print(f"  - {OUTPUT_RADAR} (전체)")
    print(f"  - 1.1_pose_radar_chart_guard.png (GUARD)")
    print(f"  - 1.2_pose_radar_chart_jab_l.png (JAB_L)")
    print(f"  - 1.3_pose_radar_chart_straight_r.png (STRAIGHT_R)")
    print(f"  - 1.4_pose_radar_chart_weave_l.png (WEAVE_L)")
    print(f"  - 1.5_pose_radar_chart_weave_r.png (WEAVE_R)")
    if BEGINNER_DATA_FILE.exists():
        print(f"  - 2.0_pose_radar_chart.png (초심자 전체)")
        print(f"  - 2.1_pose_radar_chart_guard.png (초심자 GUARD)")
        print(f"  - 2.2_pose_radar_chart_jab_l.png (초심자 JAB_L)")
        print(f"  - 2.3_pose_radar_chart_straight_r.png (초심자 STRAIGHT_R)")
        print(f"  - 2.4_pose_radar_chart_weave_l.png (초심자 WEAVE_L)")
        print(f"  - 2.5_pose_radar_chart_weave_r.png (초심자 WEAVE_R)")
        print(f"  - 3.1_pose_radar_chart_comparison_guard.png (상급자 vs 초심자 GUARD)")
        print(f"  - 3.2_pose_radar_chart_comparison_jab_l.png (상급자 vs 초심자 JAB_L)")
        print(f"  - 3.3_pose_radar_chart_comparison_straight_r.png (상급자 vs 초심자 STRAIGHT_R)")
        print(f"  - 3.4_pose_radar_chart_comparison_weave_l.png (상급자 vs 초심자 WEAVE_L)")
        print(f"  - 3.5_pose_radar_chart_comparison_weave_r.png (상급자 vs 초심자 WEAVE_R)")


if __name__ == "__main__":
    main()

