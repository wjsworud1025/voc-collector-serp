/** 보고서 페이지 — PDF 생성 + 다운로드 (4종) */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

type Status = "idle" | "checking" | "generating" | "ready" | "error";
type ReportType = "standard" | "executive" | "detailed" | "premium";

const REPORT_TYPES: { key: ReportType; label: string; desc: string; icon: string; premium?: boolean }[] = [
  {
    key: "standard",
    label: "표준 보고서",
    desc: "커버 + 수집 요약 + VOC 상세 목록",
    icon: "📄",
  },
  {
    key: "executive",
    label: "경영진 요약",
    desc: "핵심 수치 + 대표 의견 하이라이트 (1~2페이지)",
    icon: "📊",
  },
  {
    key: "detailed",
    label: "상세 보고서",
    desc: "전문 원문 + 플랫폼별 분석 + 검증 메타데이터 전체 포함",
    icon: "🔍",
  },
  {
    key: "premium",
    label: "Premium 인사이트",
    desc: "AI 전략 분석 9페이지 — 페르소나, 여정, 인사이트, 마케팅 전략 포함",
    icon: "✨",
    premium: true,
  },
];

export default function ReportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [reportType, setReportType] = useState<ReportType>("standard");
  const [status, setStatus] = useState<Status>("checking");
  const [error, setError] = useState("");
  const [vocCount, setVocCount] = useState<number | null>(null);
  const [approvedCount, setApprovedCount] = useState<number | null>(null);
  const [fileSize, setFileSize] = useState<number>(0);
  const [analysisExists, setAnalysisExists] = useState<boolean>(false);
  const [analysisGenerating, setAnalysisGenerating] = useState(false);

  // 마운트 시 기존 보고서 파일 + 프로젝트 데이터 + 분석 상태 확인
  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      api.reportStatus(projectId, reportType),
      api.getProject(projectId),
      api.analysisStatus(projectId).catch(() => ({ exists: false, generated_at: null })),
    ])
      .then(([rs, proj, as_]) => {
        const all = proj.voc_items?.length ?? 0;
        const approved = proj.voc_items?.filter((v) => v.approved === 1).length ?? 0;
        setVocCount(all);
        setApprovedCount(approved);
        setAnalysisExists(as_.exists);
        if (rs.exists) {
          setFileSize(rs.size);
          setStatus("ready");
        } else {
          setStatus("idle");
        }
      })
      .catch(() => setStatus("idle"));
  }, [projectId]);

  // 보고서 종류 바뀌면 해당 파일 존재 여부 재확인
  const handleTypeChange = async (t: ReportType) => {
    setReportType(t);
    setError("");
    if (!projectId) return;
    try {
      const [rs, as_] = await Promise.all([
        api.reportStatus(projectId, t),
        t === "premium"
          ? api.analysisStatus(projectId).catch(() => ({ exists: false, generated_at: null }))
          : Promise.resolve({ exists: analysisExists, generated_at: null }),
      ]);
      setAnalysisExists(as_.exists);
      if (rs.exists) {
        setFileSize(rs.size);
        setStatus("ready");
      } else {
        setStatus("idle");
        setFileSize(0);
      }
    } catch {
      setStatus("idle");
    }
  };

  const handleRegenerateAnalysis = async () => {
    if (!projectId) return;
    setAnalysisGenerating(true);
    try {
      await api.regenerateAnalysis(projectId);
      // 20초 후 상태 재확인 (백그라운드 작업)
      setTimeout(async () => {
        const as_ = await api.analysisStatus(projectId).catch(() => ({ exists: false, generated_at: null }));
        setAnalysisExists(as_.exists);
        setAnalysisGenerating(false);
      }, 20000);
    } catch (e: any) {
      setError(e.message || "분석 생성 실패");
      setAnalysisGenerating(false);
    }
  };

  const handleGenerate = async () => {
    if (!projectId) return;
    setStatus("generating");
    setError("");
    try {
      const res = await api.generateReport(projectId, reportType);
      setVocCount(res.voc_count);
      setStatus("ready");
      const rs = await api.reportStatus(projectId, reportType);
      setFileSize(rs.size);
    } catch (e: any) {
      setError(e.message || "PDF 생성 실패");
      setStatus("error");
    }
  };

  const handleDownload = () => {
    if (!projectId) return;
    const url = api.reportDownloadUrl(projectId, reportType);
    const a = document.createElement("a");
    a.href = url;
    a.download = `voc_report_${projectId}_${reportType}.pdf`;
    a.click();
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  const selectedTypeMeta = REPORT_TYPES.find((t) => t.key === reportType)!;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">PDF 보고서</h1>
          <p className="text-sm text-gray-500">프로젝트 ID: {projectId}</p>
        </div>
        <button
          onClick={() => navigate(`/review/${projectId}`)}
          className="text-sm text-indigo-600 hover:underline"
        >
          ← 검토 화면으로
        </button>
      </div>

      {/* 통계 카드 */}
      {vocCount !== null && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-xl shadow-sm p-5 text-center">
            <div className="text-3xl font-bold text-indigo-600">{vocCount}</div>
            <div className="text-sm text-gray-500 mt-1">총 수집 VOC</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-5 text-center">
            <div className="text-3xl font-bold text-emerald-600">{approvedCount}</div>
            <div className="text-sm text-gray-500 mt-1">승인된 VOC (보고서 포함)</div>
          </div>
        </div>
      )}

      {/* 보고서 종류 선택 */}
      <div className="bg-white rounded-xl shadow-sm p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">보고서 종류 선택</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {REPORT_TYPES.map((t) => (
            <button
              key={t.key}
              onClick={() => handleTypeChange(t.key)}
              className={`text-left p-4 rounded-lg border-2 transition-colors relative ${
                t.premium
                  ? reportType === t.key
                    ? "border-violet-500 bg-violet-50"
                    : "border-violet-200 hover:border-violet-400 hover:bg-violet-50"
                  : reportType === t.key
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
              }`}
            >
              {t.premium && (
                <div className="absolute top-2 right-2 text-xs font-bold text-violet-600 bg-violet-100 px-1.5 py-0.5 rounded">
                  AI
                </div>
              )}
              <div className="text-2xl mb-1">{t.icon}</div>
              <div className={`text-sm font-semibold ${
                t.premium
                  ? reportType === t.key ? "text-violet-700" : "text-violet-600"
                  : reportType === t.key ? "text-indigo-700" : "text-gray-700"
              }`}>
                {t.label}
              </div>
              <div className="text-xs text-gray-500 mt-1 leading-relaxed">{t.desc}</div>
            </button>
          ))}
        </div>

        {/* Premium 분석 상태 표시 */}
        {reportType === "premium" && (
          <div className={`mt-4 p-3 rounded-lg text-sm flex items-center justify-between ${
            analysisExists ? "bg-violet-50 text-violet-700" : "bg-amber-50 text-amber-700"
          }`}>
            <span>
              {analysisExists
                ? "✅ AI 분석 데이터 준비됨 — PDF 생성 가능"
                : "⚠️ AI 분석 데이터 없음 — VOC 수집 완료 후 자동 생성, 또는 아래 버튼으로 수동 생성"}
            </span>
            {!analysisExists && (
              <button
                onClick={handleRegenerateAnalysis}
                disabled={analysisGenerating || (approvedCount ?? 0) === 0}
                className="ml-3 px-4 py-1.5 bg-amber-600 text-white text-xs rounded
                           hover:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {analysisGenerating ? "생성 중..." : "분석 생성"}
              </button>
            )}
            {analysisExists && (
              <button
                onClick={handleRegenerateAnalysis}
                disabled={analysisGenerating}
                className="ml-3 px-3 py-1 border border-violet-300 text-violet-600 text-xs rounded
                           hover:bg-violet-100 disabled:opacity-40"
              >
                {analysisGenerating ? "재생성 중..." : "재생성"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* 메인 카드 */}
      <div className="bg-white rounded-xl shadow-sm p-10 text-center space-y-6">
        {status === "checking" && (
          <p className="text-gray-400 animate-pulse">보고서 상태 확인 중...</p>
        )}

        {status === "idle" && (
          <>
            <div className="text-5xl">{selectedTypeMeta.icon}</div>
            <h2 className="text-lg font-bold text-gray-700">
              {selectedTypeMeta.label}을(를) 생성할 수 있습니다
            </h2>
            <p className="text-sm text-gray-500">
              승인된 VOC {approvedCount ?? 0}건을 기반으로 PDF 보고서를 생성합니다.
            </p>
            {(approvedCount ?? 0) === 0 && (
              <p className="text-sm text-amber-600 bg-amber-50 px-4 py-2 rounded-lg inline-block">
                승인된 VOC가 없습니다. 검토 화면에서 항목을 승인해 주세요.
              </p>
            )}
            <button
              onClick={handleGenerate}
              disabled={(approvedCount ?? 0) === 0}
              className="px-8 py-3 bg-indigo-600 text-white rounded-lg text-sm
                         hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors"
            >
              {selectedTypeMeta.label} 생성
            </button>
          </>
        )}

        {status === "generating" && (
          <>
            <div className="text-5xl animate-bounce">⚙️</div>
            <h2 className="text-lg font-bold text-gray-700">PDF 생성 중...</h2>
            <p className="text-sm text-gray-500">
              {selectedTypeMeta.label}을(를) 생성하고 있습니다. 잠시 기다려 주세요.
            </p>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-indigo-500 h-2 rounded-full animate-pulse w-2/3" />
            </div>
          </>
        )}

        {status === "ready" && (
          <>
            <div className="text-5xl">✅</div>
            <h2 className="text-lg font-bold text-gray-700">{selectedTypeMeta.label} 준비 완료</h2>
            <p className="text-sm text-gray-500">
              승인된 VOC {approvedCount ?? vocCount}건 포함
              {fileSize > 0 && ` · 파일 크기 ${formatSize(fileSize)}`}
            </p>
            <div className="flex gap-3 justify-center flex-wrap">
              <button
                onClick={handleDownload}
                className="px-8 py-3 bg-indigo-600 text-white rounded-lg text-sm
                           hover:bg-indigo-700 transition-colors"
              >
                PDF 다운로드
              </button>
              <button
                onClick={handleGenerate}
                className="px-6 py-3 border border-gray-300 text-gray-600 rounded-lg text-sm
                           hover:bg-gray-50 transition-colors"
              >
                재생성
              </button>
            </div>
          </>
        )}

        {status === "error" && (
          <>
            <div className="text-5xl">❌</div>
            <h2 className="text-lg font-bold text-red-600">생성 실패</h2>
            <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg inline-block">
              {error}
            </p>
            <button
              onClick={handleGenerate}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
            >
              다시 시도
            </button>
          </>
        )}
      </div>

      {/* 보고서 구성 안내 */}
      <div className={`rounded-xl p-4 text-sm ${reportType === "premium" ? "bg-violet-50 text-violet-700" : "bg-blue-50 text-blue-700"}`}>
        <strong>{selectedTypeMeta.icon} {selectedTypeMeta.label} 구성</strong>
        {reportType === "standard" && (
          <ul className="mt-2 space-y-1 list-disc list-inside text-blue-600">
            <li>커버 페이지 (프로젝트명, 생성일, 조사 요청)</li>
            <li>수집 요약 (감성 분포, 플랫폼 분포, 주요 토픽)</li>
            <li>VOC 상세 목록 (원문 최대 400자 + 번역 + 출처 URL)</li>
          </ul>
        )}
        {reportType === "executive" && (
          <ul className="mt-2 space-y-1 list-disc list-inside text-blue-600">
            <li>핵심 KPI 카드 (총 VOC, 긍정/부정/중립 건수 및 비율)</li>
            <li>감성 분포 요약 + 플랫폼별 현황 테이블</li>
            <li>주요 토픽 태그</li>
            <li>긍정 대표 의견 3선 + 부정 대표 의견 3선</li>
          </ul>
        )}
        {reportType === "detailed" && (
          <ul className="mt-2 space-y-1 list-disc list-inside text-blue-600">
            <li>플랫폼별 상세 분석 테이블 (건수, 감성 분포, 평균 신뢰도)</li>
            <li>수집 방법 분포 (API 직접 수집 vs 웹 정적 수집)</li>
            <li>전체 VOC 원문 전문 (무제한) + 번역 전문</li>
            <li>각 VOC별 신뢰도, 수집방법, 작성자, 날짜 전체 메타데이터</li>
          </ul>
        )}
        {reportType === "premium" && (
          <ul className="mt-2 space-y-1 list-disc list-inside text-violet-600">
            <li>Page 1: KPI 대시보드 + 시장 패러다임 변화</li>
            <li>Page 3: 구매자 페르소나 3종 (인용구 포함)</li>
            <li>Page 4: 소비자 구매 여정 5단계 분석</li>
            <li>Page 5: 제품 형태별 비교 + 브랜드 지형도</li>
            <li>Page 6: 하이시그널 VOC 스포트라이트 (복합 점수 상위 5건)</li>
            <li>Page 7: 전략적 인사이트 5개 (우선순위 분류)</li>
            <li>Page 8: 마케팅 전략 전환 방향 테이블</li>
            <li>Page 9: 단기/중기/장기 제품 개발 로드맵</li>
            <li>Appendix 1: 키워드 분포 Top 20 (감성 분류 포함)</li>
          </ul>
        )}
      </div>
    </div>
  );
}
