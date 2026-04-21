"""detect_script() 단위 테스트 — 다국어 스크립트 감지."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reporter import detect_script


class TestDetectScriptKorean:
    def test_korean_basic(self):
        assert detect_script("한국어 텍스트입니다") == "ko"

    def test_korean_with_latin(self):
        assert detect_script("Korean brand 리뷰") == "ko"

    def test_empty(self):
        assert detect_script("") == "ko"

    def test_latin_only(self):
        assert detect_script("Hello World") == "ko"


class TestDetectScriptCJK:
    def test_japanese_hiragana(self):
        assert detect_script("これは日本語です") == "cjk"

    def test_japanese_katakana(self):
        assert detect_script("アイスメーカー") == "cjk"

    def test_chinese_simplified(self):
        assert detect_script("你好世界") == "cjk"

    def test_chinese_traditional(self):
        assert detect_script("製冰機評論") == "cjk"

    def test_cjk_ext_a(self):
        # CJK Extension A: U+3400–U+4DBF
        assert detect_script("\u3400\u3401\u3402") == "cjk"

    def test_japanese_mixed_ko(self):
        # 일본어가 많으면 cjk
        assert detect_script("日本語テスト製品評価") == "cjk"

    def test_korean_dominant_over_japanese(self):
        # 한글이 일본어보다 많으면 ko
        assert detect_script("한한한한한한한한 日本") == "ko"


class TestDetectScriptCyrillic:
    def test_russian(self):
        assert detect_script("Привет мир") == "cyr"

    def test_russian_product_review(self):
        assert detect_script("Отличный продукт, рекомендую") == "cyr"

    def test_ukrainian(self):
        # U+0400-04FF 포함
        assert detect_script("Слава Україні") == "cyr"

    def test_cyrillic_supplement(self):
        # U+0500-052F
        assert detect_script("\u0500\u0501") == "cyr"

    def test_korean_dominant_over_cyrillic(self):
        # 한글이 훨씬 많으면 ko
        assert detect_script("한한한한한한한한 Да") == "ko"


class TestDetectScriptSWA:
    def test_thai(self):
        assert detect_script("สวัสดี") == "swa"

    def test_arabic(self):
        assert detect_script("مرحبا بالعالم") == "swa"

    def test_hebrew(self):
        assert detect_script("שלום עולם") == "swa"

    def test_devanagari(self):
        assert detect_script("नमस्ते दुनिया") == "swa"

    def test_swa_takes_priority_over_cyr(self):
        # swa 감지 시 최우선
        assert detect_script("Привет สวัสดี") == "swa"
