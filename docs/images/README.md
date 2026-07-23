# README screenshots (Version 1.0)

Operator-console and OpenAPI captures used by the root [README](../../README.md).

Regenerate (with backend on `:8800` and frontend on `:5173`):

```bash
# from repo root, with Chrome installed
node scripts/capture-readme-screenshots.mjs
```

Requires `playwright-core` resolvable from `frontend/node_modules` (dev install) and
`VITE_API_BASE_URL` pointing at the live backend when starting Vite.
