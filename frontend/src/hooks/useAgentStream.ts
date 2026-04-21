/** SSE 기반 에이전트 이벤트 스트림 훅 — fetch POST streaming */

import { useState, useCallback, useRef } from "react";
import type { AgentEvent } from "../lib/api";

interface UseAgentStreamReturn {
  events: AgentEvent[];
  isRunning: boolean;
  start: (url: string) => void;
  stop: () => void;
  lastEvent: AgentEvent | null;
}

export function useAgentStream(): UseAgentStreamReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback((url: string) => {
    // 기존 연결 중단
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setEvents([]);
    setIsRunning(true);

    // POST SSE 스트리밍 — fetch로 직접 읽기
    (async () => {
      try {
        const response = await fetch(url, {
          method: "POST",
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          setIsRunning(false);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE 형식: "data: {...}\n\n" 단위로 파싱
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith("data:")) continue;
            try {
              const json = line.slice("data:".length).trim();
              const event: AgentEvent = JSON.parse(json);
              setEvents((prev) => [...prev, event]);

              if (["completed", "error", "stopped"].includes(event.type)) {
                setIsRunning(false);
                return;
              }
            } catch {
              // JSON 파싱 실패 무시
            }
          }
        }
      } catch (e: any) {
        if (e.name !== "AbortError") {
          // 네트워크 오류 — 이미 진행된 이벤트는 유지
        }
      } finally {
        setIsRunning(false);
      }
    })();
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsRunning(false);
  }, []);

  const lastEvent = events.length > 0 ? events[events.length - 1] : null;

  return { events, isRunning, start, stop, lastEvent };
}
