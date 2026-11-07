# Validation

## Delivered

- One shared app-origin manifest/identity, 192/512 PNGs, a separately padded maskable icon and Apple touch icon. Uses the existing vector brand and a reproducible Chromium generator, with no new production dependency.
- Root installation controller retains a browser-provided prompt across routes, waits for user action, consumes each event once and distinguishes accepted requests from confirmed installation.
- All Settings roles have an installation tab with iOS/Android steps in ES/EN/PT-BR. The outer settings strip now has six tabs for normal users, with nested guide tabs scoped independently.
- Shared app bootstrap handles manifest advertisement; known marketing hosts are excluded. Stable /overview launch preserves existing login return behavior. Nginx policy is by asset class, not application route.
- Internet connection remains required. No service worker, private-response cache, background work, push or store publishing was added.

## Results (2026-11-07)

- Production build and TypeScript: passed.
- Full Vitest run: **77 files, 401 tests passed**. Initial run collided with the harness npm ci replacing node_modules; stopped it and reran after dependency preparation. The reported complete run is the subsequent passing run.
- Official Docker harness: **43 passed (48.6s)**, comprising 8 installation flows and 35 responsive flows. APIs for browser geometry use isolated fixtures. Command:
  `bash scripts/test-local.sh playwright tests/e2e/app-install.spec.ts tests/e2e/responsive.spec.ts --project=chromium-mocked --workers=3 --reporter=line`
- Built local Nginx frontend, Chromium follow-up: **11 passed (7.6s)**, including all 9 installation tests (the added signed-out launch regression) and scoped Settings/drawer regressions.
- Built local frontend, mobile WebKit: original run passed 37 cases and exposed 7 fixture failures. The cookie-consent helper accessed documentElement before WebKit created it, preventing other init scripts from seeding authentication. Changed it to safe optional access. All **9 installation cases then passed (5.3s)**; all 35 responsive cases had passed in the preceding run. This is desktop WebKit/touch emulation, not physical iOS installation.
- `bash scripts/test-frontend-serving.sh`: four HTML routes retain shared revalidation headers.
- `python3 scripts/test-installation-assets.py`: manifest MIME/revalidation, launch/scope/display, real PNG dimensions, Apple icon and missing-icon 404 passed against built Nginx.
- `nginx -t`, safe targeted Biome, `git diff --check` and strict OpenSpec validation passed. Generated client unchanged.
- Inspected real local superuser Settings at 440x956 with both guides; screenshots `/tmp/kiizama-install-ios.png` and `/tmp/kiizama-install-android.png`. Existing brand icon inspected visually. Pixel check places all maskable artwork within radius 192px of center, inside the required 204.8px safe circle of a 512px image.

Docker development Redis/worker were temporarily stopped for the isolated harness's port requirement, then restored. Backend, Postgres and Redis healthy; worker resumed polling; frontend rebuilt and running on localhost:5173. No real scraping, report generation or billing mutations were triggered.

## Remaining device/release verification

Implementation tasks are complete; release certification requires physical iPhone/iPad Safari and Android Chrome on the deployed HTTPS application origin. Follow the checklist in development.md for OS menus, final installed icon/launch, login persistence, keyboard, rotation and external links. Native installation dialogs are simulated only in automated lifecycle tests. Browser eligibility, OS policy and existing installations can affect whether a native button appears. No production deployment or commit was made by the agent; change remains active for review/archive by the user.

## References

- https://web.dev/articles/install-criteria
- https://developer.chrome.com/blog/update-install-criteria
- https://webkit.org/blog/17333/webkit-features-in-safari-26-0/#every-site-can-be-a-web-app-on-ios-and-ipados
