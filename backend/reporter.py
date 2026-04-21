"""PDF 보고서 생성 — xhtml2pdf + Jinja2 + Freesentation"""

import logging
import os
import sys
import tempfile
from datetime import datetime
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
import xhtml2pdf.files as _xhtml2pdf_files

from models.schemas import ReportAnalysis, VocItem

log = logging.getLogger(__name__)

# ── Windows NamedTemporaryFile(delete=True) 잠금 문제 패치 ──
# xhtml2pdf가 @font-face 폰트를 임시파일로 저장 후 ReportLab이 재-open 시
# Windows에서 PermissionError 발생. delete=False로 패치하여 해결.
if sys.platform == "win32":
    def _patched_get_named_tmp_file(self):
        data = self.get_data()
        tmp_file = tempfile.NamedTemporaryFile(
            suffix=self.suffix, delete=False
        )
        if data:
            tmp_file.write(data)
            tmp_file.flush()
            _xhtml2pdf_files.files_tmp.append(tmp_file)
        if self.path is None:
            self.path = tmp_file.name
        return tmp_file

    # LocalTmpFile 포함 — 모든 하위 클래스 패치
    for _cls_name in [
        "BaseFile", "B64InlineURI", "BytesFileUri",
        "LocalFileURI", "LocalProtocolURI", "NetworkFileUri",
        "LocalTmpFile",
    ]:
        _cls = getattr(_xhtml2pdf_files, _cls_name, None)
        if _cls:
            _cls.get_named_tmp_file = _patched_get_named_tmp_file

# 경로 — 런타임에 해석 (PyInstaller _MEIPASS 안정성)
from paths import get_templates_dir, get_fonts_dir, get_reports_dir


def _get_fonts_dir() -> str:
    """매 호출마다 FONTS_DIR를 새로 해석 — PyInstaller 환경 안정성."""
    d = get_fonts_dir()
    log.debug("FONTS_DIR resolved: %s (exists=%s)", d, os.path.isdir(d))
    return d


# Freesentation 폰트 등록 (최초 1회)
_fonts_registered = False

# 웨이트별 파일 매핑 (Freesentation = 한국어 + 라틴)
_FONT_FILES = {
    "Freesentation-Thin":       "Freesentation-1Thin.ttf",
    "Freesentation-ExtraLight": "Freesentation-2ExtraLight.ttf",
    "Freesentation-Light":      "Freesentation-3Light.ttf",
    "Freesentation":            "Freesentation-4Regular.ttf",
    "Freesentation-Medium":     "Freesentation-5Medium.ttf",
    "Freesentation-SemiBold":   "Freesentation-6SemiBold.ttf",
    "Freesentation-Bold":       "Freesentation-7Bold.ttf",
    "Freesentation-ExtraBold":  "Freesentation-8ExtraBold.ttf",
    "Freesentation-Black":      "Freesentation-9Black.ttf",
}

# ── 다국어 폰트: Windows 시스템 폰트 직접 참조 ──
# 라이선스 우회 + 번들 사이즈 절감 (Windows 전용 데스크톱 앱)
_WIN_FONTS = "C:/Windows/Fonts"
_MULTILANG_FONTS = {
    # CJK (한국+일본+중국) → 맑은고딕
    "MultiCJK":      "malgun.ttf",
    "MultiCJK-Bold": "malgunbd.ttf",
    # Thai/Arabic/Hebrew/Devanagari/기타 다국어 → Tahoma (광범위 커버)
    "MultiSWA":      "tahoma.ttf",
    "MultiSWA-Bold": "tahomabd.ttf",
}


def _register_fonts():
    """pdfmetrics에 Freesentation + 다국어 폰트 등록 (최초 1회)."""
    global _fonts_registered
    if _fonts_registered:
        return
    fonts_dir = _get_fonts_dir()  # 런타임 해석
    registered = []

    # 1) Freesentation (한국어/라틴)
    for font_name, file_name in _FONT_FILES.items():
        font_path = os.path.join(fonts_dir, file_name)
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            registered.append(font_name)
        else:
            log.warning("Font file missing: %s", font_path)
    pdfmetrics.registerFontFamily(
        "Freesentation",
        normal="Freesentation",
        bold="Freesentation-Bold",
        italic="Freesentation",
        boldItalic="Freesentation-Bold",
    )

    # 2) 다국어 시스템 폰트 (Windows)
    for font_name, file_name in _MULTILANG_FONTS.items():
        font_path = os.path.join(_WIN_FONTS, file_name)
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered.append(font_name)
            except Exception as e:
                log.warning("Failed to register %s: %s", font_name, e)
        else:
            log.warning("System font missing: %s", font_path)

    # 3) Family mapping
    for fam, regular, bold in [
        ("MultiCJK", "MultiCJK", "MultiCJK-Bold"),
        ("MultiSWA", "MultiSWA", "MultiSWA-Bold"),
    ]:
        if regular in registered:
            pdfmetrics.registerFontFamily(
                fam, normal=regular,
                bold=bold if bold in registered else regular,
                italic=regular, boldItalic=bold if bold in registered else regular,
            )

    _fonts_registered = True
    log.info("Registered %d fonts (Freesentation + multilang): %s", len(registered), registered)


# ── 텍스트 스크립트 자동 감지 ──
def detect_script(text: str) -> str:
    """텍스트의 주요 스크립트를 감지하여 적절한 폰트 클래스를 반환.

    반환값:
    - "ko"  : 한글 우세/라틴  → Freesentation
    - "cjk" : 일본어/중국어   → 맑은고딕 (한+일+중 통합, CJK Ext A 포함)
    - "swa" : Thai/Arabic/Hebrew/Devanagari → Tahoma (광범위 커버)
    - "cyr" : 러시아어/키릴 계열 → Tahoma (Cyrillic 커버)
    """
    if not text:
        return "ko"
    counts = {"ko": 0, "jp": 0, "cn": 0, "swa": 0, "cyr": 0}
    for ch in text:
        cp = ord(ch)
        if 0xAC00 <= cp <= 0xD7AF:                              # Hangul
            counts["ko"] += 1
        elif 0x3040 <= cp <= 0x30FF:                             # Hiragana/Katakana
            counts["jp"] += 1
        elif (0x4E00 <= cp <= 0x9FFF                             # CJK Unified
              or 0x3400 <= cp <= 0x4DBF):                        # CJK Ext A
            counts["cn"] += 1
        elif (0x0400 <= cp <= 0x04FF                             # Cyrillic
              or 0x0500 <= cp <= 0x052F):                        # Cyrillic Supplement
            counts["cyr"] += 1
        elif (0x0E00 <= cp <= 0x0E7F                             # Thai
              or 0x0600 <= cp <= 0x06FF                          # Arabic
              or 0x0750 <= cp <= 0x077F                          # Arabic Suppl
              or 0x0590 <= cp <= 0x05FF                          # Hebrew
              or 0x0900 <= cp <= 0x097F):                        # Devanagari
            counts["swa"] += 1

    if counts["swa"] > 0:
        return "swa"
    if counts["cyr"] > 0:
        # 키릴 우세 시 cyr (Tahoma), 한글이 더 많으면 ko
        return "ko" if counts["ko"] > counts["cyr"] else "cyr"
    if counts["jp"] > 0 or counts["cn"] > 0:
        # 한글이 더 많으면 ko, 아니면 cjk
        return "ko" if counts["ko"] > counts["jp"] + counts["cn"] else "cjk"
    return "ko"


# Jinja2 (TEMPLATES_DIR는 변하지 않으므로 import 시점 OK)
TEMPLATES_DIR = get_templates_dir()

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)

# Jinja2 필터
def _sentiment_label(s: str) -> str:
    return {"positive": "긍정", "negative": "부정", "neutral": "중립"}.get(s, s)

def _platform_label(p: str) -> str:
    return {"reddit": "Reddit", "google": "Google", "web": "웹 크롤링"}.get(p, p.capitalize())

def _method_label(m: str) -> str:
    return {"tier1_api": "API 직접 수집", "tier2_static": "웹 정적 수집"}.get(m, m)

def _script_class(text: str) -> str:
    """텍스트의 스크립트를 감지하여 CSS 클래스명 반환 (lang-ko/lang-cjk/lang-swa/lang-hindi)."""
    return f"lang-{detect_script(text)}"


_jinja_env.filters["sentiment_label"] = _sentiment_label
_jinja_env.filters["platform_label"] = _platform_label
_jinja_env.filters["method_label"] = _method_label
_jinja_env.filters["script_class"] = _script_class


_TEMPLATE_MAP = {
    "standard":  "report_standard.html",
    "executive": "report_executive.html",
    "detailed":  "report_detailed.html",
    "premium":   "report_premium.html",
}


def generate_pdf(
    project_id: str,
    project_name: str,
    user_request: str,
    voc_items: list[VocItem],
    report_type: str = "standard",
    analysis: "ReportAnalysis | None" = None,
) -> str:
    """
    승인된 VOC 아이템 → PDF 파일 생성.
    report_type: "standard" | "executive" | "detailed" | "premium"
    생성된 파일 경로를 반환한다.
    """
    if report_type not in _TEMPLATE_MAP:
        report_type = "standard"

    _register_fonts()

    # 런타임 FONTS_DIR (link_callback 에서 사용)
    fonts_dir = _get_fonts_dir()

    approved = [v for v in voc_items if v.approved]

    # 통계 계산
    total = len(approved)
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    platform_counts: dict[str, int] = {}
    for item in approved:
        sentiment_counts[item.sentiment] = sentiment_counts.get(item.sentiment, 0) + 1
        platform_counts[item.platform] = platform_counts.get(item.platform, 0) + 1

    # 토픽 빈도 집계
    topic_freq: dict[str, int] = {}
    for item in approved:
        for t in item.topics:
            topic_freq[t] = topic_freq.get(t, 0) + 1
    top_topics = sorted(topic_freq.items(), key=lambda x: -x[1])[:10]

    # 감성별 그룹핑 (긍정 → 부정 → 중립)
    grouped = {
        "positive": [v for v in approved if v.sentiment == "positive"],
        "negative": [v for v in approved if v.sentiment == "negative"],
        "neutral":  [v for v in approved if v.sentiment == "neutral"],
    }

    context: dict = {
        "project_id": project_id,
        "project_name": project_name,
        "user_request": user_request,
        "generated_at": datetime.now().strftime("%Y년 %m월 %d일 %H:%M"),
        "total": total,
        "sentiment_counts": sentiment_counts,
        "platform_counts": platform_counts,
        "top_topics": top_topics,
        "grouped": grouped,
    }

    # 경영진 요약: 대표 의견 top 3씩
    if report_type == "executive":
        context["key_positives"] = grouped["positive"][:3]
        context["key_negatives"] = grouped["negative"][:3]

    # 프리미엄 보고서: ReportAnalysis 주입
    if report_type == "premium":
        if analysis is None:
            raise RuntimeError(
                "프리미엄 보고서 생성에는 분석 데이터가 필요합니다. "
                "먼저 '프리미엄 분석 생성' 버튼을 눌러 주세요."
            )
        context["analysis"] = analysis

    # 상세 보고서: 플랫폼별 세부 통계 + 수집방법 분포
    if report_type == "detailed":
        platform_stats: dict[str, dict] = {}
        for item in approved:
            p = item.platform
            if p not in platform_stats:
                platform_stats[p] = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "conf_sum": 0.0}
            platform_stats[p]["total"] += 1
            platform_stats[p][item.sentiment] = platform_stats[p].get(item.sentiment, 0) + 1
            platform_stats[p]["conf_sum"] += item.confidence or 0.0
        for p, st in platform_stats.items():
            st["avg_conf"] = st["conf_sum"] / st["total"] if st["total"] else 0.0

        method_counts: dict[str, int] = {}
        for item in approved:
            m = item.collection_method or "tier2_static"
            method_counts[m] = method_counts.get(m, 0) + 1

        context["platform_stats"] = platform_stats
        context["method_counts"] = method_counts

    template = _jinja_env.get_template(_TEMPLATE_MAP[report_type])
    html_str = template.render(**context)

    # PDF 변환 — link_callback 으로 폰트 경로 해석
    def _link_callback(uri, rel):
        if uri.endswith((".ttf", ".otf")):
            base = os.path.basename(uri)
            # 1) 번들 fonts 디렉토리 우선
            font_path = os.path.join(fonts_dir, base)
            if os.path.exists(font_path):
                return font_path.replace("\\", "/")
            # 2) Windows 시스템 폰트 fallback
            sys_path = os.path.join(_WIN_FONTS, base)
            if os.path.exists(sys_path):
                return sys_path.replace("\\", "/")
            log.warning("Font not found via callback: %s → %s / %s", uri, font_path, sys_path)
        return uri

    buf = BytesIO()
    result = pisa.CreatePDF(
        html_str,
        dest=buf,
        encoding="utf-8",
        link_callback=_link_callback,
    )

    if result.err:
        raise RuntimeError(f"PDF 생성 실패 (xhtml2pdf 오류 코드: {result.err})")

    reports_dir = get_reports_dir()
    out_path = os.path.join(reports_dir, f"{project_id}_{report_type}.pdf")
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())

    log.info("PDF generated: %s (%d bytes)", out_path, os.path.getsize(out_path))
    return out_path
