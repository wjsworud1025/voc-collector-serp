import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { setApiPort } from "./lib/api";

function renderApp() {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  );
}

async function initApp() {
  // Tauri v2: window.__TAURI__ 는 기본 undefined.
  // isTauri() 는 window.__TAURI_INTERNALS__ 를 체크하는 공식 API.
  const { isTauri, invoke } = await import("@tauri-apps/api/core");
  const { listen } = await import("@tauri-apps/api/event");

  if (!isTauri()) {
    // 웹 브라우저 개발 서버 — 즉시 렌더링
    renderApp();
    return;
  }

  let rendered = false;

  // 1. listener 먼저 등록 (이벤트 누락 방지)
  const unlisten = await listen<number>("backend-ready", (event) => {
    if (!rendered) {
      rendered = true;
      setApiPort(event.payload);
      unlisten();
      renderApp();
    }
  });

  // 2. 이미 백엔드가 준비된 경우 즉시 렌더링
  try {
    const port = await invoke<number>("get_api_port");
    if (!rendered) {
      rendered = true;
      setApiPort(port);
      unlisten();
      renderApp();
    }
  } catch {
    // 아직 준비 중 — backend-ready 이벤트 대기
  }
}

initApp();
