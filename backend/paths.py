"""
paths.py — 경로 추상화 모듈
개발 환경과 PyInstaller 번들 환경 양쪽에서 동작하는 경로 헬퍼.
"""
import os
import sys


def is_frozen() -> bool:
    """PyInstaller 번들 환경인지 확인"""
    return getattr(sys, "frozen", False)


def get_bundle_dir() -> str:
    """읽기 전용 번들 리소스 경로 (templates, fonts)
    - 번들: sys._MEIPASS (PyInstaller 임시 압축 해제 폴더)
    - 개발: backend/ 디렉터리
    """
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """쓰기 가능 데이터 경로 (DB, reports)
    - 번들: %APPDATA%/VOCCollector/  (platformdirs)
    - 개발: backend/data/
    """
    if is_frozen():
        from platformdirs import user_data_dir
        path = user_data_dir("VOCCollector", appauthor=False)
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(path, exist_ok=True)
    return path


def get_db_path() -> str:
    return os.path.join(get_data_dir(), "voc.db")


def get_reports_dir() -> str:
    path = os.path.join(get_data_dir(), "reports")
    os.makedirs(path, exist_ok=True)
    return path


def get_templates_dir() -> str:
    return os.path.join(get_bundle_dir(), "templates")


def get_fonts_dir() -> str:
    return os.path.join(get_bundle_dir(), "fonts")
