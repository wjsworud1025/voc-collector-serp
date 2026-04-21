/** VOC 카드 — 감성/출처/신뢰도 표시 */

import type { VocItemData } from "../lib/api";

interface Props {
  item: VocItemData;
  onApprove: () => void;
  onExclude: () => void;
}

const SENTIMENT_CONFIG: Record<string, { color: string; border: string; label: string }> = {
  positive: { color: "bg-green-100 text-green-700", border: "border-l-green-500", label: "긍정" },
  negative: { color: "bg-red-100 text-red-700", border: "border-l-red-500", label: "부정" },
  neutral: { color: "bg-amber-100 text-amber-700", border: "border-l-amber-500", label: "중립" },
};

export default function VocCard({ item, onApprove, onExclude }: Props) {
  const sentiment = SENTIMENT_CONFIG[item.sentiment] || SENTIMENT_CONFIG.neutral;
  const confidence = Math.round((item.confidence || 0) * 100);
  const topics: string[] = item.topics_json ? JSON.parse(item.topics_json) : [];
  const isApproved = item.approved === 1;
  const isExcluded = item.approved === -1;

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border-l-4 ${sentiment.border} p-5
                  ${isExcluded ? "opacity-50" : ""} transition-opacity`}
    >
      {/* 상단: 메타 정보 */}
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <span
          className={`${
            item.confidence_label === "확실"
              ? "bg-indigo-100 text-indigo-700"
              : "bg-gray-100 text-gray-600"
          } px-2 py-0.5 rounded-full text-xs font-medium`}
        >
          {item.confidence_label} ({confidence}%)
        </span>
        <span className={`${sentiment.color} px-2 py-0.5 rounded-full text-xs font-medium`}>
          {sentiment.label}
        </span>
        <span className="bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full text-xs font-medium">
          {item.platform}
        </span>
        {item.date && (
          <span className="text-xs text-gray-400">{item.date}</span>
        )}
        {item.collection_method && (
          <span className="text-xs text-gray-400">
            {item.collection_method === "tier1_api" ? "API" : "웹크롤"}
          </span>
        )}
      </div>

      {/* 원문 */}
      <div className="bg-gray-50 rounded-lg p-3 mb-2">
        <span className="text-[10px] font-bold text-gray-400 uppercase block mb-1">
          원문
        </span>
        <p className="text-sm text-gray-700 leading-relaxed line-clamp-3">
          {item.original_text}
        </p>
      </div>

      {/* 번역 */}
      {item.translated_text && (
        <div className="bg-indigo-50 rounded-lg p-3 mb-2">
          <span className="text-[10px] font-bold text-indigo-400 uppercase block mb-1">
            한국어 번역
          </span>
          <p className="text-sm text-indigo-800 leading-relaxed">
            {item.translated_text}
          </p>
        </div>
      )}

      {/* 하단: 토픽 + 출처 + 버튼 */}
      <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* 토픽 태그 */}
          {topics.map((t, i) => (
            <span
              key={i}
              className="bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full text-xs"
            >
              #{t}
            </span>
          ))}
          {/* 출처 링크 */}
          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:underline truncate max-w-[200px]"
            >
              {new URL(item.source_url).hostname}
            </a>
          )}
        </div>

        {/* 승인/제외 버튼 */}
        <div className="flex gap-2">
          <button
            onClick={onApprove}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              isApproved
                ? "bg-green-600 text-white"
                : "bg-green-50 text-green-700 hover:bg-green-100"
            }`}
          >
            {isApproved ? "✓ 승인됨" : "승인"}
          </button>
          <button
            onClick={onExclude}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              isExcluded
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-700 hover:bg-red-100"
            }`}
          >
            {isExcluded ? "✕ 제외됨" : "제외"}
          </button>
        </div>
      </div>
    </div>
  );
}
