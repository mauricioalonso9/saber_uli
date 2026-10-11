"""Modelos del formato de intercambio v1 (research R-03; data-model §6).

Son el formato del banco inicial (`backend/seeds/banco_inicial_saber_uli.json`) con nombres en
español. De ellos se genera `backend/schemas/banco_items.schema.json`. Las claves desconocidas se
rechazan para detectar errores de tipeo en los archivos de los docentes.

Campos que el banco inicial no traía y el formato admite (opcionales):

- `modulos[].preguntas_examen` y `modulos[].meta_banco`: preguntas en el examen y meta de ítems
  publicados para la cobertura (R-16). Si faltan, se toman de `estructura_examen` y de las metas
  del kit (150 por módulo, 225 en Inglés y 20 en Comunicación escrita).
- `modulos[].partes[].formato`: `emparejamiento` o `seleccion`; si falta, una parte con más de
  cuatro opciones es de emparejamiento.
- `componentes`, `situaciones`: cada entrada puede ser un código o `{codigo, nombre}`.
- `contextos[].tipo` e `imagen`: tipo explícito del contexto e imagen con texto alternativo.
- `consignas_escritura[].explicacion`.
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Dificultad = Literal["baja", "media", "alta"]
Estado = Literal["borrador", "en_revision", "publicado", "retirado"]
Origen = Literal["ia", "docente", "banco_inicial"]
Clave = str
# El mismo formato de código que la API (`LC-0001`, `ING-CTX-P1-001`): un ítem o contexto con otro
# código no se podría abrir después y, en una hoja de cálculo, podría ser una fórmula (T115).
CODE_PATTERN = r"^[A-Z]{2,3}(-[A-Z0-9]+){1,3}$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidencia(_Strict):
    codigo: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)


class Afirmacion(_Strict):
    codigo: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    peso_aprox: float | None = Field(default=None, ge=0, le=1)
    evidencias: list[Evidencia] = []


class Competencia(_Strict):
    codigo: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    peso_aprox: float | None = Field(default=None, ge=0, le=1)
    afirmaciones: list[Afirmacion] = []


class CategoriaNombrada(_Strict):
    codigo: str = Field(min_length=1)
    nombre: str = Field(min_length=1)


class Parte(_Strict):
    parte: int = Field(ge=1, le=7)
    opciones: int = Field(ge=2, le=8)
    tarea: str = Field(min_length=1)
    peso_aprox: float | None = Field(default=None, ge=0, le=1)
    formato: Literal["emparejamiento", "seleccion"] | None = None


class Modulo(_Strict):
    codigo: Literal["LC", "RC", "CC", "ING", "CE"]
    nombre: str = Field(min_length=1)
    tipo_pregunta: Literal["seleccion_multiple_unica_respuesta", "abierta_texto_argumentativo"]
    opciones_por_item: int | None = Field(default=None, ge=2, le=8)
    restricciones: dict[str, Any] | None = None
    preguntas_examen: int | None = Field(default=None, ge=1)
    meta_banco: int | None = Field(default=None, ge=1, le=10000)
    competencias: list[Competencia] = []
    componentes: list[str | CategoriaNombrada] = []
    situaciones: list[str | CategoriaNombrada] = []
    tipos_texto: dict[str, float] = {}
    partes: list[Parte] = []
    aspectos_evaluados: list[str] = []


class OpcionCompartida(_Strict):
    clave: Clave = Field(pattern=r"^[A-H]$")
    texto: str
    retroalimentacion: str


class Imagen(_Strict):
    media_id: UUID
    texto_alternativo: str


class Contexto(_Strict):
    id: str = Field(min_length=1, max_length=32, pattern=CODE_PATTERN)
    modulo: Literal["LC", "RC", "CC", "ING", "CE"]
    titulo: str
    tipo: Literal["texto", "tabla", "imagen", "opciones_compartidas"] | None = None
    contenido_md: str | None = None
    tipo_texto: str | None = None
    subtipo: str | None = None
    parte: int | None = Field(default=None, ge=1, le=7)
    opciones_compartidas: list[OpcionCompartida] | None = None
    imagen: Imagen | None = None
    palabras: int | None = Field(default=None, ge=0)
    origen: Origen = "docente"
    estado: Estado | None = None
    version: int | None = Field(default=None, ge=1)


class Opcion(_Strict):
    clave: Clave = Field(pattern=r"^[A-D]$")
    texto: str
    correcta: bool
    retroalimentacion: str = ""


class Item(_Strict):
    id: str = Field(min_length=1, max_length=32, pattern=CODE_PATTERN)
    modulo: Literal["LC", "RC", "CC", "ING"]
    dificultad: Dificultad
    enunciado: str
    explicacion: str = ""
    version: int | None = Field(default=None, ge=1)
    contexto_id: str | None = Field(default=None, max_length=32, pattern=CODE_PATTERN)
    competencia: str | None = None
    afirmacion: str | None = None
    evidencia: str | None = None
    componente: str | None = None
    situacion: str | None = None
    parte: int | None = Field(default=None, ge=1, le=7)
    opciones: list[Opcion] | None = None
    usa_opciones_del_contexto: bool = False
    clave_correcta: Clave | None = Field(default=None, pattern=r"^[A-H]$")
    origen: Origen = "docente"
    estado: Estado | None = None


class Consigna(_Strict):
    id: str = Field(min_length=1, max_length=32, pattern=CODE_PATTERN)
    modulo: Literal["CE"]
    dificultad: Dificultad
    contexto: str
    pregunta: str
    rubrica_id: str
    explicacion: str = ""
    version: int | None = Field(default=None, ge=1)
    origen: Origen = "docente"
    estado: Estado | None = None


class CondicionPrevia(_Strict):
    nombre: str
    descripcion: str


class Nivel(_Strict):
    nivel: int = Field(ge=1)
    descripcion: str


class Dimension(_Strict):
    codigo: str
    nombre: str
    niveles: list[Nivel] = Field(min_length=2)


class Rubrica(_Strict):
    id: str = Field(min_length=1, max_length=32)
    nombre: str
    nota: str | None = None
    condicion_previa: CondicionPrevia
    dimensiones: list[Dimension] = Field(min_length=1)


class BancoV1(_Strict):
    """Archivo completo. El lector valida cada entrada por separado (errores por ítem)."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        title="Banco de ítems Saber Uli (formato de intercambio v1)",
        json_schema_extra={
            "$id": "https://saber-uli.unilibre.edu.co/schemas/banco_items.schema.json"
        },
    )

    esquema_version: Literal["1.0"]
    nombre: str | None = None
    descripcion: str | None = None
    fuente_taxonomia: str | None = None
    estructura_examen: dict[str, Any] | None = None
    modulos: list[Modulo] = []
    contextos: list[Contexto] = []
    items: list[Item] = []
    consignas_escritura: list[Consigna] = []
    rubricas: list[Rubrica] = []
