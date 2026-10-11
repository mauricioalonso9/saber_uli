"""Rutas HTTP que expone una app FastAPI, como pares `(MÉTODO, /ruta/{parametro})`.

FastAPI envuelve cada router incluido (`_IncludedRouter`), así que `app.routes` ya no lista las
rutas finales; `iter_route_contexts` las recorre todas.
"""

from fastapi import FastAPI
from fastapi.routing import iter_route_contexts


def app_operations(app: FastAPI) -> set[tuple[str, str]]:
    return {
        (method, route.path_format)
        for route in iter_route_contexts(app.router.routes)
        if route.methods and route.path_format
        for method in route.methods
    }
