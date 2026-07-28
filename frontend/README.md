# EKIP Frontend — Knowledge Desk

A minimal, premium-feeling workspace for the EKIP backend: sign in, upload
documents to a knowledge base, ask questions, and see grounded answers with
inline citations you can inspect in an evidence panel.

Built with **React + Vite**, plain CSS (no component library, no CSS
framework) — kept intentionally small: 9 components, one API client file,
one toast context.

## Features covered

- Sign up / sign in (JWT session persisted in the browser)
- Create knowledge bases
- Upload documents (PDF/DOCX/TXT/MD) with a live progress bar
  (pending → parsing → chunking → embedding → ready) and a success toast
- Delete documents, with a confirmation prompt
- Ask questions scoped to a knowledge base, with conversation continuity
- Animated "thinking" indicator while waiting for a reply, and a
  typewriter reveal once the answer arrives
- Citations rendered as chips → click to open the evidence panel with source, page, and score
- Abstained answers are visually distinguished (amber) from grounded ones
- Run the evaluation suite and see aggregate metrics
- **Security tab**: run the tenant-isolation self-check with pass/fail
  results, and inspect each document's access rules (ACL entries)

## Setup

### 1. Install dependencies
```bash
cd frontend
npm install
```

### 2. Point it at your backend
```bash
cp .env.example .env
# edit .env if your API isn't on http://localhost:8000
```

### 3. Run it
```bash
npm run dev
```
Open `http://localhost:5173`. Make sure the EKIP backend (`docker compose up`
in the project root) is running first.

### 4. Build for production
```bash
npm run build   # outputs static files to dist/
npm run preview # serve the production build locally to sanity-check it
```
Deploy `dist/` behind any static file host / reverse proxy. Set
`VITE_API_BASE_URL` at build time to point at your deployed backend.

## Notes

- CORS is wide open (`allow_origins=["*"]`) on the backend for local dev —
  tighten this to your actual frontend origin before deploying either side.
- The session token is stored in `localStorage`. Fine for this POC; a
  production app should weigh httpOnly cookies + refresh tokens instead.
