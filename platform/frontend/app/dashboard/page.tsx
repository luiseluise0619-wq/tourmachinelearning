"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken } from "@/lib/api";

export default function Dashboard() {
  const router = useRouter();
  const [projects, setProjects] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");

  const load = async () => {
    try { setProjects(await api.projects()); }
    catch (e: any) { setErr(e.message); }
  };

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await api.createProject({ name });
    setName(""); load();
  };

  return (
    <main className="max-w-4xl mx-auto px-6 py-14">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">내 프로젝트</h1>
        <button className="btn-ghost text-sm" onClick={() => { clearToken(); router.push("/login"); }}>로그아웃</button>
      </div>

      <form onSubmit={create} className="card p-4 mt-6 flex gap-3">
        <input className="input" placeholder="새 프로젝트 이름 (예: 2026 가을축제 검토)"
          value={name} onChange={e => setName(e.target.value)} />
        <button className="btn whitespace-nowrap">＋ 생성</button>
      </form>
      {err && <div className="text-bad text-sm mt-3">{err}</div>}

      <div className="grid md:grid-cols-2 gap-3 mt-6">
        {projects.map(p => (
          <Link key={p.id} href={`/projects/${p.id}`} className="card p-5 hover:border-teal transition">
            <div className="font-bold text-lg">{p.name}</div>
            <div className="text-muted text-sm mt-1">{p.description || "축제 기획안을 입력해 AI 분석을 받으세요"}</div>
          </Link>
        ))}
        {projects.length === 0 && <div className="text-muted text-sm">아직 프로젝트가 없습니다. 위에서 생성하세요.</div>}
      </div>
    </main>
  );
}
