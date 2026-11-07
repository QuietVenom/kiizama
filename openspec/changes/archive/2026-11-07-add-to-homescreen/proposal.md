## Why

Kiizama users need a branded home-screen entry on iOS and Android without installing a native store app. Configuration and an accessible installation guide will make the existing responsive application easier to return to.

## What Changes

- Add shared web-app manifest, branded regular/maskable/Apple icons and standalone launch metadata.
- Advertise installation from the application origin, with a stable /overview launch URL that retains existing authentication redirects.
- Add an Install Kiizama tab in Settings for all users, with localized iOS/Android steps and an optional browser-provided native install prompt.
- Keep installation user-initiated, handle installed/dismissed/unavailable states and preserve ordinary browser navigation.
- Verify built manifest/icon serving and shared metadata across routes. No offline data cache, service worker, push notifications or store publishing in this change.

## Capabilities

### New Capabilities

- `home-screen-installation`: Application identity, standalone launch and localized installation assistance.

### Modified Capabilities

None. Existing responsive patterns remain the foundation for Settings and its tab navigation.

## Impact

Frontend HTML/bootstrap, static assets, Settings, common installation state, ES/EN/PT-BR localization, frontend tests and Nginx static metadata policy. No backend/API/schema changes or new production dependencies. Production requires HTTPS; device installation must be checked on real iOS/Android after deployment.
