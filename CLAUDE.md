# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RockAI** is a sports betting intelligence app that detects value bets by comparing bookmaker odds against Pinnacle (used as the "fair odds" reference, à la StatsnBet). It exposes AI-powered analysis, bankroll tracking, and live match agenda.

The project is migrating from a vanilla HTML/JS + Python FastAPI stack (deleted from main branch) to a **Next.js 16 frontend** in `rockai-frontend/`.

## Commands (run from `rockai-frontend/`)

```bash
npm run dev      # Start dev server at http://localhost:3000
npm run build    # Production build
npm run lint     # ESLint
```

The backend (FastAPI) runs separately on port 8000. Set `NEXT_PUBLIC_API_URL` in `.env.local` (defaults to `http://localhost:8000`).

## Architecture

### Frontend — `rockai-frontend/`

**Stack:** Next.js 16 · React 19 · TypeScript · Tailwind 4 · Zustand · react-hot-toast · lucide-react

**App Router layout** (`src/app/`):
- `page.tsx` — root redirector: checks `getToken()` from `@/lib/api`, sends to `/agenda` or `/login`
- `layout.tsx` — sets global font, Toaster, and dark-theme metadata
- `globals.css` — design tokens as CSS variables, utility classes

**Expected pages** (not yet created): `/login`, `/agenda`, `/analyse`, `/profil`, `/stats`

**`@/lib/api`** — needs to be created. It must export at minimum:
- `getToken()` / `setToken(t)` / `clearToken()` — localStorage key: `rockai_token`
- `apiCall(path, options?)` — authenticated fetch against `NEXT_PUBLIC_API_URL`, redirects to `/login` on 401

### Backend API (FastAPI, port 8000)

Endpoints:
- `POST /auth/register`, `POST /auth/login` → JWT bearer token
- `GET /user/me` → `{ full_name, plan, credits }`
- `GET /matches` → list of upcoming matches with Pinnacle-derived EV and value bet flags
- `GET /matches/{match_id}` → single match detail
- `POST /bets`, `GET /bets` → bet tracking
- `GET /stats` → bankroll statistics
- `GET /leagues` → supported leagues

**Value bet thresholds:** EV ≥ 2% → displayed; EV ≥ 5% → "VALUE BET" badge.

### Design System

All colors are CSS variables on `:root`:

| Variable | Value | Use |
|---|---|---|
| `--bg` | `#080c10` | Page background |
| `--surface` | `#0d1318` | Cards |
| `--accent` | `#00d4dc` | Primary accent (cyan) |
| `--red` | `#ff4757` | Alerts / loss |
| `--gold` | `#ffd700` | Premium / highlights |
| `--text` | `#e8edf2` | Body text |
| `--text-muted` | `#4a5568` | Muted text |

Fonts: `Syne` (headings, `.font-display`), `DM Mono` (numbers/mono, `.font-mono`), `DM Sans` (body default).

Pre-defined utility classes: `.pulse`, `.fade-up`, `.text-accent-glow`, `.grid-bg`.

### Important notes from `AGENTS.md`

> This is NOT the Next.js you know — version 16 has breaking changes. Read `node_modules/next/dist/docs/` before writing routing or server-component code.

Auth state lives in `localStorage` (`rockai_token`, `rockai_user`). There is no server-side session.
