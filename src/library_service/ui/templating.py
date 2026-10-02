"""작업 디렉토리와 무관한 공통 템플릿 환경."""

from fastapi.templating import Jinja2Templates

from library_service.core.paths import TEMPLATE_DIR

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
