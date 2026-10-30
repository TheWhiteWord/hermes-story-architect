# Hermes profile / desktop mismatch — known issue

## Symptom

After `story-architect hermes setup`, the app works (chat replies), but the
Hermes desktop app shows for the `story-architect` profile:

- Tools: "Error invoking remote method 'hermes:api': Error: Invalid gateway ticket response"
- Plugins: "Could not load agent plugins profile_missmatch"
- Skills: same ticket error
- Delete profile: same ticket error

## Root cause (verified)

The profile gets **parked** by the host gateway:

```
parked_profiles["story-architect"] = "session store unusable: FATAL: state.db
was replaced underneath the gateway; ..."
```

A parked profile is not in `served_profiles`, so every ticket minted for it
through the host control socket is refused → "Invalid gateway ticket
response". Desktop tools/plugins/skills/delete all depend on those tickets.

Verified causes:

1. `hermes profile create --clone` does **not** copy `state.db` (only
   config.yaml, .env, SOUL.md, skills). The profile therefore had no session
   store; the host gateway created/parked it.

2. We then flipped the profile to `gateway.standalone: true` so its
   `api_server` platform runs (multiplexing gap: the host gateway only runs
   platforms from the launching profile's config). That takes the profile out
   of `served_profiles`, so the desktop can no longer dial it through the
   multiplexer at all.

## What is NOT the cause (verified)

- Our in-app chat service / conversation store. The app talks to the profile's
  `api_server` over HTTP with a bearer token; it does not use the desktop
  gateway ticketing. Confirmed working after the chat_service init fix.

## Assumptions not verified

- Whether `gateway.standalone: true` is still required now that the profile has
  a valid `state.db` and is no longer parked. (Unverified: we have not tested
  removing the shim and relying on multiplexing.)
- Whether the desktop can be taught to dial a standalone gateway instead of
  the multiplexer. (Unverified: not investigated in desktop source.)
- Whether disabling the shim would let the desktop tools/plugins work again
  while keeping the app's api_server reachable. (Unverified.)

## Current state

- App chat works.
- Desktop Tools/Skills/Plugins/Delete for `story-architect` remain broken.
- Profile is standalone (not served by host multiplexer).

## Options (not decided)

1. Keep standalone — app works, desktop profile management stays broken.
2. Drop standalone + api_server on default profile — loses per-profile isolation.
3. Use Hermes native sessions/chat (drop app chat store + api_server) —
   largest, aligns with native; unverified effort.
## Manual prerequisite (no auto-enablement)

The app reads the LLM via the host gateway api_server at
http://127.0.0.1:8642/p/story-architect/v1/...
Hermes does not enable api_server by default, so the user must enable it once
on the default profile:

    # ~/.hermes/config.yaml
    platforms:
      api_server:
        enabled: true
        host: 127.0.0.1
        port: 8642

and set a strong API_SERVER_KEY in ~/.hermes/.env.

Then: hermes gateway restart

The app never modifies Hermes config automatically.


## Resolution

Root cause of "Start agent" timeout: host gateway api_server platform refused to start because default profile .env had no API_SERVER_KEY (removed during cleanup). Re-adding a strong key and restarting fixed it. App now reports agent ready and chat works; desktop profile stays clean (no standalone shim).
