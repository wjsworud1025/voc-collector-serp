# voc-backend.spec — PyInstaller 6.x build specification
# Run: python -m PyInstaller voc-backend.spec --clean --noconfirm
# Output: dist/voc-backend.exe

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# google.genai 및 xhtml2pdf 서브모듈 수집
_genai_mods      = collect_submodules('google.genai')
_xhtml_mods      = collect_submodules('xhtml2pdf')
_reportlab_mods  = collect_submodules('reportlab')
_serpapi_mods    = collect_submodules('serpapi')
_genai_datas     = collect_data_files('google.genai')
_xhtml_datas     = collect_data_files('xhtml2pdf')
_reportlab_datas = collect_data_files('reportlab')

a = Analysis(
    ['main_exe.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('fonts', 'fonts'),
        ('tests/fixtures/serpapi', 'tests/fixtures/serpapi'),  # DRY_RUN 모드용 fixture 번들
        *_genai_datas,
        *_xhtml_datas,
        *_reportlab_datas,
    ],
    hiddenimports=[
        # uvicorn
        'uvicorn.logging',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        # async SQLite
        'aiosqlite',
        # PDF
        'xhtml2pdf',
        'reportlab',
        'reportlab.pdfbase',
        'reportlab.pdfbase.ttfonts',
        'reportlab.platypus',
        'html5lib',
        # Google GenAI
        'google.genai',
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.api_core',
        'google.api_core.gapic_v1',
        # SerpApi SDK
        'serpapi',
        'google_search_results',
        # misc
        'platformdirs',
        'jinja2',
        'jinja2.ext',
        'pydantic',
        'multipart',
        *_genai_mods,
        *_xhtml_mods,
        *_reportlab_mods,
        *_serpapi_mods,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='voc-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # sidecar는 console=True (stdout VOC_READY 출력 필수)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
