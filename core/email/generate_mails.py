from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from premailer import transform
from core.config import settings

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"


env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

def render_template(template_name: str, **context) -> str:
    template = env.get_template(template_name)
    return template.render(**context)


def formatar_codigo(codigo: str) -> str:
    return " ".join(codigo)
