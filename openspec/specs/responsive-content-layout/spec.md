# responsive-content-layout Specification

## Purpose
Define shared content sizing, navigation and local scrolling patterns that keep Kiizama views usable across available viewport and container sizes.

## Requirements

### Requirement: Content reflows according to available space
Route content SHALL use shared sizing and composition patterns that constrain panels, grids, text and action groups to their containing region. Populated data, loading fallbacks and validation messages SHALL NOT enlarge the primary document or authenticated content area's horizontal extent. Public, auth, legal and blog content SHALL follow equivalent content boundaries while retaining their own visual composition.

#### Scenario: Populated Overview and strategy forms
- **WHEN** Overview has a long display name or either Brand Intelligence builder has long selections, validation errors and populated summaries
- **THEN** headings, cards and form actions SHALL remain within the available content width, including beside the tablet sidebar

#### Scenario: Changes between content states
- **WHEN** a search or form transitions among loading, empty, error and populated states
- **THEN** its outer panels SHALL retain viewport-bounded widths and all functional controls SHALL remain reachable

#### Scenario: Rich public content
- **WHEN** a public/auth/legal/blog page contains long URLs, localized labels, an image, table or code block
- **THEN** ordinary content SHALL reflow within its container and inherently wide content SHALL be accessible through a bounded local region

### Requirement: Stacked search job summaries fill their content region
The shared job-summary card SHALL fill the available inline size when placed in a stacked page header. Its status, identifier, query count and associated View all control SHALL remain readable and operable. Roomy header and dialog placements SHALL retain an appropriate compact or full-width composition without independent per-page device rules.

#### Scenario: Original partial-width card regression
- **WHEN** Creators Search displays recent jobs in its stacked layout at 440 CSS pixels
- **THEN** the latest job card and View all control SHALL align to the same content-region width

### Requirement: Shared tabs stay reachable within their region
Tab navigation SHALL remain bounded to its containing region, preserving selected-tab semantics and keyboard interaction. When tabs require local horizontal scrolling, selecting or focusing a tab SHALL reveal it without scrolling the entire page sideways.

#### Scenario: Settings has five tabs
- **WHEN** a normal user opens Settings at 320 or 440 CSS pixels and navigates through all five tabs
- **THEN** each tab SHALL become visible and selectable while the primary content area remains horizontally bounded

#### Scenario: Search tabs under localization
- **WHEN** the user switches between Direct Search and Browse using keyboard or pointer at a compact width in any supported language
- **THEN** both tabs SHALL remain identifiable and reachable with the selected state visible

### Requirement: Pagination adapts through a shared interaction
Browse and Admin SHALL use a shared pagination policy that exposes previous/next navigation and a localized current/total indicator in limited space, with numbered page navigation when sufficient space exists. Page changes, current-page semantics and disabled boundary actions SHALL remain correct.

#### Scenario: Browse with 490 pages
- **WHEN** Browse returns 9,783 profiles with 490 pages at 440 × 956 CSS pixels
- **THEN** pagination, result cards and filter panels SHALL remain within the available width without horizontal scrolling of the page or primary content area

#### Scenario: Pagination boundaries and resize
- **WHEN** the user visits the first or last page in Browse or Admin and resizes between compact and spacious layouts
- **THEN** the current page SHALL be preserved and previous/next controls SHALL correctly reflect the page boundary

### Requirement: Intentional horizontal scrolling is local and accessible
Tables, Kanban and code or other intrinsically wide content SHALL use bounded local scrolling regions as needed. Such regions SHALL retain their content and actions, support keyboard access, and have an accessible name when independently interactive. Outer document and authenticated shell scrollers SHALL NOT substitute for a local wide-content region.

#### Scenario: Admin user table
- **WHEN** Admin displays populated or pending user rows at 320, 440 or 768 CSS pixels
- **THEN** all columns and row actions SHALL be accessible inside the table's own bounded viewport without widening the authenticated content area

#### Scenario: Profile tables and Kanban
- **WHEN** a user reviews profile tables or moves through a populated Kanban board in a compact workspace
- **THEN** the user SHALL be able to reach all content through its identified local region while the surrounding dialog and page remain bounded
