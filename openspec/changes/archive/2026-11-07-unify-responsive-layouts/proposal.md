## Why

Kiizama has responsive styles, but shared navigation and content sizing can still overlap, overflow, or become inaccessible when the available space changes. The reported 440 × 956 viewport reproduces real defects, and a wider audit found the same problems in Settings, Overview, Admin, notifications, and the public navigation at tablet widths.

## What Changes

- Establish one authenticated shell that owns navigation, available width, scrolling, and viewport height; reuse the existing dashboard content shell across authenticated pages, including Admin.
- Make the dashboard header and public navbar adapt to the space their controls actually need, with no floating menu overlap and no loss of essential actions.
- Introduce a small set of shared layout patterns for shrinkable grids/panels, wrapping action rows, accessible tabs, compact pagination, and locally scrollable wide content. Migrate repeated patterns rather than applying independent device-specific fixes.
- Apply these patterns to Overview, both Creators Search tabs and job/history surfaces, Settings and Payments, both Brand Intelligence builders, and Admin.
- Constrain notifications, dialogs, drawers, and popovers to available viewport space; retain intentional local scrolling for tables, code blocks, and Kanban.
- Audit and address the public/auth/legal/blog route families using their existing shared components; preserve their distinct visual composition.
- Add browser regression coverage for content-driven overflow, intermediate widths, orientation, localization, and critical overlay interactions.

## Capabilities

### New Capabilities

- `responsive-shell-navigation`: Shared authenticated shell and available-space-aware dashboard/public navigation.
- `responsive-content-layout`: Reusable content sizing, tabs, pagination, action rows, and intentional local scrolling across route families.
- `responsive-overlay-surfaces`: Viewport-bounded menus, dialogs, drawers, and scrollable workspaces.

### Modified Capabilities

None. This is the project's first set of OpenSpec capability specifications.

## Impact

- Frontend only: `frontend/src/routes/_layout.tsx`, dashboard/sidebar/language/public navigation components, existing UI wrappers and theme/layout styles, authenticated page compositions, public content containers, and relevant browser/component tests.
- A migration/evidence inventory is recorded in `audit.md`; architecture and validation are described in `design.md`.
- No backend/API, database, generated client, billing policy, report content, or stored note/job format changes. No new UI framework or device-detection dependency is expected.
