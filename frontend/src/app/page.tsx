"use client";

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import FestivalForm from '../components/FestivalForm';
import AnalysisDashboard from '../components/AnalysisDashboard';

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (isLoggedIn) {
      fetchProjects();
    }
  }, [isLoggedIn]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'admin' && password === 'admin') {
      setIsLoggedIn(true);
    } else {
      alert("Invalid credentials. Use admin/admin");
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/festivals');
      setProjects(res.data);
    } catch (error) {
      console.error("Failed to fetch projects", error);
    }
  };

  const handleProjectCreated = (id: number) => {
    fetchProjects();
    setSelectedProjectId(id);
    setIsCreating(false);
  };

  if (!isLoggedIn) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded shadow-md w-96">
          <h1 className="text-2xl font-bold text-indigo-700 mb-6 text-center">🎪 FestCast 로그인</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">아이디</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">비밀번호</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" required />
            </div>
            <button type="submit" className="w-full bg-indigo-600 text-white p-2 rounded shadow hover:bg-indigo-700">로그인</button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <header className="mb-8 flex justify-between items-center">
        <h1 className="text-3xl font-bold text-indigo-700">🎪 FestCast (축제 흥행예보관)</h1>
        {!isCreating && !selectedProjectId && (
          <button
            onClick={() => setIsCreating(true)}
            className="bg-indigo-600 text-white px-4 py-2 rounded shadow hover:bg-indigo-700 transition"
          >
            새 축제 프로젝트 기획
          </button>
        )}
        {(isCreating || selectedProjectId) && (
          <button
            onClick={() => { setIsCreating(false); setSelectedProjectId(null); }}
            className="text-gray-600 hover:text-gray-900"
          >
            ← 대시보드로 돌아가기
          </button>
        )}
      </header>

      {isCreating ? (
        <FestivalForm onSuccess={handleProjectCreated} />
      ) : selectedProjectId ? (
        <AnalysisDashboard projectId={selectedProjectId} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.length === 0 ? (
            <div className="col-span-full text-center text-gray-500 py-12 bg-white rounded shadow">
              등록된 축제 프로젝트가 없습니다. '새 축제 프로젝트 기획'을 클릭하세요.
            </div>
          ) : (
            projects.map((p) => (
              <div
                key={p.id}
                className="bg-white p-6 rounded shadow cursor-pointer hover:shadow-md transition border border-gray-100"
                onClick={() => setSelectedProjectId(p.id)}
              >
                <h3 className="text-xl font-semibold mb-2">{p.name}</h3>
                <p className="text-gray-600 text-sm mb-4">{p.region} | {p.start_date} ~ {p.end_date}</p>
                <div className="text-sm text-gray-500">
                  <p>예상 예산: {(p.expected_budget / 10000).toLocaleString()}억 원</p>
                  <p>타겟 방문객 수: {p.total_visitors ? p.total_visitors.toLocaleString() : '미정'}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </main>
  );
}
