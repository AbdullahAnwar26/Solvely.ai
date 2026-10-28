import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.strict],
    languageOptions: {
      ecmaVersion: 2023,
      globals: { ...globals.browser },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["error", { allowConstantExport: true }],
      // UX-DR1: colours come from DESIGN.md tokens (CSS variables), never hex literals in code.
      "no-restricted-syntax": [
        "error",
        {
          selector: "Literal[value=/#[0-9a-fA-F]{3,8}\\b/]",
          message: "Use a --color-* token from src/styles/tokens.css instead of a hex colour.",
        },
        {
          selector: "TemplateElement[value.raw=/#[0-9a-fA-F]{3,8}\\b/]",
          message: "Use a --color-* token from src/styles/tokens.css instead of a hex colour.",
        },
      ],
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/test/**"],
    rules: {
      "no-restricted-syntax": "off",
      "react-refresh/only-export-components": "off",
    },
  },
  {
    // The route table holds React.lazy() page components; it is config, not a refreshable component module.
    files: ["src/app/routes.tsx"],
    rules: { "react-refresh/only-export-components": "off" },
  },
  {
    files: ["vite.config.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
);
