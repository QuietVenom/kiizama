# home-screen-installation Specification

## Purpose
TBD - created by archiving change add-to-homescreen. Update Purpose after archive.
## Requirements
### Requirement: Shared branded application identity
Kiizama SHALL advertise a same-origin web app manifest on application hosts, with stable identity, standalone display, full application scope and /overview launch URL. It SHALL supply real 192/512 PNG icons, a safely padded maskable icon and an Apple touch icon. Known marketing hosts SHALL NOT advertise installation of a separate marketing app.

#### Scenario: Shared metadata across app routes
- **WHEN** a user opens login, overview or Settings on the application origin
- **THEN** the same manifest and installation identity SHALL apply without per-route configuration

#### Scenario: Installed launch requires authentication
- **WHEN** an installed app opens without a valid session
- **THEN** the existing login flow SHALL protect /overview and preserve the return destination

#### Scenario: Manifest and icons are fetched
- **WHEN** the browser requests installation assets
- **THEN** valid files SHALL have appropriate content types and missing installation assets SHALL return 404 rather than application HTML

### Requirement: Localized Settings installation guide
All user roles SHALL have an Install Kiizama section in Settings, with selectable iOS and Android instructions in ES, EN and PT-BR. Instructions SHALL remain bounded and keyboard reachable on narrow viewports and SHALL explain that Kiizama needs an internet connection.

#### Scenario: iOS manual installation
- **WHEN** a user selects iOS
- **THEN** the guide SHALL describe Safari Share, Add to Home Screen and enabling Open as Web App where available, followed by opening the new Kiizama icon

#### Scenario: Android manual installation
- **WHEN** a user selects Android and no native prompt is available
- **THEN** Chrome menu installation instructions SHALL remain available without a nonfunctional install button

### Requirement: User-initiated progressive install prompt
A shared install controller SHALL retain browser-provided install events across route changes and offer prompting only when available. It SHALL handle cancellation, failure and installed/standalone states without forcing navigation, repeated prompts or representing accepted requests as completed installs.

#### Scenario: Native prompt available
- **WHEN** the browser offers installation and the user presses Install Kiizama
- **THEN** its captured prompt SHALL be invoked once and the button SHALL be disabled during that request

#### Scenario: Cancelled or failed request
- **WHEN** the user cancels installation or the prompt fails
- **THEN** the guide SHALL remain usable with accurate status and no unhandled rejection

#### Scenario: Standalone or completed installation
- **WHEN** the app runs standalone or receives appinstalled
- **THEN** Settings SHALL show an installed state and SHALL NOT offer another native installation prompt
