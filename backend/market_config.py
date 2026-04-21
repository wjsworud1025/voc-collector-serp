"""
국가/시장별 VOC 수집 설정 — 언어, 플랫폼, 커뮤니티 매핑

각 국가에 대해:
- 해당 국가의 주요 언어
- 전자제품 소비자 커뮤니티
- 화장품/뷰티 소비자 커뮤니티
- 범용 소비자 플랫폼
- 검색 엔진 설정
"""

from __future__ import annotations

# ── 언어별 네이티브 리뷰 어휘 (VOC 필터링 + 검색 쿼리용) ────────────────
# 해당 국가 소비자가 실제로 사용하는 리뷰/평가 표현들
_REVIEW_VOCAB: dict[str, list[str]] = {
    "ko":    ["후기", "리뷰", "추천", "불만", "단점", "평가", "솔직", "사용기"],
    "ja":    ["口コミ", "レビュー", "評判", "不具合", "おすすめ", "比較", "使ってみた"],
    "zh-TW": ["心得", "開箱", "評價", "推薦", "缺點", "使用心得", "好用"],
    "zh":    ["评测", "口碑", "推荐", "缺点", "体验", "评价", "值得买"],
    "th":    ["รีวิว", "ดีไหม", "ข้อเสีย", "แนะนำ", "รีวิวจริง", "คุ้มไหม"],
    "vi":    ["đánh giá", "review", "trải nghiệm", "nhược điểm", "có nên mua"],
    "id":    ["review", "ulasan", "kelebihan", "kekurangan", "pengalaman", "worth it"],
    "ms":    ["review", "ulasan", "bagus", "rugi", "pengalaman", "berbaloi"],
    "de":    ["Test", "Erfahrung", "Bewertung", "Probleme", "Nachteile", "Meinung", "Erfahrungsbericht"],
    "fr":    ["avis", "test", "problèmes", "comparatif", "inconvénients", "expérience", "vaut le coup"],
    "it":    ["recensione", "opinioni", "problemi", "difetti", "vale la pena", "esperienza"],
    "es":    ["opiniones", "reseña", "problemas", "experiencia", "defectos", "merece la pena"],
    "pt":    ["avaliação", "opinião", "problemas", "defeitos", "vale a pena", "experiência"],
    "pt-BR": ["avaliação", "opinião", "reclamação", "resenha", "vale a pena", "problemas"],
    "ar":    ["مراجعة", "تجربة", "عيوب", "مشاكل", "يستاهل", "تقييم"],
    "he":    ["ביקורת", "חוות דעת", "בעיות", "חסרונות", "שווה לקנות"],
    "en":    ["review", "complaints", "problems", "worth it", "issues", "honest review"],
}

MARKET_CONFIG: dict[str, dict] = {
    # ─── 아시아 ───
    "한국": {
        "code": "KR",
        "language": "ko",
        "language_name": "한국어",
        "search_engine": "naver",
        "serpapi_engines": ["google", "naver"],
        "platforms": ["google", "naver", "youtube"],
        "electronics": [
            {"name": "다나와", "domain": "danawa.com", "query_suffix": "리뷰 사용기"},
            {"name": "에누리", "domain": "enuri.com", "query_suffix": "리뷰"},
            {"name": "뽐뿌", "domain": "ppomppu.co.kr", "query_suffix": "후기"},
            {"name": "클리앙", "domain": "clien.net", "query_suffix": "후기"},
            {"name": "네이버 블로그", "domain": "blog.naver.com", "query_suffix": "후기 리뷰"},
            {"name": "네이버 카페", "domain": "cafe.naver.com", "query_suffix": "후기"},
            {"name": "디시인사이드", "domain": "dcinside.com", "query_suffix": ""},
        ],
        "cosmetics": [
            {"name": "화해", "domain": "hwahae.co.kr", "query_suffix": "리뷰"},
            {"name": "올리브영", "domain": "oliveyoung.co.kr", "query_suffix": "리뷰 후기"},
            {"name": "네이버 블로그", "domain": "blog.naver.com", "query_suffix": "후기 리뷰"},
            {"name": "파우더룸", "domain": "powderroom.co.kr", "query_suffix": ""},
            {"name": "글로우픽", "domain": "glowpick.com", "query_suffix": "리뷰"},
        ],
        "sample_queries": {
            "electronics": [
                "{product} 후기 사용기",
                "{product} 추천 비교",
                "{product} 불만 단점 고장",
                "{product} AS후기 수리",
                "{product} 에너지효율 소음",
            ],
            "cosmetics": ["{product} 리뷰 후기", "{product} 추천 비추", "{product} 성분 분석"],
        },
    },
    "미국": {
        "code": "US",
        "language": "en",
        "language_name": "English",
        "search_engine": "google",
        "serpapi_engines": ["google", "amazon", "ebay", "walmart"],
        "platforms": ["google", "reddit", "youtube"],
        "electronics": [
            {"name": "Reddit", "domain": "reddit.com", "query_suffix": "review"},
            {"name": "Amazon Reviews", "domain": "amazon.com", "query_suffix": "review"},
            {"name": "CNET Forums", "domain": "cnet.com", "query_suffix": "forum"},
            {"name": "Wirecutter", "domain": "nytimes.com/wirecutter", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Reddit r/SkincareAddiction", "domain": "reddit.com/r/SkincareAddiction", "query_suffix": "review"},
            {"name": "Reddit r/MakeupAddiction", "domain": "reddit.com/r/MakeupAddiction", "query_suffix": ""},
            {"name": "MakeupAlley", "domain": "makeupalley.com", "query_suffix": "review"},
            {"name": "Beautylish", "domain": "beautylish.com", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} review 2024", "{product} complaints problems", "{product} vs comparison"],
            "cosmetics": ["{product} review honest", "{product} before after", "{product} worth it reddit"],
        },
    },
    "일본": {
        "code": "JP",
        "language": "ja",
        "language_name": "日本語",
        "search_engine": "google",
        "serpapi_engines": ["google", "yahoo_jp", "amazon"],
        "platforms": ["google", "yahoo_jp", "youtube"],
        "electronics": [
            {"name": "価格.com", "domain": "kakaku.com", "query_suffix": "レビュー"},
            {"name": "みんなの評判ランキング", "domain": "minhyo.jp", "query_suffix": "口コミ"},
            {"name": "Amazon.co.jp", "domain": "amazon.co.jp", "query_suffix": "レビュー"},
            {"name": "家電Watch", "domain": "kaden.watch.impress.co.jp", "query_suffix": ""},
        ],
        "cosmetics": [
            {"name": "@cosme", "domain": "cosme.net", "query_suffix": "口コミ"},
            {"name": "LIPS", "domain": "lipscosme.com", "query_suffix": "レビュー"},
            {"name": "美的", "domain": "biteki.com", "query_suffix": ""},
            {"name": "Voce", "domain": "voce.jp", "query_suffix": ""},
        ],
        "sample_queries": {
            "electronics": ["{product} 口コミ 評判", "{product} レビュー 比較", "{product} 不具合 問題"],
            "cosmetics": ["{product} 口コミ ランキング", "{product} 使ってみた", "{product} 成分 分析"],
        },
    },
    "대만": {
        "code": "TW",
        "language": "zh-TW",
        "language_name": "繁體中文",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "PTT", "domain": "ptt.cc", "query_suffix": "心得"},
            {"name": "Mobile01", "domain": "mobile01.com", "query_suffix": "開箱"},
            {"name": "ePrice", "domain": "eprice.com.tw", "query_suffix": "評測"},
            {"name": "Dcard", "domain": "dcard.tw", "query_suffix": "心得"},
        ],
        "cosmetics": [
            {"name": "Beauty321", "domain": "beauty321.com", "query_suffix": "評價"},
            {"name": "PTT BeautySalon", "domain": "ptt.cc", "query_suffix": "心得"},
            {"name": "Dcard 美妝版", "domain": "dcard.tw", "query_suffix": "心得"},
            {"name": "UrCosme", "domain": "urcosme.com", "query_suffix": "評價"},
        ],
        "sample_queries": {
            "electronics": ["{product} 開箱 心得", "{product} 推薦 評價", "{product} 缺點 問題"],
            "cosmetics": ["{product} 心得 推薦", "{product} 評價 好用嗎", "{product} 成分 分析"],
        },
    },
    "베트남": {
        "code": "VN",
        "language": "vi",
        "language_name": "Tiếng Việt",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Tinhte", "domain": "tinhte.vn", "query_suffix": "đánh giá"},
            {"name": "VnReview", "domain": "vnreview.vn", "query_suffix": ""},
            {"name": "VoZ Forum", "domain": "voz.vn", "query_suffix": "review"},
            {"name": "Shopee Reviews", "domain": "shopee.vn", "query_suffix": "đánh giá"},
        ],
        "cosmetics": [
            {"name": "Sociolla", "domain": "sociolla.com", "query_suffix": "review"},
            {"name": "Lixibox", "domain": "lixibox.com", "query_suffix": "đánh giá"},
            {"name": "VoZ BeautyForum", "domain": "voz.vn", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} đánh giá", "{product} review trải nghiệm", "{product} ưu nhược điểm"],
            "cosmetics": ["{product} review có tốt không", "{product} đánh giá chi tiết", "{product} nên mua không"],
        },
    },
    "태국": {
        "code": "TH",
        "language": "th",
        "language_name": "ภาษาไทย",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Pantip", "domain": "pantip.com", "query_suffix": "รีวิว"},
            {"name": "Lazada Reviews", "domain": "lazada.co.th", "query_suffix": "รีวิว"},
            {"name": "Specphone", "domain": "specphone.com", "query_suffix": "รีวิว"},
        ],
        "cosmetics": [
            {"name": "Pantip Clinic", "domain": "pantip.com", "query_suffix": "รีวิว"},
            {"name": "Jeban", "domain": "jeban.com", "query_suffix": "รีวิว"},
            {"name": "SistaCafe", "domain": "sistacafe.com", "query_suffix": "รีวิว"},
        ],
        "sample_queries": {
            "electronics": ["{product} รีวิว", "{product} ดีไหม", "{product} ข้อเสีย"],
            "cosmetics": ["{product} รีวิว ใช้ดีไหม", "{product} ราคา คุ้มไหม"],
        },
    },
    "인도네시아": {
        "code": "ID",
        "language": "id",
        "language_name": "Bahasa Indonesia",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Kaskus", "domain": "kaskus.co.id", "query_suffix": "review"},
            {"name": "Tokopedia Reviews", "domain": "tokopedia.com", "query_suffix": "ulasan"},
            {"name": "Pricebook", "domain": "pricebook.co.id", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Female Daily", "domain": "femaledaily.com", "query_suffix": "review"},
            {"name": "Sociolla", "domain": "sociolla.com", "query_suffix": "review"},
            {"name": "Beautynesia", "domain": "beautynesia.id", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} review pengalaman", "{product} kelebihan kekurangan", "{product} worth it gak"],
            "cosmetics": ["{product} review jujur", "{product} cocok untuk kulit", "{product} bagus gak"],
        },
    },
    "호주": {
        "code": "AU",
        "language": "en",
        "language_name": "English",
        "search_engine": "google",
        "platforms": ["google", "reddit", "youtube"],
        "electronics": [
            {"name": "Whirlpool Forums", "domain": "whirlpool.net.au", "query_suffix": "review"},
            {"name": "Reddit r/australia", "domain": "reddit.com/r/australia", "query_suffix": ""},
            {"name": "ProductReview.com.au", "domain": "productreview.com.au", "query_suffix": ""},
            {"name": "Choice", "domain": "choice.com.au", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Beauty Heaven", "domain": "beautyheaven.com.au", "query_suffix": "review"},
            {"name": "Adore Beauty", "domain": "adorebeauty.com.au", "query_suffix": "review"},
            {"name": "Reddit r/AusSkincare", "domain": "reddit.com/r/AusSkincare", "query_suffix": ""},
        ],
        "sample_queries": {
            "electronics": ["{product} review australia", "{product} whirlpool forum", "{product} worth it"],
            "cosmetics": ["{product} review australia", "{product} skincare routine"],
        },
    },
    "말레이시아": {
        "code": "MY",
        "language": "ms",
        "language_name": "Bahasa Melayu",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Lowyat Forum", "domain": "forum.lowyat.net", "query_suffix": "review"},
            {"name": "SoyaCincau", "domain": "soyacincau.com", "query_suffix": "review"},
            {"name": "Shopee MY Reviews", "domain": "shopee.com.my", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Female Daily MY", "domain": "femaledaily.com", "query_suffix": "review"},
            {"name": "Hermo", "domain": "hermo.my", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} review malaysia", "{product} lowyat forum", "{product} bagus tak"],
            "cosmetics": ["{product} review honest", "{product} sesuai untuk kulit"],
        },
    },
    "인도": {
        "code": "IN",
        "language": "en",
        "language_name": "English",
        "search_engine": "google",
        "platforms": ["google", "reddit", "youtube"],
        "electronics": [
            {"name": "Reddit r/IndianGaming", "domain": "reddit.com/r/IndianGaming", "query_suffix": ""},
            {"name": "Flipkart Reviews", "domain": "flipkart.com", "query_suffix": "review"},
            {"name": "Amazon.in", "domain": "amazon.in", "query_suffix": "review"},
            {"name": "Digit Forum", "domain": "digit.in/forum", "query_suffix": ""},
        ],
        "cosmetics": [
            {"name": "Nykaa", "domain": "nykaa.com", "query_suffix": "review"},
            {"name": "Reddit r/IndianSkincareAddicts", "domain": "reddit.com/r/IndianSkincareAddicts", "query_suffix": ""},
            {"name": "VanityCaseBox", "domain": "vanitycasebox.com", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} review india", "{product} worth buying india", "{product} problems issues"],
            "cosmetics": ["{product} review indian skin", "{product} nykaa review", "{product} worth it india"],
        },
    },
    # ─── 유럽 ───
    "영국": {
        "code": "GB",
        "language": "en",
        "language_name": "English",
        "search_engine": "google",
        "serpapi_engines": ["google", "amazon", "ebay"],
        "platforms": ["google", "reddit", "youtube"],
        "electronics": [
            {"name": "Reddit r/UKPersonalFinance", "domain": "reddit.com", "query_suffix": "review"},
            {"name": "Which?", "domain": "which.co.uk", "query_suffix": "review"},
            {"name": "Trustpilot UK", "domain": "uk.trustpilot.com", "query_suffix": ""},
            {"name": "AVForums", "domain": "avforums.com", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Reddit r/SkincareAddictionUK", "domain": "reddit.com/r/SkincareAddictionUK", "query_suffix": ""},
            {"name": "Boots Reviews", "domain": "boots.com", "query_suffix": "review"},
            {"name": "Beautylish", "domain": "beautylish.com", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} review UK", "{product} which review", "{product} worth it UK"],
            "cosmetics": ["{product} review UK", "{product} boots review", "{product} honest review"],
        },
    },
    "독일": {
        "code": "DE",
        "language": "de",
        "language_name": "Deutsch",
        "search_engine": "google",
        "serpapi_engines": ["google", "amazon", "ebay"],
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "ComputerBase Forum", "domain": "computerbase.de", "query_suffix": "Test"},
            {"name": "Idealo", "domain": "idealo.de", "query_suffix": "Bewertung"},
            {"name": "Amazon.de", "domain": "amazon.de", "query_suffix": "Bewertung"},
            {"name": "Geizhals", "domain": "geizhals.de", "query_suffix": "Test"},
            {"name": "Chip.de", "domain": "chip.de", "query_suffix": "Test Erfahrung"},
            {"name": "Stiftung Warentest", "domain": "test.de", "query_suffix": "Test"},
            {"name": "Notebookcheck", "domain": "notebookcheck.com", "query_suffix": "Test"},
            {"name": "Trustpilot DE", "domain": "de.trustpilot.com", "query_suffix": "Bewertung"},
        ],
        "cosmetics": [
            {"name": "Douglas Reviews", "domain": "douglas.de", "query_suffix": "Bewertung"},
            {"name": "Beautyjunkies", "domain": "beautyjunkies.de", "query_suffix": "Erfahrung"},
            {"name": "Codecheck", "domain": "codecheck.info", "query_suffix": ""},
            {"name": "Notino DE", "domain": "notino.de", "query_suffix": "Bewertung"},
            {"name": "Flaconi", "domain": "flaconi.de", "query_suffix": "Bewertung"},
        ],
        "sample_queries": {
            "electronics": ["{product} Test Erfahrung", "{product} Bewertung Meinung", "{product} Probleme Nachteile", "{product} Erfahrungsbericht"],
            "cosmetics": ["{product} Erfahrung Bewertung", "{product} Test Hauttyp", "{product} empfehlenswert", "{product} Inhaltsstoffe"],
        },
    },
    "프랑스": {
        "code": "FR",
        "language": "fr",
        "language_name": "Français",
        "search_engine": "google",
        "serpapi_engines": ["google", "amazon", "ebay"],
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Les Numériques", "domain": "lesnumeriques.com", "query_suffix": "test avis"},
            {"name": "Dealabs Forum", "domain": "dealabs.com", "query_suffix": "avis"},
            {"name": "Amazon.fr", "domain": "amazon.fr", "query_suffix": "avis"},
            {"name": "Fnac", "domain": "fnac.com", "query_suffix": "avis"},
            {"name": "Clubic", "domain": "clubic.com", "query_suffix": "test avis"},
            {"name": "01net", "domain": "01net.com", "query_suffix": "test"},
            {"name": "Trustpilot FR", "domain": "fr.trustpilot.com", "query_suffix": "avis"},
        ],
        "cosmetics": [
            {"name": "Beauté-Test", "domain": "beaute-test.com", "query_suffix": "avis"},
            {"name": "Sephora.fr", "domain": "sephora.fr", "query_suffix": "avis"},
            {"name": "Doctissimo Beauté", "domain": "doctissimo.fr", "query_suffix": "avis"},
            {"name": "Notino FR", "domain": "notino.fr", "query_suffix": "avis"},
        ],
        "sample_queries": {
            "electronics": ["{product} avis test", "{product} comparatif", "{product} problèmes défauts", "{product} retour expérience"],
            "cosmetics": ["{product} avis consommateur", "{product} test peau", "{product} vaut le coup", "{product} ingrédients avis"],
        },
    },
    "이탈리아": {
        "code": "IT",
        "language": "it",
        "language_name": "Italiano",
        "search_engine": "google",
        "serpapi_engines": ["google", "amazon", "ebay"],
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Amazon.it", "domain": "amazon.it", "query_suffix": "recensione"},
            {"name": "Trovaprezzi", "domain": "trovaprezzi.it", "query_suffix": "opinioni"},
            {"name": "Tom's Hardware IT", "domain": "tomshw.it", "query_suffix": "recensione"},
            {"name": "Hwupgrade", "domain": "hwupgrade.it", "query_suffix": "recensione"},
            {"name": "Eprice", "domain": "eprice.it", "query_suffix": "opinioni"},
            {"name": "Trustpilot IT", "domain": "it.trustpilot.com", "query_suffix": "recensione"},
        ],
        "cosmetics": [
            {"name": "Clio MakeUp", "domain": "cliomakeup.com", "query_suffix": "recensione"},
            {"name": "Douglas.it", "domain": "douglas.it", "query_suffix": "recensione"},
            {"name": "Sephora.it", "domain": "sephora.it", "query_suffix": "opinioni"},
            {"name": "Notino IT", "domain": "notino.it", "query_suffix": "recensione"},
        ],
        "sample_queries": {
            "electronics": ["{product} recensione opinioni", "{product} problemi difetti", "{product} vale la pena", "{product} esperienza"],
            "cosmetics": ["{product} recensione onesta", "{product} opinioni pelle", "{product} consigliato", "{product} ingredienti"],
        },
    },
    "스페인": {
        "code": "ES",
        "language": "es",
        "language_name": "Español",
        "search_engine": "google",
        "serpapi_engines": ["google", "amazon", "ebay"],
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "PcComponentes", "domain": "pccomponentes.com", "query_suffix": "opiniones"},
            {"name": "Foro Coches (Off-topic)", "domain": "forocoches.com", "query_suffix": "opiniones"},
            {"name": "Amazon.es", "domain": "amazon.es", "query_suffix": "opiniones"},
            {"name": "MediaMarkt Reviews", "domain": "mediamarkt.es", "query_suffix": "opiniones"},
            {"name": "Idealo ES", "domain": "idealo.es", "query_suffix": "opiniones"},
            {"name": "Xataka", "domain": "xataka.com", "query_suffix": "análisis"},
            {"name": "Trustpilot ES", "domain": "es.trustpilot.com", "query_suffix": "opiniones"},
        ],
        "cosmetics": [
            {"name": "Druni", "domain": "druni.es", "query_suffix": "opiniones"},
            {"name": "Sephora.es", "domain": "sephora.es", "query_suffix": "opiniones"},
            {"name": "Beautylish ES", "domain": "beautylish.com", "query_suffix": "reseña"},
            {"name": "Notino ES", "domain": "notino.es", "query_suffix": "opiniones"},
        ],
        "sample_queries": {
            "electronics": ["{product} opiniones reseña", "{product} problemas defectos", "{product} merece la pena", "{product} análisis"],
            "cosmetics": ["{product} reseña opiniones", "{product} experiencia piel", "{product} vale la pena", "{product} ingredientes"],
        },
    },
    "포르투갈": {
        "code": "PT",
        "language": "pt",
        "language_name": "Português",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Zwame Forum", "domain": "forum.zwame.pt", "query_suffix": "review"},
            {"name": "KuantoKusta", "domain": "kuantokusta.pt", "query_suffix": "opinião"},
            {"name": "Worten", "domain": "worten.pt", "query_suffix": "opinião"},
            {"name": "FNAC PT", "domain": "fnac.pt", "query_suffix": "avaliação"},
            {"name": "Trustpilot PT", "domain": "pt.trustpilot.com", "query_suffix": "avaliação"},
        ],
        "cosmetics": [
            {"name": "Notino PT", "domain": "notino.pt", "query_suffix": "avaliação"},
            {"name": "Sephora PT", "domain": "sephora.pt", "query_suffix": "opinião"},
            {"name": "FNAC Beleza PT", "domain": "fnac.pt", "query_suffix": "opinião"},
        ],
        "sample_queries": {
            "electronics": ["{product} opinião avaliação", "{product} problemas defeitos", "{product} vale a pena", "{product} experiência"],
            "cosmetics": ["{product} opinião review", "{product} experiência pele", "{product} ingredientes avaliação"],
        },
    },
    # ─── 중남미 ───
    "브라질": {
        "code": "BR",
        "language": "pt-BR",
        "language_name": "Português Brasileiro",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Reclame Aqui", "domain": "reclameaqui.com.br", "query_suffix": "reclamação"},
            {"name": "Adrenaline Forum", "domain": "adrenaline.com.br", "query_suffix": "review"},
            {"name": "Mercado Livre", "domain": "mercadolivre.com.br", "query_suffix": "avaliação"},
            {"name": "TecMundo Forum", "domain": "tecmundo.com.br", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Beleza na Web", "domain": "belezanaweb.com.br", "query_suffix": "avaliação"},
            {"name": "Reclame Aqui", "domain": "reclameaqui.com.br", "query_suffix": "reclamação"},
            {"name": "Sephora BR", "domain": "sephora.com.br", "query_suffix": "avaliação"},
        ],
        "sample_queries": {
            "electronics": ["{product} avaliação opinião", "{product} reclamação problema", "{product} vale a pena comprar"],
            "cosmetics": ["{product} resenha opinião", "{product} pele oleosa", "{product} vale a pena"],
        },
    },
    "아르헨티나": {
        "code": "AR",
        "language": "es",
        "language_name": "Español",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Mercado Libre AR", "domain": "mercadolibre.com.ar", "query_suffix": "opiniones"},
            {"name": "3DGames Forum", "domain": "3dgames.com.ar", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "Juleriaque", "domain": "juleriaque.com.ar", "query_suffix": "opiniones"},
        ],
        "sample_queries": {
            "electronics": ["{product} opiniones reseña argentina", "{product} problemas"],
            "cosmetics": ["{product} reseña opiniones"],
        },
    },
    "멕시코": {
        "code": "MX",
        "language": "es",
        "language_name": "Español",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Mercado Libre MX", "domain": "mercadolibre.com.mx", "query_suffix": "opiniones"},
            {"name": "Profeco", "domain": "profeco.gob.mx", "query_suffix": ""},
            {"name": "Amazon.com.mx", "domain": "amazon.com.mx", "query_suffix": "opiniones"},
        ],
        "cosmetics": [
            {"name": "Sephora MX", "domain": "sephora.com.mx", "query_suffix": "opiniones"},
            {"name": "Liverpool Reviews", "domain": "liverpool.com.mx", "query_suffix": "opiniones"},
        ],
        "sample_queries": {
            "electronics": ["{product} opiniones méxico", "{product} reseña experiencia", "{product} problemas defectos"],
            "cosmetics": ["{product} reseña opiniones méxico", "{product} piel grasa"],
        },
    },
    # ─── 중동/아프리카 ───
    "이집트": {
        "code": "EG",
        "language": "ar",
        "language_name": "العربية",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "عرب هاردوير", "domain": "arabhardware.net", "query_suffix": "مراجعة"},
            {"name": "جوميا مصر", "domain": "jumia.com.eg", "query_suffix": "تقييم"},
        ],
        "cosmetics": [
            {"name": "جوميا بيوتي", "domain": "jumia.com.eg", "query_suffix": "تقييم"},
        ],
        "sample_queries": {
            "electronics": ["{product} مراجعة تجربة", "{product} عيوب مشاكل", "{product} يستاهل"],
            "cosmetics": ["{product} تجربة ريفيو", "{product} للبشرة"],
        },
    },
    "UAE": {
        "code": "AE",
        "language": "ar",
        "language_name": "العربية",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "عرب هاردوير", "domain": "arabhardware.net", "query_suffix": "مراجعة"},
            {"name": "نون", "domain": "noon.com", "query_suffix": "تقييم"},
            {"name": "Amazon.ae", "domain": "amazon.ae", "query_suffix": "review"},
        ],
        "cosmetics": [
            {"name": "سيفورا الشرق الأوسط", "domain": "sephora.ae", "query_suffix": "تقييم"},
            {"name": "Noon Beauty", "domain": "noon.com", "query_suffix": "review"},
        ],
        "sample_queries": {
            "electronics": ["{product} مراجعة تجربة", "{product} review UAE", "{product} عيوب"],
            "cosmetics": ["{product} تجربة ريفيو", "{product} review dubai"],
        },
    },
    "러시아": {
        "code": "RU",
        "language": "ru",
        "language_name": "Русский",
        "search_engine": "yandex",
        "serpapi_engines": ["yandex", "google"],
        "platforms": ["yandex", "google", "youtube"],
        "electronics": [
            {"name": "Яндекс Маркет", "domain": "market.yandex.ru", "query_suffix": "отзывы"},
            {"name": "iXBT", "domain": "ixbt.com", "query_suffix": "обзор"},
            {"name": "DNS Forum", "domain": "club.dns-shop.ru", "query_suffix": "отзывы"},
            {"name": "Ozon", "domain": "ozon.ru", "query_suffix": "отзывы"},
        ],
        "cosmetics": [
            {"name": "Отзовик", "domain": "otzovik.com", "query_suffix": "отзывы"},
            {"name": "iRecommend", "domain": "irecommend.ru", "query_suffix": "отзывы"},
            {"name": "Wildberries", "domain": "wildberries.ru", "query_suffix": "отзывы"},
        ],
        "sample_queries": {
            "electronics": ["{product} отзывы опыт", "{product} обзор недостатки", "{product} стоит ли покупать"],
            "cosmetics": ["{product} отзывы реальные", "{product} состав кожа", "{product} рекомендую"],
        },
    },
    "중국": {
        "code": "CN",
        "language": "zh",
        "language_name": "中文",
        "search_engine": "baidu",
        "serpapi_engines": ["baidu"],
        "platforms": ["baidu", "youtube"],
        "electronics": [
            {"name": "什么值得买", "domain": "smzdm.com", "query_suffix": "评测"},
            {"name": "京东", "domain": "jd.com", "query_suffix": "评价"},
            {"name": "淘宝", "domain": "taobao.com", "query_suffix": "评价"},
            {"name": "知乎", "domain": "zhihu.com", "query_suffix": "评测推荐"},
            {"name": "贴吧", "domain": "tieba.baidu.com", "query_suffix": "使用体验"},
        ],
        "cosmetics": [
            {"name": "小红书", "domain": "xiaohongshu.com", "query_suffix": "推荐"},
            {"name": "淘宝美妆", "domain": "taobao.com", "query_suffix": "评价"},
            {"name": "微博", "domain": "weibo.com", "query_suffix": "测评"},
        ],
        "sample_queries": {
            "electronics": ["{product} 评测 体验", "{product} 优缺点 推荐", "{product} 值得买吗"],
            "cosmetics": ["{product} 测评 真实感受", "{product} 适合什么肤质", "{product} 种草推荐"],
        },
    },
    "이스라엘": {
        "code": "IL",
        "language": "he",
        "language_name": "עברית",
        "search_engine": "google",
        "platforms": ["google", "youtube"],
        "electronics": [
            {"name": "Zap", "domain": "zap.co.il", "query_suffix": "ביקורת"},
            {"name": "FXP Forum", "domain": "fxp.co.il", "query_suffix": "חוות דעת"},
        ],
        "cosmetics": [
            {"name": "Zap Beauty", "domain": "zap.co.il", "query_suffix": "ביקורת"},
        ],
        "sample_queries": {
            "electronics": ["{product} ביקורת חוות דעת", "{product} בעיות", "{product} שווה לקנות"],
            "cosmetics": ["{product} ביקורת חוות דעת", "{product} לעור"],
        },
    },
}

# 별칭 매핑 (사용자 입력 유연성)
MARKET_ALIASES: dict[str, str] = {
    # 영어
    "korea": "한국", "south korea": "한국", "kr": "한국",
    "usa": "미국", "us": "미국", "united states": "미국", "america": "미국",
    "japan": "일본", "jp": "일본",
    "taiwan": "대만", "tw": "대만",
    "vietnam": "베트남", "vn": "베트남",
    "thailand": "태국", "th": "태국",
    "indonesia": "인도네시아", "id": "인도네시아",
    "australia": "호주", "au": "호주",
    "malaysia": "말레이시아", "my": "말레이시아",
    "india": "인도", "in": "인도",
    "uk": "영국", "united kingdom": "영국", "gb": "영국", "britain": "영국",
    "germany": "독일", "de": "독일",
    "france": "프랑스", "fr": "프랑스",
    "italy": "이탈리아", "it": "이탈리아",
    "spain": "스페인", "es": "스페인",
    "portugal": "포르투갈", "pt": "포르투갈",
    "brazil": "브라질", "br": "브라질",
    "argentina": "아르헨티나", "ar": "아르헨티나",
    "mexico": "멕시코", "mx": "멕시코",
    "egypt": "이집트", "eg": "이집트",
    "uae": "UAE", "aeu": "UAE", "dubai": "UAE",
    "israel": "이스라엘", "il": "이스라엘",
    # 신규 시장
    "russia": "러시아", "ru": "러시아", "рф": "러시아",
    "china": "중국", "cn": "중국", "prc": "중국", "中国": "중국",
    # 동유럽 시장은 러시아(Yandex) 엔진으로 라우팅
    "eastern europe": "러시아",
    "ukraine": "러시아", "ua": "러시아",
    "belarus": "러시아", "by": "러시아",
    "kazakhstan": "러시아", "kz": "러시아",
}


# ── 제품 유형 감지 키워드 ─────────────────────────────────────────────────
# 사용자 요청에서 제품 카테고리를 키워드 매칭으로 빠르게 결정
_PRODUCT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "electronics": [
        # 한국어 — 가전/전자
        "세탁기", "건조기", "워시타워", "냉장고", "에어컨", "TV", "텔레비전",
        "청소기", "식기세척기", "오븐", "전자레인지", "공기청정기", "가습기",
        "제습기", "선풍기", "노트북", "데스크탑", "모니터", "태블릿", "스마트폰",
        "이어폰", "헤드폰", "프린터", "카메라", "블루투스", "게이밍", "GPU", "CPU",
        "SSD", "공유기", "라우터", "스피커", "빔프로젝터", "전기밥솥", "인덕션",
        "전기레인지", "드럼세탁기", "통돌이", "진공청소기", "로봇청소기",
        # 영어 — electronics
        "washer", "dryer", "refrigerator", "dishwasher", "air conditioner",
        "vacuum", "laptop", "monitor", "smartphone", "headphone", "earphone",
        "printer", "camera", "speaker", "router", "gaming", "television",
        "electric", "appliance",
        # 독일어
        "Waschmaschine", "Kühlschrank", "Fernseher", "Geschirrspüler", "Staubsauger",
        # 일본어
        "洗濯機", "冷蔵庫", "テレビ", "掃除機", "食洗機", "エアコン",
        # 브랜드 (가전/전자 전용)
        "삼성", "LG", "다이슨", "소니", "파나소닉", "필립스", "보쉬", "밀레",
        "Samsung", "Sony", "Panasonic", "Philips", "Bosch", "Miele", "Dyson",
        "Siemens", "Electrolux", "Whirlpool", "Haier",
        "아이폰", "갤럭시", "Galaxy", "iPhone",
    ],
    "cosmetics": [
        # 한국어 — 뷰티/화장품
        "스킨케어", "화장품", "세럼", "크림", "로션", "토너", "클렌징",
        "마스크팩", "립스틱", "파운데이션", "선크림", "자외선차단", "앰플",
        "에센스", "아이크림", "미스트", "패드", "립밤", "아이섀도",
        # 영어
        "skincare", "serum", "moisturizer", "sunscreen", "foundation",
        "lipstick", "toner", "cleanser", "essence", "ampoule", "cosmetic",
        # 일본어
        "クリーム", "化粧品", "スキンケア", "美容液",
        # 뷰티 브랜드
        "설화수", "헤라", "아이오페", "라네즈", "이니스프리", "에뛰드",
        "SK-II", "La Mer", "Estee Lauder", "Clinique",
    ],
    "food": [
        "식품", "음식", "음료", "커피", "차", "과자", "초콜릿", "라면",
        "냉동식품", "즉석식품", "분유", "영양제", "프로틴", "단백질",
        "food", "drink", "coffee", "tea", "snack", "beverage", "chocolate",
        "supplement", "protein", "nutrition",
    ],
    "automotive": [
        "자동차", "차량", "SUV", "세단", "전기차", "하이브리드", "엔진",
        "타이어", "자동차용품", "블랙박스", "내비게이션",
        "car", "vehicle", "SUV", "sedan", "EV", "electric vehicle",
        "tire", "automotive", "Auto", "Fahrzeug",
    ],
    "software": [
        "앱", "소프트웨어", "게임", "프로그램", "플랫폼", "구독", "서비스",
        "OTT", "넷플릭스", "유튜브 프리미엄", "스트리밍",
        "app", "software", "game", "program", "service", "platform",
        "subscription", "streaming", "SaaS",
    ],
}

# 제품 유형별 한국어 레이블
_PRODUCT_TYPE_LABELS: dict[str, str] = {
    "electronics": "전자/가전제품",
    "cosmetics": "뷰티/화장품",
    "food": "식품/음료",
    "automotive": "자동차/자동차용품",
    "software": "소프트웨어/앱/서비스",
    "general": "일반 제품/서비스",
}

# 제품 유형별 특화 VOC 키워드 (검색 쿼리용)
_PRODUCT_TYPE_VOC_HINTS: dict[str, dict[str, list[str]]] = {
    "electronics": {
        "ko": ["AS후기", "고장", "불량", "수리비", "소음", "진동", "에너지효율", "전기세", "설치후기"],
        "en": ["warranty", "repair", "broken", "noise", "energy efficiency", "installation", "defect"],
        "ja": ["故障", "修理", "騒音", "省エネ", "クレーム", "初期不良"],
        "de": ["Reparatur", "Defekt", "Lärm", "Garantie", "Energieverbrauch", "Einbau"],
    },
    "cosmetics": {
        "ko": ["피부타입", "성분", "부작용", "발림성", "지속력", "향", "자극"],
        "en": ["skin type", "ingredients", "breakout", "irritation", "long-lasting", "texture"],
        "ja": ["肌質", "成分", "副作用", "使用感", "持続性"],
    },
    "food": {
        "ko": ["맛", "성분", "칼로리", "유통기한", "알레르기", "가성비"],
        "en": ["taste", "ingredients", "calories", "shelf life", "allergen", "value"],
    },
    "automotive": {
        "ko": ["연비", "내구성", "AS", "옵션", "가성비", "안전성"],
        "en": ["fuel economy", "reliability", "warranty", "safety", "maintenance"],
    },
}


def detect_product_type(user_request: str) -> str:
    """사용자 요청 텍스트에서 제품 유형을 키워드 매칭으로 감지.

    Returns:
        "electronics" | "cosmetics" | "food" | "automotive" | "software" | "general"
    """
    text_lower = user_request.lower()
    scores: dict[str, int] = {k: 0 for k in _PRODUCT_TYPE_KEYWORDS}

    for product_type, keywords in _PRODUCT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[product_type] += 1

    best_type = max(scores, key=lambda k: scores[k])
    return best_type if scores[best_type] > 0 else "general"


def resolve_market(market_text: str) -> dict | None:
    """사용자 입력에서 시장 설정을 찾아 반환."""
    key = market_text.strip()
    # 정확히 매칭
    if key in MARKET_CONFIG:
        return MARKET_CONFIG[key]
    # 별칭 매칭
    normalized = key.lower()
    if normalized in MARKET_ALIASES:
        return MARKET_CONFIG[MARKET_ALIASES[normalized]]
    # 부분 매칭
    for alias, market_key in MARKET_ALIASES.items():
        if alias in normalized or normalized in alias:
            return MARKET_CONFIG[market_key]
    return None


def get_native_keywords(
    market_config_entry: dict,
    product_name: str = "",
    category: str = "",
) -> list[str]:
    """시장 설정에서 네이티브 언어 키워드 목록 반환 (VOC 필터링용).

    반환된 키워드는 executor → collector 의 keywords 파라미터로 전달되어
    관련 없는 페이지/댓글을 사전 필터링하는 데 쓰인다.
    """
    lang = market_config_entry.get("language", "en")
    seen: set[str] = set()
    keywords: list[str] = []

    def _add(kw: str) -> None:
        kw = kw.strip()
        if kw and kw.lower() not in seen:
            seen.add(kw.lower())
            keywords.append(kw)

    # 1. 제품명을 맨 앞에 (가장 중요한 필터)
    if product_name:
        _add(product_name)

    # 2. 언어별 고정 리뷰 어휘
    for kw in _REVIEW_VOCAB.get(lang, _REVIEW_VOCAB["en"]):
        _add(kw)

    # 3. sample_queries 접미사 추출 (제품명 제거 후 남은 리뷰 표현)
    cats = [category] if category else list(market_config_entry.get("sample_queries", {}).keys())
    for cat in cats:
        for q_template in market_config_entry.get("sample_queries", {}).get(cat, []):
            suffix = q_template.replace("{product}", "").strip()
            if suffix:
                _add(suffix)

    return keywords


def get_market_context(market_text: str, product_type: str = "general") -> str:
    """planner 프롬프트에 주입할 시장 컨텍스트 문자열 생성.

    Args:
        market_text: 사용자 요청 전문 (국가 감지용)
        product_type: detect_product_type() 결과 ("electronics"|"cosmetics"|...)
    """
    config = resolve_market(market_text)
    if not config:
        return ""

    lang = config["language"]
    native_review_kws = _REVIEW_VOCAB.get(lang, _REVIEW_VOCAB["en"])
    type_label = _PRODUCT_TYPE_LABELS.get(product_type, "일반 제품/서비스")

    lines = [
        f"[감지된 시장: {market_text} / 감지된 제품 유형: {type_label}]",
        f"- 국가코드: {config['code']}",
        f"- 언어: {config['language']} ({config['language_name']})",
        f"- 사용 플랫폼: {', '.join(config['platforms'])}",
    ]

    # ── 제품 유형별 커뮤니티 & site: 힌트 ──────────────────────────────
    if product_type == "electronics":
        elec_sites = config["electronics"]
        lines.append(
            f"- **[전자/가전 특화] 이 제품에 맞는 커뮤니티:** "
            f"{', '.join(c['name'] for c in elec_sites)}"
        )
        domains = [c["domain"] for c in elec_sites]
        lines.append(
            f"- **Google site: 검색 권장 도메인 (전자/가전 우선 활용):** "
            f"{', '.join(domains[:6])}"
        )
        # 전자제품 특화 VOC 키워드
        voc_hints = _PRODUCT_TYPE_VOC_HINTS.get("electronics", {}).get(lang, [])
        if voc_hints:
            lines.append(
                f"- **전자/가전 특화 VOC 키워드 (keywords 필드 및 쿼리에 반드시 활용):** "
                f"{', '.join(voc_hints)}"
            )
        # 전자 샘플 쿼리
        for q in config.get("sample_queries", {}).get("electronics", []):
            lines.append(f"  쿼리 예시: {q}")

    elif product_type == "cosmetics":
        cosm_sites = config["cosmetics"]
        lines.append(
            f"- **[뷰티/화장품 특화] 이 제품에 맞는 커뮤니티:** "
            f"{', '.join(c['name'] for c in cosm_sites)}"
        )
        domains = [c["domain"] for c in cosm_sites]
        lines.append(
            f"- **Google site: 검색 권장 도메인 (뷰티 우선 활용):** "
            f"{', '.join(domains[:5])}"
        )
        voc_hints = _PRODUCT_TYPE_VOC_HINTS.get("cosmetics", {}).get(lang, [])
        if voc_hints:
            lines.append(
                f"- **뷰티/화장품 특화 VOC 키워드:** {', '.join(voc_hints)}"
            )
        for q in config.get("sample_queries", {}).get("cosmetics", []):
            lines.append(f"  쿼리 예시: {q}")

    else:
        # general / food / automotive / software — 전체 커뮤니티 표시
        lines.append(
            f"- 전자제품 커뮤니티: {', '.join(c['name'] for c in config['electronics'])}"
        )
        lines.append(
            f"- 화장품/뷰티 커뮤니티: {', '.join(c['name'] for c in config['cosmetics'])}"
        )
        all_sites = config["electronics"] + config["cosmetics"]
        domains = list({c["domain"] for c in all_sites})[:5]
        lines.append(f"- Google site: 검색 가능 도메인: {', '.join(domains)}")
        # 카테고리별 VOC 힌트
        voc_hints = _PRODUCT_TYPE_VOC_HINTS.get(product_type, {}).get(lang, [])
        if voc_hints:
            lines.append(f"- 카테고리 특화 VOC 키워드: {', '.join(voc_hints)}")
        for cat, queries in config.get("sample_queries", {}).items():
            lines.append(f"- {cat} 쿼리 예시: {', '.join(queries[:3])}")

    lines.append(
        f"- **keywords 필드에 반드시 포함할 네이티브 리뷰 키워드:** "
        f"{', '.join(native_review_kws)}"
    )

    return "\n".join(lines)


def get_review_vocab(lang: str) -> list[str]:
    """언어 코드에 해당하는 네이티브 리뷰 어휘 반환.

    serpapi_search.py 추출 프롬프트의 native vocab hint에 활용.
    매칭 없으면 영어 어휘로 폴백.
    """
    return list(_REVIEW_VOCAB.get(lang, _REVIEW_VOCAB["en"]))
