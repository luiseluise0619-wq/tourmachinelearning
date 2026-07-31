# API 데이터 붙이기 — 발급 & 실행 가이드

> 목표: 축제 1,266건에 **날씨·인구·K콘텐츠**를 API로 자동 결합.
> ⚠️ **로컬 PC에서 실행하세요.** 클라우드(웹) 세션은 보안 정책상 공공 API 접속이
> 차단됩니다. 키 발급 후 아래 명령을 로컬에서 돌리면 데이터가 붙습니다.

---

## 1. API 키 발급 (전부 무료)

### ⭐ 공공데이터포털 — 하나의 키로 여러 API
1. https://www.data.go.kr 회원가입/로그인
2. 아래 3개 검색 → 각각 **활용신청**(즉시 승인):
   - **기상청_지상(종관, ASOS) 일자료 조회서비스** → 날씨(기온·강수)
   - **한국관광공사_국문 관광정보 서비스(TourAPI)** → 축제 실시간 정보 (필수 요건)
   - **행정안전부_주민등록 인구통계**(또는 지역별 연령별 인구) → 주변 인구
3. 마이페이지 → **일반 인증키(Decoding)** 복사 → 세 API 공통 사용 가능

### 네이버 데이터랩 (K콘텐츠 검색량)
1. https://developers.naver.com → 애플리케이션 등록
2. 사용 API: **데이터랩(검색어 트렌드)** → Client ID / Secret 발급

---

## 2. 키 입력

```bash
cp .env.example .env      # 최초 1회
# .env 를 열어 채우기:
#   TOURAPI_SERVICE_KEY=<공공데이터포털 일반인증키(Decoding)>
#   KMA_SERVICE_KEY=<공공데이터포털 일반인증키(Decoding)>   # 같은 키 사용
#   NAVER_CLIENT_ID=...
#   NAVER_CLIENT_SECRET=...
```

---

## 3. 실행 (명령어 한 줄씩)

```bash
pip install -r requirements.txt

# ① 날씨 자동 결합 → data/processed/festivals_enriched.csv
python -m src.enrich
#   축제 개최지 → ASOS 지점 매핑 → 개최 기간 실제 기온·강수 집계·결합
#   (키/네트워크 없으면 날씨 컬럼만 비우고 진행)

# ② 개별 수집도 가능
python -m src.collect_weather   --stn 108 --start 20250101 --end 20251231
python -m src.collect_population --region "경기도 수원시"
python -m src.collect_trends     --keyword "오징어게임" --start 2021-08 --end 2021-12

# ③ 보강 데이터로 모델 재학습 (근거 갱신)
python -m src.model
```

> 네트워크 확인: `python -m src.enrich --selftest` (키 없이 집계 로직만 검증)

---

## 4. 무엇이 붙는가

| 데이터 | 붙는 컬럼 | 소스 | 파이프라인 |
|--------|-----------|------|-----------|
| 날씨 | `wx_avg_temp` · `wx_rain_prob` · `wx_rained_days` | 기상청 ASOS | `src/enrich.py` ✅ |
| 주변 인구(연령대) | 연령대별 인구 | 주민등록 | `src/collect_population.py` ✅ |
| K콘텐츠 인기도 | 시점별 검색량 | 네이버 데이터랩 | `src/collect_trends.py` ✅ |
| 축제 실시간 | 프로그램·상세 | TourAPI | `src/collect_tourapi.py` ✅ |

> 결합 방식: 축제 **개최지(ASOS 지점) × 개최 기간(연례 축제는 전년 동일 월·일)**의
> 실제 날씨를 집계. 지점 매핑은 `src/stations.py` (키 불필요, 이미 완성).

## 5. 참고 — 왜 로컬인가

이 클라우드 세션의 외부 접속은 조직 egress 정책으로 `apis.data.go.kr`·기상청 등이
차단(403)됩니다. 코드·파이프라인은 모두 완성되어 있으니, **로컬에서 키만 넣으면**
동일하게 동작합니다.
