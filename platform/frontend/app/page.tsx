import Link from "next/link";

export default function Home() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-24">
      <span className="inline-block text-tealink bg-[#123236] px-3 py-1.5 rounded-full text-sm font-semibold">
        🎪 FestCast · 축제 기획 AI SaaS
      </span>
      <h1 className="text-4xl md:text-5xl font-extrabold mt-6 leading-tight tracking-tight">
        축제 흥행을 <span className="text-teal">감이 아니라 데이터로</span> 예보한다
      </h1>
      <p className="text-muted text-lg mt-4 max-w-2xl">
        기획안을 입력하면 AI가 방문객 예측·성공 진단·예산/프로그램/홍보/운영 추천·위험 요소·
        생성형 기획서까지 자동으로 만들어 줍니다. 지자체·축제 운영기관 실무자용.
      </p>
      <div className="flex gap-3 mt-8">
        <Link href="/login" className="btn">시작하기</Link>
        <Link href="/dashboard" className="btn-ghost">대시보드</Link>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-16">
        {[
          ["방문객 예측", "예상 방문객·신뢰구간·성공확률·영향 변수 TOP10"],
          ["성공 진단 & 보완", "약점 요인·위험 요소·개선 처방 자동 생성"],
          ["생성형 기획자", "예산·타깃·지역만 넣으면 컨셉·프로그램·예산배분 생성"],
        ].map(([t, d]) => (
          <div key={t} className="card p-5">
            <div className="font-bold text-lg">{t}</div>
            <div className="text-muted text-sm mt-1.5">{d}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
