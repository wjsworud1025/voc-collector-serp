/** 결과 검토 페이지 — VOC 카드 그리드 + 승인/제외 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, type VocItemData } from "../lib/api";
import VocCard from "../components/VocCard";

export default function ReviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [items, setItems] = useState<VocItemData[]>([]);
  const [filter, setFilter] = useState({ sentiment: "all", platform: "all" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    api
      .getProject(projectId)
      .then((data) => setItems(data.voc_items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  // 필터 적용
  const filtered = items.filter((item) => {
    if (filter.sentiment !== "all" && item.sentiment !== filter.sentiment)
      return false;
    if (filter.platform !== "all" && item.platform !== filter.platform)
      return false;
    return true;
  });

  // 통계
  const approved = items.filter((i) => i.approved === 1).length;
  const excluded = items.filter((i) => i.approved === -1).length;
  const platforms = [...new Set(items.map((i) => i.platform))];

  const toggleApprove = (id: string, approved: boolean) => {
    const value = approved ? 1 : -1;
    setItems((prev) =>
      prev.map((i) => (i.id === id ? { ...i, approved: value } : i)),
    );
    if (projectId) {
      api.approveVoc(projectId, id, value).catch(() => {});
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-400">데이터 로딩 중...</div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">수집 결과 검토</h1>
          <p className="text-sm text-gray-500">
            총 {items.length}건 | 승인 {approved}건 | 제외 {excluded}건
          </p>
        </div>
        <button
          onClick={() => navigate(`/report/${projectId}`)}
          className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
        >
          PDF 보고서 생성 →
        </button>
      </div>

      {/* 필터 */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filter.sentiment}
          onChange={(e) =>
            setFilter((f) => ({ ...f, sentiment: e.target.value }))
          }
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="all">감성: 전체</option>
          <option value="positive">긍정</option>
          <option value="negative">부정</option>
          <option value="neutral">중립</option>
        </select>

        <select
          value={filter.platform}
          onChange={(e) =>
            setFilter((f) => ({ ...f, platform: e.target.value }))
          }
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="all">플랫폼: 전체</option>
          {platforms.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      {/* VOC 카드 그리드 */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          필터 조건에 맞는 결과가 없습니다.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <VocCard
              key={item.id}
              item={item}
              onApprove={() => toggleApprove(item.id, true)}
              onExclude={() => toggleApprove(item.id, false)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
