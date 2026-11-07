# Responsive audit

## Evidence and limits

Source review covered the authenticated layout, all authenticated route families, public/auth/legal/blog compositions, and shared UI surfaces. Browser diagnostics used the local instance at `http://localhost:5173`, Chromium, isolated browser storage, and intercepted API responses. No real searches, billing mutations, user changes, or application source edits were performed. These diagnostics are evidence for planning, not a passing end-to-end test suite. The local instance serves a built frontend; implementation must repeat regressions against the checkout served by the repo harness.

The supplied screenshots identify DevTools' iPhone 16 Pro Max preset at **440 × 956 CSS pixels**. That size is a regression fixture, not a device-specific layout target. Earlier diagnostics reproduced Browse with 9,783 results and 490 pages.

## Findings and shared migration targets

| Surface / source | Evidence | Shared treatment |
| --- | --- | --- |
| `Common/Sidebar.tsx`, `Dashboard/DashboardTopbar.tsx` | Confirmed at 440px: menu spans x=12–52, language starts x=33. Fixed trigger is outside header flow; padding cannot contain the toolbar's intrinsic width. | One shell-owned header/drawer trigger; compact language and secondary actions based on available space. |
| `Dashboard/DashboardPageShell.tsx`, Creators Search and Reputation Strategy pages | Source-confirmed duplication of header, viewport minimum height and content spacing. Admin uses a separate Container/layout path. | Layout owns the header once; existing page shell becomes consistent content wrapper; migrate all authenticated pages including Admin. |
| `creators-search/CurrentJobCard.tsx`, `CurrentJobsSummary.tsx` | Source-confirmed max-width 240px while parent and View all stretch. | Shared job-card sizing policy: full available width in stacked placement, compact only in roomy header placement; preserve dialog usage. |
| `creators-search/CreatorsDirectoryPreview.tsx` | Confirmed: at 440px, filters/results grow from 408px to ~476px when a ~434px pagination row appears. Hiding pagination in the browser restores 408px; constraining the grid alone leaves the pagination overflow. | Shrinkable grid/panels plus shared adaptive pagination, also used by Admin. |
| `UserSettingsPage.tsx` | Confirmed with normal user and five tabs: tab list ~451px at both 320px and 440px; whole application content scrolls horizontally. | Bounded accessible tab strip with local horizontal scrolling and focused/selected tab revealed. |
| `OverviewPage.tsx`, `Dashboard/MetricCard.tsx` | With a long display name, authenticated content scroll width was ~468px at 320/440px, and ~593px in the 523px content area at a 768px viewport. Source has a truncating greeting in an unbounded flex child and viewport-based metric columns. Precise contribution of greeting versus metrics remains to isolate during implementation. | Bound header text and panel minima; use available content width for multi-column transitions. |
| `UsersManagementPage.tsx`, pending user table | Confirmed: user table ~606px at 320/440px and ~662px at 768px. No dedicated horizontal table wrapper. Admin also repeats full pagination. | Shared table viewport and adaptive pagination; keep columns/actions available through explicit local scroll. |
| Dashboard billing notices | Confirmed at 320px: menu ~401px wide, spanning x=8–409. Source requests min-width 24rem. | Shared viewport-bounded menu surface; remove conflicting caller minima, allow text/actions to wrap. |
| `Landing/Navbar.tsx` used by landing/blog | Confirmed at 768px: Sign Up extends to x=857 and document width becomes 857px. Desktop controls become visible at md before they fit. | Adjust shared public navigation's collapse threshold/available-space policy; retain all destinations/actions. |
| Campaign/Creator strategy builders, `StrategySection`, `MultiSelectOptionGroup` | Source risks: repeated 1fr minima, fixed 360px summary columns, viewport-based nested form columns. Initial campaign form stayed bounded in browser checks at 320/440/768/1024px. Populated summaries, errors and creator variant require stress coverage; not confirmed broken. | Reuse bounded panels and form/summary grid pattern; migrate both variants and fallbacks together. |
| `NotesWorkspaceDialog.tsx`, Guide, profile detail and history/job dialogs | Source risks: 100vh sizing, fixed workspace sidebar at md inside 75vw dialog, nested scrolling, fixed skeleton sizes and nonwrapping badges. No claim that all these surfaces currently fail. | Shared overlay size/height policy and content-area-driven workspace split; verify open, populated and short-height states. |
| `KanbanBoardView.tsx`, profile detail tables, `CookieTablesPage.tsx`, blog code | Existing useful pattern: explicit local overflow for Kanban, profile/legal tables and code blocks. Kanban uses 280px columns. | Preserve intentional local scroll; ensure wrappers themselves shrink, local scrollers are keyboard reachable/labeled, and column contents fit the narrowest supported workspace. |
| Public auth forms, legal/provider/about/security pages and blog content | Source-reviewed; no complete browser certification. Blog images already cap width; rendered tables lack an explicit local scroll wrapper. Public decorative overflow clipping is intentional but must not conceal functional content. | Reuse public content boundaries, long-token wrapping and wide-content wrapper where needed; do not force dashboard chrome into public pages. |

## Route and state coverage for implementation

- Overview: ordinary/long names, limited/unlimited usage, empty/populated local reports, billing states.
- Creators Search: Direct and Browse, tabs, job/history dialogs, idle/loading/empty/error/success, long labels, 490-page pagination, update queue and profile detail.
- Brand Intelligence: campaign and creator forms, validation errors, selected options, populated summaries, generated report actions and loading fallbacks.
- Settings: all five normal-user tabs and restricted superuser tabs; profile/password/appearance/payments/danger-zone states and confirmations.
- Admin: users, loading table, long identities/access labels, many pages, add/edit/delete dialogs and worker job form.
- Shared authenticated surfaces: sidebar navigation, language, notifications, guide, notes editor and populated Kanban.
- Public routes: landing, blog listing and a real blog post, login/signup/recover/reset/waiting list, privacy/terms/security/cookie notice/cookie tables/about/providers, not-found/error UI and cookie consent.

## Interpretation

One shared foundation can remove repeated sizing and navigation defects. It cannot decide how every kind of content should reflow: tabs, data tables and Kanban have different interaction needs. The implementation uses a small collection of reusable patterns at their owners, with explicit migrations at call sites. A universal overflow-hidden rule would conceal the bugs and is excluded.

## Implementation follow-up

The shared foundation and call-site migrations are implemented. See `validation.md` for exact automated results, route/state coverage, source-risk resolution, native Chrome zoom verification and the resolved Docker limitation.

Additional source risks discovered during implementation were addressed at shared owners: long Settings profile text is constrained to its form, public error-screen decoration is bounded, cookie choices/preferences use the shared overlay primitives, and overlay caps preserve desktop width/height limits rather than replacing them. Search uses fitted wrapping tabs while Settings retains a keyboard-revealed local tab strip.

All initially listed findings have either a shared fix or targeted verification. The standard Docker harness now passes its selected 43 cases after a fresh rebuild. Physical-device behavior remains outside the verified scope. The implementation does not use global horizontal clipping to hide functional overflow.
