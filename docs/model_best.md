# 최고 성능 모델 결과 (model_best)

학습 1,183건 · 피처 35개 · y=log10(방문객)

## 모델 비교 (5-fold CV R²)

| 모델 | R² |
|------|-----|
| GradientBoosting **(채택)** | 0.546 |
| RandomForest | 0.537 |
| LightGBM | 0.486 |
| HistGBM | 0.465 |
| 선형회귀 | 0.401 |

**채택: GradientBoosting (R²=0.546)** · 이전 GBM 0.55 대비 개선.

## 확률 예보

- 분위수 회귀 P10~P90 커버리지 57% (목표 80%)
- 몬테카를로 대신 **데이터 학습 기반** 예측구간으로 승격 가능

## SHAP 변수 기여도 (상위 10)

| 변수 | 평균 |SHAP| |
|------|------|
| log_budget | 0.423 |
| duration_days | 0.142 |
| num_editions | 0.089 |
| month | 0.066 |
| category_지역특산물 | 0.045 |
| operator_type_민간 협/단체 | 0.043 |
| category_자연생태 | 0.036 |
| region_서울 | 0.036 |
| measured | 0.026 |
| operator_type_정부/지자체 | 0.026 |

> SHAP = 개별 예측을 변수별로 분해 → 보완 피드백('일정 옮기면 +N')의 근거.
> 예산↔방문객 양방향(규모 대리지표) 해석 유지.