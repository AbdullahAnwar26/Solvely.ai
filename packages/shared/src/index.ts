export type { components, operations, paths } from "./generated/api";

import type { components } from "./generated/api";

/** Named schema types from the OpenAPI components, e.g. `Schema<"Health">`. */
export type Schema<Name extends keyof components["schemas"]> = components["schemas"][Name];
