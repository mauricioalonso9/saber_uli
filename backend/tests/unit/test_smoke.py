"""Prueba de humo del empaquetado: el paquete `saber_uli` y sus contextos son importables.

Garantiza que `uv sync` instaló el proyecto y que pytest recoge pruebas (exitoso en lugar del
código 5 de "sin pruebas"). No sustituye las pruebas funcionales de cada tarea.
"""


def test_package_is_importable() -> None:
    import saber_uli
    import saber_uli.identity
    import saber_uli.notifications
    import saber_uli.shared

    assert saber_uli is not None
    assert saber_uli.identity is not None
    assert saber_uli.notifications is not None
    assert saber_uli.shared is not None
