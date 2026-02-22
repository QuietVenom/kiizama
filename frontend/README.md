# Kiizama - Frontend

The frontend uses:

- [React 19](https://react.dev)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vitejs.dev/)
- [Chakra UI v3](https://chakra-ui.com/)
- [TanStack Router](https://tanstack.com/router)
- [TanStack Query](https://tanstack.com/query)
- [Biome](https://biomejs.dev/) for linting/formatting

## Frontend Development

Before starting, install Node.js using `fnm` or `nvm`.

```bash
cd frontend
```

Install/use the version in `.nvmrc`:

```bash
# fnm
fnm install
fnm use

# nvm
nvm install
nvm use
```

Install dependencies and start dev server:

```bash
npm install
npm run dev
```

Open http://localhost:5173.

## Useful Scripts

From `frontend/`:

```bash
npm run dev
npm run build
npm run lint
npm run preview
npm run generate-client
```

## Generate API Client

### Automatic

From repository root:

```bash
./scripts/generate-client.sh
```

### Manual

1. Start backend.
2. Download `http://localhost:8000/api/v1/openapi.json`.
3. Save it as `frontend/openapi.json`.
4. Run:

```bash
npm run generate-client
```

Generated files are in `frontend/src/client`.

## Using a Remote API

Set `VITE_API_URL` in `frontend/.env`, for example:

```env
VITE_API_URL=https://api.my-domain.example.com
```

## End-to-End Testing (Playwright)

Start required services:

```bash
docker compose up -d --wait backend
```

Run tests:

```bash
npx playwright test
```

UI mode:

```bash
npx playwright test --ui
```

Stop stack and clean data:

```bash
docker compose down -v
```

## Code Structure

- `frontend/src/assets` - static assets
- `frontend/src/client` - generated API client
- `frontend/src/components` - UI components
- `frontend/src/hooks` - custom hooks
- `frontend/src/routes` - route modules/pages
