#!/usr/bin/env python3
"""
상급자와 초심자의 가드 포지션 비교 리포트 생성
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
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
BEGINNER_DATA_FILE = DATA_DIR / "pose_data" / "초심자 Sample2.csv"
EXPERT_DATA_FILE = DATA_DIR / "pose_data" / "상급자 Sample1.csv"
STANDARDS_FILE = DATA_DIR / "pose_standards.json"

# 8개 변수 (레이더 차트 순서: 시계방향, 12시부터 시작)
# 이미지 기준 순서: 오른손 각도(11시) -> 오른손 거리(1시) -> 왼손 각도(2시) -> 왼손 거리(3시) -> 코가 어깨 위(4시) -> 코 위치(6시) -> 오른팔 각도(7시) -> 왼팔 각도(9시)
# 12시부터 시작하도록 재배열: 오른손 각도 -> 오른손 거리 -> 왼손 각도 -> 왼손 거리 -> 코가 어깨 위 -> 코 위치 -> 오른팔 각도 -> 왼팔 각도
VARIABLES = [
    "right_fist_angle",      # 오른손 각도 (12시 방향)
    "right_fist_dist",       # 오른손 거리 (1-2시 방향)
    "left_fist_angle",       # 왼손 각도 (3시 방향)
    "left_fist_dist",        # 왼손 거리 (4-5시 방향)
    "nose_above_shoulder",   # 코가 어깨 위 (6시 방향)
    "nose_position",         # 코 위치 (7-8시 방향)
    "right_arm_angle",       # 오른팔 각도 (9시 방향)
    "left_arm_angle"         # 왼팔 각도 (10-11시 방향)
]

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


def get_expert_data_range():
    """상급자 데이터의 각 변수별 최소/최대값 구하기 (모든 포즈 타입 포함)"""
    expert_df = pd.read_csv(EXPERT_DATA_FILE)
    
    # 모든 포즈 타입의 데이터를 합쳐서 최소/최대값 계산 (1단계와 동일한 방식)
    expert_ranges = {}
    for var in VARIABLES:
        all_values = expert_df[var].values
        expert_ranges[var] = {
            'min': float(np.min(all_values)),
            'max': float(np.max(all_values))
        }
    
    return expert_ranges


def create_comparison_report():
    """비교 리포트 생성"""
    print("=" * 60)
    print("상급자 vs 초심자 가드 포지션 비교 리포트")
    print("=" * 60)
    
    # 1. 데이터 로드
    print(f"\n[1] 데이터 로드")
    beginner_df = pd.read_csv(BEGINNER_DATA_FILE)
    guard_data = beginner_df[beginner_df['Note_Type'] == 'GUARD'].copy()
    print(f"   초심자 가드 데이터: {len(guard_data)}개")
    
    with open(STANDARDS_FILE, 'r', encoding='utf-8') as f:
        standards = json.load(f)
    
    expert_centroid = standards['results']['GUARD']['centroid']
    print(f"   상급자 기준 벡터 로드 완료")
    
    # 상급자 데이터 범위 구하기
    expert_ranges = get_expert_data_range()
    print(f"   상급자 데이터 범위 계산 완료")
    
    # 2. 통계 계산
    print(f"\n[2] 통계 계산")
    beginner_stats = {}
    expert_values = {}
    differences = {}
    percent_differences = {}
    
    for var in VARIABLES:
        beginner_values = guard_data[var].values
        expert_value = expert_centroid[var]
        
        beginner_stats[var] = {
            'mean': float(np.mean(beginner_values)),
            'std': float(np.std(beginner_values)),
            'min': float(np.min(beginner_values)),
            'max': float(np.max(beginner_values)),
            'median': float(np.median(beginner_values))
        }
        expert_values[var] = expert_value
        differences[var] = beginner_stats[var]['mean'] - expert_value
        
        # 백분율 차이 계산 (0으로 나누기 방지)
        if expert_value != 0:
            percent_differences[var] = (differences[var] / abs(expert_value)) * 100
        else:
            percent_differences[var] = 0.0
    
    # 3. 리포트 텍스트 생성
    print(f"\n[3] 리포트 생성")
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("상급자 vs 초심자 가드 포지션 비교 리포트")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"**분석 대상**: 초심자 Sample2.csv의 GUARD 포즈 ({len(guard_data)}개 샘플)")
    report_lines.append(f"**비교 기준**: 상급자 기준 포즈 벡터 (Centroid)")
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("")
    
    # 변수별 상세 비교
    report_lines.append("## 변수별 상세 비교")
    report_lines.append("")
    
    for var in VARIABLES:
        label = VARIABLE_LABELS[var]
        expert_val = expert_values[var]
        beginner_mean = beginner_stats[var]['mean']
        beginner_std = beginner_stats[var]['std']
        diff = differences[var]
        percent_diff = percent_differences[var]
        
        report_lines.append(f"### {label} ({var})")
        report_lines.append("")
        report_lines.append(f"- **상급자 기준값**: {expert_val:.4f}")
        report_lines.append(f"- **초심자 평균값**: {beginner_mean:.4f} ± {beginner_std:.4f}")
        report_lines.append(f"- **초심자 범위**: {beginner_stats[var]['min']:.4f} ~ {beginner_stats[var]['max']:.4f}")
        report_lines.append(f"- **평균 차이**: {diff:+.4f} ({percent_diff:+.2f}%)")
        
        # 해석
        if abs(percent_diff) < 5:
            interpretation = "거의 일치"
        elif abs(percent_diff) < 15:
            interpretation = "약간의 차이"
        elif abs(percent_diff) < 30:
            interpretation = "상당한 차이"
        else:
            interpretation = "큰 차이"
        
        report_lines.append(f"- **해석**: {interpretation}")
        report_lines.append("")
    
    # 요약
    report_lines.append("-" * 80)
    report_lines.append("## 요약")
    report_lines.append("")
    
    # 가장 큰 차이를 보인 변수
    sorted_diffs = sorted(
        [(var, abs(differences[var])) for var in VARIABLES],
        key=lambda x: x[1],
        reverse=True
    )
    
    report_lines.append("### 가장 큰 차이를 보인 변수 (상위 3개)")
    for i, (var, diff) in enumerate(sorted_diffs[:3], 1):
        label = VARIABLE_LABELS[var]
        actual_diff = differences[var]
        percent_diff = percent_differences[var]
        direction = "큼" if actual_diff > 0 else "작음"
        report_lines.append(f"{i}. **{label}**: 평균 {abs(actual_diff):.4f} 차이 ({percent_diff:+.2f}%), 초심자가 기준보다 {direction}")
    report_lines.append("")
    
    # 가장 일치한 변수
    sorted_diffs_asc = sorted(
        [(var, abs(differences[var])) for var in VARIABLES],
        key=lambda x: x[1]
    )
    
    report_lines.append("### 가장 일치한 변수 (상위 3개)")
    for i, (var, diff) in enumerate(sorted_diffs_asc[:3], 1):
        label = VARIABLE_LABELS[var]
        actual_diff = differences[var]
        percent_diff = percent_differences[var]
        direction = "큼" if actual_diff > 0 else "작음"
        report_lines.append(f"{i}. **{label}**: 평균 {abs(actual_diff):.4f} 차이 ({percent_diff:+.2f}%), 초심자가 기준보다 {direction}")
    report_lines.append("")
    
    # 일관성 분석
    report_lines.append("### 일관성 분석")
    sorted_std = sorted(
        [(var, beginner_stats[var]['std']) for var in VARIABLES],
        key=lambda x: x[1],
        reverse=True
    )
    
    report_lines.append("**가장 일관성이 낮은 변수 (상위 3개)**:")
    for i, (var, std) in enumerate(sorted_std[:3], 1):
        label = VARIABLE_LABELS[var]
        report_lines.append(f"{i}. **{label}**: 표준편차 {std:.4f}")
    report_lines.append("")
    
    report_lines.append("**가장 일관성이 높은 변수 (상위 3개)**:")
    for i, (var, std) in enumerate(sorted_std[-3:], 1):
        label = VARIABLE_LABELS[var]
        report_lines.append(f"{i}. **{label}**: 표준편차 {std:.4f}")
    report_lines.append("")
    
    # 교정 권장 사항
    report_lines.append("-" * 80)
    report_lines.append("## 교정 권장 사항")
    report_lines.append("")
    
    # 가장 큰 차이를 보인 변수에 대한 교정 권장
    top_diff_var = sorted_diffs[0][0]
    top_diff_label = VARIABLE_LABELS[top_diff_var]
    top_diff_value = differences[top_diff_var]
    
    report_lines.append(f"### 1순위: {top_diff_label} 개선")
    report_lines.append(f"- 현재 초심자 평균값이 기준보다 {abs(top_diff_value):.4f} 차이 ({percent_differences[top_diff_var]:+.2f}%)")
    if top_diff_value > 0:
        report_lines.append(f"- **권장**: 값을 줄이는 연습이 필요합니다.")
    else:
        report_lines.append(f"- **권장**: 값을 늘리는 연습이 필요합니다.")
    report_lines.append("")
    
    # 일관성 개선
    top_std_var = sorted_std[0][0]
    top_std_label = VARIABLE_LABELS[top_std_var]
    top_std_value = beginner_stats[top_std_var]['std']
    
    report_lines.append(f"### 일관성 개선: {top_std_label}")
    report_lines.append(f"- 현재 표준편차: {top_std_value:.4f}")
    report_lines.append(f"- **권장**: 같은 자세를 반복할 때 일관되게 유지하는 연습이 필요합니다.")
    report_lines.append("")
    
    report_text = "\n".join(report_lines)
    
    # 리포트 저장
    report_file = REPORTS_DIR / "guard_position_comparison_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"   리포트 저장: {report_file}")
    
    # 4. 시각화 생성
    print(f"\n[4] 시각화 생성")
    create_comparison_visualizations(expert_values, beginner_stats, differences, expert_ranges)
    
    return report_text


def create_comparison_visualizations(expert_values, beginner_stats, differences, expert_ranges):
    """비교 시각화 생성"""
    
    # 1. 평균값 비교 바 차트
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = np.arange(len(VARIABLES))
    width = 0.35
    
    expert_vals = [expert_values[var] for var in VARIABLES]
    beginner_vals = [beginner_stats[var]['mean'] for var in VARIABLES]
    beginner_stds = [beginner_stats[var]['std'] for var in VARIABLES]
    
    bars1 = ax.bar(x - width/2, expert_vals, width, label='상급자 기준', 
                   color='steelblue', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, beginner_vals, width, label='초심자 평균', 
                   yerr=beginner_stds, capsize=5, color='coral', alpha=0.8, edgecolor='black')
    
    ax.set_xlabel('변수', fontsize=12)
    ax.set_ylabel('값', fontsize=12)
    ax.set_title('상급자 vs 초심자 가드 포지션 비교', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([VARIABLE_LABELS[var] for var in VARIABLES], rotation=45, ha='right')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "guard_comparison_bar.png", dpi=300, bbox_inches='tight')
    print(f"  바 차트 저장: {REPORTS_DIR / 'guard_comparison_bar.png'}")
    plt.close()
    
    # 2. 차이 히트맵
    fig, ax = plt.subplots(figsize=(10, 6))
    
    diff_values = [differences[var] for var in VARIABLES]
    diff_array = np.array(diff_values).reshape(1, -1)
    
    im = ax.imshow(diff_array, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
    
    ax.set_xticks(np.arange(len(VARIABLES)))
    ax.set_xticklabels([VARIABLE_LABELS[var] for var in VARIABLES], rotation=45, ha='right')
    ax.set_yticks([0])
    ax.set_yticklabels(['차이'])
    
    # 값 표시
    for j, diff in enumerate(diff_values):
        text_color = 'white' if abs(diff) > 0.5 else 'black'
        ax.text(j, 0, f'{diff:+.3f}', ha='center', va='center', 
               color=text_color, fontsize=10, fontweight='bold')
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('차이 (초심자 - 상급자)', fontsize=11)
    
    ax.set_title('상급자 vs 초심자 가드 포지션 차이', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "guard_comparison_heatmap.png", dpi=300, bbox_inches='tight')
    print(f"  히트맵 저장: {REPORTS_DIR / 'guard_comparison_heatmap.png'}")
    plt.close()
    
    # 3. 레이더 차트 (수정된 버전: 상급자 데이터 범위 기준 정규화)
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    # 각도 설정
    angles = np.linspace(0, 2 * np.pi, len(VARIABLES), endpoint=False).tolist()
    angles += angles[:1]  # 닫기
    
    # 값 정규화 (상급자 데이터 범위 기준으로 0-1 범위로)
    expert_normalized = []
    beginner_normalized = []
    
    for var in VARIABLES:
        # 상급자 데이터의 최소/최대값 사용
        min_val = expert_ranges[var]['min']
        max_val = expert_ranges[var]['max']
        range_val = max_val - min_val if max_val != min_val else 1
        
        # 상급자 기준값 정규화
        expert_norm = (expert_values[var] - min_val) / range_val
        # 초심자 평균값 정규화 (같은 범위 사용)
        beginner_norm = (beginner_stats[var]['mean'] - min_val) / range_val
        
        # 0-1 범위로 제한
        expert_norm = max(0, min(1, expert_norm))
        beginner_norm = max(0, min(1, beginner_norm))
        
        expert_normalized.append(expert_norm)
        beginner_normalized.append(beginner_norm)
    
    expert_normalized += expert_normalized[:1]
    beginner_normalized += beginner_normalized[:1]
    
    ax.plot(angles, expert_normalized, 'o-', linewidth=2, label='상급자 기준', color='steelblue', markersize=8)
    ax.fill(angles, expert_normalized, alpha=0.25, color='steelblue')
    ax.plot(angles, beginner_normalized, 'o-', linewidth=2, label='초심자 평균', color='coral', markersize=8)
    ax.fill(angles, beginner_normalized, alpha=0.25, color='coral')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([VARIABLE_LABELS[var] for var in VARIABLES], fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title('상급자 vs 초심자 가드 포지션 레이더 차트\n(상급자 데이터 범위 기준 정규화)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "guard_comparison_radar_fixed.png", dpi=300, bbox_inches='tight')
    print(f"  레이더 차트 저장 (수정됨): {REPORTS_DIR / 'guard_comparison_radar_fixed.png'}")
    plt.close()
    
    # 4. 레이더 차트 (1단계와 동일한 정규화 방식: 모든 포즈 타입 데이터 범위 사용)
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    # 각도 설정
    angles = np.linspace(0, 2 * np.pi, len(VARIABLES), endpoint=False).tolist()
    angles += angles[:1]  # 닫기
    
    # 값 정규화 (모든 포즈 타입 데이터 범위 기준으로 0-1 범위로 - 1단계와 동일)
    expert_normalized = []
    beginner_normalized = []
    
    for var in VARIABLES:
        # 모든 포즈 타입 데이터의 최소/최대값 사용 (1단계와 동일)
        min_val = expert_ranges[var]['min']
        max_val = expert_ranges[var]['max']
        range_val = max_val - min_val if max_val != min_val else 1
        
        # 상급자 기준값 정규화
        expert_norm = (expert_values[var] - min_val) / range_val
        # 초심자 평균값 정규화 (같은 범위 사용)
        beginner_norm = (beginner_stats[var]['mean'] - min_val) / range_val
        
        # 0-1 범위로 제한
        expert_norm = max(0, min(1, expert_norm))
        beginner_norm = max(0, min(1, beginner_norm))
        
        expert_normalized.append(expert_norm)
        beginner_normalized.append(beginner_norm)
    
    expert_normalized += expert_normalized[:1]
    beginner_normalized += beginner_normalized[:1]
    
    ax.plot(angles, expert_normalized, 'o-', linewidth=2, label='상급자 기준', color='steelblue', markersize=8)
    ax.fill(angles, expert_normalized, alpha=0.25, color='steelblue')
    ax.plot(angles, beginner_normalized, 'o-', linewidth=2, label='초심자 평균', color='coral', markersize=8)
    ax.fill(angles, beginner_normalized, alpha=0.25, color='coral')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([VARIABLE_LABELS[var] for var in VARIABLES], fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title('상급자 vs 초심자 가드 포지션 레이더 차트\n(모든 포즈 타입 데이터 범위 기준 정규화)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "guard_comparison_radar_unified.png", dpi=300, bbox_inches='tight')
    print(f"  레이더 차트 저장 (통합 정규화): {REPORTS_DIR / 'guard_comparison_radar_unified.png'}")
    plt.close()


if __name__ == "__main__":
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_text = create_comparison_report()
    
    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"생성된 파일:")
    print(f"  - reports/3.report/guard_position_comparison_report.txt")
    print(f"  - reports/3.report/guard_comparison_bar.png")
    print(f"  - reports/3.report/guard_comparison_heatmap.png")
    print(f"  - reports/3.report/guard_comparison_radar_fixed.png (GUARD 데이터 범위 기준)")
    print(f"  - reports/3.report/guard_comparison_radar_unified.png (모든 포즈 타입 범위 기준 - 신규)")

