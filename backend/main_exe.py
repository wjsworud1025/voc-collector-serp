"""
main_exe.py — PyInstaller 번들 진입점
포트 탐색 후 stdout으로 "VOC_READY:{port}" 출력, Uvicorn 서버 시작.
Tauri sidecar가 이 파일을 실행하고 stdout 라인을 파싱한다.
"""
import os
import socket
import sys

# PyInstaller 번들 환경에서 sys.path에 번들 디렉터리 추가
if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS  # type: ignore[attr-defined]
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

import uvicorn  # noqa: E402 (paths must be set first)
from main import app  # noqa: E402


def find_free_port(start: int = 8000, end: int = 8999) -> int:
    """start~end 범위에서 사용 가능한 첫 포트 반환"""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"포트 {start}~{end} 범위에 사용 가능한 포트가 없습니다")


def main():
    port = find_free_port()

    # Tauri가 이 라인을 stdout에서 파싱하여 API 포트를 획득한다
    print(f"VOC_READY:{port}", flush=True)
    sys.stdout.flush()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",   # 번들: 경고만 출력
        access_log=False,
    )


if __name__ == "__main__":
    main()
