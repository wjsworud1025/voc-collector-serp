/** 에이전트 실행 페이지 — 실시간 타임라인 */

import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAgentStream } from "../hooks/useAgentStream";
import AgentTimeline from "../components/AgentTimeline";

export default function AgentPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { events, isRunning, start, stop, lastEvent } = useAgentStream();

  useEffect(() => {
    if (!projectId) return;
    start(api.startAgent(projectId));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleStop = async () => {
    if (projectId) {
      await api.stopAgent(projectId);
      stop();
    }
  };

  const isCompleted = lastEvent?.type === "completed";
  const isError = lastEvent?.type === "error";

  // 진행률 계산
  const progressEvent = events.findLast((e) => e.type === "progress");
  const collected = progressEvent?.data?.collected || 0;
  const planEvent = events.find((e) => e.type === "plan_created");
  const estimated = planEvent?.data?.estimated_total || 30;
  const progress = Math.min(Math.round((collected / estimated) * 100), 100);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">VOC 수집 진행</h1>
          <p className="text-sm text-gray-500">프로젝트: {projectId}</p>
        </div>
        <div className="flex gap-3">
          {isRunning && (
            <button
              onClick={handleStop}
              className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600"
            >
              중단
            </button>
          )}
          {isCompleted && (
            <button
              onClick={() => navigate(`/review/${projectId}`)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
            >
              결과 검토 →
            </button>
          )}
        </div>
      </div>

      {/* 진행률 바 */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {isCompleted
              ? "수집 완료"
              : isError
              ? "오류 발생"
              : isRunning
              ? "수집 중..."
              : "대기"}
          </span>
          <span className="text-sm text-gray-500">{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${
              isError ? "bg-red-500" : isCompleted ? "bg-green-500" : "bg-indigo-500"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex gap-4 mt-2 text-xs text-gray-500">
          <span>수집 {collected}건</span>
          {(progressEvent?.data?.dedup ?? 0) > 0 && (
            <span>중복제거 {progressEvent?.data?.dedup}건</span>
          )}
          {(progressEvent?.data?.verified ?? 0) > 0 && (
            <span>검증 {progressEvent?.data?.verified}건</span>
          )}
        </div>
      </div>

      {/* 타임라인 */}
      <AgentTimeline events={events} />

      {/* 완료 요약 */}
      {isCompleted && lastEvent?.data && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6">
          <h3 className="font-bold text-green-800 mb-3">수집 완료 요약</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-700">
                {lastEvent.data.total || 0}
              </div>
              <div className="text-xs text-green-600">총 수집</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-700">
                {lastEvent.data.verified || 0}
              </div>
              <div className="text-xs text-blue-600">검증 완료</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-700">
                {lastEvent.data.duplicates_removed || 0}
              </div>
              <div className="text-xs text-gray-600">중복 제거</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-700">
                {lastEvent.data.iterations || 0}
              </div>
              <div className="text-xs text-purple-600">탐색 반복</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
