import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import AgentPage from "./pages/AgentPage";
import ReviewPage from "./pages/ReviewPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 상단 네비게이션 */}
      <header className="bg-gradient-to-r from-indigo-900 to-blue-800 text-white px-8 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <a href="/" className="text-xl font-bold tracking-tight">
            VOC Collector
          </a>
          <span className="text-sm opacity-75">
            글로벌 VOC 수집 및 리포팅 시스템
          </span>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-6xl mx-auto px-8 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/agent/:projectId" element={<AgentPage />} />
          <Route path="/review/:projectId" element={<ReviewPage />} />
          <Route path="/report/:projectId" element={<ReportPage />} />
        </Routes>
      </main>
    </div>
  );
}
