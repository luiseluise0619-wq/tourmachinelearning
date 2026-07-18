# notebooks/

EDA·모델링 주피터 노트북. 번호 순서대로 진행한다.

| 노트북 | 내용 | 로드맵 |
|--------|------|--------|
| `00_practice_heart.ipynb` | ML 워크플로 연습 (심장병 데이터로 EDA→회귀 몸에 익히기) | 0단계 |
| `01_eda.ipynb` | 축제·날씨·방문자 데이터 탐색 | 3단계 |
| `02_features.ipynb` | 파생변수 생성 (날씨별 방문자 증감 분석) | 3단계 |
| `03_model.ipynb` | 방문자수/흥행도 예측 회귀 모델링 + 평가 | 4단계 |

## 실행

```bash
pip install -r ../requirements.txt
jupyter lab
```

> 노트북에서 프로젝트 모듈을 쓰려면 상위 경로를 추가한다:
> ```python
> import sys; sys.path.append("..")
> from src.preprocess import add_calendar_features
> ```
