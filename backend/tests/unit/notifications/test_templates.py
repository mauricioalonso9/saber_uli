"""T037: plantillas de correo (research R-30; principio V)."""

import pytest
from jinja2 import UndefinedError

from saber_uli.notifications.infrastructure.templates import (
    ExternalLinkError,
    JinjaTemplateRenderer,
)

BASE_URL = "https://saber.unilibre.edu.co"


@pytest.fixture
def renderer() -> JinjaTemplateRenderer:
    return JinjaTemplateRenderer(public_base_url=BASE_URL)


def context(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "title": "Tu acceso a Saber Uli",
        "paragraphs": ["Hola <b>Ana</b>, ya puedes practicar."],
        "action_path": "/ingresar?desde=correo",
        "action_label": "Ingresar",
    }
    values.update(overrides)
    return values


def test_html_y_texto_en_es_co(renderer: JinjaTemplateRenderer) -> None:
    rendered = renderer.render("aviso", context())

    assert rendered.subject == "Tu acceso a Saber Uli"
    assert '<html lang="es-CO">' in rendered.html
    assert "Tu acceso a Saber Uli" in rendered.text
    assert "Universidad Libre" in rendered.html
    assert "Universidad Libre" in rendered.text


def test_autoescape_activo_en_html(renderer: JinjaTemplateRenderer) -> None:
    rendered = renderer.render("aviso", context())

    assert "&lt;b&gt;Ana&lt;/b&gt;" in rendered.html
    assert "<b>Ana</b>" not in rendered.html
    # El texto plano no se escapa como HTML.
    assert "Hola <b>Ana</b>" in rendered.text


def test_enlaces_absolutos_con_public_base_url(renderer: JinjaTemplateRenderer) -> None:
    rendered = renderer.render("aviso", context())

    url = "https://saber.unilibre.edu.co/ingresar?desde=correo"
    assert f'href="{url}"' in rendered.html
    assert url in rendered.text


@pytest.mark.parametrize(
    "path", ["https://otro.example.com/robo", "//otro.example.com", "ingresar"]
)
def test_no_se_aceptan_enlaces_externos_ni_relativos_sin_barra(
    renderer: JinjaTemplateRenderer, path: str
) -> None:
    with pytest.raises(ExternalLinkError):
        renderer.render("aviso", context(action_path=path))


def test_una_variable_faltante_es_un_error(renderer: JinjaTemplateRenderer) -> None:
    values = context()
    del values["title"]

    with pytest.raises(UndefinedError):
        renderer.render("aviso", values)


def test_el_asunto_no_admite_saltos_de_linea(renderer: JinjaTemplateRenderer) -> None:
    rendered = renderer.render("aviso", context(title="Hola\r\nBcc: x@evil.com"))

    assert "\n" not in rendered.subject
    assert "\r" not in rendered.subject


def test_plantilla_inexistente(renderer: JinjaTemplateRenderer) -> None:
    with pytest.raises(LookupError):
        renderer.render("no-existe", context())
