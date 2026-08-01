"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken } from "@/lib/api";
import { DistBars, FactorBars, ScoreGauge } from "@/components/Charts";

const REGIONS = ["서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주"];

export default function ProjectPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const pid = Number(id);
  const [tab, setTab] = useState<"predict" | "generate">("predict");
  const [f, setF] = useState<any>({
    name: "○○ 가을 별빛 축제", region: "경기", start_date: "2026-10-17", end_date: "2026-10-19",
    duration_days: 3, budget_mil_won: 500, is_free: true, visitors_total: "",
    content: { num_programs: 8, performance: true, food: true, experience: false, celebrity: false, kcontent: false },
    operations: { capacity: 80000 },
  });
  const [result, setResult] = useState<any>(null);
  const [gen, setGen] = useState<any>(null);
  const [genReq, setGenReq] = useState({ budget_mil_won: 500, target_audience: "20대", region: "서울 근교", theme: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { if (!getToken()) router.push("/login"); }, []);

  const toggle = (k: string) => setF({ ...f, content: { ...f.content, [k]: !f.content[k] } });

  const runPredict = async () => {
    setBusy(true); setErr("");
    try {
      const payload = { ...f, visitors_total: f.visitors_total ? Number(f.visitors_total) : null };
      setResult(await api.predict(payload, pid));
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const runGenerate = async () => {
    setBusy(true); setErr("");
    try { setGen(await api.generate({ ...genReq, project_id: pid })); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const downloadPdf = async () => {
    const blob = await api.pdf({ ...f, visitors_total: f.visitors_total ? Number(f.visitors_total) : null });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "festcast_report.pdf"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="max-w-6xl mx-auto px-6 py-10">
      <Link href="/dashboard" className="text-tealink text-sm">← 대시보드</Link>
      <div className="flex gap-2 mt-4">
        <button className={tab === "predict" ? "btn" : "btn-ghost"} onClick={() => setTab("predict")}>흥행 예보</button>
        <button className={tab === "generate" ? "btn" : "btn-ghost"} onClick={() => setTab("generate")}>생성형 기획자</button>
      </div>
      {err && <div className="text-bad text-sm mt-3">{err}</div>}

      {tab === "predict" && (
        <div className="grid lg:grid-cols-2 gap-5 mt-5">
          {/* 입력 */}
          <div className="card p-5">
            <h2 className="font-bold text-lg mb-4">기획안 입력</h2>
            <div className="flex flex-col gap-3">
              <div><label className="label">축제명</label><input className="input" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">지역</label>
                  <select className="input" value={f.region} onChange={e => setF({ ...f, region: e.target.value })}>
                    {REGIONS.map(r => <option key={r}>{r}</option>)}
                  </select></div>
                <div><label className="label">예산(백만원)</label><input className="input" type="number" value={f.budget_mil_won} onChange={e => setF({ ...f, budget_mil_won: Number(e.target.value) })} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">시작일</label><input className="input" type="date" value={f.start_date} onChange={e => setF({ ...f, start_date: e.target.value })} /></div>
                <div><label className="label">종료일</label><input className="input" type="date" value={f.end_date} onChange={e => setF({ ...f, end_date: e.target.value })} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">기간(일)</label><input className="input" type="number" value={f.duration_days} onChange={e => setF({ ...f, duration_days: Number(e.target.value) })} /></div>
                <div><label className="label">수용인원(쏠림)</label><input className="input" type="number" value={f.operations.capacity} onChange={e => setF({ ...f, operations: { ...f.operations, capacity: Number(e.target.value) } })} /></div>
              </div>
              <div><label className="label">전년 방문객(있으면)</label><input className="input" type="number" value={f.visitors_total} onChange={e => setF({ ...f, visitors_total: e.target.value })} placeholder="신규면 비움" /></div>
              <div>
                <label className="label">프로그램 구성</label>
                <div className="flex flex-wrap gap-2">
                  {[["experience","체험"],["food","먹거리"],["performance","공연"],["celebrity","셀럽"],["kcontent","K콘텐츠"]].map(([k, lbl]) => (
                    <button key={k} onClick={() => toggle(k)} type="button"
                      className={`px-3 py-1.5 rounded-full text-sm border ${f.content[k] ? "bg-teal text-black border-teal font-semibold" : "border-line text-muted"}`}>{lbl}</button>
                  ))}
                </div>
              </div>
              <button className="btn mt-2" onClick={runPredict} disabled={busy}>{busy ? "분석 중…" : "AI 흥행 예보 실행"}</button>
            </div>
          </div>

          {/* 결과 */}
          <div className="card p-5">
            <h2 className="font-bold text-lg mb-4">AI 분석 결과</h2>
            {!result && <div className="text-muted text-sm">왼쪽에서 기획안을 입력하고 실행하세요.</div>}
            {result && (
              <div className="flex flex-col gap-5">
                <div className="grid grid-cols-2 gap-4 items-center">
                  <ScoreGauge score={result.appeal_score} grade={result.grade} />
                  <div>
                    <div className="text-2xl font-extrabold tabular-nums">{result.expected_visitors.toLocaleString()}<span className="text-sm text-muted font-normal">명</span></div>
                    <div className="text-xs text-muted">예상 방문객 · 성공확률 {Math.round(result.success_probability * 100)}%</div>
                    <div className="text-sm mt-2">내국 {result.domestic.toLocaleString()} · <span className="text-amber">외국 {result.foreign.toLocaleString()}</span></div>
                  </div>
                </div>
                <div><div className="text-sm font-bold text-muted mb-2">흥행 요인</div><FactorBars factors={result.top_factors} /></div>
                <div><div className="text-sm font-bold text-muted mb-2">방문자 확률 예보</div><DistBars buckets={result.distribution} interval={result.interval_80} /></div>
                {result.overcrowding?.prob_pct != null && (
                  <div className="text-sm p-3 rounded-lg bg-surface2">쏠림 위험: <b className={result.overcrowding.risk === "높음" ? "text-bad" : result.overcrowding.risk === "주의" ? "text-warn" : "text-good"}>{result.overcrowding.risk}</b> · 수용 초과 확률 {result.overcrowding.prob_pct}%</div>
                )}
                <div>
                  <div className="text-sm font-bold text-muted mb-2">기획 보완 피드백 ({result.feedback.length})</div>
                  <div className="flex flex-col gap-2">
                    {result.feedback.slice(0, 6).map((fb: any, i: number) => (
                      <div key={i} className="text-sm border-l-2 border-amber pl-3 py-1">
                        <b>{fb.issue}</b> — <span className="text-muted">{fb.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="text-sm p-3 rounded-lg bg-[#123236]">
                  <b className="text-tealink">마케팅</b> · 타깃 {result.marketing.primary_segment} · {result.marketing.recommended_channels.join(", ")}
                </div>
                <button className="btn-ghost" onClick={downloadPdf}>📄 PDF 보고서 다운로드</button>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "generate" && (
        <div className="grid lg:grid-cols-2 gap-5 mt-5">
          <div className="card p-5">
            <h2 className="font-bold text-lg mb-4">생성형 기획자</h2>
            <div className="flex flex-col gap-3">
              <div><label className="label">예산(백만원)</label><input className="input" type="number" value={genReq.budget_mil_won} onChange={e => setGenReq({ ...genReq, budget_mil_won: Number(e.target.value) })} /></div>
              <div><label className="label">타깃</label><input className="input" value={genReq.target_audience} onChange={e => setGenReq({ ...genReq, target_audience: e.target.value })} placeholder="예: 20대" /></div>
              <div><label className="label">지역</label><input className="input" value={genReq.region} onChange={e => setGenReq({ ...genReq, region: e.target.value })} placeholder="예: 서울 근교" /></div>
              <div><label className="label">테마(선택)</label><input className="input" value={genReq.theme} onChange={e => setGenReq({ ...genReq, theme: e.target.value })} /></div>
              <button className="btn mt-2" onClick={runGenerate} disabled={busy}>{busy ? "생성 중…" : "AI 기획서 생성"}</button>
            </div>
          </div>
          <div className="card p-5">
            <h2 className="font-bold text-lg mb-4">AI 생성 기획서</h2>
            {!gen && <div className="text-muted text-sm">조건을 입력하면 컨셉·프로그램·예산배분·운영·리스크를 생성합니다.</div>}
            {gen && (
              <div className="flex flex-col gap-4 text-sm">
                <div><b className="text-teal">컨셉</b><div className="mt-1">{gen.concept}</div></div>
                {gen.predicted_visitors && <div className="p-2 rounded bg-surface2">예상 방문 <b className="tabular-nums">{Number(gen.predicted_visitors).toLocaleString()}명</b> · 성공확률 {Math.round((gen.success_probability || 0) * 100)}%</div>}
                <div><b className="text-teal">프로그램</b><ul className="list-disc ml-5 mt-1 text-muted">{(gen.programs || []).map((p: string, i: number) => <li key={i}>{p}</li>)}</ul></div>
                <div><b className="text-teal">홍보 전략</b><ul className="list-disc ml-5 mt-1 text-muted">{(gen.promotion || []).map((p: string, i: number) => <li key={i}>{p}</li>)}</ul></div>
                <div><b className="text-teal">예산 배분</b>
                  <div className="mt-1 text-muted">{Object.entries(gen.budget_allocation || {}).map(([k, v]) => `${k} ${v}%`).join(" · ")}</div></div>
                <div><b className="text-teal">예상 문제와 해결</b>
                  <ul className="list-disc ml-5 mt-1 text-muted">{(gen.risks || []).map((r: any, i: number) => <li key={i}>{r.risk} → {r.solution}</li>)}</ul></div>
                <div className="text-xs text-muted">생성: {gen.generated_by}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
