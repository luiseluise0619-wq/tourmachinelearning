"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", name: "", org: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const res = mode === "login"
        ? await api.login({ email: form.email, password: form.password })
        : await api.register(form);
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (e: any) {
      setErr(e.message);
    } finally { setLoading(false); }
  };

  return (
    <main className="max-w-md mx-auto px-6 py-24">
      <h1 className="text-2xl font-extrabold">{mode === "login" ? "로그인" : "회원가입"}</h1>
      <p className="text-muted text-sm mt-1">FestCast 축제 기획 AI</p>
      <form onSubmit={submit} className="card p-6 mt-6 flex flex-col gap-4">
        {mode === "register" && (
          <>
            <div><label className="label">이름</label>
              <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            <div><label className="label">소속 기관</label>
              <input className="input" placeholder="○○시청" value={form.org} onChange={e => setForm({ ...form, org: e.target.value })} /></div>
          </>
        )}
        <div><label className="label">이메일</label>
          <input className="input" type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
        <div><label className="label">비밀번호</label>
          <input className="input" type="password" required value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
        {err && <div className="text-bad text-sm">{err}</div>}
        <button className="btn" disabled={loading}>{loading ? "처리 중…" : mode === "login" ? "로그인" : "가입하기"}</button>
      </form>
      <button className="text-tealink text-sm mt-4"
        onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "계정이 없으신가요? 회원가입" : "이미 계정이 있으신가요? 로그인"}
      </button>
    </main>
  );
}
