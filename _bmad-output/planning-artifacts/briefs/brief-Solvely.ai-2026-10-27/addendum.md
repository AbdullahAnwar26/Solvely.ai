# Addendum: depth for downstream PRD / architecture

## Verified facts (2026-10-27)
- Gemini API terms (https://ai.google.dev/gemini-api/terms): 18+ only; clients "directed towards or likely to be accessed by individuals under the age of 18" are barred; EEA/UK/CH users require Paid Services only; Unpaid Services content may be used to improve Google products and Google asks that no personal or sensitive data be submitted.
- Excalidraw `@excalidraw/excalidraw` latest on npm is 0.18.1, MIT, peer react/react-dom `^17 || ^18 || ^19`. Programmatic generation via `convertToExcalidrawElements` + `updateScene`.
- Gemini free-tier limits are per project and no longer published as a static table; exact RPM/TPM/RPD are only visible in AI Studio. Not verified.

## Unverified, must check before relying on
- Solvely pricing, free-trial length, and whether it has a whiteboard (its homepage did not mention one).
- Competitor details (Khanmigo, Photomath, Brilliant, Gauth, ChatGPT study mode, Gemini guided learning): only from prior knowledge.
- COPPA / GDPR-K specifics for a later high-school phase.

## Rejected / parked options
- **Free-tier-only Gemini:** rejected; shared quota, training use of data, EU/UK barred.
- **Bring-your-own-key:** rejected for v1 as too much friction for students; possible escape hatch if costs grow.
- **High-school launch on Gemini:** rejected by the terms; revisit with another provider.

## Technical constraints already fixed by the user's master prompt
React + TS + Vite, Excalidraw, Django + DRF, PostgreSQL, `google-genai` backend-only, model id from env, schema-validated AI output mapped to a fixed board-operation vocabulary, object-level authorization, mocked-Gemini tests, 8 GB dev machine.
