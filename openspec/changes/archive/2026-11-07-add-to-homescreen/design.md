## Context

React/Vite serves both www and app through shared Nginx host routing. There is currently an SVG favicon, no manifest and no install assistance. Authentication protects /overview and redirects signed-out users to login with returnTo. Settings already has bounded localized tabs.

## Goals / Non-Goals

**Goals:** Branded standalone home-screen launch from the app origin; one shared configuration; Settings guide in ES/EN/PT-BR; optional progressive native prompting.

**Non-Goals:** Offline data, service worker/cache, background sync, push, store submission, automatic installation, changing authentication persistence.

## Decisions

- A same-origin static manifest uses stable id /, scope / and start_url /overview. This avoids the app-host root redirect to www and preserves normal authentication. Bootstrap advertises the manifest once, only outside known marketing hosts; metadata is shared across app routes. Do not offer a manifest on www that launches users into a different origin.
- Rasterize the existing brand symbol onto opaque backgrounds; ship 192/512 PNGs, separate maskable 512 icon with safe padding, and 180 Apple icon. Keep the vector source and a reproducible generator.
- Use a single root install-state provider for beforeinstallprompt, appinstalled and display-mode changes. The Settings panel consumes state; it never automatically opens a prompt. Acceptance does not imply installation completed; only appinstalled/standalone establishes that UI state. Cancellation/failure retains manual instructions.
- iOS instructions use Safari Share and Add to Home Screen, with Open as Web App enabled where shown. Android uses Chrome menu Install app / Add to Home screen. Avoid promising exact toolbar position or native prompt availability. Both platform guides are manually selectable.
- No service worker: current installation requirements do not require offline caching. Native prompt eligibility remains browser-controlled; all browsers retain manual help. Avoid introducing stale HTML or caching authenticated API responses.
- Nginx serves manifest with application/manifest+json, revalidation and real 404 for absent metadata/icons rather than SPA HTML fallback. Other routes retain the shared HTML policy.

## Risks / Trade-offs

- Browser criteria and UI vary → native prompt is optional; manual guide is always available.
- Session storage may differ after iOS installation → normal login remains supported; no token copied into manifest/URLs.
- Physical OS installation cannot be certified in desktop emulation → document explicit device checks after HTTPS deployment.
- Already-open tabs run old JS → reload after rebuild; no automatic reload/state loss.

## Follow-up: Service Worker (deferred)

A service worker is not required for installation (Chrome no longer requires it; iOS Safari never did), and without one every launch already fetches the current deployment. Introduce one in a separate change only when there is a concrete need:

- **Primary trigger: Web Push notifications.** Push requires a service worker; on iOS/iPadOS it only works for apps added to the Home Screen.
- Secondary: faster repeat loads or a minimal offline fallback page. Full offline use adds little value because most features depend on the API.

Guardrails for that change:

- Prefer `vite-plugin-pwa` (Workbox) over a hand-written worker; serve the worker script from the app origin root with `no-cache` so update checks are not delayed.
- Never cache authenticated API responses or `index.html` with a cache-first strategy; precache only hashed static assets.
- Use a prompt-to-reload update flow ("new version available") instead of silently serving stale versions; never force-reload users mid-task.
- Keep the worker app-host only, matching manifest advertisement (no worker on marketing hosts).
- Ship a documented kill-switch (self-unregistering worker) before rollout, because removing a worker from devices later is harder than adding it.

Low current adoption (few users, no known installations) makes adding it later low-risk.

## Migration Plan

Deploy static frontend, then test app-domain manifest/icons and native iOS/Android launch on HTTPS. No database migration. Roll back frontend release to remove promotion; existing installations may retain OS-cached icons until refreshed/reinstalled.

## References

- https://web.dev/articles/install-criteria
- https://developer.chrome.com/blog/update-install-criteria
- https://webkit.org/blog/17333/webkit-features-in-safari-26-0/#every-site-can-be-a-web-app-on-ios-and-ipados
