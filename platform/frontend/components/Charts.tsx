"use client";

export function ScoreGauge({ score, grade }: { score: number; grade: string }) {
  return (
    <div>
      <div className="text-5xl font-extrabold text-teal tabular-nums">{Math.round(score)}</div>
      <div className="inline-block mt-2 text-xs font-bold px-3 py-1 rounded-full bg-[#123236] text-tealink">{grade}</div>
      <div className="h-3 rounded-full mt-3" style={{ background: "linear-gradient(90deg,#e08066,#e0b25b,#57bd93)", position: "relative" }}>
        <div style={{ position: "absolute", left: `${Math.max(0, Math.min(100, score))}%`, top: -4, width: 4, height: 20, background: "#e9efec", borderRadius: 2, transform: "translateX(-2px)" }} />
      </div>
      <div className="flex justify-between text-[11px] text-muted mt-1"><span>재검토</span><span>보통</span><span>유력</span></div>
    </div>
  );
}

export function FactorBars({ factors }: { factors: { factor: string; score: number }[] }) {
  const label: Record<string, string> = { weather: "날씨", demand: "수요·입지", program: "프로그램", timing: "시기", reputation: "평판·이력" };
  return (
    <div className="flex flex-col gap-2.5">
      {factors.map(f => (
        <div key={f.factor} className="grid items-center gap-3" style={{ gridTemplateColumns: "90px 1fr 40px" }}>
          <span className="text-sm">{label[f.factor] || f.factor}</span>
          <span className="h-2.5 rounded-full bg-surface2 overflow-hidden">
            <span className="block h-full rounded-full" style={{ width: `${f.score}%`, background: "linear-gradient(90deg,#8fe0e7,#56c6d1)" }} />
          </span>
          <span className="text-xs text-muted text-right tabular-nums">{Math.round(f.score)}</span>
        </div>
      ))}
    </div>
  );
}

export function DistBars({ buckets, interval }: { buckets: { range: string; prob_pct: number }[]; interval: number[] }) {
  const max = Math.max(...buckets.map(b => b.prob_pct), 1);
  return (
    <div>
      <div className="text-sm text-muted mb-2">80% 예측구간 <b className="text-ink tabular-nums">{interval[0].toLocaleString()}~{interval[1].toLocaleString()}명</b></div>
      <div className="flex items-end gap-[2px] h-28">
        {buckets.map((b, i) => (
          <div key={i} title={`${b.range} · ${b.prob_pct}%`} className="flex-1 rounded-t"
            style={{ height: `${(b.prob_pct / max) * 100}%`, background: "#56c6d1", minWidth: 2 }} />
        ))}
      </div>
    </div>
  );
}
