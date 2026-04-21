"""앱 전역 설정 상수 — 환경변수 오버라이드 지원."""
import os

# Gemini 기본 모델 (조사계획 · 수집 · 요약 · 평가 등 일반 작업)
# gemini-2.0-flash: 2026-03-06 이후 신규 키 차단, 2026-06-01 완전 종료
# gemini-2.5-flash: GA 릴리즈, 신규 키 즉시 사용 가능
# 재빌드 없이 변경하려면: 환경변수 GEMINI_MODEL 또는 Settings DB에 값 설정
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Gemini 분석 모델 (프리미엄 인사이트 전용 — 고품질 전략 분석)
# gemini-2.5-pro: 복잡한 추론·전략 도출에 최적화된 최상위 모델
# 재빌드 없이 변경하려면: 환경변수 GEMINI_ANALYSIS_MODEL 또는 Settings DB에 값 설정
GEMINI_ANALYSIS_MODEL = os.getenv("GEMINI_ANALYSIS_MODEL", "gemini-2.5-pro")
