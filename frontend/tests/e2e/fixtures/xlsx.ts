/**
 * Llena y lee archivos XLSX de la prueba, con openpyxl dentro del contenedor `api` (el
 * frontend no tiene una librería de hojas de cálculo). El archivo viaja en base64 por la entrada
 * y la salida estándar; las filas, como JSON.
 */
import { execFileSync } from "node:child_process";

import { composeContainer } from "./db";

const SCRIPT = `
import base64, io, json, sys
from openpyxl import load_workbook
template, rows = sys.stdin.read().split(chr(10), 1)
book = load_workbook(io.BytesIO(base64.b64decode(template)))
sheet = book["items"]
header = [cell.value for cell in sheet[1]]
for number, row in enumerate(json.loads(rows), start=2):
    for column, name in enumerate(header, start=1):
        sheet.cell(row=number, column=column, value=row.get(name))
out = io.BytesIO()
book.save(out)
sys.stdout.write(base64.b64encode(out.getvalue()).decode())
`;

const READ_SCRIPT = `
import base64, io, json, sys
from openpyxl import load_workbook
sheet = load_workbook(io.BytesIO(base64.b64decode(sys.stdin.read())), read_only=True)["items"]
rows = sheet.iter_rows(values_only=True)
header = next(rows)
sys.stdout.write(json.dumps([dict(zip(header, row)) for row in rows], ensure_ascii=False))
`;

function runPython(script: string, input: string): string {
  const container = process.env.E2E_API_CONTAINER ?? composeContainer("api");
  // En Windows, Docker altera las comillas del argumento: el script viaja en base64.
  const code = `import base64; exec(base64.b64decode('${Buffer.from(script).toString("base64")}'))`;
  return execFileSync("docker", ["exec", "-i", container, "python", "-c", code], {
    input,
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  });
}

export function fillTemplate(template: Buffer, rows: Record<string, unknown>[]): Buffer {
  const output = runPython(SCRIPT, `${template.toString("base64")}\n${JSON.stringify(rows)}`);
  return Buffer.from(output, "base64");
}

/** Filas de la hoja `items` de un XLSX, con los encabezados como claves. */
export function readItemRows(file: Buffer): Record<string, unknown>[] {
  return JSON.parse(runPython(READ_SCRIPT, file.toString("base64"))) as Record<string, unknown>[];
}
