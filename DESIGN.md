# Brightloop UI Design System

This document is the portable design contract for every Brightloop feature branch. Copy it into another branch or paste it into a coding agent before implementing UI. It is self-contained and does not require any external design reference.

## Copy/paste implementation brief

> Extend Brightloop using the existing visual system. Use a warm-paper operational canvas, near-white panels, ink text, cobalt primary actions, and restrained red, yellow and green accents. Use locally bundled Inter at weights 400 and 500 with tabular numerals for all operational values. At widths below 1280px, replace the permanent sidebar with a sticky top bar and hamburger-triggered slide-over drawer; never render the full navigation horizontally. Add `Home / section / page` breadcrumbs above each page header. From 768px upward, use dense bordered tables. Below 768px, render table records as labeled two-column cards. Use Lucide outline icons only where they improve scanning: navigation, menu, search, close, logout and directional actions. Use centered modals for create/edit and confirmations, right-side sheets for row details, deduplicated toasts for feedback, and an undo action for reversible state changes. Keep touch targets at least 40px, preserve visible keyboard focus, and ensure all icon-only controls have accessible labels.

## Source-of-truth files

Copy these files together when another branch does not already contain the design system:

- `frontend/src/index.css` — tokens, font loading, canvas and motion
- `frontend/src/components/AppShell.tsx` — responsive navigation, drawer and breadcrumbs
- `frontend/src/components/BrandMark.tsx` — Brightloop geometric identity
- `frontend/src/components/ui.tsx` — buttons, cards, badges and page headers
- `frontend/src/components/forms.tsx` — inputs, selects, text areas and inline errors
- `frontend/src/components/DataTable.tsx` — tablet/desktop tables and mobile record cards
- `frontend/src/components/CommandPalette.tsx` — Cmd/Ctrl+K navigation
- `frontend/src/components/Modal.tsx` — create/edit dialog foundation
- `frontend/src/components/ConfirmDialog.tsx` — irreversible-action confirmation
- `frontend/src/components/Sheet.tsx` — contextual row detail
- `frontend/src/components/Toast.tsx` — deduplicated feedback and undo
- `frontend/src/components/DateField.tsx` — optional date input with Clear
- `frontend/src/components/StatusBadge.tsx` — shared status language
- `frontend/src/components/button-class.ts` — button variants shared by buttons and links

Required frontend packages:

```json
{
  "@fontsource/inter": "^5.2.8",
  "lucide-react": "^0.468.0"
}
```

## Design principles

1. **Operational clarity first.** Dense information is welcome, but hierarchy must remain obvious.
2. **One responsive shell.** Navigation changes form at the breakpoint; it is not squeezed or horizontally scrolled.
3. **Context stays visible.** Breadcrumbs identify location and side sheets preserve list position.
4. **Colour carries meaning.** Cobalt is action, red is risk, green is healthy, and yellow is emphasis.
5. **Geometry provides character.** The mark, chart accents and occasional circle or diamond create personality; controls remain quiet.
6. **Numbers line up.** Currency, quantities, dates, totals and chart axes use tabular numerals.

## Design tokens

### Colour

| Role | Token | Value |
|---|---|---|
| Canvas | `surface` | `#f2eee4` |
| Panel | `paper` | `#fffdf7` |
| Primary text | `ink` | `#171713` |
| Secondary text | `muted` | `#6c6a62` |
| Border | `line` | `#d7d1c4` |
| Primary action | `brand` | `#1849d6` |
| Destructive | `danger` | `#d93b2b` |
| Highlight | `yellow` | `#f2c230` |
| Positive | `green` | `#2b7755` |

Use ink borders only for major separators. Most cards and controls use `line`.

### Typography

- Family: Inter, bundled locally
- Weights: 400 and 500 only
- Page title: 22px, weight 500, tight tracking
- Section heading: 16–18px, weight 500
- Body and table cells: 13px
- Secondary copy: 11–12px
- Eyebrows and field labels: 9–11px uppercase with `0.08em–0.16em` tracking
- Apply `font-variant-numeric: tabular-nums` globally

### Spacing and shape

- Base spacing unit: 4px
- Common gaps: 8px, 12px, 16px, 20px and 24px
- Control height: 36–40px
- Touch target: minimum 40px
- Panel radius: 6px
- Drawer width: `min(288px, 88vw)`
- Desktop rail width: 256px
- Content maximum: 1440px
- Avoid soft, floating drop shadows. Use a border first and a restrained shadow only for overlays.

## Application shell

### Wide desktop: 1280px and above

- Persistent 256px left rail
- Workspace mark at the top
- Navigation grouped under Overview, Sales, Billing, Catalog and Configuration
- 16px Lucide icon plus 13px label for each destination
- Active item uses a pale cobalt surface, cobalt text and a 2px left indicator
- Compact account footer: 36px avatar, name/email, icon-only logout
- Sticky 60px top bar with current page context and command search

### Tablet and mobile: below 1280px

- Hide the permanent rail completely
- Show a sticky 60px top bar
- Left: 40px hamburger control
- Middle: current page and section; show the geometric mark when space allows
- Right: search and compact avatar
- Hamburger opens a 288px slide-over drawer with a dimmed backdrop
- Drawer closes on navigation, backdrop click, close control or Escape
- Lock body scrolling while the drawer is open
- Do not show a horizontal strip of navigation destinations

## Breadcrumbs

Render breadcrumbs once in the application shell, before routed content:

```text
Home / Sales / Subscriptions
Home / Billing / Invoices
Home / Overview / Dashboard
```

- Use an outline home icon for the first item
- Use small chevrons between levels
- Current page uses ink and medium weight
- Keep the row horizontally scrollable on very narrow screens

## Page composition

Use this order on operational screens:

1. Breadcrumbs
2. Page title, one-line description and primary actions
3. Filter surface
4. Main table, cards, chart or form
5. Pagination or supporting action

Page padding:

- Mobile: 16px
- Tablet: 24px
- Wide desktop: 32px

## Navigation icon map

Use `lucide-react` outline icons with `strokeWidth={1.8}`:

| Destination | Icon |
|---|---|
| Dashboard | `LayoutDashboard` |
| Reports | `ChartNoAxesCombined` |
| Subscriptions | `Repeat2` |
| Customers | `Users` |
| Quotation templates | `FileStack` |
| Invoices | `ReceiptText` |
| Payments | `WalletCards` |
| Products | `Package` |
| Plans | `CalendarRange` |
| Taxes | `Percent` |
| Discounts | `BadgePercent` |
| Users | `UserCog` |

Do not add icons to every label or button. Use them when they materially improve navigation or action recognition.

## Data tables and mobile records

### Tablet and desktop: 768px and above

- Bordered panel with a quiet header background
- 10px uppercase column headings
- 13px cells with 10px vertical padding
- Right-align numeric values
- Use a subtle surface change for hover
- Keep wide tables horizontally scrollable as a fallback

### Mobile: below 768px

Render each row as a record card:

- First field becomes the card title
- Remaining fields form a two-column definition grid
- Each value retains its original badge, amount or formatted date
- Row click opens the same contextual side sheet as the desktop table
- Cards use separators rather than individual heavy shadows

## Cards and dashboards

- KPI cards use a 4px top colour rule and an oversized tabular value
- Limit the first dashboard row to four primary KPIs
- Use dark or coloured feature panels sparingly and force their backgrounds with an explicit component variant or important utility so the base card surface cannot override them
- Charts must render the complete selected timeline, inserting zero-value months when the API omits empty periods
- Six-month charts fit the card at all widths
- Twelve-month charts may scroll horizontally on phones
- Include axis labels, period labels, a legend and native hover titles

## Forms

- Labels sit above fields and use the small uppercase style
- Inputs are 36px high with a 1px line border and 6px radius
- Focus uses a cobalt border plus a restrained 2px halo
- Inline errors appear directly below the field with a red left rule
- Optional date fields expose a visible Clear action
- On phones, filter controls and form actions use full available width where practical

## Overlays and feedback

### Modal

- Centered, maximum width 512px
- Header contains eyebrow, title, status pill and close control
- Cancel and primary actions share equal width
- Prevent background scrolling

### Detail sheet

- Slides from the right
- Full width on phones, maximum width 672px otherwise
- Sticky header with title, context line and close control
- Used for invoice and subscription details so users keep their table position

### Confirmation

- Use only for irreversible actions
- State the consequence in plain language
- Destructive action uses red; Cancel remains neutral

### Toast

- Short, deduplicated messages in the lower-right corner
- Provide Undo for reversible actions such as pausing a subscription
- Dismiss automatically after approximately 4.5 seconds

## Accessibility and interaction

- Every icon-only control requires `aria-label` and `title` where helpful
- Drawer, modal and sheet close with Escape
- Interactive table cards work with Enter and Space
- Maintain visible focus styles
- Respect `prefers-reduced-motion`
- Never communicate status through colour alone; include a text label
- Do not reduce body text below 11px

## Definition of done

Before merging a new UI feature, verify:

- 390px phone layout
- 768–1024px tablet layout
- 1280px or wider desktop layout
- Hamburger drawer opens, closes and locks background scrolling
- Breadcrumb matches the current route
- Table becomes record cards below 768px
- Long labels and currency values do not overflow
- Keyboard focus and Escape behavior work
- `npm run build` passes
- `npm run lint` passes
