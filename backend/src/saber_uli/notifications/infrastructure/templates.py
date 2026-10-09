"""Plantillas de correo con Jinja2 (research R-30).

Cada plantilla `<nombre>` tiene tres archivos en `templates/`: `<nombre>.subject.j2`,
`<nombre>.html.j2` (hereda de `base.html.j2`, con autoescape) y `<nombre>.txt.j2` (hereda de
`base.txt.j2`, sin escape HTML). Las variables faltantes son un error (`StrictUndefined`).

Los enlaces se construyen solo con el filtro `absolute_url`, que exige una ruta que empiece por
`/` y la une a `PUBLIC_BASE_URL`: un correo nunca lleva enlaces a otros dominios.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from saber_uli.notifications.application.ports import RenderedEmail

TEMPLATES_DIR = Path(__file__).parent / "templates"


class ExternalLinkError(ValueError):
    """Un enlace del correo no es una ruta de la propia aplicación."""


class JinjaTemplateRenderer:
    def __init__(self, *, public_base_url: str) -> None:
        self._base_url = public_base_url.rstrip("/")
        loader = FileSystemLoader(TEMPLATES_DIR)
        self._html = Environment(loader=loader, autoescape=True, undefined=StrictUndefined)
        self._text = Environment(
            loader=loader,
            autoescape=False,  # noqa: S701 - texto plano: nunca se interpreta como HTML
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        for env in (self._html, self._text):
            env.filters["absolute_url"] = self._absolute_url
            env.globals["base_url"] = self._base_url

    def _absolute_url(self, path: str) -> str:
        parts = urlsplit(path)
        if parts.scheme or parts.netloc or not path.startswith("/"):
            raise ExternalLinkError("los enlaces del correo deben ser rutas de la aplicación")
        return f"{self._base_url}{path}"

    def render(self, template: str, context: Mapping[str, Any]) -> RenderedEmail:
        try:
            subject = self._text.get_template(f"{template}.subject.j2").render(context)
            html = self._html.get_template(f"{template}.html.j2").render(context)
            text = self._text.get_template(f"{template}.txt.j2").render(context)
        except TemplateNotFound as error:
            raise LookupError(f"plantilla de correo inexistente: {template}") from error
        # Un salto de línea en el asunto permitiría inyectar cabeceras.
        clean_subject = " ".join(subject.split())
        return RenderedEmail(subject=clean_subject, html=html, text=text)
