"use client";

import React, { useState } from 'react';
import axios from 'axios';

interface FestivalFormProps {
  onSuccess: (id: number) => void;
}

export default function FestivalForm({ onSuccess }: FestivalFormProps) {
  const [formData, setFormData] = useState({
    name: '', region: '', location: '중앙 공원', start_date: '', end_date: '',
    duration_days: 3, event_time: '10:00 - 22:00', area_size: 10000, is_free: true,
    expected_budget: 100000000, promo_budget: 10000000, staff_count: 50, volunteer_count: 20,
    population: 500000, tourist_count: 50000, foreign_visitors: 1000,
    public_transport_access: 7.5, parking_capacity: 1000, lodging_count: 50,
    avg_temp: 20, rain_prob: 0.1,
    program_count: 15, has_experience: false, has_food: true, has_celebrity: false,
    search_volume: 5000, sns_mentions: 1000,
    toilets_count: 20, police_count: 10, medical_staff_count: 5
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target as HTMLInputElement;
    let val: any = value;
    if (type === 'checkbox') {
      val = (e.target as HTMLInputElement).checked;
    } else if (type === 'number') {
      val = Number(value);
    }
    setFormData(prev => ({ ...prev, [name]: val }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post('http://localhost:8000/api/festivals', formData);
      onSuccess(res.data.id);
    } catch (err) {
      console.error(err);
      alert('저장 중 오류가 발생했습니다.');
    }
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-8 rounded shadow max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-semibold mb-6 border-b pb-2">기본 정보 입력</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">축제명</label>
          <input type="text" name="name" required value={formData.name} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">개최 지역</label>
          <input type="text" name="region" required value={formData.region} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">시작일</label>
          <input type="date" name="start_date" required value={formData.start_date} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">종료일</label>
          <input type="date" name="end_date" required value={formData.end_date} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">개최 장소</label>
          <input type="text" name="location" required value={formData.location} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">행사 시간</label>
          <input type="text" name="event_time" required value={formData.event_time} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">행사 면적 (㎡)</label>
          <input type="number" name="area_size" required value={formData.area_size} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">예상 예산 (원)</label>
          <input type="number" name="expected_budget" required value={formData.expected_budget} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">홍보 예산 (원)</label>
          <input type="number" name="promo_budget" required value={formData.promo_budget} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
           <label className="flex items-center mt-6">
            <input type="checkbox" name="is_free" checked={formData.is_free} onChange={handleChange} className="rounded border-gray-300 text-indigo-600 shadow-sm" />
            <span className="ml-2 text-sm text-gray-700">무료 입장</span>
          </label>
        </div>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-6 border-b pb-2">콘텐츠 및 환경 변수</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
         <div>
          <label className="block text-sm font-medium text-gray-700">프로그램 수</label>
          <input type="number" name="program_count" value={formData.program_count} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">평균 기온 (℃)</label>
          <input type="number" name="avg_temp" value={formData.avg_temp} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">강수 확률 (0~1)</label>
          <input type="number" name="rain_prob" step="0.1" value={formData.rain_prob} onChange={handleChange} className="mt-1 block w-full rounded border-gray-300 shadow-sm p-2 border" />
        </div>
        <div className="flex space-x-4 col-span-full">
           <label className="flex items-center">
            <input type="checkbox" name="has_experience" checked={formData.has_experience} onChange={handleChange} className="rounded border-gray-300 text-indigo-600" />
            <span className="ml-2 text-sm text-gray-700">체험형 프로그램</span>
          </label>
          <label className="flex items-center">
            <input type="checkbox" name="has_celebrity" checked={formData.has_celebrity} onChange={handleChange} className="rounded border-gray-300 text-indigo-600" />
            <span className="ml-2 text-sm text-gray-700">유명 연예인 출연</span>
          </label>
        </div>
      </div>

      <div className="pt-6">
        <button type="submit" disabled={loading} className="w-full bg-indigo-600 text-white p-3 rounded shadow font-semibold hover:bg-indigo-700 disabled:opacity-50">
          {loading ? '저장 중...' : '데이터 저장 및 AI 분석 대기'}
        </button>
      </div>
    </form>
  );
}
