## 1. Reproduction and regression foundations

- [x] 1.1 Read the frontend implementation/test skills and repo harness documentation; reproduce the audit's confirmed issues against the checkout served by the harness, updating evidence if the existing built instance differs.
- [x] 1.2 Add reusable browser assertions for document, primary authenticated content, panel and overlay boundaries; identify intentional local scrollers explicitly rather than accepting hidden overflow or shell-level horizontal scrolling.
- [x] 1.3 Add meaningful regression fixtures for 440 × 956 header overlap, partial-width Queries and 490-page Browse overflow; include long identities/categories and ES/EN/PT-BR text.
- [x] 1.4 Add reproductions for Settings' five tabs, populated Admin table/pagination, 320px notifications, long-name Overview and 768px public navbar; isolate Overview's exact overflowing children.

## 2. Shared shell and sizing ownership

- [x] 2.1 Establish shared content/panel sizing and gutters using existing theme/layer-style conventions; provide only the focused helpers required by repeated grid, action-row and wide-content patterns.
- [x] 2.2 Move authenticated header and mobile drawer-trigger ownership to the shared layout, preserve sidebar/auth behavior and route/form state, and establish one primary vertical scroller with dynamic-height fallback.
- [x] 2.3 Refactor DashboardPageShell into the shared content boundary; migrate Overview, Settings, Creators Search, Reputation Strategy and Admin with exactly one header per page and equivalent loading-fallback bounds.
- [x] 2.4 Implement compact shared dashboard actions and language presentation with localized accessible names and preserved notification indication; verify drawer dismissal/focus restoration and landscape reachability.

## 3. Shared content and navigation patterns

- [x] 3.1 Implement bounded accessible tab-strip behavior; migrate Settings and Creators Search, and reuse where needed in Admin/profile surfaces without changing selected-tab or keyboard semantics.
- [x] 3.2 Implement shared adaptive pagination on existing UI primitives with localized current/total and labeled previous/next controls; migrate Browse and Admin and test boundary/current-page behavior.
- [x] 3.3 Implement/reuse a bounded accessible wide-content viewport; migrate loaded and pending Admin tables and align profile/legal/blog table or code containers where necessary.
- [x] 3.4 Apply shared stacked/compact placement sizing to current-job summaries and compatible history/list cards, preserving identifiers, status, query count and View all interaction.
- [x] 3.5 Migrate Direct Search and Browse grids, filters, result cards, update queue, badges and action rows to shared sizing patterns; verify idle/loading/error/empty/success states and populated profile dialogs.
- [x] 3.6 Migrate Overview headings/metrics/report cards to bounded available-space layouts; verify long display names, usage values, billing presentation and populated/empty reports.
- [x] 3.7 Apply available-content-width form/summary and option-grid policies to both strategy builders, shared sections and their skeletons; verify populated summaries and validation/report actions.
- [x] 3.8 Check all Settings tabs and Admin worker-job/admin dialogs against the shared patterns; fix reproduced residual width/action problems at their owning reusable components.

## 4. Shared overlay and workspace policies

- [x] 4.1 Add viewport/safe-gutter/dynamic-height constraints to shared overlay surfaces, retaining portals, dismissal and focus behavior; remove notification minimum-width conflicts and verify empty/populated messages.
- [x] 4.2 Migrate guide, profile, job/history and relevant account/admin dialogs to shared bounds and bounded body scrolling; verify close/footer actions in narrow and short viewports.
- [x] 4.3 Make Notes' navigation/editor split depend on actual dialog space; verify long titles/tags and note selection/editing without losing stored content or access to navigation.
- [x] 4.4 Keep populated Kanban horizontally scrollable only inside its bounded workspace, size columns/controls for compact space as needed, and verify keyboard/touch reachability of content/actions.

## 5. Public routes and residual audit

- [x] 5.1 Adapt the shared landing/blog navbar collapse policy to fit intermediate widths, including 768px and longer localized labels, while retaining language/auth/navigation actions.
- [x] 5.2 Audit landing, blog listing/post, auth/recovery/reset/waiting-list forms, legal/about/providers pages, consent and error/not-found UI; apply shared content/overlay patterns to reproduced problems and preserve decorative composition.
- [x] 5.3 Resolve every source-risk entry in audit.md through targeted populated-state verification or a justified shared fix; record cleared risks and any remaining manual/environment verification limits.

## 6. Validation and completion evidence

- [x] 6.1 Add/strengthen Vitest and React Testing Library coverage for shared pagination, tabs and compact-action accessibility plus affected functional regressions; use browser coverage for geometry.
- [x] 6.2 Run route-family browser smoke checks at compact/intermediate/desktop sizes and focused regressions across 320, 360, 390, 440, 768, 1024, 1280 and 1920px plus just below/above adopted layout thresholds; verify ES/EN/PT-BR representative populated states.
- [x] 6.3 Validate 956 × 440 landscape, short-height dialogs, resize state preservation, keyboard/focus access and 200% browser zoom; use mobile/WebKit emulation where available and document real-device keyboard/safe-area/touch checks separately.
- [x] 6.4 Run appropriate frontend Vitest checks, frontend build and Playwright through bash scripts/test-local.sh playwright with supported selections; inspect representative screenshots and record results/limits without claiming unexecuted device coverage.
- [x] 6.5 Validate the final implementation against all three capability specs, confirm every essential action remains reachable and intentional scrollers stay local, and update audit evidence before archiving the change.

## Execution notes

Implementation and validation are complete (28/28). The Docker image-resolution blocker was cleared on the fresh rebuild; the standard harness passed all 43 selected Chromium tests, including all 35 responsive cases against the current checkout. See validation.md for results, local-stack seed verification and physical-device limits. The three capability specs were synced to main specs and the change was archived on 2026-11-07.
