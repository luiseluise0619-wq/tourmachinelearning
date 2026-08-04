"use client";

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

export default function AnalysisDashboard({ projectId }: { projectId: number }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const res = await axios.post(`http://localhost:8000/api/festivals/${projectId}/analyze`);
        setData(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalysis();
  }, [projectId]);

  const exportPDF = async () => {
    const element = document.getElementById('report-content');
    if (!element) return;
    const canvas = await html2canvas(element, { scale: 2 });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save(`festival_report_${projectId}.pdf`);
  };

  if (loading) return <div className="text-center p-12">AI 모델이 데이터를 분석하고 기획안을 생성 중입니다...</div>;
  if (!data) return <div className="text-center p-12 text-red-500">데이터를 불러오지 못했습니다.</div>;

  const features = JSON.parse(data.feature_importance);
  const plan = JSON.parse(data.generated_plan);

  // Dummy budget allocation data for the UI enhancement
  const budgetData = [
    { name: '프로그램', value: 40 },
    { name: '운영 및 인건비', value: 30 },
    { name: '홍보/마케팅', value: 15 },
    { name: '시설 및 인프라', value: 10 },
    { name: '예비비', value: 5 },
  ];
  const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ec4899', '#6b7280'];

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="flex justify-end">
        <button onClick={exportPDF} className="bg-red-500 text-white px-4 py-2 rounded shadow hover:bg-red-600">
          PDF 다운로드
        </button>
      </div>

      <div id="report-content" className="bg-white p-8 rounded shadow space-y-8">

        {/* Header KPI */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-indigo-50 p-6 rounded-lg text-center border border-indigo-100">
            <h3 className="text-lg font-medium text-indigo-800 mb-2">예상 방문객 수</h3>
            <p className="text-4xl font-bold text-indigo-900">{data.predicted_visitors.toLocaleString()}명</p>
          </div>
          <div className="bg-green-50 p-6 rounded-lg text-center border border-green-100">
            <h3 className="text-lg font-medium text-green-800 mb-2">AI 흥행 예측 점수</h3>
            <p className="text-4xl font-bold text-green-900">{(data.success_probability * 100).toFixed(1)}점</p>
          </div>
        </div>

        {/* Feature Importance Chart */}
        <div>
          <h3 className="text-xl font-semibold mb-4 border-b pb-2">방문객 수 영향 변수 TOP 10 (Feature Importance)</h3>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={features} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="feature" type="category" width={100} tick={{fontSize: 12}} />
                <Tooltip />
                <Bar dataKey="importance" fill="#4f46e5" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Budget Allocation Pie Chart */}
        <div>
          <h3 className="text-xl font-semibold mb-4 border-b pb-2">추천 예산 배분 (Budget Allocation)</h3>
          <div className="h-64 w-full flex justify-center items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={budgetData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {budgetData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* LLM Generated Plan */}
        <div className="space-y-6">
          <h3 className="text-2xl font-bold text-gray-800 border-b pb-2">생성형 AI 기획 및 운영 전략</h3>

          <div className="bg-gray-50 p-4 rounded border">
            <h4 className="font-semibold text-lg mb-2">핵심 컨셉</h4>
            <p className="text-gray-700">{plan.concept}</p>
            <p className="text-gray-700 mt-2"><span className="font-semibold">타겟 방문객:</span> {plan.target_audience}</p>
          </div>

          <div className="bg-gray-50 p-4 rounded border">
            <h4 className="font-semibold text-lg mb-2">추천 프로그램 구성</h4>
            <ul className="list-disc pl-5 space-y-1">
              {plan.program_plan.map((p: any, idx: number) => (
                <li key={idx} className="text-gray-700"><span className="font-medium">{p.time}</span> : {p.activity}</li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 p-4 rounded border border-blue-100">
              <h4 className="font-semibold text-lg mb-2 text-blue-800">마케팅 전략</h4>
              <p className="text-sm text-gray-700 mb-1"><strong>주요 채널:</strong> {plan.marketing_strategy.main_channel}</p>
              <p className="text-sm text-gray-700 mb-1"><strong>핵심 메시지:</strong> {plan.marketing_strategy.key_message}</p>
              <p className="text-sm text-gray-700"><strong>예산 배분:</strong> {plan.marketing_strategy.budget_allocation}</p>
            </div>

            <div className="bg-yellow-50 p-4 rounded border border-yellow-100">
              <h4 className="font-semibold text-lg mb-2 text-yellow-800">위험 요소 (Risk)</h4>
              <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
                {plan.risk_factors.map((r: string, idx: number) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded border">
            <h4 className="font-semibold text-lg mb-2">운영 및 인력 계획</h4>
            <p className="text-sm text-gray-700 mb-1"><strong>인력:</strong> {plan.operational_plan.staffing}</p>
            <p className="text-sm text-gray-700 mb-1"><strong>안전:</strong> {plan.operational_plan.safety}</p>
            <p className="text-sm text-gray-700"><strong>시설:</strong> {plan.operational_plan.facilities}</p>
          </div>

        </div>

      </div>
    </div>
  );
}
