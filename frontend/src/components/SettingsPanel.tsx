/** API 키 설정 패널 — 발급 가이드 포함 */

import { useState, useEffect } from "react";
import { api } from "../lib/api";

interface SettingDef {
  key: string;
  label: string;
  placeholder: string;
  type?: "text" | "password" | "select";
  options?: { value: string; label: string }[];
  guide: {
    title: string;
    free: boolean;
    steps: { text: string; url?: string; urlLabel?: string }[];
    note?: string;
  };
}

const SETTINGS: SettingDef[] = [
  {
    key: "GEMINI_API_KEY",
    label: "Gemini API 키",
    placeholder: "AIzaSy...",
    guide: {
      title: "Google AI Studio에서 무료 발급",
      free: true,
      steps: [
        {
          text: "아래 링크에서 Google AI Studio 접속 (구글 계정 로그인)",
          url: "https://aistudio.google.com/apikey",
          urlLabel: "Google AI Studio 열기",
        },
        { text: '상단의 "Get API key" 버튼 클릭' },
        { text: '"Create API key" 선택 → 프로젝트는 "Create in new project"로 생성' },
        { text: "생성된 키(AIzaSy...로 시작) 복사 후 위 입력란에 붙여넣기" },
      ],
      note: "무료 티어: 분당 15회, 일 1,500회 요청 가능. 일반 조사엔 충분합니다.",
    },
  },
  {
    key: "SERPAPI_KEY",
    label: "SerpApi 키 (Google 검색)",
    placeholder: "be6fb3...",
    guide: {
      title: "SerpApi.com에서 무료 발급 (월 250회 무료)",
      free: true,
      steps: [
        {
          text: "SerpApi 사이트 접속 후 무료 회원가입",
          url: "https://serpapi.com/users/sign_up",
          urlLabel: "SerpApi 회원가입",
        },
        {
          text: "이메일 인증 완료 후 Dashboard → API Key 메뉴 이동",
          url: "https://serpapi.com/manage-api-key",
          urlLabel: "API Key 관리",
        },
        { text: "Your Private API Key 값 전체 복사 후 위 입력란에 붙여넣기" },
      ],
      note: "무료 플랜: 월 250회 검색. 1개 프로젝트당 약 5~10회 소비. 한도 초과 시 $50/월 플랜으로 5,000회 사용 가능.",
    },
  },
  {
    key: "GEMINI_MODEL",
    label: "Gemini 기본 모델 (조사계획·수집·요약)",
    placeholder: "gemini-2.5-flash",
    type: "select",
    options: [
      { value: "gemini-2.5-flash", label: "gemini-2.5-flash (기본 · 빠름)" },
      { value: "gemini-2.5-pro",   label: "gemini-2.5-pro (고품질 · 느림)" },
      { value: "gemini-2.0-flash", label: "gemini-2.0-flash (구버전)" },
    ],
    guide: {
      title: "Gemini 기본 모델 선택",
      free: false,
      steps: [
        { text: "조사계획 수립, 리뷰 요약, 감성 분석 등 일반 작업에 사용되는 모델입니다." },
        { text: "기본값 gemini-2.5-flash는 속도와 품질의 균형이 잡혀 있어 대부분의 조사에 적합합니다." },
        { text: "빈칸으로 두면 기본값(gemini-2.5-flash)이 자동 적용됩니다." },
      ],
      note: "모델 변경은 재빌드 없이 즉시 반영됩니다. 변경 후 [저장]을 클릭하세요.",
    },
  },
  {
    key: "GEMINI_ANALYSIS_MODEL",
    label: "Gemini 분석 모델 (프리미엄 인사이트 전용)",
    placeholder: "gemini-2.5-pro",
    type: "select",
    options: [
      { value: "gemini-2.5-pro",   label: "gemini-2.5-pro (기본 · 고품질 전략 분석)" },
      { value: "gemini-2.5-flash", label: "gemini-2.5-flash (빠름 · 비용 절감)" },
    ],
    guide: {
      title: "프리미엄 인사이트 분석 모델 선택",
      free: false,
      steps: [
        { text: "프리미엄 보고서의 전략적 인사이트·페르소나·마케팅 전략 생성에 사용되는 모델입니다." },
        { text: "gemini-2.5-pro는 복잡한 추론과 전략 도출에 최적화된 최상위 모델입니다." },
        { text: "빈칸으로 두면 기본값(gemini-2.5-pro)이 자동 적용됩니다." },
      ],
      note: "프리미엄 분석은 1회 실행 시 요청 수가 많아 무료 티어 한도에 주의하세요.",
    },
  },
  {
    key: "YOUTUBE_API_KEY",
    label: "YouTube API 키",
    placeholder: "AIzaSy...",
    guide: {
      title: "Google Cloud Console에서 발급 (YouTube Data API v3)",
      free: true,
      steps: [
        {
          text: "YouTube Data API v3 먼저 활성화",
          url: "https://console.cloud.google.com/apis/library/youtube.googleapis.com",
          urlLabel: "YouTube API 활성화",
        },
        {
          text: "Credentials 페이지에서 새 API 키 생성",
          url: "https://console.cloud.google.com/apis/credentials",
          urlLabel: "Credentials 페이지",
        },
        {
          text: '"+ CREATE CREDENTIALS" → "API key" 클릭 → 생성된 키(AIzaSy...) 복사 후 입력',
        },
      ],
      note: "무료 티어: 하루 10,000 유닛 (검색 100회, 댓글 1회 수집 = 각 100 유닛). 일반 조사에 충분합니다.",
    },
  },
];

export default function SettingsPanel() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [showVal, setShowVal] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.getSettings().then(setValues).catch(() => {});
  }, []);

  const handleSave = async (key: string) => {
    setSaving(key);
    try {
      await api.updateSetting(key, values[key] || "");
      setSaved((prev) => ({ ...prev, [key]: true }));
      setTimeout(() => setSaved((prev) => ({ ...prev, [key]: false })), 2000);
    } catch (e: any) {
      alert(`저장 실패: ${e.message}`);
    } finally {
      setSaving(null);
    }
  };

  const toggleGuide = (key: string) =>
    setOpen((prev) => ({ ...prev, [key]: !prev[key] }));

  const toggleShow = (key: string) =>
    setShowVal((prev) => ({ ...prev, [key]: !prev[key] }));

  const isFilled = (key: string) => (values[key] || "").trim().length > 0;

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
      <h3 className="font-bold text-gray-800 mb-1">API 설정</h3>
      <p className="text-xs text-gray-500 mb-5">
        VOC 수집에 필요한 API 키를 입력해 주세요. 각 항목 아래 발급 방법이 안내됩니다.
      </p>

      <div className="space-y-6">
        {SETTINGS.map(({ key, label, placeholder, type, options, guide }) => (
          <div key={key}>
            {/* 라벨 + 상태 */}
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-gray-700">
                {label}
              </label>
              {type !== "select" && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    isFilled(key)
                      ? "bg-green-100 text-green-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {isFilled(key) ? "✓ 입력됨" : "미입력"}
                </span>
              )}
            </div>

            {/* 입력 + 저장 */}
            <div className="flex gap-2">
              {type === "select" && options ? (
                <select
                  value={values[key] || ""}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                >
                  <option value="">기본값 사용 ({placeholder})</option>
                  {options.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              ) : (
                <>
                  <input
                    type={showVal[key] ? "text" : "password"}
                    value={values[key] || ""}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                    placeholder={placeholder}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm
                               focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    onClick={() => toggleShow(key)}
                    title={showVal[key] ? "숨기기" : "보기"}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-500 hover:bg-gray-50"
                  >
                    {showVal[key] ? "🙈" : "👁️"}
                  </button>
                </>
              )}
              <button
                onClick={() => handleSave(key)}
                disabled={saving === key}
                className={`px-4 py-2 rounded-lg text-sm text-white transition-colors ${
                  saved[key]
                    ? "bg-green-600"
                    : "bg-gray-800 hover:bg-gray-900 disabled:opacity-50"
                }`}
              >
                {saved[key] ? "✓ 저장됨" : saving === key ? "..." : "저장"}
              </button>
            </div>

            {/* 발급 가이드 토글 */}
            <button
              onClick={() => toggleGuide(key)}
              className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
            >
              <span>{open[key] ? "▲" : "▼"}</span>
              <span>발급 방법 보기</span>
              {guide.free && (
                <span className="ml-1 bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] font-bold">
                  무료
                </span>
              )}
            </button>

            {/* 가이드 내용 */}
            {open[key] && (
              <div className="mt-2 bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm">
                <p className="font-medium text-blue-800 mb-3">{guide.title}</p>
                <ol className="space-y-2">
                  {guide.steps.map((step, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                        {i + 1}
                      </span>
                      <span className="text-gray-700 leading-snug">
                        {step.text}
                        {step.url && (
                          <>
                            {" "}
                            <a
                              href={step.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-block bg-indigo-600 text-white text-xs px-2 py-0.5 rounded hover:bg-indigo-700 ml-1"
                            >
                              {step.urlLabel ?? step.url} ↗
                            </a>
                          </>
                        )}
                      </span>
                    </li>
                  ))}
                </ol>
                {guide.note && (
                  <p className="mt-3 text-xs text-blue-600 bg-blue-100 px-3 py-2 rounded">
                    💡 {guide.note}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 mt-6 pt-4 border-t border-gray-100">
        🔒 입력한 키는 이 PC의 로컬 SQLite DB에만 저장되며 외부 서버로 전송되지 않습니다.
      </p>
    </div>
  );
}
