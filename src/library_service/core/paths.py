"""패키지 자산과 기존 로컬 데이터 경로를 구분한다."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
_CHECKOUT_DIR = PACKAGE_DIR.parent.parent
PROJECT_DIR = (
    _CHECKOUT_DIR if (_CHECKOUT_DIR / "pyproject.toml").is_file() else Path.cwd()
)
TEMPLATE_DIR = PACKAGE_DIR / "ui" / "templates"
STATIC_DIR = PACKAGE_DIR / "ui" / "static"
