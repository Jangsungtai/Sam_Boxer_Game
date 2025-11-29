#!/usr/bin/env python3
"""
3단계: 포즈품질 습관 평가
사용자 포즈 데이터를 분석하여 포즈 품질과 습관을 평가하고 종합 보고서를 생성합니다.
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 사용

# 한글 폰트 설정 (macOS)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports" / "3.report"
USER_DATA_FILE = DATA_DIR / "pose_data" / "초심자 Sample2.csv"
STANDARDS_FILE = DATA_DIR / "pose_standards.json"
WEIGHTS_FILE = DATA_DIR / "pose_evaluation_weights.json"
OUTPUT_JSON = REPORTS_DIR / "pose_quality_report.json"

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


def calculate_weighted_euclidean_distance(user_pose, centroid, weights):
    """가중 유클리드 거리 계산"""
    distance_squared = 0.0
    for var in VARIABLES:
        user_value = user_pose.get(var, 0.0)
        centroid_value = centroid.get(var, 0.0)
        weight = weights.get(var, 0.0)
        
        diff = user_value - centroid_value
        distance_squared += weight * (diff ** 2)
    
    return np.sqrt(distance_squared)


def distance_to_score(distance, max_distance=100.0):
    """거리를 점수로 변환 (0-100)"""
    # 거리를 정규화하여 점수로 변환
    # 거리가 0이면 100점, 거리가 max_distance 이상이면 0점
    # 지수 함수를 사용하여 더 부드러운 변환
    if distance <= 0:
        return 100.0
    elif distance >= max_distance:
        return 0.0
    else:
        # 지수 변환: distance가 클수록 점수가 빠르게 감소
        normalized = distance / max_distance
        score = 100 * np.exp(-2 * normalized)
        return max(0, min(100, score))


def analyze_pose_quality(user_df, standards_dict, weights_dict):
    """포즈 품질 분석"""
    results = {}
    
    for pose_type in POSE_TYPES:
        # 포즈 타입별 데이터 추출
        pose_data = user_df[user_df['Note_Type'] == pose_type].copy()
        
        if len(pose_data) == 0:
            continue
        
        # 기준 벡터와 가중치 가져오기
        if pose_type not in standards_dict['results']:
            continue
        if pose_type not in weights_dict['results']:
            continue
        
        centroid = standards_dict['results'][pose_type]['centroid']
        weights = weights_dict['results'][pose_type]['feature_importance']
        
        # 각 노트별 분석
        note_analyses = []
        distances = []
        scores = []
        variable_errors = defaultdict(list)
        
        for idx, row in pose_data.iterrows():
            user_pose = {
                var: row[var] for var in VARIABLES
            }
            
            # 가중 유클리드 거리 계산
            distance = calculate_weighted_euclidean_distance(user_pose, centroid, weights)
            score = distance_to_score(distance)
            
            distances.append(distance)
            scores.append(score)
            
            # 변수별 오차 계산
            variable_error = {}
            for var in VARIABLES:
                user_value = user_pose.get(var, 0.0)
                centroid_value = centroid.get(var, 0.0)
                error = user_value - centroid_value
                variable_error[var] = error
                variable_errors[var].append(error)
            
            note_analyses.append({
                'index': idx,
                'distance': float(distance),
                'score': float(score),
                'variable_errors': variable_error
            })
        
        # 통계 계산
        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        # 변수별 평균 오차
        mean_variable_errors = {
            var: float(np.mean(variable_errors[var])) 
            for var in VARIABLES
        }
        
        # 변수별 오차 표준편차
        std_variable_errors = {
            var: float(np.std(variable_errors[var])) 
            for var in VARIABLES
        }
        
        # 최대 오차 노트 찾기 (상위 5개)
        sorted_notes = sorted(note_analyses, key=lambda x: x['distance'], reverse=True)
        top_5_worst = sorted_notes[:5]
        
        # 최대 오차 노트에서 가장 크게 이탈한 변수 분석
        worst_variable_errors = defaultdict(list)
        for note in top_5_worst:
            for var, error in note['variable_errors'].items():
                worst_variable_errors[var].append(abs(error))
        
        worst_variables = sorted(
            worst_variable_errors.items(),
            key=lambda x: np.mean(x[1]),
            reverse=True
        )
        
        results[pose_type] = {
            'count': len(pose_data),
            'mean_distance': float(mean_distance),
            'std_distance': float(std_distance),
            'mean_score': float(mean_score),
            'std_score': float(std_score),
            'min_score': float(min_score),
            'max_score': float(max_score),
            'mean_variable_errors': mean_variable_errors,
            'std_variable_errors': std_variable_errors,
            'top_5_worst_notes': [
                {
                    'index': note['index'],
                    'distance': note['distance'],
                    'score': note['score'],
                    'variable_errors': note['variable_errors']
                }
                for note in top_5_worst
            ],
            'worst_variables': [
                {'variable': var, 'mean_abs_error': float(np.mean(errors))}
                for var, errors in worst_variables[:3]
            ],
            'note_analyses': note_analyses
        }
    
    return results


def create_visualizations(analysis_results):
    """시각화 생성"""
    # 1. 포즈 타입별 평균 점수 비교
    fig, ax = plt.subplots(figsize=(10, 6))
    pose_types = []
    mean_scores = []
    std_scores = []
    
    for pose_type in POSE_TYPES:
        if pose_type not in analysis_results:
            continue
        result = analysis_results[pose_type]
        pose_types.append(pose_type)
        mean_scores.append(result['mean_score'])
        std_scores.append(result['std_score'])
    
    bars = ax.bar(pose_types, mean_scores, yerr=std_scores, 
                  capsize=5, alpha=0.7, color='steelblue', edgecolor='black')
    
    # 값 표시
    for i, (mean, std) in enumerate(zip(mean_scores, std_scores)):
        ax.text(i, mean + std + 2, f'{mean:.1f}±{std:.1f}', 
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_ylabel('평균 점수', fontsize=12)
    ax.set_title('포즈 타입별 평균 품질 점수', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "3.1_mean_score_comparison.png", dpi=300, bbox_inches='tight')
    print(f"  평균 점수 비교 차트 저장: {REPORTS_DIR / '3.1_mean_score_comparison.png'}")
    plt.close()
    
    # 2. 포즈 타입별 점수 분포 (박스플롯)
    fig, ax = plt.subplots(figsize=(10, 6))
    score_data = []
    labels = []
    
    for pose_type in POSE_TYPES:
        if pose_type not in analysis_results:
            continue
        result = analysis_results[pose_type]
        scores = [note['score'] for note in result['note_analyses']]
        score_data.append(scores)
        labels.append(pose_type)
    
    bp = ax.boxplot(score_data, tick_labels=labels, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    ax.set_ylabel('품질 점수', fontsize=12)
    ax.set_title('포즈 타입별 점수 분포', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "3.2_score_distribution.png", dpi=300, bbox_inches='tight')
    print(f"  점수 분포 차트 저장: {REPORTS_DIR / '3.2_score_distribution.png'}")
    plt.close()
    
    # 3. 변수별 평균 오차 히트맵
    fig, ax = plt.subplots(figsize=(12, 6))
    
    error_matrix = []
    pose_type_list = []
    
    for pose_type in POSE_TYPES:
        if pose_type not in analysis_results:
            continue
        result = analysis_results[pose_type]
        errors = [result['mean_variable_errors'][var] for var in VARIABLES]
        error_matrix.append(errors)
        pose_type_list.append(pose_type)
    
    error_array = np.array(error_matrix)
    
    im = ax.imshow(error_array, cmap='RdBu_r', aspect='auto', vmin=-0.5, vmax=0.5)
    
    ax.set_xticks(np.arange(len(VARIABLES)))
    ax.set_yticks(np.arange(len(pose_type_list)))
    ax.set_xticklabels(VARIABLES, rotation=45, ha='right')
    ax.set_yticklabels(pose_type_list)
    
    # 값 표시
    for i in range(len(pose_type_list)):
        for j in range(len(VARIABLES)):
            value = error_array[i, j]
            text_color = 'white' if abs(value) > 0.25 else 'black'
            ax.text(j, i, f'{value:.3f}', ha='center', va='center', 
                   color=text_color, fontsize=8)
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('평균 오차', fontsize=11)
    
    ax.set_title('포즈 타입별 변수 평균 오차 히트맵', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('변수', fontsize=12)
    ax.set_ylabel('포즈 타입', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "3.3_variable_error_heatmap.png", dpi=300, bbox_inches='tight')
    print(f"  변수 오차 히트맵 저장: {REPORTS_DIR / '3.3_variable_error_heatmap.png'}")
    plt.close()
    
    # 4. 포즈 타입별 일관성 (표준편차) 비교
    fig, ax = plt.subplots(figsize=(10, 6))
    pose_types = []
    std_scores = []
    
    for pose_type in POSE_TYPES:
        if pose_type not in analysis_results:
            continue
        result = analysis_results[pose_type]
        pose_types.append(pose_type)
        std_scores.append(result['std_score'])
    
    bars = ax.bar(pose_types, std_scores, alpha=0.7, color='coral', edgecolor='black')
    
    # 값 표시
    for i, std in enumerate(std_scores):
        ax.text(i, std + 0.5, f'{std:.1f}', 
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_ylabel('점수 표준편차 (일관성)', fontsize=12)
    ax.set_title('포즈 타입별 일관성 비교 (낮을수록 일관적)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "3.4_consistency_comparison.png", dpi=300, bbox_inches='tight')
    print(f"  일관성 비교 차트 저장: {REPORTS_DIR / '3.4_consistency_comparison.png'}")
    plt.close()


def generate_report_text(analysis_results):
    """텍스트 보고서 생성"""
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("포즈 품질 종합 진단 보고서")
    report_lines.append("=" * 60)
    report_lines.append("")
    
    for pose_type in POSE_TYPES:
        if pose_type not in analysis_results:
            continue
        
        result = analysis_results[pose_type]
        report_lines.append(f"### {pose_type} 진단")
        report_lines.append("")
        report_lines.append(f"- **평균 점수**: {result['mean_score']:.1f}점")
        report_lines.append(f"- **점수 범위**: {result['min_score']:.1f} ~ {result['max_score']:.1f}점")
        report_lines.append(f"- **일관성**: 표준편차 {result['std_score']:.1f} ({'높음' if result['std_score'] > 15 else '보통' if result['std_score'] > 10 else '낮음'})")
        report_lines.append(f"- **수행 횟수**: {result['count']}회")
        report_lines.append("")
        
        # 주요 문제 변수
        worst_vars = result['worst_variables'][:3]
        if worst_vars:
            report_lines.append("**주요 문제 변수**:")
            for var_info in worst_vars:
                var = var_info['variable']
                mean_error = result['mean_variable_errors'][var]
                report_lines.append(f"  - {var}: 평균 오차 {mean_error:.3f}")
        report_lines.append("")
        
        # 교정 방향
        report_lines.append("**교정 방향**:")
        if result['mean_score'] < 70:
            report_lines.append("  - 전반적인 포즈 개선이 필요합니다.")
        elif result['mean_score'] < 85:
            report_lines.append("  - 일부 변수에서 개선이 필요합니다.")
        else:
            report_lines.append("  - 양호한 포즈입니다. 유지하세요.")
        
        if result['std_score'] > 15:
            report_lines.append("  - 포즈 일관성을 높이기 위한 연습이 필요합니다.")
        
        report_lines.append("")
        report_lines.append("-" * 60)
        report_lines.append("")
    
    return "\n".join(report_lines)


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("3단계: 포즈품질 습관 평가")
    print("=" * 60)
    
    # 디렉토리 생성
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 데이터 로드
    print(f"\n[1] 데이터 로드")
    print(f"   사용자 데이터: {USER_DATA_FILE}")
    if not USER_DATA_FILE.exists():
        raise FileNotFoundError(f"사용자 데이터 파일을 찾을 수 없습니다: {USER_DATA_FILE}")
    
    print(f"   기준 벡터: {STANDARDS_FILE}")
    if not STANDARDS_FILE.exists():
        raise FileNotFoundError(f"기준 벡터 파일을 찾을 수 없습니다: {STANDARDS_FILE}")
    
    print(f"   가중치: {WEIGHTS_FILE}")
    if not WEIGHTS_FILE.exists():
        raise FileNotFoundError(f"가중치 파일을 찾을 수 없습니다: {WEIGHTS_FILE}")
    
    user_df = pd.read_csv(USER_DATA_FILE)
    print(f"   사용자 데이터: {len(user_df)}개 행")
    
    with open(STANDARDS_FILE, 'r', encoding='utf-8') as f:
        standards_dict = json.load(f)
    
    with open(WEIGHTS_FILE, 'r', encoding='utf-8') as f:
        weights_dict = json.load(f)
    
    # 2. 포즈 품질 분석
    print(f"\n[2] 포즈 품질 분석")
    analysis_results = analyze_pose_quality(user_df, standards_dict, weights_dict)
    
    for pose_type, result in analysis_results.items():
        print(f"   {pose_type}: 평균 점수 {result['mean_score']:.1f}점, {result['count']}회 수행")
    
    # 3. 결과 저장
    print(f"\n[3] 결과 저장: {OUTPUT_JSON}")
    output_data = {
        "metadata": {
            "description": "포즈 품질 평가 결과",
            "user_data_source": str(USER_DATA_FILE),
            "standards_source": str(STANDARDS_FILE),
            "weights_source": str(WEIGHTS_FILE),
            "evaluation_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "results": analysis_results
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"   저장 완료: {len(analysis_results)}개 포즈 타입")
    
    # 4. 시각화 생성
    print(f"\n[4] 시각화 생성")
    create_visualizations(analysis_results)
    
    # 5. 텍스트 보고서 생성
    print(f"\n[5] 텍스트 보고서 생성")
    report_text = generate_report_text(analysis_results)
    report_file = REPORTS_DIR / "pose_quality_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"   보고서 저장: {report_file}")
    
    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"결과 파일:")
    print(f"  - {OUTPUT_JSON}")
    print(f"  - {report_file}")
    print(f"  - reports/3.report/3.1_mean_score_comparison.png")
    print(f"  - reports/3.report/3.2_score_distribution.png")
    print(f"  - reports/3.report/3.3_variable_error_heatmap.png")
    print(f"  - reports/3.report/3.4_consistency_comparison.png")


if __name__ == "__main__":
    main()

