// Regenerate src/generated/api.ts from the live API schema (GET /api/v1/schema/).
// Usage: npm run gen:api (from the repo root). Override the API origin with API_URL.
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const apiOrigin = (process.env.API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const schemaUrl = `${apiOrigin}/api/v1/schema/?format=json`;
const here = dirname(fileURLToPath(import.meta.url));
const outFile = resolve(here, "../src/generated/api.ts");

function fail(message) {
  console.error(`gen:api failed: ${message}`);
  process.exit(1);
}

let response;
try {
  response = await fetch(schemaUrl, {
    headers: { Accept: "application/vnd.oai.openapi+json, application/json" },
    signal: AbortSignal.timeout(10_000),
  });
} catch (error) {
  fail(
    `could not reach ${schemaUrl} (${error?.cause?.code ?? error?.name ?? "network error"}).\n` +
      "Start the API first: cd apps/api && .venv/Scripts/python manage.py runserver",
  );
}
if (!response.ok) {
  fail(`${schemaUrl} answered HTTP ${response.status}; expected 200 with the OpenAPI schema.`);
}

let schema;
try {
  schema = await response.json();
} catch {
  fail(`${schemaUrl} did not return JSON.`);
}
if (typeof schema?.openapi !== "string") {
  fail(`${schemaUrl} did not return an OpenAPI document.`);
}

const ast = await openapiTS(schema, { alphabetize: true });
const header =
  "/**\n" +
  " * Generated from GET /api/v1/schema/ by packages/shared/scripts/gen-api.mjs.\n" +
  " * Do not edit by hand. Regenerate with `npm run gen:api` from the repo root.\n" +
  " */\n\n";
await mkdir(dirname(outFile), { recursive: true });
await writeFile(outFile, header + astToString(ast).replace(/\r\n/g, "\n"), "utf8");
console.log(`gen:api wrote ${outFile} from ${schemaUrl}`);
