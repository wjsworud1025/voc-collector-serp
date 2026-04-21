/** 에이전트 타임라인 — CLI급 작업 가시화 */

import type { AgentEvent } from "../lib/api";

interface Props {
  events: AgentEvent[];
}

const ICON_MAP: Record<string, string> = {
  state_change: "⏳",
  plan_created: "📋",
  plan_revised: "🔄",
  iteration_start: "🔁",
  task_started: "🔍",
  task_done: "✅",
  task_error: "❌",
  task_skipped: "⏭️",
  item_found: "📌",
  progress: "📊",
  evaluated: "📈",
  completed: "🎉",
  error: "🚨",
  stopped: "⏹️",
  replan_error: "⚠️",
};

const TYPE_STYLE: Record<string, string> = {
  completed: "bg-green-50 border-green-300 text-green-800",
  error: "bg-red-50 border-red-300 text-red-800",
  plan_revised: "bg-amber-50 border-amber-300 text-amber-800",
  evaluated: "bg-blue-50 border-blue-300 text-blue-800",
  item_found: "text-gray-600",
};

export default function AgentTimeline({ events }: Props) {
  // item_found는 요약으로 표시 (너무 많을 수 있으므로)
  const displayEvents = summarizeEvents(events);

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="font-bold text-gray-800 mb-4">작업 타임라인</h3>

      {displayEvents.length === 0 ? (
        <div className="text-center text-gray-400 py-8">
          에이전트 시작 대기 중...
        </div>
      ) : (
        <div className="space-y-2">
          {displayEvents.map((event, i) => {
            const icon = ICON_MAP[event.type] || "•";
            const style = TYPE_STYLE[event.type] || "";
            const elapsed = getElapsed(events[0]?.timestamp, event.timestamp);

            return (
              <div
                key={i}
                className={`flex items-start gap-3 py-2 px-3 rounded-lg text-sm ${style}`}
              >
                <span className="flex-shrink-0 text-base">{icon}</span>
                <div className="flex-1 min-w-0">
                  <span className="font-medium">{event.message}</span>
                  {/* 추가 데이터 표시 */}
                  {event.type === "plan_created" && event.data && (
                    <div className="text-xs mt-1 text-gray-500">
                      키워드: {event.data.keywords?.join(", ")} | 플랫폼:{" "}
                      {event.data.platforms?.join(", ")} | 예상:{" "}
                      {event.data.estimated_total}건
                    </div>
                  )}
                  {event.type === "task_done" && event.data && (
                    <div className="text-xs mt-1 text-gray-500">
                      {event.data.source}: {event.data.collected}건 수집
                      {event.data.duplicates > 0 &&
                        ` (중복 ${event.data.duplicates}건 제거)`}
                    </div>
                  )}
                  {event.type === "plan_revised" && event.data && (
                    <div className="text-xs mt-1">
                      사유: {event.data.reason}
                      {event.data.added_tasks?.map((t: any, j: number) => (
                        <div key={j} className="ml-2">
                          + {t.source}: "{t.query}"
                        </div>
                      ))}
                    </div>
                  )}
                  {event.type === "evaluated" && event.data && (
                    <div className="text-xs mt-1">
                      수집 {event.data.total}건 | 검증 {event.data.verified}건
                      {event.data.gaps?.length > 0 && (
                        <div className="text-amber-600">
                          부족: {event.data.gaps.join(", ")}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {elapsed}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** item_found 이벤트를 그룹 요약으로 변환 */
function summarizeEvents(events: AgentEvent[]): AgentEvent[] {
  const result: AgentEvent[] = [];
  let itemBuffer: AgentEvent[] = [];

  for (const event of events) {
    if (event.type === "item_found") {
      itemBuffer.push(event);
    } else {
      // 버퍼에 쌓인 item_found를 요약
      if (itemBuffer.length > 0) {
        if (itemBuffer.length <= 3) {
          result.push(...itemBuffer);
        } else {
          result.push({
            type: "item_found",
            message: `VOC ${itemBuffer.length}건 수집됨`,
            data: { count: itemBuffer.length },
            timestamp: itemBuffer[itemBuffer.length - 1].timestamp,
          });
        }
        itemBuffer = [];
      }
      result.push(event);
    }
  }

  // 남은 버퍼
  if (itemBuffer.length > 0) {
    if (itemBuffer.length <= 3) {
      result.push(...itemBuffer);
    } else {
      result.push({
        type: "item_found",
        message: `VOC ${itemBuffer.length}건 수집됨`,
        data: { count: itemBuffer.length },
        timestamp: itemBuffer[itemBuffer.length - 1].timestamp,
      });
    }
  }

  return result;
}

/** 경과 시간 계산 */
function getElapsed(startTs: string | undefined, currentTs: string): string {
  if (!startTs) return "";
  try {
    const start = new Date(startTs).getTime();
    const current = new Date(currentTs).getTime();
    const diff = Math.max(0, Math.floor((current - start) / 1000));
    const min = Math.floor(diff / 60);
    const sec = diff % 60;
    return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  } catch {
    return "";
  }
}
