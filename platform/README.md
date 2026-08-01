# FestCast Platform — 축제 기획 AI SaaS

지자체·축제 운영기관이 기획 데이터를 입력하면 AI가 **방문객 예측 · 성공 진단 ·
예산/프로그램/운영/홍보 추천 · 위험 요소 · 생성형 기획서**까지 자동 생성하는 B2B SaaS.

기존 FestCast 예측 엔진(`../src/`, 문체부 1,266건 학습)을 그대로 서빙한다.

## 아키텍처

```
[Next.js + TS + Tailwind]  ──HTTP──▶  [FastAPI]  ──▶  [PostgreSQL/SQLite]
  로그인·프로젝트·데이터입력·                │
  대시보드·차트·AI기획서·PDF               ├─ 인증(JWT)
                                          ├─ 프로젝트/축제 데이터 CRUD + CSV 업로드
                                          ├─ AI: 방문객 예측·성공분석·변수영향 (../src ML)
                                          ├─ 생성형 기획자 (OpenAI/Gemini, 폴백 내장)
                                          └─ 보고서 + PDF export
```

## 폴더
```
platform/
├─ backend/   FastAPI · SQLAlchemy · JWT · ML 서빙 · LLM · PDF
│  └─ app/{config,database,models,schemas,security,deps, routers/, services/}
└─ frontend/  Next.js(App Router) · TS · Tailwind
   └─ app/{login,dashboard,projects/[id]} · components · lib
```

## 실행 (로컬)

### 백엔드
```bash
cd platform/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 키 없어도 동작(폴백). DB 미설정 시 SQLite 자동
uvicorn app.main:app --reload --port 8000
# 문서: http://localhost:8000/docs   ·   샘플 시드: POST /api/dev/seed
```

### 프론트
```bash
cd platform/frontend
npm install
npm run dev                    # http://localhost:3000  (API_BASE=localhost:8000)
```

## 완성/구현 상태
- ✅ 인증(회원가입·로그인·JWT), 프로젝트 관리, 축제 데이터 저장(전 필드), CSV 업로드
- ✅ AI 방문객 예측(예상·신뢰구간·성공확률·영향변수 TOP10) — XGBoost/RF/GBM 비교
- ✅ 성공 분석(점수·위험요소·개선추천), 변수 영향도
- ✅ 생성형 기획자(LLM 연결 + 키 없을 때 규칙 기반 폴백)
- ✅ 보고서 저장 + PDF export
- ✅ 현실적 샘플 데이터 생성 + 스키마(실데이터 교체 가능)
- ⚙️ 외부 API(공공데이터·날씨·LLM)는 키/네트워크 필요 → 로컬/배포에서 활성

> 상세 설계: `../docs/platform_architecture.md`
