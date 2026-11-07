## Context

Kiizama uses React 19, Vite, Chakra UI v3, TanStack Router/Query and existing shared UI wrappers. `_layout.tsx` owns authentication, the sidebar and a full-height scroll area. Overview and Settings use `DashboardPageShell`; Creators Search and Reputation Strategy duplicate its header and spacing. Admin uses another composition. The authenticated sidebar consumes about 245–270px on desktop, so viewport width is not equivalent to usable page width. Dialogs and nested panels reduce available width further.

`audit.md` distinguishes source risks from browser-confirmed failures. In particular, pagination's intrinsic width expands Browse's base `1fr` track, Settings' tabs overflow, Admin lacks a table viewport, notification menus exceed narrow viewports, and public navigation becomes desktop-sized too early.

## Goals / Non-Goals

**Goals:**
- Make all existing route families usable as available width and height change, including 440 × 956, narrower phones, tablet, desktop and landscape.
- Centralize repeated responsive rules at their owning shell/component and reuse them across pages.
- Preserve branding, feature access, keyboard navigation, focus visibility and intentional wide-content scrolling.
- Bound layout through data/state changes and ES/EN/PT-BR text lengths.

**Non-Goals:**
- A new visual identity, routing system, UI framework, device detection library or bespoke layout for each phone model.
- Backend/API/schema changes, regenerated clients, new billing/reporting behavior, or changes to persisted notes/jobs.
- Forcing every surface into the same composition or promising verification on every physical device. Below 320 CSS pixels the layout should degrade gracefully; the acceptance baseline begins at 320px with fluid behavior between tested samples.

## Decisions

### 1. A single authenticated shell owns navigation and scrolling

Extend the existing `_layout.tsx` composition so its authenticated shell owns the sidebar/drawer state, header and one primary vertical content scroller. The menu trigger participates in header layout; it is no longer independently fixed over page content. Include Admin in this shell. Refactor `DashboardPageShell` into the reusable content boundary, then adopt it in Creators Search, Reputation Strategy and Admin as well as its existing callers. Exactly one header renders per route.

Keep authentication, route loaders, feature access, query caching and form state intact. Resizing or opening navigation must not remount active page content. Provide a `100vh` fallback with dynamic viewport sizing (`100dvh`) and safe-area-aware bounds where appropriate. Sticky header behavior must be relative to the chosen scroller. Keep adequate room for drawer close controls and navigation in short landscape viewports.

Alternative considered: keep the fixed trigger and increase header padding. This cannot guarantee enough space across language/content widths and preserves duplicate ownership. Moving dashboard chrome into public pages is also unnecessary; public shells remain distinct.

### 2. Available content space drives composition

Reuse existing theme/layer styles for common gutters and panel boundaries; add only a few focused layout helpers where repeated composition warrants them. Shared patterns establish `min-inline-size: 0`, bounded inline size and grid tracks such as `minmax(0, 1fr)`. Use intrinsic grids (`auto-fit`/bounded column minima) where suitable; use a named content container and CSS container queries for compositions whose structure depends on remaining space, such as form/summary splits and workspace sidebars. Prefer existing Chakra responsive props for simple viewport-level concerns. Choose thresholds against the minimum usable content width during implementation, not against device names.

Do not indiscriminately set every descendant to width:100%, min-width:0 or overflow:hidden. A bounded outer panel cannot fix an intrinsically wide child by itself. Audit and migrate direct children, text and action groups with their intended semantics. Reuse the existing `StrategySection` and job-card ownership rather than introducing a universal configurable layout engine. Loading fallbacks use the same sizing policy as loaded content.

Alternative considered: a global CSS reset or per-route breakpoint patches. Both obscure the owner of the problem; global clipping also makes controls unreachable.

### 3. Shared navigation primitives handle their own adaptation

- Dashboard header: menu on the leading edge, compact accessible language selector in limited space, essential actions retained through a shared secondary-actions menu when needed. Date is secondary informational content and may leave the compact row. Preserve guide, notes and billing-notice access and unread indication.
- Public navbar: use its own shared collapse policy before links/language/auth actions stop fitting, including the confirmed 768px failure. Preserve all destinations in the compact navigation.
- Tab strip: a reusable bounded horizontal scroller retaining Tabs semantics, selected/focused tab visibility and keyboard behavior. Adopt in Settings and Creators Search; apply to Admin/other real tab lists where needed. Do not replace Brand Intelligence's option cards with tabs.
- Pagination: one shared adaptive control built on the current pagination primitives. Limited space shows Previous, localized current/total and Next; ample space retains numbered pages. Use it in Browse and Admin. Labels, disabled ends, page fetching and current-page semantics remain intact. Reducing page count merely to fit is not allowed.

Alternative considered: hiding features, shrinking all controls, or letting the entire page scroll sideways. Each harms usability; local navigation adaptation maintains access.

### 4. Wide content scrolls inside a bounded, identifiable region

Provide a focused reusable wide-content viewport for tables and comparable rich content. Migrate Admin's loaded and pending tables; align existing profile/legal table containers and blog table/code handling where needed. Preserve native table semantics, all columns and actions. Keep Kanban's horizontal interaction within the workspace and ensure its columns fit within the usable region when necessary.

A scrollable region must be keyboard reachable, have an accessible name when independently interactive, and not create an unlabeled keyboard trap. Tab strips and Kanban may reuse sizing rules without pretending to be the same component as tables. Tests identify intentional scrollers explicitly; the authenticated outer content scroller is never an allowed horizontal-overflow exception.

### 5. Overlay constraints live in shared surface wrappers

Establish width/height bounds in existing menu/dialog/drawer wrappers or a small shared overlay variant, retaining their existing portal, focus trap, dismissal and event behavior. The viewport cap must win over caller-provided minimum widths; remove conflicting minima such as notification `24rem`. Use dynamic viewport height plus safe gutters, a bounded scrolling body and reachable close/actions. Refactor guide/notes/profile/job/history callers to these defaults where compatible, preserving their intended desktop maximum widths.

Nested workspace columns respond to dialog content width, not the viewport breakpoint that currently enables a 280px sidebar within 75vw. Compact notes keep list/editor navigation reachable without shrinking the editor below usable width. Actual mobile browser chrome/keyboard effects need manual verification in addition to viewport emulation.

### 6. Validation measures behavior and overflow at every boundary

Use Vitest/React Testing Library for pagination/action/tab behavior and route-specific functional regressions. Use Playwright for real layout; jsdom does not establish geometry. Extend existing browser coverage rather than adding source-style assertions or `node:test` tests.

Create shared browser assertions for document width, authenticated content width, visible panel boundaries and overlay bounds. A root overflow:hidden or an outer overflow:auto is not proof of success: assert `scrollWidth <= clientWidth + 1` on the primary content boundary and ensure controls' rectangles remain reachable. Exempt only identified, bounded local scrollers; assert their own boundary and keyboard access. Also check menu/language rectangle separation and the job card width relative to its stacked container.

Acceptance samples: widths 320, 360, 390, 440, 768, 1024, 1280 and 1920px; landscape 956 × 440 and a short mobile viewport. Check just below/above the actual composition thresholds. Run broad route-family smoke checks at compact, intermediate and desktop widths; exercise each confirmed regression at its reproducing width and at least one adjacent size. Run ES/EN/PT-BR stress fixtures for shared navigation and populated representative content, with 490 pages, long names/handles/URLs, multiword labels, badges, error messages and loading/empty/success states. Test resize and 200% browser zoom/reduced effective space; do not infer true browser zoom or touch behavior from viewport resizing alone.

Use the repository harness `bash scripts/test-local.sh playwright` (and its supported arguments) for browser runs. Run appropriate Vitest checks and the frontend build. Include Chromium automation plus WebKit/mobile emulation where the local/CI runtime supports it; report unavailable coverage. Manual touch/keyboard/safe-area checks on a real mobile browser remain a practical limit of desktop emulation.

## Risks / Trade-offs

- [Shell migration changes sticky/scroll behavior] → Migrate all header owners together, preserve route state and check top/bottom reachability and drawer restoration before/after navigation.
- [Global wrappers affect unrelated screens] → Audit caller overrides, use focused variants, keep public/decorative composition distinct, and include error/auth/admin surfaces in smoke checks.
- [Component adaptation multiplies breakpoints] → Centralize policies in each shared component, use available-space constraints, and record threshold reasoning.
- [Compact actions become hard to discover] → Use labeled accessible triggers, preserve unread indication, and verify every feature remains reachable.
- [Table/Kanban horizontal scrolling can hide content] → Keep scrolling local and discoverable, label regions and verify keyboard/touch reachability.
- [Large test matrix becomes slow] → Combine representative shared-component stress cases with route-family smoke coverage; avoid multiplying every state by every viewport/browser.
- [Static local build differs from checkout] → Reproduce all confirmed findings against the harness-served implementation before marking tasks done.

## Migration Plan

1. Add meaningful baseline fixtures/assertions for confirmed regressions, then introduce the shared shell and content sizing policies.
2. Migrate authenticated page compositions; implement/reuse adaptive tabs, pagination and wide-content boundaries.
3. Migrate overlays and public navbar/content callers; close source-risk items with targeted verification or justified changes.
4. Run the validation matrix, record remaining environment/manual limits, and review visual behavior across content states.
5. Roll back through frontend commits if needed; no data migration or cleanup is required.

## Open Questions

No blocking product question remains. Exact available-space thresholds and the compact workspace arrangement are implementation decisions to validate against populated content. Findings labeled source risks in `audit.md` must be reproduced or explicitly cleared before closing the change; they are not assumed confirmed defects.
