/** 홈페이지 — 자연어 입력 + 프로젝트 목록 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Project } from "../lib/api";
import SettingsPanel from "../components/SettingsPanel";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const project = await api.createProject(query.trim());
      navigate(`/agent/${project.id}`);
    } catch (e: any) {
      alert(`오류: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const statusLabel: Record<string, string> = {
    created: "대기",
    running: "수집 중",
    completed: "완료",
    failed: "실패",
  };

  const statusColor: Record<string, string> = {
    created: "bg-gray-100 text-gray-600",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <div className="space-y-8">
      {/* 자연어 입력 */}
      <section className="bg-white rounded-xl shadow-sm p-8">
        <h2 className="text-lg font-bold text-gray-800 mb-2">
          VOC 조사 요청
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          수집하고 싶은 시장과 제품에 대해 자연어로 설명하세요.
        </p>
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="예: 미국 MZ세대의 제빙기에 대한 VOC를 수집해줘"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg text-sm font-medium
                       hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? "생성 중..." : "조사 시작"}
          </button>
        </div>
      </section>

      {/* 프로젝트 목록 */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-800">프로젝트 목록</h2>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            {showSettings ? "설정 닫기" : "API 설정"}
          </button>
        </div>

        {showSettings && <SettingsPanel />}

        {projects.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">
            아직 프로젝트가 없습니다. 위에서 VOC 조사를 시작하세요.
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((p) => (
              <div
                key={p.id}
                onClick={() => {
                  if (p.status === "completed") navigate(`/review/${p.id}`);
                  else if (p.status === "running") navigate(`/agent/${p.id}`);
                  else navigate(`/agent/${p.id}`);
                }}
                className="bg-white rounded-xl shadow-sm p-5 cursor-pointer
                           hover:shadow-md transition-shadow flex items-center justify-between"
              >
                <div>
                  <h3 className="font-medium text-gray-800">{p.name}</h3>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-1">
                    {p.user_request}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {p.voc_count > 0 && (
                    <span className="text-sm text-gray-500">
                      {p.voc_count}건
                    </span>
                  )}
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      statusColor[p.status] || "bg-gray-100"
                    }`}
                  >
                    {statusLabel[p.status] || p.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
