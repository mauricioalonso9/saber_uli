/**
 * Llena la plantilla XLSX que descargó la prueba, con openpyxl dentro del contenedor `api` (el
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

export function fillTemplate(template: Buffer, rows: Record<string, unknown>[]): Buffer {
  const container = process.env.E2E_API_CONTAINER ?? composeContainer("api");
  // En Windows, Docker altera las comillas del argumento: el script viaja en base64.
  const code = `import base64; exec(base64.b64decode('${Buffer.from(SCRIPT).toString("base64")}'))`;
  const output = execFileSync("docker", ["exec", "-i", container, "python", "-c", code], {
    input: `${template.toString("base64")}\n${JSON.stringify(rows)}`,
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  });
  return Buffer.from(output, "base64");
}
