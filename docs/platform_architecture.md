# FestCast Platform — 시스템 아키텍처 (축제 기획 AI SaaS)

## 1. 개요
지자체·축제 운영기관이 기획 데이터를 입력하면 AI가 방문객 예측·성공 진단·
예산/프로그램/운영/홍보 추천·위험 요소·생성형 기획서를 자동 생성하는 B2B SaaS.
기존 FestCast 예측 엔진(`src/`, 문체부 1,266건 학습)을 그대로 서빙한다.

## 2. 구성
```
Next.js(TS·Tailwind)  ─HTTP(JWT)─▶  FastAPI  ─▶  PostgreSQL / SQLite
  로그인·프로젝트·데이터입력·          │  인증·CRUD·CSV·AI서빙·LLM·PDF
  대시보드·차트·기획서·PDF            └─▶  src/ ML 엔진 + 학습모델(joblib)
```

## 3. 데이터 모델 (`platform/backend/app/models.py`)
- **User** (기관 실무자) 1—N **Project** 1—N **Festival** / **Analysis(기록)**
- Festival: 핵심 필드 + 카테고리별 **JSON**(basic·performance·region_data·access·
  weather·content·online·operations) → 요구된 전 데이터 항목을 유연 수용,
  실데이터 확보 시 동일 스키마로 교체.

## 4. API 표면 (`/docs` Swagger)
| 그룹 | 엔드포인트 |
|------|-----------|
| auth | POST /register · /login · GET /me |
| projects | GET/POST /api/projects · GET/DELETE /{id} |
| festivals | GET/POST /api/projects/{id}/festivals · POST /upload-csv |
| ai | POST /predict · /success · /generate · GET /model-comparison · /history/{pid} |
| reports | POST /api/reports/pdf |
| dev | POST /api/dev/seed (샘플 데이터) |

## 5. AI 파이프라인
- **방문객 예측**(`services/ml.py`): 입력→`src.scoring`(5요인·확률예보·쏠림·내외국인)
  → 예상·80%구간·성공확률·영향변수·피드백·마케팅.
- **모델 비교**: `src.model_best` 교차검증(XGBoost/RF/GBM/LightGBM) + 영향변수.
- **생성형 기획**(`services/llm.py`): OpenAI/Gemini 연결, 키 없으면 규칙 기반 폴백
  (예측 엔진으로 예상 방문객 검증 첨부).
- 학습 모델은 **joblib 파일** → 백엔드가 로드해 서빙(로컬 학습 → 서버 배포).

## 6. 데이터 확보 구조
- API 연결(로컬/배포): 공공데이터·기상청·주민등록·네이버·유튜브 (`src/collect_*`, `enrich`).
- CSV 업로드: `/upload-csv`. 샘플 생성: `services/sample_data.py`.
- 스키마 우선 설계 → 실데이터로 무중단 교체.

## 7. 배포
- Frontend → Vercel(`NEXT_PUBLIC_API_BASE`), Backend → Render/Cloud(uvicorn),
  DB → Supabase/PostgreSQL(`DATABASE_URL`). CORS는 `*.vercel.app` 자동 허용.

## 8. 구현 상태
- ✅ 백엔드 전 기능 **e2e 검증 통과**(회원가입→예측→생성→PDF→시드→모델비교).
- ✅ 프론트 전 페이지 구현(로컬 `npm install && npm run dev`로 구동).
- ⚙️ 외부 API·LLM은 키/네트워크 필요 → 로컬·배포에서 활성(폴백으로 무키 동작).
- 확장: 대시보드 상세 차트, 팀/권한, 결제, 관측지표 모니터링 등 단계적 추가 가능.
