"""생성형 AI 기획자 — LLM 연결(OpenAI/Gemini) + 키 없을 때 규칙 기반 폴백.

입력(예산·타깃·지역·테마)으로 축제 컨셉·프로그램·홍보·예산배분·운영·리스크를 생성.
LLM이 없으면 FestCast 예측 엔진 + 템플릿으로 실사용 가능한 기획서를 만든다.
"""
from __future__ import annotations

import json

import httpx

from app.config import settings


def _prompt(req: dict) -> str:
    return (
        "당신은 대한민국 지역축제 기획 전문가다. 아래 조건으로 실행 가능한 축제 기획안을 "
        "JSON으로 만들어라. 키: concept, programs(list), performances(list), "
        "promotion(list), budget_allocation(object 항목:비율%), operations(list), risks(list of {risk,solution}).\n"
        f"- 예산: {req['budget_mil_won']}백만원\n- 타깃: {req['target_audience']}\n"
        f"- 지역: {req['region']}\n- 테마: {req.get('theme') or '자유'}\n"
        "반드시 JSON만 출력."
    )


def _via_openai(req: dict) -> dict | None:
    if not settings.OPENAI_API_KEY:
        return None
    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions", timeout=40,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"model": "gpt-4o-mini", "response_format": {"type": "json_object"},
                  "messages": [{"role": "user", "content": _prompt(req)}]},
        )
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


def _via_gemini(req: dict) -> dict | None:
    if not settings.GEMINI_API_KEY:
        return None
    try:
        r = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            timeout=40,
            json={"contents": [{"parts": [{"text": _prompt(req)}]}],
                  "generationConfig": {"responseMimeType": "application/json"}},
        )
        r.raise_for_status()
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(txt)
    except Exception:
        return None


def _fallback(req: dict) -> dict:
    """LLM 없이 규칙 기반 기획서 — 타깃별 템플릿."""
    aud = req["target_audience"]
    budget = req["budget_mil_won"]
    young = any(k in aud for k in ("10", "20", "청년", "MZ"))
    fam = any(k in aud for k in ("가족", "30", "40", "아이"))
    programs = (["체험 부스", "플리마켓", "버스킹", "야간 라이트쇼", "포토존"] if young
                else ["가족 체험존", "먹거리 장터", "전통공연", "키즈존"] if fam
                else ["대표 공연", "지역 특산물 장터", "전시·체험", "경연 대회"])
    channels = (["인스타그램/틱톡", "대학 커뮤니티", "네이버 지역카페"] if young
                else ["맘카페", "지역 현수막", "카카오 지역채널"] if fam
                else ["지역 신문/방송", "관광버스 연계", "현수막"])
    return {
        "concept": f"{req['region']} {aud} 대상 {req.get('theme') or '체험형'} 축제",
        "programs": programs,
        "performances": (["인디밴드·DJ 라인업"] if young else ["트로트·전통공연"]),
        "promotion": channels,
        "budget_allocation": {"프로그램/공연": 40, "홍보": 20, "운영/안전": 20,
                              "시설/인프라": 15, "예비비": 5},
        "operations": ["셔틀버스 운영", "혼잡 구간 동선 분리", "안전요원·응급부스 배치"],
        "risks": [
            {"risk": "우천 시 방문 급감", "solution": "실내 대체공간·천막·우천 프로그램"},
            {"risk": "주차/교통 혼잡", "solution": "사전예약 주차+셔틀, 대중교통 홍보"},
            {"risk": "특정 시간대 쏠림", "solution": "시간대 분산 이벤트·입장 안내"},
        ],
        "budget_total_mil_won": budget,
        "generated_by": "rule-based fallback (LLM 키 미설정)",
    }


def generate_plan(req: dict) -> dict:
    provider = settings.LLM_PROVIDER
    result = None
    if provider == "openai":
        result = _via_openai(req)
    elif provider == "gemini":
        result = _via_gemini(req)
    else:
        result = _via_openai(req) or _via_gemini(req)
    if result:
        result.setdefault("generated_by", provider or "llm")
        return result
    return _fallback(req)
