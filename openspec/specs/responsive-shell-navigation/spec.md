# responsive-shell-navigation Specification

## Purpose
Define shared authenticated and public navigation behavior that keeps Kiizama headers, actions and page content bounded and accessible across screen sizes.

## Requirements

### Requirement: Authenticated routes share a bounded shell
The application SHALL use one shared authenticated navigation and content shell for Overview, Creators Search, Brand Intelligence, Settings and Admin. The shell SHALL render exactly one header and keep the primary content within its available inline size at viewport widths of 320 CSS pixels and above, including intermediate widths. Its vertical content SHALL remain reachable when viewport height changes.

#### Scenario: Tablet content beside the sidebar
- **WHEN** an authenticated page is displayed at 768 CSS pixels with the desktop sidebar visible
- **THEN** its content SHALL adapt to the remaining width without requiring horizontal scrolling of the primary content area

#### Scenario: Resize preserves active work
- **WHEN** a user resizes a populated search, settings form or strategy form from desktop to mobile and back
- **THEN** the shell SHALL preserve the active route, selected tab and entered data without rendering duplicate headers

#### Scenario: Short landscape viewport
- **WHEN** an authenticated page and its navigation are used at 956 × 440 CSS pixels
- **THEN** the user SHALL be able to reach the page content and navigation actions through bounded vertical scrolling

### Requirement: Dashboard controls adapt without overlap
The dashboard SHALL place the mobile navigation trigger in the shared header's flow. Navigation, language, guide, notes and billing notifications SHALL remain accessible without overlapping controls. Compact representations SHALL have localized accessible names and preserve unread-notification indication; date information SHALL NOT force functional controls outside the header.

#### Scenario: Original mobile regression
- **WHEN** the header is shown at 440 × 956 CSS pixels
- **THEN** the navigation trigger and language selector SHALL have non-overlapping visible and interactive bounds

#### Scenario: Long localized header labels
- **WHEN** the header is used at 320 CSS pixels in Spanish, English or Brazilian Portuguese
- **THEN** every essential action SHALL remain reachable through the header or its accessible secondary-actions menu without horizontal page scrolling

#### Scenario: Drawer interaction
- **WHEN** a user opens the mobile drawer, navigates to another page, and dismisses or reopens it
- **THEN** navigation SHALL remain keyboard usable and focus SHALL return to the trigger on dismissal without losing access to page content

### Requirement: Public navigation collapses before its controls overflow
The shared public navigation SHALL adapt its composition before navigation links, language and authentication actions exceed the available width. Compact navigation SHALL retain all existing destinations and actions.

#### Scenario: Tablet public navigation regression
- **WHEN** the landing page or blog is displayed at 768 CSS pixels
- **THEN** the shared navbar including Sign Up SHALL fit within the viewport without creating horizontal document scrolling

#### Scenario: Compact public navigation
- **WHEN** a user opens compact navigation at 320 CSS pixels in any supported interface language
- **THEN** all navigation destinations, language choices and authentication actions SHALL be reachable with visible focus and no overlapping controls
