# Kairos Mobile Roadmap

## Overview

Kairos targets mobile-first use via a responsive web frontend (Vite + React).
The backend API at `:8400` runs locally (laptop, NAS, or home server) and is
accessed by any device on the same network.

---

## M1 — Responsive Shell + Quick Job (DONE)

**Goal:** Get the full pipeline into 3 taps on mobile.

### Delivered
- **Responsive `AppShell`** — desktop gets the sidebar; mobile gets a bottom tab bar
- **`BottomNav`** — 5-tab bottom navigation: Library, Clips, Quick, Render, Settings
- **`/quick` page — `QuickJobPage`** — URL input(s) + template picker + aspect ratio + optional captions → "Generate" button
- **`POST /api/jobs/quick`** — single endpoint that chains the full pipeline as a background thread
- **`GET /api/jobs/{job_id}`** — polling endpoint; returns `{job_status, stage_label, progress, output_path}`
- **`QuickJob` DB table** — tracks orchestrator state through all pipeline stages
- **Orchestrator service** (`kairos/services/orchestrator.py`) — `threading.Thread` that chains:
  `download → transcribe → analyze → generate clips → build story → render`
- **Progress screen** — live polling every 3 s, stage label + progress bar, download button when done

### TODOs / Known Gaps
- [ ] Output download link requires the render service to actually write a file (`output_path` in RenderJob). Verify render pipeline writes correctly.
- [ ] Error recovery: failed quick jobs must be manually restarted (no retry UI yet)
- [ ] Quick jobs list screen (view history of past jobs and their outputs)
- [ ] No job cancellation endpoint yet

---

## M2 — Mobile Library + Camera Roll Upload (DONE)

**Goal:** Browse the library and add videos from the device's camera roll.

### Delivered
- **`POST /api/acquisition/upload`** — multipart file upload; saves to `media_library/local/{year}/`, creates `MediaItem(platform="local")`, enqueues `ingest_task`
- **Mobile card layout** — `grid-cols-1` on mobile (horizontal thumbnail-left card), multi-column grid on sm+
- **Camera roll upload button** in `LibraryPage` — hidden `<input type="file" accept="video/*">` triggered by Upload button; shows XHR progress bar + error banner
- **Pull-to-refresh** — Refresh button visible on mobile (below sm), auto-polling already handles live updates
- **Responsive `ItemPage`** — header stacks vertically on mobile (back+title row, then action buttons row); `px-4 sm:px-6` padding

### TODOs / Known Gaps
- [ ] True swipe-gesture pull-to-refresh (currently a tap button; needs a touch library for gesture)
- [ ] Chunked upload for very large files (currently single-shot multipart — fine for typical camera videos)
- [ ] Upload title prompt (currently uses filename; could add a modal to name the video before upload)

---

## M3 — Quick Job History + Share

**Goal:** Review and share past jobs; retry failures.

### Planned features
- `GET /api/jobs` list screen in the frontend — job history with status badges
- Retry button for failed jobs (re-runs the full pipeline from the failed stage if possible, or from scratch)
- "Share" button on completed jobs — uses Web Share API or clipboard copy of download link
- Job cancellation — `DELETE /api/jobs/{job_id}` endpoint (kills thread, marks status=cancelled)
- Push notification (via local Service Worker) when a long-running job finishes (optional)

### TODOs
- [ ] `GET /api/jobs` list page component
- [ ] `DELETE /api/jobs/{job_id}` endpoint + thread cancellation (use `threading.Event`)
- [ ] Retry endpoint: `POST /api/jobs/{job_id}/retry`
- [ ] Web Share API integration in QuickJobPage progress screen
- [ ] Service Worker for background completion notifications

---

## M4 — Clip Review + Manual Edit on Mobile

**Goal:** Swipe through AI-generated clips and approve/reject/trim before rendering.

### Planned features
- Clip review swipe UI — swipe right = keep, swipe left = skip
- Inline video preview for each clip (uses `<video>` element + range request streaming)
- Trim handles (touch-draggable start/end markers) — sends `PATCH /api/clips/{clip_id}` with new `start_ms`/`end_ms`
- Approved clips flow directly into Quick Job or Story Builder
- "Quick render approved clips only" shortcut

### TODOs
- [ ] `PATCH /api/clips/{clip_id}` — update `start_ms`, `end_ms`, `clip_status`
- [ ] Swipe gesture component (react-spring or CSS transitions)
- [ ] Clip review route `/clips/review/:item_id`
- [ ] Inline video preview with streaming range requests (`/media/clips/...`)
- [ ] "Render selection" button → POST /api/jobs/quick with pre-approved clip list override

---

## Architecture Notes

- **Network access:** Run Kairos on a home server or laptop; mobile accesses via local IP
  (e.g. `http://192.168.1.x:8400`). Vite dev server `--host` flag or production build works.
- **No native app needed:** The frontend is a PWA-capable SPA. Add `manifest.json` + service
  worker for M3 to enable "Add to Home Screen" on iOS/Android.
- **Tailwind `md:` breakpoint** = 768px. Below = mobile layout, above = desktop layout.
- **`pb-safe`** in BottomNav uses `env(safe-area-inset-bottom)` for iPhone notch padding.
  Add `screens: { 'pb-safe': ... }` in `tailwind.config.js` if needed, or use `pb-4` as fallback.
