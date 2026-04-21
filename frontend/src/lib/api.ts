/** Backend API 클라이언트 */

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown; // Tauri v2 내부 API (isTauri() 체크용)
    __API_PORT__?: number;
  }
}

function getApiBase(): string {
  // Tauri 앱에서 백엔드 포트가 주입된 경우
  if (typeof window !== "undefined" && window.__API_PORT__) {
    return `http://127.0.0.1:${window.__API_PORT__}/api`;
  }
  // Vite 개발 서버 프록시 (기존 동작)
  return "/api";
}

let API_BASE = getApiBase();

/** Tauri backend-ready 이벤트 수신 후 포트를 갱신한다 */
export function setApiPort(port: number): void {
  window.__API_PORT__ = port;
  API_BASE = `http://127.0.0.1:${port}/api`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json();
}

// ── 프로젝트 ──

export interface Project {
  id: string;
  name: string;
  user_request: string;
  status: string;
  created_at: string;
  voc_count: number;
}

export const api = {
  // 프로젝트
  createProject: (user_request: string) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ user_request }),
    }),

  listProjects: () => request<Project[]>("/projects"),

  getProject: (id: string) =>
    request<{ project: Project; voc_items: VocItemData[] }>(`/projects/${id}`),

  // 에이전트
  startAgent: (projectId: string) =>
    `${API_BASE}/agent/${projectId}/start`,  // SSE URL 반환

  stopAgent: (projectId: string) =>
    request<{ ok: boolean }>(`/agent/${projectId}/stop`, { method: "POST" }),

  // 보고서
  generateReport: (projectId: string, reportType: string = "standard") =>
    request<{ ok: boolean; project_id: string; report_type: string; voc_count: number; download_url: string }>(
      `/reports/${projectId}/generate`,
      {
        method: "POST",
        body: JSON.stringify({ report_type: reportType }),
      },
    ),

  reportStatus: (projectId: string, reportType: string = "standard") =>
    request<{ exists: boolean; size: number; report_type: string }>(
      `/reports/${projectId}/status?report_type=${reportType}`,
    ),

  reportDownloadUrl: (projectId: string, reportType: string = "standard") =>
    `${getApiBase()}/reports/${projectId}/download?report_type=${reportType}`,

  analysisStatus: (projectId: string) =>
    request<{ exists: boolean; generated_at: string | null }>(
      `/reports/${projectId}/analysis/status`,
    ),

  regenerateAnalysis: (projectId: string) =>
    request<{ ok: boolean; message: string }>(
      `/reports/${projectId}/analysis/regenerate`,
      { method: "POST" },
    ),

  // 설정
  getSettings: () => request<Record<string, string>>("/settings"),

  updateSetting: (key: string, value: string) =>
    request<{ ok: boolean }>("/settings", {
      method: "PUT",
      body: JSON.stringify({ key, value }),
    }),

  // VOC 승인/제외 (1=승인, -1=제외, 0=미결정)
  approveVoc: (projectId: string, vocId: string, approved: number) =>
    request<{ ok: boolean }>(`/projects/${projectId}/voc/${vocId}`, {
      method: "PATCH",
      body: JSON.stringify({ approved }),
    }),
};

// ── 타입 ──

export interface VocItemData {
  id: string;
  project_id: string;
  platform: string;
  sentiment: string;
  original_text: string;
  translated_text: string;
  source_url: string;
  author: string | null;
  date: string | null;
  topics_json: string;
  content_hash: string;
  confidence: number;
  confidence_label: string;
  collection_method: string;
  approved: number;
  created_at: string;
}

export interface AgentEvent {
  type: string;
  message: string;
  data: Record<string, any>;
  timestamp: string;
}
