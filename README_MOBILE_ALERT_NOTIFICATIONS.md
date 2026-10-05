# Mobile App Alert Notifications (Class Fatigue Advisory, Loud Sound)

> **What it does:** while the backend is running and a class session is being monitored, the teacher's phone gets a **push notification with a loud sound** that tells them what to do, based on the class fatigue score.
> **Extends:** `README_MOBILE_FATIGUE_ALERTS.md` (score definition and banner). This file covers **delivery**: push notifications, sound, run order and tests.
> **Follows:** `README.md` (D4, D7, D8), `contracts.md`, `ui.md`, `implementation.md` (phases 15, 21-22).

---

## 1. The four alerts

| Class fatigue score | Level | Message on the phone |
|---------------------|-------|----------------------|
| 0% to below 25% | 1 | **Continue with the class.** |
| 25% to below 50% | 2 | **Make the session more interactive.** |
| 50% to below 75% | 3 | **Do a short activity or give a short break.** |
| 75% to 100% | 4 | **Most students show fatigue indicators. Consider continuing the class tomorrow.** |

> **Fix to the original request:** it had `50 to 75%` and `70 to 100%`, which overlap between 70 and 75. This README uses **75** as the boundary. Boundaries are configurable (section 6.4).

> **Wording:** level 4 was "all the students are fatigue, take class tomorrow". It is written here as an indicator and a suggestion because the project rules (D8) forbid presenting AI output as a verdict. The teacher decides.

### How the score is computed (summary)

```text
class_fatigue_pct = 100 × mean(fatigue_index of tracks whose fatigue_status is not "Unknown")
```
Computed on the backend. The app never calculates it. Fewer than `ADVISORY_MIN_TRACKS` usable faces means no advisory. Full details are in `README_MOBILE_FATIGUE_ALERTS.md`.

---

## 2. What must be running

| Component | Needed for notifications? | Role |
|-----------|---------------------------|------|
| **Backend** (FastAPI) | **Yes** | Computes the score, decides the level, sends the push |
| **AI pipeline + camera feed** | **Yes** (or the mock generator for testing) | Produces the fatigue data |
| **A session in `Monitoring` state** | **Yes** | Scores only exist during a session |
| **Phone with the app, logged in, notifications allowed, push token registered** | **Yes** | Receives the alert |
| **Web Operator Console** | **No** (not for delivery) | Used to log in and **start the session**. Once the session is running you can close it and the phone still gets alerts |

So the full demo setup is: backend running, web console running (to start the session), phone app logged in.

---

## 3. How the loud sound is achieved, and what cannot be forced

An app **cannot** raise the phone's volume or override the silent switch. What this feature does instead is use every mechanism the operating systems offer to make the alert as loud and hard to miss as they allow.

| Platform | What we set | Effect | Limit |
|----------|-------------|--------|-------|
| **Android** | Notification channel with importance **MAX**, a bundled loud sound, audio usage **ALARM**, strong vibration, optional **bypass Do Not Disturb** | Plays on the **alarm volume stream**, pops up as a heads-up notification | The user can lower or mute the channel in system settings; bypass-DND needs a permission the user must grant. Channel settings cannot be changed by the app after creation, so use versioned channel IDs (`-v1`, `-v2`) |
| **iOS** | Bundled custom sound (up to 30 s) and **Time Sensitive** interruption level for levels 3-4 | Plays at the ringer volume; time-sensitive can break through a Focus mode | The **silent switch mutes** normal notification sounds. **Critical alerts** (which ignore the silent switch) need special approval from Apple and are normally granted for health/safety apps, so they are **off by default** |
| **Both** | Sound file normalized to be loud but short (2-3 s), and the in-app **Test alert sound** screen | Teacher can check the real loudness | Loudness at the phone is still limited by the volume the user chose |

**Visual and vibration alerts are always sent too**, so the notification works for anyone who cannot hear it, and a muted phone still shows the message.

Because a loud alarm in the middle of a lecture can be disruptive, the app has a setting per level (section 8.6). The default is **high sound for all four levels**, as requested.

---

## 4. End-to-end flow

```text
 Camera/mock ─► AI pipeline ─► class_fatigue_pct ─► level + stability rules (persist, cooldown)
                                                        │
                                          ┌─────────────┴───────────────┐
                                          ▼                             ▼
                           WebSocket /ws/telemetry               Push service (backend)
                           fatigue_advisory field                POST to Expo Push API
                           (app is open: banner)                         │
                                                                         ▼
                                                              Apple APNs / Google FCM
                                                                         │
                                                                         ▼
                                                          Teacher's phone: LOUD sound + message
                                                          Tap ─► opens Dashboard for the session
```

- **App open:** the banner updates from the WebSocket and the notification handler also plays the sound.
- **App in background or closed:** the operating system shows the push and plays the sound.
- The app removes duplicates using `session_id + level + since` (section 8.5).

---

## 5. Prerequisites

| Needed | Why |
|--------|-----|
| Phases 10-11, 14, 15 PASS (scoring, FastAPI, auth, alert engine) | Backend side |
| Phases 21-22 PASS (mobile scaffold, teacher screens) | App side |
| `README_MOBILE_FATIGUE_ALERTS.md` contract addition approved (AQ-4) | `fatigue_advisory` field |
| **A real phone** for sound tests | Simulators and emulators do not give a realistic sound or push test |
| **Expo development build**, not Expo Go | Remote push is not supported in Expo Go on current Android versions; check the current Expo docs for your SDK |
| Expo project ID (`eas init`) and push credentials: **FCM** for Android, **APNs** for iOS (EAS manages APNs) | Needed to send push |
| Phone and backend reachable from each other (same Wi-Fi for local tests) | App calls the API |

---

## 6. Contract additions (additive; add to `contracts.md` after approval)

### 6.1 REST

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/devices/push-token` | A/T | Register or refresh the phone's push token. Body `{ "token": "ExponentPushToken[...]", "platform": "android" \| "ios" }` |
| DELETE | `/devices/push-token` | A/T | Remove the token (on logout). Body `{ "token": "..." }` |

Both require `Authorization: Bearer <JWT>`. A user can only register and delete **their own** tokens.

### 6.2 Database table (additive)

| Table | Columns |
|-------|---------|
| `push_tokens` | id, user_id → users, token (unique), platform, created_at, last_seen, active |

No other table changes. No image columns (D4).

### 6.3 Push payload sent to Expo

```json
{
  "to": "ExponentPushToken[xxxxxxxx]",
  "title": "III AI & DS: fatigue indicator",
  "body": "Do a short activity or give a short break.",
  "data": { "session_id": 12, "level": 3, "code": "SHORT_BREAK", "since": "2026-10-05T09:42:11Z" },
  "sound": "alert_high.wav",
  "priority": "high",
  "channelId": "fatigue-l3-v1",
  "interruptionLevel": "time-sensitive",
  "ttl": 120
}
```

| Field | Why |
|-------|-----|
| `priority: "high"` | Wakes the device on Android |
| `channelId` | Selects the loud Android channel for that level |
| `sound` | Custom bundled sound on iOS |
| `interruptionLevel` | `time-sensitive` for levels 3-4 (iOS); `active` for levels 1-2 |
| `ttl: 120` | If the phone is offline, the alert expires after 2 minutes. A late "continue with the class" would be wrong advice, so stale alerts are dropped |

The text is **class-level only**: no student names, no labels, no counts per student.

### 6.4 Configuration (env/config)

| Key | Default | Meaning |
|-----|---------|---------|
| `ADVISORY_BANDS` | `25,50,75` | Upper limits for levels 1, 2, 3 (percent) |
| `ADVISORY_MIN_TRACKS` | `5` | Minimum usable faces |
| `ADVISORY_PERSIST_S` | `60` | A level must hold this long before a push |
| `ALERT_COOLDOWN_S` | `300` | Minimum gap between pushes for the same level and session |
| `STATUS_HYSTERESIS_S` | `3` | Reused from `contracts.md` |
| `PUSH_ENABLED` | `true` | Master switch for sending push |
| `PUSH_TTL_S` | `120` | Time-to-live of a push |
| `PUSH_NOTIFY_LEVEL1` | `true` | Also notify for "Continue with the class" |
| `EXPO_ACCESS_TOKEN` | (secret, env only) | Expo access token, if enhanced push security is on |

Never hard-code these. Never commit `EXPO_ACCESS_TOKEN`.

---

## 7. Backend implementation

### 7.1 Files

```text
backend/
├─ app/notifications/
│  ├─ advisory.py          # level selection + stability state per session
│  ├─ expo_push.py         # send + receipts + token cleanup
│  └─ __init__.py
├─ app/api/devices.py      # POST/DELETE /devices/push-token
├─ scripts/send_test_advisory.py   # test helper (blocked in production)
└─ tests/test_advisory_push.py
```

### 7.2 Level selection and stability

```python
def advisory_level(pct: float, bands=(25, 50, 75)) -> int:
    if pct < bands[0]: return 1      # 0  to <25
    if pct < bands[1]: return 2      # 25 to <50
    if pct < bands[2]: return 3      # 50 to <75
    return 4                         # 75 to 100
```

Rules (D7):
1. Apply EMA smoothing (α = 0.3) to `class_fatigue_pct`.
2. The displayed level changes only after the new level holds `STATUS_HYSTERESIS_S`.
3. A **push** is sent only after the level has held `ADVISORY_PERSIST_S`.
4. At most one push per `(session, level)` within `ALERT_COOLDOWN_S`. A change to a different level can push after its own persistence time.
5. No push while fewer than `ADVISORY_MIN_TRACKS` usable faces, and none during the camera or AI warm-up.
6. If the camera or AI is offline, **do not** send a fatigue advisory (that case is the `camera_offline` / `ai_offline` alert).

### 7.3 Sending through Expo

```python
# backend/app/notifications/expo_push.py (sketch)
import httpx

EXPO_URL = "https://exp.host/--/api/v2/push/send"
RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"

def build(token: str, adv) -> dict:
    return {
        "to": token,
        "title": f"{adv.class_name}: fatigue indicator",
        "body": adv.message,
        "data": {"session_id": adv.session_id, "level": adv.level,
                 "code": adv.code, "since": adv.since},
        "sound": "alert_high.wav",
        "priority": "high",
        "channelId": f"fatigue-l{adv.level}-v1",
        "interruptionLevel": "time-sensitive" if adv.level >= 3 else "active",
        "ttl": settings.PUSH_TTL_S,
    }

async def send_advisory(adv, tokens: list[str]) -> None:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if settings.EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"
    messages = [build(t, adv) for t in tokens]
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(0, len(messages), 100):          # Expo accepts up to 100 per request
            r = await client.post(EXPO_URL, json=messages[i:i + 100], headers=headers)
            r.raise_for_status()
            handle_tickets(r.json()["data"], tokens[i:i + 100])
```

`handle_tickets`:
- For a ticket with `status: "error"` and `details.error == "DeviceNotRegistered"`, mark that token `active = false`.
- Store ticket IDs and check receipts about 15 minutes later with `getReceipts`; deactivate tokens that report `DeviceNotRegistered`.
- Log failures **without** the token value or message body.

Do not block the telemetry loop: run sending as a background task with a timeout, and never let a push failure affect the AI pipeline or WebSocket telemetry.

### 7.4 Who receives the push
- Teachers assigned to the session's classroom (`teacher_classrooms`), only if `active` and with at least one active token.
- Never teachers of other classrooms. Admins only if the owner decides so (AQ-3 in the earlier README).

### 7.5 Device endpoints

```python
@router.post("/devices/push-token")
def register(body: PushTokenIn, user=Depends(require_roles("teacher", "admin")), db=Depends(get_db)):
    validate_expo_token(body.token)            # must match ExponentPushToken[...] or ExpoPushToken[...]
    upsert_token(db, user.id, body.token, body.platform)   # a token belongs to ONE user at a time
    return {"ok": True}
```

If the same token is registered by a different user (shared phone), move it to the new user. `DELETE` removes only the caller's own token.

### 7.6 Test-only helper

```bash
# Sends a real push for a chosen level without needing a camera.
# Refuses to run when APP_ENV=production.
python scripts/send_test_advisory.py --session 12 --level 4
```
The helper calls the notification service directly. **Do not expose it as an HTTP endpoint.**

---

## 8. Mobile implementation (React Native + Expo)

### 8.1 Packages and config

```bash
cd mobile
npx expo install expo-notifications expo-device expo-constants expo-secure-store
eas init                  # creates the project ID
eas build --profile development --platform android   # development build
```

`app.json` (plugin adds the sound to the native projects):

```json
{
  "expo": {
    "plugins": [
      ["expo-notifications", {
        "icon": "./assets/notification-icon.png",
        "color": "#465FFF",
        "sounds": ["./assets/sounds/alert_high.wav"]
      }]
    ]
  }
}
```

The `color` equals the `accent.primary` token. `app.json` cannot import `tokens.ts`, so keep the value in sync and exclude this file from the "no hex" lint.

### 8.2 Android channels (loud)

Create channels **before** requesting permission (required on Android 13 and later). Channel settings are fixed once created, so changing sound or importance later needs a new ID (`-v2`).

```ts
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

const LEVELS = [
  { id: "fatigue-l1-v1", name: "Fatigue level 1: continue",       bypassDnd: false },
  { id: "fatigue-l2-v1", name: "Fatigue level 2: interactive",    bypassDnd: false },
  { id: "fatigue-l3-v1", name: "Fatigue level 3: short break",    bypassDnd: true  },
  { id: "fatigue-l4-v1", name: "Fatigue level 4: reschedule",     bypassDnd: true  },
];

export async function setupChannels() {
  if (Platform.OS !== "android") return;
  for (const c of LEVELS) {
    await Notifications.setNotificationChannelAsync(c.id, {
      name: c.name,
      importance: Notifications.AndroidImportance.MAX,
      sound: "alert_high.wav",
      vibrationPattern: [0, 400, 200, 400, 200, 800],
      enableVibrate: true,
      audioAttributes: {
        usage: Notifications.AndroidAudioUsage.ALARM,
        contentType: Notifications.AndroidAudioContentType.SONIFICATION,
      },
      lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
      bypassDnd: c.bypassDnd,       // only takes effect if the user grants Do Not Disturb access
    });
  }
}
```

The text is class-level, so showing it on the lock screen is acceptable. Check enum names against the `expo-notifications` version you install.

### 8.3 Permission and token registration

```ts
import * as Device from "expo-device";
import Constants from "expo-constants";

export async function registerForPush(): Promise<string | null> {
  if (!Device.isDevice) return null;                 // simulators cannot receive real push
  await setupChannels();

  let { status } = await Notifications.getPermissionsAsync();
  if (status !== "granted") {
    ({ status } = await Notifications.requestPermissionsAsync({
      ios: { allowAlert: true, allowSound: true, allowBadge: false },
    }));
  }
  if (status !== "granted") return null;             // show the "notifications are off" warning

  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
  await api.post("/devices/push-token", { token, platform: Platform.OS });
  return token;
}
```

When to call it: after every successful login and on every app start (the token can change). On logout call `DELETE /devices/push-token` before clearing the auth token.

### 8.4 Showing and playing while the app is open

```ts
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,       // the loud sound also plays in the foreground
    shouldSetBadge: false,
  }),
});
```

Older SDKs use `shouldShowAlert` instead of `shouldShowBanner` and `shouldShowList`. Use the names your installed version documents.

### 8.5 Avoiding duplicates and handling taps

```ts
const seen = new Set<string>();                         // key = `${session_id}:${level}:${since}`

export function shouldHandle(d: { session_id: number; level: number; since: string }) {
  const key = `${d.session_id}:${d.level}:${d.since}`;
  if (seen.has(key)) return false;
  seen.add(key);
  return true;
}

Notifications.addNotificationResponseReceivedListener((resp) => {
  const d = resp.notification.request.content.data as { session_id: number };
  navigation.navigate("Dashboard", { sessionId: d.session_id });   // tap opens the dashboard
});
```

The in-app banner (from the WebSocket) and the push use the same key, so one event never shows twice. Keep the `seen` set bounded (for example the last 50 keys).

### 8.6 Settings screen: "Alert sound"

| Item | Behavior |
|------|----------|
| **Test alert sound** button | Sends a local notification using the level 4 channel so the teacher hears the real loudness. Use `Notifications.scheduleNotificationAsync` with a 1-second trigger |
| Per-level on/off | Toggle each level; default **all on**, **sound high** |
| **Open system notification settings** | `Linking.openSettings()` |
| Permission state | If denied, show a clear warning with an **Enable** action |
| Channel check (Android) | Read each channel with `Notifications.getNotificationChannelAsync(id)`. If its importance is below MAX or its sound is none, show: "Alert sound is reduced in system settings" |
| Guidance text | "Turn up the alarm and notification volume, switch off silent mode, and allow notifications for this app." (iOS: "the silent switch mutes alert sounds.") |
| Battery tip (Android) | "If alerts arrive late, turn off battery optimization for this app." (Some phone makers delay background push) |

### 8.7 Visual design (`ui.md` tokens only, no new colors)

Status is never shown by color alone: icon + text on every level.

| Level | Icon | Text/icon token | Background | Border |
|-------|------|-----------------|------------|--------|
| 1 | check-circle | `accent.success` | `bg.success` | `accent.success` |
| 2 | message-circle | `accent.primary` | `bg.info` | `accent.primary` |
| 3 | alert-triangle | `accent.danger` | `bg.surface` | `accent.danger` |
| 4 | alert-octagon | `accent.danger` | `bg.surface` | `accent.danger` |

There is no amber token in the design system (open gap in `ui.md` UI-3), so levels 3 and 4 differ by icon and wording. Touch targets are at least 44 dp. The banner uses an accessibility live region (`accessibilityLiveRegion="polite"`).

---

## 9. Sound asset specification

| Property | Requirement |
|----------|-------------|
| Files | `mobile/assets/sounds/alert_high.wav` (one default; optional per-level files later) |
| Format | WAV, PCM 16-bit, 44.1 kHz, mono |
| Length | 2-3 seconds (iOS limit is 30 s; Android should stay short) |
| Loudness | Normalized so the peak is about -1 dBFS and it is clearly louder than the default tone. No clipping or distortion |
| Character | Attention-getting but not alarming to the point of panic; no sudden extreme peaks (hearing safety) |
| Licence | Created by you or properly licensed; record the source |

Normalizing example (requires ffmpeg):

```bash
ffmpeg -i source.wav -af "loudnorm=I=-12:TP=-1:LRA=7" -ar 44100 -ac 1 -c:a pcm_s16le alert_high.wav
```

If you change the sound later, bump the Android channel IDs to `-v2` so the new sound takes effect.

---

## 10. Run order (backend + web + phone)

**1. Backend**
```bash
cd backend && source .venv/bin/activate
export PUSH_ENABLED=true   # and the other env values; EXPO_ACCESS_TOKEN only if you enabled it
uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
```

**2. Web Operator Console**
```bash
cd operator-console && npm run dev
```
Log in as a teacher or admin and **start a session** for the classroom (this calls `POST /sessions`).

**3. Mobile app (development build on a real phone, same network)**
```bash
cd mobile
EXPO_PUBLIC_API_URL=http://<your-computer-LAN-IP>:8000 npx expo start --dev-client
```
Log in, **allow notifications**, then confirm a row exists in `push_tokens` for that user.

**4. Produce fatigue data** (any one of these)
- Real camera through the AI pipeline.
- The mock frame generator from Phase 12.
- The test helper: `python scripts/send_test_advisory.py --session <id> --level 1` (then 2, 3, 4).

**5. Verify:** the phone shows the message for the level and plays the loud sound. Try with the app open, in the background, and fully closed.

> For production, serve the API over HTTPS. Plain `http://` is for local development only.

---

## 11. Test plan

### 11.1 Level logic (backend, automated)

| # | Input | Expected |
|---|-------|----------|
| L1 | 0, 10, 24.9 | Level 1 |
| L2 | 25, 40, 49.9 | Level 2 |
| L3 | 50, 60, 74.9 | Level 3 |
| L4 | 75, 90, 100 | Level 4 |
| L5 | Score spikes to 80% for 1 s then returns | No level change, no push (D7) |
| L6 | Level held for `ADVISORY_PERSIST_S` | Exactly one push |
| L7 | Same level repeats inside `ALERT_COOLDOWN_S` | No second push |
| L8 | Fewer than `ADVISORY_MIN_TRACKS` usable faces | No push |
| L9 | Camera or AI offline | No fatigue push (offline alert instead) |
| L10 | Two sessions in different classrooms | Each teacher gets only their own |

### 11.2 Delivery and sound (manual, real phones)

Test on at least one Android phone and one iPhone.

| # | Scenario | Expected |
|---|----------|----------|
| D1 | App open, levels 1-4 | Banner appears and loud sound plays |
| D2 | App in background | Notification shown with loud sound |
| D3 | App swiped away (closed) | Notification still arrives with sound |
| D4 | Screen locked | Notification wakes the screen, sound plays |
| D5 | Phone on silent (iOS switch / Android sound off) | Message still shown; sound muted by the OS (documented limit); vibration on Android |
| D6 | Do Not Disturb / Focus on | Levels 3-4 can break through where allowed; others follow system rules |
| D7 | Phone offline for longer than `PUSH_TTL_S`, then back online | Stale alert is **not** delivered |
| D8 | Tap the notification | Opens the Dashboard for that session |
| D9 | Same event arrives by WebSocket and push | Shown once (dedupe) |
| D10 | Permission denied | Warning shown, no crash; **Enable** opens settings |
| D11 | User lowers channel importance in system settings (Android) | App warns "Alert sound is reduced" |
| D12 | **Test alert sound** button | Plays the real level 4 sound |

**Loudness check:** record in `PROGRESS.md`, for each phone, whether the alert is clearly audible from the back of a classroom at about 50% volume, and measure with a sound-level meter app at 1 m. The project owner sets the acceptance level (a proposal, not a validated figure).

### 11.3 Privacy and security

| # | Check | Expected |
|---|-------|----------|
| S1 | Push payload contains no student names, labels, images or per-student data | Class-level text only |
| S2 | `POST /devices/push-token` without a token | 401 |
| S3 | User A cannot delete or overwrite user B's token | 403 or ignored |
| S4 | Teacher not assigned to a classroom receives nothing for it | Confirmed |
| S5 | Logout removes the token; push no longer arrives on that phone | Confirmed |
| S6 | Invalid or fake token string | 422 |
| S7 | Push tokens and message bodies are not logged | Grep logs |
| S8 | `EXPO_ACCESS_TOKEN` is only in env, not in the repo or app bundle | Grep |
| S9 | A push failure (Expo down) never slows or breaks telemetry or the AI loop | Fault-injection test |
| S10 | Wording check: no "sleeping", "sick" in any message | Pass (D8) |

### 11.4 Reliability
- Expo returns an error ticket `DeviceNotRegistered`: the token is deactivated.
- Expo API timeout: logged, retried once at most, never blocks the pipeline.
- 200 tokens in one send: batched in groups of 100.

---

## 12. Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| No notification at all | Permission denied, simulator used, token not registered, or backend not sending | Use a real phone; check `push_tokens`; check `PUSH_ENABLED`; look at the Expo ticket/receipt |
| Works in the app but not when closed | Using Expo Go, or missing FCM/APNs credentials | Use a development build; configure push credentials with EAS |
| Notification arrives but is silent (Android) | Channel sound/importance reduced, alarm volume low, DND | Check the channel in system settings; raise alarm volume; the app's channel warning should flag it |
| Notification arrives but is silent (iPhone) | Silent switch on, Focus mode | Switch off silent; use Time Sensitive and allow it in Focus settings |
| Sound did not change after updating the file | Android channel is immutable | Create new channel IDs (`-v2`) and update the backend `channelId` |
| Alerts arrive late | Battery optimization, poor network | Disable battery optimization for the app; check the network |
| Two alerts for one event | Dedupe key missing | Use `session_id + level + since` (section 8.5) |
| Alert says "continue" when the class is tired | Stale message delivered late | Confirm `ttl` is set; check device clock |
| Phone cannot reach the backend in development | Using `localhost` on the phone | Use the computer's LAN IP; same Wi-Fi; allow the port in the firewall |

---

## 13. Privacy and security notes

- Push messages travel through Expo's service and Apple/Google's push networks. Keep the content **minimal and class-level only**. Record this in the privacy notice (OQ-5).
- Push tokens identify a device. Treat them as sensitive: only authenticated users can register them, they are removed on logout, and they never appear in logs.
- The alert is an indicator to support teacher observation, never an automatic action (D8).
- All checks in `README_SECURITY_TESTING.md` apply to the new endpoints.

---

## 14. Open questions (add to `docs/OPEN_QUESTIONS.md`)

| ID | Question | Conservative default |
|----|----------|----------------------|
| NQ-1 | Should level 1 ("continue") also make a loud sound? | Yes by request; configurable per level |
| NQ-2 | Should levels 3-4 bypass Do Not Disturb? | Yes on Android where permission is granted; owner confirms |
| NQ-3 | Apply for iOS Critical Alerts? | No (normally limited to health/safety apps) |
| NQ-4 | Approve the new endpoints and the `push_tokens` table in `contracts.md` | Add only after approval |
| NQ-5 | Should admins also receive these pushes? | Teachers of the classroom only |
| NQ-6 | Acceptable loudness target per phone | Measure and let the owner set it |
| NQ-7 | Is routing class-level text through Expo, APNs and FCM acceptable under the school's data policy? | Do not enable in a real classroom until approved |

---

## 15. Final checklist

- [ ] Backend, web console and a monitoring session are running (section 10).
- [ ] Development build installed on a real phone; push credentials configured.
- [ ] Android channels created with MAX importance, loud sound and ALARM usage (versioned IDs).
- [ ] Sound file normalized and added to `assets/sounds/` and `app.json`.
- [ ] Token registered after login, removed on logout.
- [ ] `fatigue_advisory` and device endpoints approved and added to `contracts.md`.
- [ ] Level boundaries, persistence and cooldown tests pass (L1-L10).
- [ ] Delivery tests D1-D12 pass on one Android phone and one iPhone; loudness recorded.
- [ ] Privacy and security tests S1-S10 pass.
- [ ] A push failure never affects telemetry or the AI pipeline.
- [ ] Results appended to `docs/PROGRESS.md`.
