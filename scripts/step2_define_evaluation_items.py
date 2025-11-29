#!/usr/bin/env python3
"""
2단계: 평가항목 정의
상급자와 초심자 데이터를 학습하여 포즈 타입별 변수 중요도(가중치)를 추출합니다.
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 사용

# 한글 폰트 설정 (macOS)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports" / "2.RFC"
EXPERT_DATA_FILE = DATA_DIR / "pose_data" / "상급자 Sample1.csv"
BEGINNER_DATA_FILE = DATA_DIR / "pose_data" / "초심자 Sample1.csv"
OUTPUT_JSON = DATA_DIR / "pose_evaluation_weights.json"

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


def train_random_forest(X, y, pose_type):
    """Random Forest 모델 학습 및 변수 중요도 추출"""
    # 교차 검증 설정 (5-fold)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Random Forest 모델 생성
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    # 교차 검증 수행
    cv_scores = cross_val_score(rf_model, X, y, cv=cv, scoring='accuracy')
    
    # 전체 데이터로 최종 모델 학습
    rf_model.fit(X, y)
    
    # 변수 중요도 추출
    feature_importance = rf_model.feature_importances_
    
    # 변수 중요도를 딕셔너리로 변환
    importance_dict = {
        var: float(importance) 
        for var, importance in zip(VARIABLES, feature_importance)
    }
    
    # 변수 중요도 정규화 (합이 1이 되도록)
    total_importance = sum(importance_dict.values())
    if total_importance > 0:
        importance_dict = {
            var: importance / total_importance 
            for var, importance in importance_dict.items()
        }
    
    # 변수 중요도 순위
    sorted_importance = sorted(
        importance_dict.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    return {
        'model': rf_model,
        'feature_importance': importance_dict,
        'sorted_importance': sorted_importance,
        'cv_mean_accuracy': float(cv_scores.mean()),
        'cv_std_accuracy': float(cv_scores.std()),
        'cv_scores': [float(score) for score in cv_scores]
    }


def get_variable_color(var_name):
    """변수 이름에 따라 색상 반환"""
    if 'left_fist' in var_name:
        return '#DC143C'  # 붉은색 (Crimson)
    elif 'right_fist' in var_name:
        return '#FF8C00'  # 주황색 (DarkOrange)
    elif 'arm_angle' in var_name:
        return '#228B22'  # 녹색 (ForestGreen)
    else:
        return '#808080'  # 회색 (Gray)


def create_feature_importance_charts(results_dict):
    """변수 중요도 시각화"""
    n_poses = len(POSE_TYPES)
    
    # 전체 비교 차트
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for idx, pose_type in enumerate(POSE_TYPES):
        if pose_type not in results_dict:
            continue
        
        ax = axes[idx]
        result = results_dict[pose_type]
        importance = result['feature_importance']
        
        # 변수와 중요도 추출
        variables = list(importance.keys())
        importances = list(importance.values())
        
        # 변수별 색상 지정
        colors = [get_variable_color(var) for var in variables]
        
        # 막대 그래프
        bars = ax.barh(variables, importances, color=colors, alpha=0.7)
        
        # 값 표시
        for i, (var, imp) in enumerate(zip(variables, importances)):
            ax.text(imp + 0.01, i, f'{imp:.3f}', va='center', fontsize=9)
        
        ax.set_xlabel('변수 중요도', fontsize=11)
        ax.set_title(f'{pose_type} - 변수 중요도', fontsize=12, fontweight='bold')
        ax.set_xlim(0, max(importances) * 1.3)
        ax.grid(True, alpha=0.3, axis='x')
    
    # 마지막 subplot 제거 (6개만 필요)
    if len(POSE_TYPES) < 6:
        axes[-1].remove()
    
    plt.tight_layout()
    output_file = REPORTS_DIR / "2.0_feature_importance_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  전체 비교 차트 저장: {output_file}")
    plt.close()
    
    # 포즈 타입별 개별 차트
    for pose_type in POSE_TYPES:
        if pose_type not in results_dict:
            continue
        
        result = results_dict[pose_type]
        importance = result['feature_importance']
        
        # 변수와 중요도 추출
        variables = list(importance.keys())
        importances = list(importance.values())
        
        # 변수별 색상 지정
        colors = [get_variable_color(var) for var in variables]
        
        # 개별 차트
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(variables, importances, color=colors, alpha=0.7)
        
        # 값 표시
        for i, (var, imp) in enumerate(zip(variables, importances)):
            ax.text(imp + 0.01, i, f'{imp:.3f}', va='center', fontsize=11)
        
        ax.set_xlabel('변수 중요도 (가중치)', fontsize=12)
        ax.set_title(f'{pose_type} - 변수 중요도 (Random Forest)', size=14, fontweight='bold')
        ax.set_xlim(0, max(importances) * 1.3)
        ax.grid(True, alpha=0.3, axis='x')
        
        # 교차 검증 정확도 표시
        cv_mean = result['cv_mean_accuracy']
        cv_std = result['cv_std_accuracy']
        ax.text(0.02, 0.98, f'교차 검증 정확도: {cv_mean:.3f} ± {cv_std:.3f}', 
                transform=ax.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # 파일명 매핑
        pose_file_mapping = {
            'GUARD': '2.1_feature_importance_guard.png',
            'JAB_L': '2.2_feature_importance_jab_l.png',
            'STRAIGHT_R': '2.3_feature_importance_straight_r.png',
            'WEAVE_L': '2.4_feature_importance_weave_l.png',
            'WEAVE_R': '2.5_feature_importance_weave_r.png'
        }
        
        output_file = REPORTS_DIR / pose_file_mapping[pose_type]
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  {pose_type} 차트 저장: {output_file}")
        plt.close()


def create_heatmap(results_dict):
    """변수 중요도 히트맵 생성"""
    # 데이터 준비
    pose_types = []
    variables = VARIABLES.copy()
    importance_matrix = []
    
    for pose_type in POSE_TYPES:
        if pose_type not in results_dict:
            continue
        pose_types.append(pose_type)
        result = results_dict[pose_type]
        importance = result['feature_importance']
        row = [importance.get(var, 0.0) for var in variables]
        importance_matrix.append(row)
    
    # numpy 배열로 변환
    importance_array = np.array(importance_matrix)
    
    # 히트맵 생성
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 히트맵 그리기
    im = ax.imshow(importance_array, cmap='YlOrRd', aspect='auto', vmin=0, vmax=0.6)
    
    # 축 레이블 설정
    ax.set_xticks(np.arange(len(variables)))
    ax.set_yticks(np.arange(len(pose_types)))
    ax.set_xticklabels(variables, rotation=45, ha='right')
    ax.set_yticklabels(pose_types)
    
    # 값 표시
    for i in range(len(pose_types)):
        for j in range(len(variables)):
            value = importance_array[i, j]
            # 값에 따라 텍스트 색상 조정
            text_color = 'white' if value > 0.3 else 'black'
            ax.text(j, i, f'{value:.3f}', ha='center', va='center', 
                   color=text_color, fontsize=9, fontweight='bold')
    
    # 컬러바 추가
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('변수 중요도 (가중치)', fontsize=11)
    
    # 제목 설정
    ax.set_title('포즈 타입별 변수 중요도 히트맵 (Random Forest)', 
                fontsize=14, fontweight='bold', pad=20)
    
    # 축 레이블
    ax.set_xlabel('변수', fontsize=12)
    ax.set_ylabel('포즈 타입', fontsize=12)
    
    plt.tight_layout()
    output_file = REPORTS_DIR / "2.6_feature_importance_heatmap.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  히트맵 저장: {output_file}")
    plt.close()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("2단계: 평가항목 정의")
    print("=" * 60)
    
    # 디렉토리 생성
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 데이터 로드
    print(f"\n[1] 데이터 로드")
    print(f"   상급자 데이터: {EXPERT_DATA_FILE}")
    if not EXPERT_DATA_FILE.exists():
        raise FileNotFoundError(f"상급자 데이터 파일을 찾을 수 없습니다: {EXPERT_DATA_FILE}")
    
    print(f"   초심자 데이터: {BEGINNER_DATA_FILE}")
    if not BEGINNER_DATA_FILE.exists():
        raise FileNotFoundError(f"초심자 데이터 파일을 찾을 수 없습니다: {BEGINNER_DATA_FILE}")
    
    expert_df = pd.read_csv(EXPERT_DATA_FILE)
    beginner_df = pd.read_csv(BEGINNER_DATA_FILE)
    
    print(f"   상급자 데이터: {len(expert_df)}개 행")
    print(f"   초심자 데이터: {len(beginner_df)}개 행")
    
    # 2. 데이터 전처리 및 레이블링
    print(f"\n[2] 데이터 전처리 및 레이블링")
    
    # 상급자 데이터에 레이블 추가
    expert_df['skill_level'] = 1  # 상급자 = 1
    beginner_df['skill_level'] = 0  # 초심자 = 0
    
    # 데이터 결합
    combined_df = pd.concat([expert_df, beginner_df], ignore_index=True)
    print(f"   전체 데이터: {len(combined_df)}개 행")
    
    # 3. 포즈 타입별 모델 학습
    print(f"\n[3] 포즈 타입별 Random Forest 모델 학습")
    results_dict = {}
    
    for pose_type in POSE_TYPES:
        print(f"\n   {pose_type} 분석 중...")
        
        # 포즈 타입별 데이터 추출
        pose_data = combined_df[combined_df['Note_Type'] == pose_type].copy()
        
        if len(pose_data) == 0:
            print(f"     데이터 없음")
            continue
        
        # IQR 이상치 제거
        pose_data_clean = remove_outliers_iqr(pose_data, VARIABLES)
        print(f"     데이터: {len(pose_data)}개 → {len(pose_data_clean)}개 (이상치 제거 후)")
        
        if len(pose_data_clean) < 10:
            print(f"     데이터가 너무 적어 모델 학습 불가 (최소 10개 필요)")
            continue
        
        # 특성과 레이블 분리
        X = pose_data_clean[VARIABLES].values
        y = pose_data_clean['skill_level'].values
        
        # 클래스 분포 확인
        unique, counts = np.unique(y, return_counts=True)
        class_dist = dict(zip(unique, counts))
        print(f"     클래스 분포: 상급자={class_dist.get(1, 0)}개, 초심자={class_dist.get(0, 0)}개")
        
        # Random Forest 모델 학습
        result = train_random_forest(X, y, pose_type)
        
        print(f"     교차 검증 정확도: {result['cv_mean_accuracy']:.3f} ± {result['cv_std_accuracy']:.3f}")
        print(f"     가장 중요한 변수: {result['sorted_importance'][0][0]} ({result['sorted_importance'][0][1]:.3f})")
        
        results_dict[pose_type] = {
            'cv_mean_accuracy': result['cv_mean_accuracy'],
            'cv_std_accuracy': result['cv_std_accuracy'],
            'cv_scores': result['cv_scores'],
            'feature_importance': result['feature_importance'],
            'sorted_importance': [
                {'variable': var, 'importance': imp} 
                for var, imp in result['sorted_importance']
            ],
            'data_count': len(pose_data_clean),
            'class_distribution': {
                'expert': int(class_dist.get(1, 0)),
                'beginner': int(class_dist.get(0, 0))
            }
        }
    
    # 4. JSON 저장
    print(f"\n[4] 결과 저장: {OUTPUT_JSON}")
    output_data = {
        "metadata": {
            "description": "포즈 타입별 변수 중요도 (가중치) - Random Forest Classifier",
            "expert_data_source": str(EXPERT_DATA_FILE),
            "beginner_data_source": str(BEGINNER_DATA_FILE),
            "variables": VARIABLES,
            "pose_types": POSE_TYPES,
            "method": "Random Forest Classifier",
            "cv_folds": 5
        },
        "results": results_dict
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"   저장 완료: {len(results_dict)}개 포즈 타입")
    
    # 5. 시각화 생성
    print(f"\n[5] 시각화 생성")
    create_feature_importance_charts(results_dict)
    create_heatmap(results_dict)
    
    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"결과 파일:")
    print(f"  - {OUTPUT_JSON}")
    print(f"  - reports/2.RFC/2.0_feature_importance_comparison.png (전체 비교)")
    print(f"  - reports/2.RFC/2.6_feature_importance_heatmap.png (히트맵)")
    for pose_type in POSE_TYPES:
        if pose_type in results_dict:
            pose_file_mapping = {
                'GUARD': '2.1_feature_importance_guard.png',
                'JAB_L': '2.2_feature_importance_jab_l.png',
                'STRAIGHT_R': '2.3_feature_importance_straight_r.png',
                'WEAVE_L': '2.4_feature_importance_weave_l.png',
                'WEAVE_R': '2.5_feature_importance_weave_r.png'
            }
            print(f"  - reports/2.RFC/{pose_file_mapping[pose_type]} ({pose_type})")


if __name__ == "__main__":
    main()

