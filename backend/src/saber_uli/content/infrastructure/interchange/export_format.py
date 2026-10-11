"""Formatos de exportación del banco (FR-038): el JSON v1 y la plantilla XLSX."""

from collections.abc import Callable, Mapping

from saber_uli.content.application.bank_export import ExportWriter
from saber_uli.content.infrastructure.interchange.json_format import JsonExportWriter
from saber_uli.content.infrastructure.interchange.xlsx_format import XlsxExportWriter

EXPORT_WRITERS: Mapping[str, Callable[[], ExportWriter]] = {
    "json": JsonExportWriter,
    "xlsx": XlsxExportWriter,
}
