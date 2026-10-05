# Feature: Live Camera Detection (Operator Console)

> **What it is:** a **Live camera detection** button in the web Operator Console. Clicking it opens the user's camera, finds every face in view, and shows for each face: **attention status** (`Attentive` / `Distracted` / `Unknown`), **fatigue status** (`Normal` / `Fatigued` / `Unknown`) and the current **expression** (emotion).
> **Follows:** `README.md` (D1-D10, section 7), `contracts.md`, `system_work.md`, `model_download_integration_plan.md`, `ui.md`, `implementation.md`.
> **Hard requirement:** adding this feature must not change or break any existing feature. Section 4 lists the isolation guarantees and section 12 lists the tests that prove them.

---

## 1. Scope

### What the feature does
1. The user clicks **Live camera detection**.
2. A consent notice appears; after accepting, the browser asks for camera permission.
3. The browser sends compressed frames to the backend over an authenticated WebSocket.
4. The backend runs the **existing** AI pipeline (face mesh, tracking, MobileViT drowsiness, ViT expression, temporal scoring) and returns **JSON results only**.
5. The browser draws a box and a status card on every detected face. Closing the dialog stops the camera and the connection.

### What the feature does not do
- It does **not** save, record or return video or face images (D4). Frames exist in memory only while being analysed.
- It does **not** identify anyone (D5). Faces get anonymous labels `S001`, `S002`, ... for that live view only.
- It does **not** create sessions, observations or alerts, and does not touch the database.
- It does **not** appear in the mobile app (AI stays on the backend and video never reaches mobile, D3/D4).
- It does **not** promise 100% accuracy. See section 9.

---

## 2. Project rules this feature must respect

| Rule | How this feature complies |
|------|---------------------------|
| **D1/D3** AI runs on the backend, not in the client | The browser only captures and uploads frames and draws results. No model runs in the browser. |
| **D4** No raw video stored; video not sent to mobile; annotated frames only to the console | Nothing is stored. The server returns **no frames at all**, only numbers and labels; boxes are drawn locally over the user's own camera preview. |
| **D5** No face recognition | Labels are per-connection anonymous IDs. |
| **D6** Frozen labels | Uses the enums in `contracts.md` section 1 exactly. |
| **D7** Only validated results | Smoothing, `MIN_CONFIDENCE`, and hysteresis apply. A single frame never produces `Fatigued`. |
| **D8** Indicators, not diagnoses | UI copy says "indicator" and "possible". Expression is labelled a weak indicator. |
| **D10** No trained LSTM yet | Runs in `heuristic` mode and shows the mode. Untrained LSTM output is never shown as a real prediction. |
| **README section 7** Honest output | Shows `Unknown` for no face, occlusion, small face or low confidence. |
| **ui.md** | Tokens only, no new colors, icon + text for every status. |

---

## 3. Architecture

```text
 Browser (Operator Console)                          Backend (FastAPI)
 ┌────────────────────────────────────┐              ┌──────────────────────────────────────┐
 │ LiveCameraButton ─► Consent dialog │              │ /ws/live-camera  (new, isolated)     │
 │   getUserMedia (video only)        │   JSON       │  1. auth (JWT) + role + Origin       │
 │   <video> preview (mirrored)       │  frame ─────►│  2. limits (conns, size, fps, idle)  │
 │   canvas ► JPEG (≤640 px wide)     │  (1 in       │  3. LiveRunner (own tracker/state)   │
 │   one frame in flight at a time    │   flight)    │     reuses ai/ modules, read-only    │
 │                                    │◄───── JSON ──│  4. returns LiveTrackResult[] only   │
 │   overlay canvas draws boxes       │   results    │     (no image, no DB, no alerts)     │
 │   ResultsPanel lists each face     │              └──────────────────────────────────────┘
 └────────────────────────────────────┘
```

Existing paths stay untouched: `/ws/telemetry`, `/ws/video`, the session pipeline (Phase 12), REST routes, alerts, reports and the database.

---

## 4. Isolation guarantees (so other features are not affected)

| # | Guarantee | How it is enforced |
|---|-----------|--------------------|
| I1 | **Feature flag, off by default** | `LIVE_CAMERA_ENABLED=false` in config. When off, the endpoint closes with 4403 and the button is hidden (`VITE_LIVE_CAMERA_ENABLED`). |
| I2 | **New code only in new files** | Backend: `app/ws/live_camera.py`, `ai/live_runner.py`. Frontend: `src/features/live-camera/`. No existing function is edited. |
| I3 | **Minimal touch points** | Backend: one `include_router`/route registration line. Frontend: one lazy import for the button and one route. Nothing else. |
| I4 | **Additive contract only** | One new WebSocket endpoint, new message types, new config keys. No existing endpoint, schema, enum or table changes. |
| I5 | **No database use** | No migrations, no inserts. A test compares row counts before and after a live run. |
| I6 | **No alerts, no telemetry broadcast** | Live results go only to the connection that sent the frames. Never to `/ws/telemetry`, never to the alert engine. |
| I7 | **Separate state per connection** | Each connection owns its own MediaPipe instance, temporal buffers and scorer. The session pipeline's objects are never shared. |
| I8 | **Config is read, never mutated** | Live-specific values (for example `LIVE_WINDOW_FRAMES`) are passed as parameters. Global settings are not modified. A test asserts settings are identical before and after. |
| I9 | **Resource caps** | `LIVE_MAX_CONNECTIONS`, `LIVE_MAX_PER_USER`, `LIVE_WORKERS`, `LIVE_MAX_FPS`, `LIVE_MAX_FACES`. Live inference runs in its own bounded executor so it cannot starve the session pipeline. |
| I10 | **Failure containment** | Any exception inside a live connection closes only that connection. The frontend feature sits in an error boundary and is lazy-loaded, so a crash cannot take down other pages. |
| I11 | **Easy rollback** | Turn the flag off, or remove the two touch points and the new files. No data to migrate back. |

---

## 5. Prerequisites (must already be PASS in `docs/PROGRESS.md`)

| Needed | Phase | Why |
|--------|-------|-----|
| Models downloaded and verified | 2 | MobileViT and ViT weights |
| Tracker + features | 3 | Faces, landmarks, EAR/MAR, head pose |
| ROI crop | 4 | Model inputs |
| Drowsiness + expression wrappers | 5, 6 | Per-face predictions |
| Temporal buffer | 7 | Windowed PERCLOS, yawn, off-task |
| Scoring + validation | 10 | Statuses and scores |
| FastAPI + WebSocket + auth | 11, 14 | Endpoint pattern and JWT |
| Console scaffolding + tokens | 17 | Frontend shell and design system |

Also required:
- **HTTPS.** Browsers allow camera access only in a *secure context* (`https://` or `localhost`). A console opened as `http://192.168.x.x` on the school LAN **will not be able to open the camera**. Serve the console over TLS (see `README_SECURITY_TESTING.md`, S7). For local development use `localhost` or a local certificate (for example mkcert).
- A declared hardware profile (OQ-3). Frame rate depends on the number of faces and the CPU/GPU.

---

## 6. Contract additions (additive; add to `contracts.md` after owner approval)

Record the approval request in `docs/OPEN_QUESTIONS.md` (LC-4, section 14).

### 6.1 WebSocket endpoint

| Endpoint | Audience | Notes |
|----------|----------|-------|
| `/ws/live-camera?token=` | Operator Console only (`teacher` or `admin`), only when `LIVE_CAMERA_ENABLED=true` | Client sends frames; server replies with results only. Never forwarded to mobile. |

### 6.2 Messages

Client to server:

```json
{ "type": "frame", "seq": 41, "ts": "2026-10-05T09:30:12.120Z", "jpeg_b64": "<base64 JPEG>" }
{ "type": "ping" }
```

Server to client:

```json
{
  "type": "live_result",
  "seq": 41,
  "ts": "2026-10-05T09:30:12.310Z",
  "frame_size": [640, 480],
  "latency_ms": 74,
  "model_mode": "heuristic",
  "tracks": [ LiveTrackResult ]
}
{ "type": "skipped", "seq": 42, "reason": "rate_limit" }
{ "type": "pong" }
{ "type": "error", "code": "bad_frame", "message": "Frame could not be decoded." }
```

### 6.3 `LiveTrackResult`

```json
{
  "track_id": 1,
  "label": "S001",
  "bbox": [0.31, 0.18, 0.22, 0.34],
  "bbox_normalized": true,
  "warming_up": false,
  "attention_status": "Attentive",
  "fatigue_status": "Normal",
  "attention_score": 86.0,
  "fatigue_index": 0.14,
  "confidence": 0.94,
  "expression": { "top": "Neutral", "confidence": 0.71 }
}
```

Rules:
- `bbox` is `[x, y, w, h]`, each in 0-1 of the analysed frame (origin top-left, **not mirrored**).
- `warming_up = true` means the rolling window is not full yet. Both statuses are then `Unknown`.
- `expression` is `null` when its confidence is below `LIVE_EMOTION_MIN_CONF` or the face is unusable. `top` is one of the seven `emotion` values in `contracts.md` section 1.
- Emotion probabilities, landmarks, attention weights and embeddings are **never** sent (UI-6, APP-9).
- No image data in any server message.

### 6.4 Close codes

| Code | Meaning |
|------|---------|
| 4403 | Feature disabled, bad/expired token, role not allowed, or Origin not allowed |
| 4413 | Frame too large (bytes or dimensions) |
| 4429 | Too many live connections (global or per user) |
| 4408 | Idle timeout or maximum duration reached |
| 4503 | Server busy, try again |

> A WebSocket closed *before* it is accepted shows the browser only a generic failure, not the code. The endpoint therefore accepts the socket first, then closes with the code, so the UI can show a clear message.

### 6.5 Configuration (env/config, never hard-coded)

| Key | Default | Meaning |
|-----|---------|---------|
| `LIVE_CAMERA_ENABLED` | `false` | Master switch |
| `LIVE_MAX_CONNECTIONS` | `2` | Global concurrent live connections |
| `LIVE_MAX_PER_USER` | `1` | Concurrent live connections per user |
| `LIVE_WORKERS` | `1` | Size of the live inference executor |
| `LIVE_TARGET_FPS` | `10` | Frame rate the client aims for |
| `LIVE_MAX_FPS` | `15` | Server hard cap; extra frames get `skipped` |
| `LIVE_MAX_FACES` | `10` | `max_num_faces` for the live tracker |
| `LIVE_WINDOW_FRAMES` | `30` | Rolling window for the live view |
| `LIVE_MAX_FRAME_BYTES` | `300000` | Reject larger frames |
| `LIVE_MAX_DIM` | `1280` | Reject frames whose longest side is larger (pixels) |
| `LIVE_IDLE_TIMEOUT_S` | `300` | Close if no frames arrive |
| `LIVE_MAX_SESSION_S` | `1800` | Hard cap on one live connection |
| `LIVE_EMOTION_MIN_CONF` | `0.50` | Below this, expression is hidden (starting value, tune with data) |
| `VITE_LIVE_CAMERA_ENABLED` | `false` | Frontend build-time switch for the button |

Reused unchanged from `contracts.md` section 5: `MIN_CONFIDENCE`, `SMOOTHING`, `STATUS_HYSTERESIS_S`, `HEAD_LIMIT_DEG`, `MAX_INFER_MS_PER_FACE`.

---

## 7. Backend implementation

### 7.1 Files

```text
backend/
├─ ai/live_runner.py            # NEW  per-connection analysis (no I/O, no DB)
├─ app/ws/live_camera.py        # NEW  WebSocket endpoint, limits, validation
└─ tests/
   ├─ test_live_runner.py       # NEW
   ├─ test_live_camera_ws.py    # NEW
   └─ test_live_isolation.py    # NEW
```
Plus one line registering the new route in `app/main.py`.

### 7.2 `LiveRunner` (reuses existing modules)

Class and function names below are illustrative; use the real APIs from phases 3-10.

```python
# backend/ai/live_runner.py
import time
import numpy as np

class LiveRunner:
    """Analyses frames for ONE live connection.
    Owns its own tracker, temporal buffers and scorer. Writes nothing anywhere."""

    def __init__(self, models, cfg):
        self.models = models                    # shared, read-only weights
        self.cfg = cfg
        self.tracker = make_tracker(max_faces=cfg.LIVE_MAX_FACES)       # own instance
        self.buffers = make_buffers(window=cfg.LIVE_WINDOW_FRAMES)      # own state
        self.scorer = make_scorer(cfg)                                  # own EMA/hysteresis

    def process(self, frame_bgr: np.ndarray) -> dict:
        t0 = time.perf_counter()
        faces = self.tracker.update(frame_bgr)             # Phase 3 (boxes, landmarks, ids)
        results = []
        if faces:
            crops = build_rois(frame_bgr, faces)           # Phase 4 (in memory only)
            drowsy = self.models.drowsiness(crops)         # Phase 5 (batched)
            expr = self.models.expression(crops)           # Phase 6 (batched)
            for f, d, e in zip(faces, drowsy, expr):
                feats = compute_features(f)                # Phase 3/7
                window = self.buffers.push(f.track_id, feats, d, e)
                results.append(self.scorer.score(f, window, d, e))   # Phase 10
        h, w = frame_bgr.shape[:2]
        return {
            "frame_size": [w, h],
            "latency_ms": round((time.perf_counter() - t0) * 1000),
            "tracks": [to_live_track(r, self.cfg) for r in results],
        }

    def close(self):
        self.tracker.close()                               # release MediaPipe
```

Rules for `to_live_track`:
- `warming_up = window not full`; while true, both statuses are `Unknown`.
- Statuses are the **validated** ones (after smoothing and hysteresis), never per-frame.
- `expression` is smoothed (EMA over the seven probabilities) and its displayed `top` changes only after holding for `STATUS_HYSTERESIS_S`. Hidden if confidence is below `LIVE_EMOTION_MIN_CONF`.
- Face smaller than `MIN_FACE_PX` or landmark confidence below `MIN_CONFIDENCE` gives `Unknown`.
- Round numbers; never include arrays of probabilities, landmarks or image data.

### 7.3 Endpoint

```python
# backend/app/ws/live_camera.py  (sketch)
import asyncio, base64, binascii, io, time
from concurrent.futures import ThreadPoolExecutor
import cv2, numpy as np
from PIL import Image
from fastapi import APIRouter, WebSocket, Query

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=settings.LIVE_WORKERS)   # isolated from session pipeline
_limiter = LiveLimiter(settings.LIVE_MAX_CONNECTIONS, settings.LIVE_MAX_PER_USER)

@router.websocket("/ws/live-camera")
async def live_camera(ws: WebSocket, token: str = Query(...)):
    await ws.accept()                                   # accept first so close codes reach the browser
    if not settings.LIVE_CAMERA_ENABLED:
        return await ws.close(code=4403)
    user = authenticate_ws(token)                       # same helper as /ws/telemetry
    if user is None or user.role not in ("teacher", "admin") or not origin_allowed(ws):
        return await ws.close(code=4403)
    if not _limiter.acquire(user.id):
        return await ws.close(code=4429)

    runner = LiveRunner(model_registry, settings)
    started, last_ok = time.monotonic(), 0.0
    try:
        while True:
            if time.monotonic() - started > settings.LIVE_MAX_SESSION_S:
                return await ws.close(code=4408)
            try:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=settings.LIVE_IDLE_TIMEOUT_S)
            except asyncio.TimeoutError:
                return await ws.close(code=4408)

            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"}); continue
            if msg.get("type") != "frame":
                continue

            now = time.monotonic()
            if now - last_ok < 1.0 / settings.LIVE_MAX_FPS:
                await ws.send_json({"type": "skipped", "seq": msg.get("seq"), "reason": "rate_limit"})
                continue

            frame = decode_frame(msg.get("jpeg_b64"))   # raises FrameTooLarge / BadFrame
            loop = asyncio.get_running_loop()
            out = await loop.run_in_executor(_executor, runner.process, frame)
            last_ok = time.monotonic()
            await ws.send_json({"type": "live_result", "seq": msg["seq"],
                                "ts": utcnow_iso(), "model_mode": model_mode(), **out})
    except FrameTooLarge:
        await ws.close(code=4413)
    except BadFrame:
        await ws.send_json({"type": "error", "code": "bad_frame", "message": "Frame could not be decoded."})
    except Exception:
        log.exception("live camera connection failed")  # never log frames or tokens
        await ws.close(code=4503)
    finally:
        runner.close()
        _limiter.release(user.id)
```

`decode_frame` must be safe against oversized or malicious images:

```python
def decode_frame(b64: str) -> np.ndarray:
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, TypeError):
        raise BadFrame()
    if len(raw) > settings.LIVE_MAX_FRAME_BYTES:
        raise FrameTooLarge()
    w, h = Image.open(io.BytesIO(raw)).size            # reads the header only, no full decode
    if max(w, h) > settings.LIVE_MAX_DIM:              # blocks "small file, huge pixels" bombs
        raise FrameTooLarge()
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise BadFrame()
    return frame
```

Wrap the `Image.open` call so a non-image payload raises `BadFrame`, not an unhandled exception.

### 7.4 Backend rules
- **Never** write a frame, crop or decoded array to disk, a queue that persists, or a log (D4).
- **Never** call the database, alert engine or `/ws/telemetry` broadcaster from this module.
- Use a **new** MediaPipe Face Mesh instance per connection (it is not safe to share), and release it in `close()`.
- Model weights are shared read-only; use `torch.inference_mode()` and `.eval()` as in the wrappers.
- If the executor is saturated, answer with `{"type":"error","code":"busy"}` and close 4503 rather than queueing without limit.

---

## 8. Frontend implementation

### 8.1 Files

```text
operator-console/src/features/live-camera/      # NEW folder, self-contained
├─ index.ts                       # exports LiveCameraButton (lazy)
├─ LiveCameraButton.tsx           # the button in the toolbar
├─ LiveCameraDialog.tsx           # consent, preview, overlay, results
├─ ConsentNotice.tsx
├─ OverlayCanvas.tsx              # draws boxes and labels
├─ ResultsPanel.tsx               # one card per face
├─ useCamera.ts                   # getUserMedia lifecycle
├─ useLiveSocket.ts               # WebSocket + one-in-flight loop
├─ frameCapture.ts                # video -> JPEG base64
├─ errors.ts                      # error to message mapping
├─ types.ts                       # LiveTrackResult etc.
└─ __tests__/
```

Touch points elsewhere (the only two):
1. The toolbar renders `<LiveCameraButton />` (imported with `React.lazy`, wrapped in an error boundary, rendered only if `VITE_LIVE_CAMERA_ENABLED === "true"`).
2. Optional route `/live-camera` if you prefer a page over a dialog.

Existing components keep their props and behavior. Reuse existing `StatusBadge`, `Dialog` and `Button`; do not edit them.

### 8.2 User flow

| Step | What the user sees |
|------|--------------------|
| 1 | Button **Live camera detection** (camera icon + text). |
| 2 | Dialog with consent text: camera is used only while this window is open; video is analysed on the server and **not recorded or stored**; results are indicators only. Buttons: **Start camera** / **Cancel**. |
| 3 | Browser permission prompt. While waiting: loading state. |
| 4 | Live preview with a persistent **Camera on** badge, face boxes, and a results panel. |
| 5 | **Stop** button, Escape key, closing the dialog, switching tab for more than 30 s, or the idle/max-duration timeout all stop the camera and close the socket. |

### 8.3 Camera access (`useCamera.ts`)

```ts
export async function openCamera(): Promise<MediaStream> {
  if (!window.isSecureContext) throw new LiveCameraError("INSECURE_CONTEXT");
  if (!navigator.mediaDevices?.getUserMedia) throw new LiveCameraError("UNSUPPORTED");
  return navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
    audio: false,                                   // never request the microphone
  });
}

export function stopCamera(stream: MediaStream | null) {
  stream?.getTracks().forEach((t) => t.stop());     // turns the camera light off
}
```

Video element: `muted`, `playsInline`, `autoPlay`. Mirror the **preview only** with CSS `transform: scaleX(-1)` so it feels like a mirror. The frames sent to the server are **not** mirrored.

Always call `stopCamera` on dialog close, component unmount, route change and `visibilitychange` (hidden for more than 30 s).

### 8.4 Sending frames (`frameCapture.ts`, `useLiveSocket.ts`)

```ts
const canvas = document.createElement("canvas");

export function grabFrame(video: HTMLVideoElement, maxW = 640, quality = 0.7): string | null {
  const vw = video.videoWidth, vh = video.videoHeight;
  if (!vw || !vh) return null;                      // camera not ready yet
  const scale = Math.min(1, maxW / vw);
  canvas.width = Math.round(vw * scale);
  canvas.height = Math.round(vh * scale);
  canvas.getContext("2d")!.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", quality).split(",")[1];   // base64 only
}
```

Loop rules (this is what keeps the connection healthy):
- **One frame in flight.** Send the next frame only after `live_result` or `skipped` for the previous one arrives. The effective frame rate then adapts to server speed automatically and no queue builds up.
- Throttle to `LIVE_TARGET_FPS` (default 10) using `requestVideoFrameCallback` when available, else `setTimeout`.
- If no reply arrives within 3 s, clear the in-flight flag and show "Connection slow".
- Send `ping` every 20 s.
- On socket close, map the code (section 6.4) to a message and stop the camera.
- Token goes in `?token=`. Never print it to the console.
- Use `wss://` whenever the page is served over `https://`.

### 8.5 Drawing results (`OverlayCanvas.tsx`)

- Overlay canvas sits exactly on top of the video, same displayed size.
- Convert normalized boxes to pixels and account for the mirrored preview:

```ts
function toCanvasRect([x, y, w, h]: number[], W: number, H: number, mirrored = true) {
  const nx = mirrored ? 1 - (x + w) : x;
  return { x: nx * W, y: y * H, w: w * W, h: h * H };
}
```

- Stroke color and icon come from `tokens.ts` status constants (UI-3). **No hex literals in drawing code.**
- The label (`S001 · Attentive · Normal`) is drawn as normal, unmirrored text.
- If no result arrives for 2 s, clear the overlay rather than showing stale boxes.
- Respect `prefers-reduced-motion` (no animated transitions).

### 8.6 Results panel (`ResultsPanel.tsx`)

One card per face:

| Element | Source | Rule |
|---------|--------|------|
| Label `S001` | `label` | Anonymous only |
| Attention badge | `attention_status` | `StatusBadge` (UI-3): color + icon + text |
| Fatigue badge | `fatigue_status` | Same |
| Expression chip | `expression.top` | Neutral styling, **no color coding** (ui.md has no emotion palette); text such as "Expression (indicator): Neutral". If `null`: "Expression: not clear" |
| Confidence | `confidence` | Percentage, for example "94%" |
| Warm-up note | `warming_up` | "Collecting data (about N s)" where N is roughly `LIVE_WINDOW_FRAMES` divided by the current frame rate |

Footer line: "Mode: heuristic (rule-based). Indicators to support teacher observation, not a diagnosis." (D8, D10).

### 8.7 UI states (required by `ui.md` UI-5)

| State | Behavior |
|-------|----------|
| Default | Button visible, enabled |
| Hover / focus-visible / active | Per tokens; focus ring `accent.primary` 2 px |
| Disabled | If feature flag on but server says disabled (4403), button stays but shows a message on click |
| Loading | While waiting for permission or the first result |
| Error | Message from the table below with a **Try again** button |
| Empty | Camera on, no face: "No face detected. Face the camera in good light." |
| Many faces | Panel scrolls; summary line "N faces detected" |
| Unknown | Shown explicitly, never hidden |

### 8.8 Error messages

| Cause | Detection | Message to the user |
|-------|-----------|---------------------|
| Not HTTPS | `!window.isSecureContext` | "The camera needs a secure (HTTPS) connection. Ask your administrator." |
| Permission denied | `NotAllowedError` | "Camera permission was blocked. Allow it in the browser address bar and try again." |
| No camera | `NotFoundError` | "No camera found." |
| Camera busy | `NotReadableError` | "The camera is in use by another app or window. Close it and try again." |
| Unsupported settings | `OverconstrainedError` | Retry once with plain `{ video: true }` |
| Browser unsupported | no `getUserMedia` | "This browser does not support camera access. Use a current Chrome, Edge, Firefox or Safari." |
| Feature disabled | close 4403 | "Live camera detection is not enabled on this server." |
| Too many users | close 4429 | "Live detection is busy. Try again in a moment." |
| Server busy | close 4503 | Same as above |
| Idle / max time | close 4408 | "The live view stopped after a period of inactivity." |
| Connection lost | socket error | "Connection lost." with **Reconnect** |

### 8.9 Accessibility (UI-5)
- Dialog: focus moves in on open and returns to the button on close; Escape closes; Tab order is logical.
- A text list of results (the panel) is the accessible alternative to the visual overlay.
- A hidden `aria-live="polite"` region announces **changes of status or face count only**, not every frame.
- Camera-on state is shown by text and icon, not color alone.
- Contrast and touch targets follow `ui.md`.

### 8.10 Frontend rules
- Tokens only; the CI token lint must pass.
- Forbidden in this folder (add to the CI forbidden-pattern lint): `MediaRecorder`, `canvas.toBlob`/`toDataURL` results stored anywhere, `localStorage`/`sessionStorage`/`IndexedDB` writes of frames or results, `dangerouslySetInnerHTML`, any `console.log` of tokens or frames.
- Frames live only in local variables and are dropped after sending.

---

## 9. What "correct output" means here (honest accuracy)

The project does **not** include a measured accuracy figure for these models in real conditions (`model_download_integration_plan.md` MDL-5). So the feature is built to be **correct about its own uncertainty**, not to claim a fixed accuracy.

| Principle | Implementation |
|-----------|----------------|
| Don't guess | `Unknown` when there is no face, the face is too small or occluded, or confidence is below `MIN_CONFIDENCE` |
| Don't judge from one frame | Rolling window, smoothing, hysteresis (D7). Fatigue needs several seconds of data; until then `Unknown` with "Collecting data" |
| Be transparent | Confidence shown; mode `heuristic` shown (D10) |
| Weak signals stay weak | Expression is labelled an indicator and **never** drives attention or fatigue on its own (`contracts.md` section 6) |
| Measure, don't assume | Section 12.5 defines a validation protocol; results go in `PROGRESS.md` and replace assumptions |

How each output is produced:
- **Fatigue status:** from `fatigue_index = 0.45*p_drowsy + 0.35*perclos + 0.20*yawn`; `Fatigued` at 0.55 or above, held through hysteresis (`contracts.md` section 6, starting values to tune).
- **Attention status:** from `attention_score`, mainly head direction outside `HEAD_LIMIT_DEG` over the window; `Distracted` at 55 or below.
- **Expression:** top class of the ViT model, smoothed; a weak, culturally variable proxy.

Known limits to show in the UI help text: low light, glasses glare, masks, hands over the face, extreme head angles, small or distant faces, many overlapping faces, and webcams with low resolution.

---

## 10. Security and privacy

Apply the checks in `README_SECURITY_TESTING.md` and `README_SECURITY_ADDITIONAL_CHECKS.md`. Specific to this feature:

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| LS1 | Connect without token, or with expired/tampered token | Closed with 4403 | MUST |
| LS2 | Role other than `teacher`/`admin` | Closed with 4403 | MUST |
| LS3 | `Origin` not in the allow-list | Closed with 4403 | MUST |
| LS4 | Flag off | Closed with 4403 | MUST |
| LS5 | Second connection from the same user | Closed with 4429 | MUST |
| LS6 | Connections above `LIVE_MAX_CONNECTIONS` | Closed with 4429 | MUST |
| LS7 | Frame above `LIVE_MAX_FRAME_BYTES` | Closed with 4413 | MUST |
| LS8 | Small file with huge pixel dimensions (decompression bomb) | Rejected before full decode, 4413 | MUST |
| LS9 | Non-image or invalid base64 payload | `error` message, no crash | MUST |
| LS10 | Frames sent faster than `LIVE_MAX_FPS` | `skipped`, server stays healthy | MUST |
| LS11 | No frames for `LIVE_IDLE_TIMEOUT_S` | Closed with 4408 | MUST |
| LS12 | Run for `LIVE_MAX_SESSION_S` | Closed with 4408 | SHOULD |
| LS13 | No `.jpg/.png/.npy/.mp4` created anywhere during a run | None | MUST |
| LS14 | No frame data, base64 or token in logs | None | MUST |
| LS15 | Server messages contain no image field, landmarks or probabilities | Payload check | MUST |
| LS16 | Mobile app has no code path to this endpoint | Code search | MUST |
| LS17 | Camera light turns off after Stop, dialog close, route change and tab-hidden timeout | Manual check | MUST |
| LS18 | Microphone is never requested | Network/permission check | MUST |

Consent: this feature captures people's faces. Before use with students or visitors, the consent and notification policy (OQ-5) must exist. The in-app notice does not replace it.

---

## 11. Build plan (follow the README section 6 protocol: one step, test, record)

| Step | Work | Test | Pass condition |
|------|------|------|----------------|
| **LC-1** Contract and config | Add section 6 to `contracts.md` (after owner approval); add the `LIVE_*` keys to config with defaults | Schema review; config loads with flag off | No existing key or schema changed |
| **LC-2** Live runner | Implement `ai/live_runner.py` | `test_live_runner.py`: no face, one face, five faces, warm-up, closed-eye sequence, look-away sequence, low confidence | Statuses `Unknown` during warm-up; a single closed-eye frame never gives `Fatigued`; output has no image/landmark/probability fields; `close()` releases the tracker |
| **LC-3** Endpoint | Implement `app/ws/live_camera.py`, register route | `test_live_camera_ws.py`: auth, role, Origin, flag, limits, size, bomb, bad payload, idle, rate limit | All LS1-LS12 pass; one failing connection does not affect others |
| **LC-4** Frontend camera | `useCamera`, `frameCapture`, error mapping | Unit tests with mocked `getUserMedia` for each error name | Every error in 8.8 shows the right message; tracks are stopped on close |
| **LC-5** Frontend UI | Button, consent, dialog, socket hook, overlay, results panel | Component tests plus a mock WebSocket; axe accessibility check; token lint | All states in 8.7 render; overlay boxes line up (mirror test); no hex/px literals; axe clean |
| **LC-6** Isolation and regression | Run section 12.3 | Full existing backend and frontend suites; Phase 12 benchmark with live clients | Existing tests unchanged and passing; session FPS still at or above `TARGET_FPS` |
| **LC-7** Accuracy validation | Run protocol 12.5 with consenting adult volunteers | Scenario table | Results recorded; owner-approved acceptance targets met or limits documented |
| **LC-8** Security and privacy | Run section 10 and the two security guides | Listed tests | All MUST pass |

Append a record to `docs/PROGRESS.md` after each step using the README template.

---

## 12. Test plan

### 12.1 Functional

| # | Scenario | Expected |
|---|----------|----------|
| F1 | Click button, accept consent, allow camera | Preview appears, **Camera on** badge shown |
| F2 | One person facing camera, eyes open | After warm-up: `Attentive` / `Normal` |
| F3 | Person looks away for longer than the persistence window | `Distracted` |
| F4 | Person keeps eyes closed for several seconds | `Fatigued` after hysteresis; never on a normal blink |
| F5 | Several people in view | One box and one card per face, distinct labels |
| F6 | Person leaves and returns | Previous label may change; no crash |
| F7 | Cover the camera | "No face detected" |
| F8 | Face too small or far away | `Unknown` |
| F9 | Posed expressions (happy, sad, surprise, neutral, ...) | Expression follows; hidden if unclear |
| F10 | Press Stop / Escape / close dialog | Camera light off, socket closed |
| F11 | Switch to another tab for more than 30 s | Camera stops, message shown |
| F12 | Open the feature twice (second tab) | Second refused with the 4429 message |

### 12.2 UX and errors
Run every row of section 8.8 (block permission, unplug camera, camera in use, plain HTTP, old browser, server flag off, server restart during use).

### 12.3 Isolation (proves other features are unaffected)

| # | Test | Pass condition |
|---|------|----------------|
| ISO1 | Flag off | Button hidden; endpoint closes 4403; everything else behaves as before |
| ISO2 | Run the **entire existing backend test suite** | Same results as before the feature |
| ISO3 | Run existing frontend tests and production build | Same results; main bundle size unchanged (live code is a separate lazy chunk) |
| ISO4 | Row counts of `observations`, `alerts`, `sessions`, `users` before and after a live run | Identical |
| ISO5 | Start a monitoring session, then run live detection | No live data on `/ws/telemetry`; no new alerts; session `ClassSnapshot` unchanged |
| ISO6 | Phase 12 benchmark with 0, 1 and `LIVE_MAX_CONNECTIONS` live clients | Session FPS stays at or above `TARGET_FPS`, or the measured drop is recorded and accepted by the owner |
| ISO7 | Inject an exception inside `LiveRunner.process` | Only that connection closes; session pipeline keeps running |
| ISO8 | Compare global settings object before and after a live run | Identical (nothing mutated) |
| ISO9 | Live client and session pipeline run together | Separate track IDs and state, no cross-talk |
| ISO10 | OpenAPI/route diff | Only the new WebSocket route added; no existing route changed |
| ISO11 | Existing contract tests (JSON shapes) | Unchanged and passing |
| ISO12 | Remove the two touch points and the new files | Project builds and passes all tests (rollback works) |

### 12.4 Performance (measure on the declared hardware, OQ-3)

Record in `PROGRESS.md`: frames per second reached with 1, 3 and 5 faces; round-trip latency p50 and p95; server CPU/GPU use; bandwidth per client; memory after a 30-minute run (must not grow).
Expectations to verify, not assumptions: frame rate adapts down under load instead of queueing; closing the dialog frees server memory and the MediaPipe instance.

### 12.5 Accuracy validation protocol (LC-7)

Use consenting adult volunteers only, a fixed webcam, and log results without saving video.

| Scenario | Repeats | What to record |
|----------|---------|----------------|
| Frontal, good light, eyes open, looking at camera | 10 | Correct `Attentive` / `Normal` rate |
| Looking away (left, right, down) for 10 s | 10 | Correct `Distracted` rate and delay |
| Eyes closed 3 s, normal blinks, long blinks | 10 each | `Fatigued` triggered vs blinks wrongly flagged |
| Yawning | 10 | Effect on fatigue index |
| Seven posed expressions | 10 each | Top expression matches the pose |
| Glasses, low light, mask, hand on chin | 5 each | How often output correctly falls back to `Unknown` |
| 2, 3 and 5 people together | 5 each | All faces found; labels stable |

Compute per-scenario correct rates and false-alert rates, then have the project owner approve acceptance targets. A starting proposal for controlled conditions (frontal, good light) is a correct-status rate of at least 90 percent with near-zero false `Fatigued` on normal blinks; this is a **proposal to tune, not a validated figure**. Report anything that misses the target as a documented limit rather than hiding it.

---

## 13. Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Button does nothing / "needs HTTPS" | Page served over plain HTTP on the LAN | Serve the console over HTTPS; use `localhost` for development |
| `NotReadableError` on the same computer as the server | The server-side pipeline (OpenCV) already holds the webcam | Use a different camera, or stop the server capture for the test |
| Overlay boxes in the wrong place | Mirror not accounted for, or overlay size differs from video | Use `toCanvasRect` with `mirrored=true`; match canvas size to the displayed video size |
| Everything shows `Unknown` | Warm-up, small face, poor light, or low landmark confidence | Wait a few seconds; move closer; improve lighting |
| Low frame rate | Many faces or slow hardware | Reduce `LIVE_MAX_FACES`; measure per-face latency; frame rate adapts automatically |
| Closes with 4403 | Flag off, expired token, wrong role or Origin | Check `LIVE_CAMERA_ENABLED`, log in again, check the Origin allow-list |
| Closes with 4429 | Another live window open, or global limit reached | Close the other window or raise limits carefully |
| Closes with 4413 | Frame too big | Lower `maxW` or JPEG quality in `frameCapture.ts` |

---

## 14. Open questions (add to `docs/OPEN_QUESTIONS.md`)

| ID | Question | Conservative default |
|----|----------|----------------------|
| LC-1 | Should `PRIVACY_MODE=true` also block this feature? It returns no video, only results, but it uploads faces from the user's own camera. | Independent flag, off by default; owner decides |
| LC-2 | Who may use it: teachers and admins, or admins only? | Both, per this README |
| LC-3 | Acceptance targets for correct-status rates (section 12.5) | Measure first, owner sets targets |
| LC-4 | Approve the additive contract changes in section 6 | Add to `contracts.md` only after approval |
| LC-5 | Should live detection be usable while a monitoring session is running? | Allowed, with resource caps and the ISO6 check |
| LC-6 | Consent and notification policy for people in front of the camera (OQ-5) | Do not use with students until approved |

---

## 15. Final checklist

- [ ] Prerequisites (section 5) are PASS, HTTPS is available.
- [ ] Contract and config additions approved and added (LC-1).
- [ ] `LiveRunner` tests pass, including single-closed-frame and warm-up cases (LC-2).
- [ ] Endpoint tests pass: auth, role, Origin, limits, size, bomb, idle (LC-3).
- [ ] Frontend camera lifecycle and all error messages verified (LC-4).
- [ ] UI states, overlay alignment, accessibility and token lint pass (LC-5).
- [ ] All isolation tests ISO1-ISO12 pass; existing suites unchanged (LC-6).
- [ ] Accuracy protocol run and recorded; limits documented (LC-7).
- [ ] Security tests LS1-LS18 and both security guides pass (LC-8).
- [ ] No frames stored, none in logs, none returned to the browser, none reachable from mobile.
- [ ] Rollback verified: flag off, and removal of the two touch points, restores the original behavior.
- [ ] Results appended to `docs/PROGRESS.md`.
