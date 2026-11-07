## ADDED Requirements

### Requirement: Shared overlays remain inside the usable viewport
Menus, popovers, dialogs and drawers SHALL apply shared width and height constraints that keep their functional content within the usable viewport with safe gutters. Long labels and caller-requested minimum sizes SHALL NOT force surfaces beyond those bounds. Dismissal controls SHALL remain reachable.

#### Scenario: Notification menu on a narrow viewport
- **WHEN** a user opens empty or populated billing notifications at 320 CSS pixels
- **THEN** the menu SHALL remain within the viewport and its messages/actions SHALL wrap or scroll within the surface

#### Scenario: Narrow profile and job dialogs
- **WHEN** a user opens a creator profile, job detail, job/history list or guide at a compact width with long content
- **THEN** the dialog SHALL remain within the usable viewport, its body SHALL scroll as needed, and close/actions SHALL remain reachable

### Requirement: Overlay workspaces adapt to their own available space
Guide and Notes workspaces SHALL adapt internal navigation and content columns to the space inside the overlay. A sidebar SHALL NOT leave the main editor or content pane unusably narrow merely because a viewport breakpoint has been reached.

#### Scenario: Tablet Notes workspace
- **WHEN** a user opens Notes at a 768px viewport with a selected note or populated board
- **THEN** the list/navigation and editor or board SHALL remain reachable using a composition that fits the actual dialog width

#### Scenario: Long workspace content
- **WHEN** a note has a long custom tag/title or the guide has long localized section labels in a compact dialog
- **THEN** controls SHALL remain operable without widening the overlay or clipping required actions

### Requirement: Height changes preserve overlay interaction
Overlay bodies SHALL accommodate short/dynamic viewport heights through bounded scrolling while preserving keyboard focus, dismissal and access to required actions. Safe-area insets SHALL be respected where supplied by the browser.

#### Scenario: Landscape dialog
- **WHEN** the guide, Notes or a profile dialog is opened at 956 × 440 CSS pixels
- **THEN** its close control and content/actions SHALL remain accessible without requiring scrolling outside the overlay

#### Scenario: Keyboard reduces usable height
- **WHEN** a user focuses an input in a compact overlay and the browser reduces the usable viewport height
- **THEN** the focused field and required controls SHALL remain reachable through overlay scrolling and keyboard navigation
