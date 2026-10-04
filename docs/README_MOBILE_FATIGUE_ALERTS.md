# Mobile App: Class Fatigue Advisory Alerts

> **Scope:** the teacher/admin **Mobile App** (React Native + Expo, phases 21–23). The backend turns the class-level fatigue score into one of four advisory messages. The app shows the message on the dashboard and as a push notification.
> **Follows:** `README.md` (D4, D7, D8), `contracts.md` (§1 enums, §2.4 `ClassSnapshot`, §4 WebSocket), `ui.md` (UI-2 tokens, UI-3 status colors).
> **Not covered:** the per-student `fatigue` alert in `contracts.md` §2.3. That alert stays as it is. This advisory is a separate, class-level message.

---

## 1. What it does

The app tells the teacher what to do next, based on how fatigued the class is overall:

| Class fatigue score | Level | Message shown to the teacher |
|---------------------|-------|------------------------------|
| 0% to below 25% | 1 | **Continue with the class.** |
| 25% to below 50% | 2 | **Make the session more interactive.** |
| 50% to below 75% | 3 | **Do a short activity or give a short break.** |
| 75% to 100% | 4 | **Most students show fatigue indicators. Consider continuing the class tomorrow.** |

> **Fix to the original request:** it listed `50 to 75%` and `70 to 100%`, which overlap between 70 and 75. This README uses **75** as the boundary. The values are configurable (section 5).

The messages are **suggestions**. The teacher decides what to do (decision D8). Nothing happens automatically.

---

## 2. How the score is computed

```text
class_fatigue_pct = 100 × mean(fatigue_index of all tracks whose status is not "Unknown")
```

- `fatigue_index` is the 0–1 value from `contracts.md` §2.1 / §6, so the percentage ranges from 0 to 100.
- Tracks with `fatigue_status = "Unknown"` (no face, occlusion, confidence below `MIN_CONFIDENCE`) are **excluded**, not counted as zero.
- If fewer than `ADVISORY_MIN_TRACKS` (default 5) tracks are usable, no advisory is sent and the app shows "Not enough data".
- The score comes from the backend. The app never computes it and never runs AI (SYS-0).

---

## 3. Stability rules (avoid flickering messages)

Per decision D7, a single noisy reading must never change the message.

1. **Smoothing:** apply an EMA (α = 0.3, same as `SMOOTHING`) to `class_fatigue_pct`.
2. **Hold time:** a new level must hold for `STATUS_HYSTERESIS_S` (3 s) before the displayed level changes.
3. **Push persistence:** a push notification is sent only when the level has held for `ADVISORY_PERSIST_S` (default 60 s).
4. **Cooldown:** at most one push per level per session within `ALERT_COOLDOWN_S` (300 s). Moving up to a higher level may push immediately after its persistence time.
5. **Level 4 needs confirmation:** it requires `ADVISORY_PERSIST_S` plus `ADVISORY_MIN_TRACKS` usable tracks, because "take the class tomorrow" is the most consequential message.
6. **Dashboard vs push:** the dashboard banner always shows the current level. Push notifications follow rules 3–5.

---

## 4. Data contract (additive change)

The advisory is an **additive field** on the existing `ClassSnapshot` (`contracts.md` §2.4), delivered over `/ws/telemetry` and `GET /teacher/dashboard`. No existing field changes.

```json
{
  "session_id": 12,
  "class_name": "III AI & DS",
  "status": "Monitoring",
  "students_detected": 45,
  "counts": { "attentive": 35, "distracted": 7, "unknown": 0, "fatigued": 3 },
  "avg_attention_score": 82.0,
  "open_alerts": 3,

  "fatigue_advisory": {
    "class_fatigue_pct": 62.4,
    "level": 3,
    "code": "SHORT_BREAK",
    "message": "Do a short activity or give a short break.",
    "usable_tracks": 41,
    "since": "2026-09-30T10:42:11Z"
  }
}
```

| `level` | `code` | `message` |
|---------|--------|-----------|
| 1 | `CONTINUE` | Continue with the class. |
| 2 | `INTERACTIVE` | Make the session more interactive. |
| 3 | `SHORT_BREAK` | Do a short activity or give a short break. |
| 4 | `RESCHEDULE` | Most students show fatigue indicators. Consider continuing the class tomorrow. |

When there is not enough data: `"fatigue_advisory": null`.

**Privacy (D4):** the advisory contains only class-level numbers. It has no names, no per-student data, no images. It is safe to send to mobile.

### Push notification payload

```json
{
  "title": "III AI & DS: fatigue indicator",
  "body": "Do a short activity or give a short break.",
  "data": { "session_id": 12, "level": 3, "code": "SHORT_BREAK" }
}
```

Tapping the notification opens the Dashboard for that session.

---

## 5. Configuration (env / config, never hard-coded)

| Key | Default | Meaning |
|-----|---------|---------|
| `ADVISORY_BANDS` | `25,50,75` | Upper limits for levels 1, 2 and 3 (percent) |
| `ADVISORY_MIN_TRACKS` | `5` | Minimum usable tracks before any advisory |
| `ADVISORY_PERSIST_S` | `60` | A level must hold this long before a push |
| `ALERT_COOLDOWN_S` | `300` | Reused from `contracts.md` §5 |
| `STATUS_HYSTERESIS_S` | `3` | Reused from `contracts.md` §5 |

Level selection:

```python
def advisory_level(pct, bands=(25, 50, 75)):
    if pct < bands[0]: return 1   # 0  to <25
    if pct < bands[1]: return 2   # 25 to <50
    if pct < bands[2]: return 3   # 50 to <75
    return 4                      # 75 to 100
```

---

## 6. Mobile app behavior

### Dashboard banner
- A single banner above the `StatCard`s showing the level icon, the level label and the message.
- It updates live from `/ws/telemetry`.
- It sits at the top of the screen, never inside a menu (UI-6 anti-pattern).
- It uses `aria-live="polite"` (or `accessibilityLiveRegion="polite"` on React Native) so screen readers announce changes.

### Visual mapping (`ui.md` tokens only, no new colors)

Status is never shown by color alone: every level has an icon **and** a text label (UI-3).

| Level | Icon | Text/icon token | Background | Border |
|-------|------|-----------------|------------|--------|
| 1 | check-circle | `accent.success` | `bg.success` | `accent.success` |
| 2 | message-circle | `accent.primary` | `bg.info` | `accent.primary` |
| 3 | alert-triangle | `accent.danger` | `bg.surface` | `accent.danger` |
| 4 | alert-octagon | `accent.danger` | `bg.surface` | `accent.danger` |
| No data | help-circle | `text.secondary` | `bg.surface` | `border.subtle` |

> **Open design gap (from UI-3):** the palette has no amber/warning color. Levels 3 and 4 differ by icon and wording only. Add a warning token to `ui.md` UI-2 first if the project owner approves one.

### Offline and stale data
- If the WebSocket is down or the AI is offline, show the `ConnectionBanner` and **hide the advisory** (or mark it "Stale"). Never show an old advisory as if it were live (APP-21).
- If `fatigue_advisory` is `null`, show "Not enough data" with the `help-circle` icon.

### Copy rules (D8, UI-6)
- Say "indicator", "show fatigue indicators", "consider". Never "is sleeping", "is sick", "lazy".
- Level 4 is a recommendation to the teacher, not an instruction.

---

## 7. Example client code (React Native + TypeScript)

```tsx
type Advisory = {
  class_fatigue_pct: number;
  level: 1 | 2 | 3 | 4;
  code: "CONTINUE" | "INTERACTIVE" | "SHORT_BREAK" | "RESCHEDULE";
  message: string;
  usable_tracks: number;
  since: string;
};

const LEVEL_STYLE = {
  1: { icon: "check-circle",  color: "accent.success", bg: "bg.success" },
  2: { icon: "message-circle", color: "accent.primary", bg: "bg.info" },
  3: { icon: "alert-triangle", color: "accent.danger",  bg: "bg.surface" },
  4: { icon: "alert-octagon",  color: "accent.danger",  bg: "bg.surface" },
} as const;

export function AdvisoryBanner({ advisory }: { advisory: Advisory | null }) {
  if (!advisory) return <NoDataBanner />;                  // "Not enough data"
  const s = LEVEL_STYLE[advisory.level];
  return (
    <View accessibilityLiveRegion="polite" accessibilityRole="alert"
          style={bannerStyle(s.bg, s.color)}>
      <Icon name={s.icon} color={token(s.color)} />
      <Text>{`Level ${advisory.level}`}</Text>
      <Text>{advisory.message}</Text>
      <Text>{`${Math.round(advisory.class_fatigue_pct)}% fatigue indicators`}</Text>
    </View>
  );
}
```

Use token names from `theme.ts`. Do not write hex values in components.

---

## 8. Tests (pass conditions)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Score 10%, 24.9% | Level 1, `CONTINUE` |
| 2 | Score 25%, 49.9% | Level 2, `INTERACTIVE` |
| 3 | Score 50%, 74.9% | Level 3, `SHORT_BREAK` |
| 4 | Score 75%, 100% | Level 4, `RESCHEDULE` |
| 5 | Score jumps 20% to 80% for 1 second, then returns to 20% | No level change, no push (D7) |
| 6 | Level 4 held for `ADVISORY_PERSIST_S` | One push, then none inside the cooldown |
| 7 | Fewer than 5 usable tracks | `fatigue_advisory = null`, "Not enough data" |
| 8 | Many `Unknown` tracks | Unknown tracks excluded from the average |
| 9 | WebSocket drops | Advisory hidden or marked "Stale", connection banner shown |
| 10 | Accessibility | Level text and icon present, screen reader announces changes, touch targets at least 44 dp |
| 11 | Wording check | No diagnostic or disciplinary words in any message |

---

## 9. Open questions (record in `docs/OPEN_QUESTIONS.md`)

| ID | Question | Conservative default |
|----|----------|----------------------|
| AQ-1 | Is the class score the **mean fatigue index** (used here) or the **percentage of students marked `Fatigued`**? | Mean fatigue index. |
| AQ-2 | Should teachers be able to snooze or dismiss an advisory? | No dismissal. The banner reflects the live level. |
| AQ-3 | Should admins also receive the advisory? | Teachers only, for their assigned classes. |
| AQ-4 | The `fatigue_advisory` field is an addition to `contracts.md` §2.4. Approve it and update the contract before building. | Add it as an optional field only. |
| AQ-5 | Add a warning (amber) token to `ui.md`? | No new colors without approval. |

---

## 10. Build checklist

- [ ] Add `fatigue_advisory` to `contracts.md` §2.4 and backend `ClassSnapshot` (after AQ-4 approval).
- [ ] Backend: compute class score, apply EMA, hysteresis, persistence and cooldown.
- [ ] Backend: send the field over `/ws/telemetry` and `/teacher/dashboard`.
- [ ] Backend: send push notifications (Expo push) for levels per section 3.
- [ ] Mobile: `AdvisoryBanner` with all states (default, no data, stale, error).
- [ ] Mobile: notification tap opens the Dashboard.
- [ ] Tests 1–11 pass; append results to `docs/PROGRESS.md`.
