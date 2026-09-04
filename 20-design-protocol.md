# Design Protocol
> The UI gate. Runs in Phase 2 **before any screen is built**, verified again in Phase 4 and 5.
> Owner: **Vera**. Applies to every admin console, portal, dashboard and back-office screen.

## Why this exists

Phase 2 gives the **schema** a human approval gate — *"{USER_NAME} approves the schema before
any code is written."* The UI had no equivalent. So the first time {USER_NAME} saw a screen it
was already built, and every note became a rework instead of a design decision.

That is the whole cause of repeated edit rounds. Fix it by approving intent, not output.

**Rule: no admin screen is built before its Screen Brief is approved.**

---

## 1. The Screen Brief

One per screen, or one per tight group of screens. Under a page. Written by Vera in Phase 2,
approved by {USER_NAME} alongside the schema. If a brief takes long to write, the screen was
not understood well enough to build.

| Field | What it must answer |
|---|---|
| **Who + how often** | The actual role, and whether they open this hourly or twice a month. This sets density and nothing else does. |
| **The one primary action** | Exactly one. It gets the accent colour and the strongest position. Everything else is secondary or a link. |
| **Real data volume** | Rows expected: 12 or 40,000? Drives table vs list vs search-first. |
| **Widest realistic value** | The longest name, the biggest amount, the deepest hierarchy level in *this* project's data. Design to that, not to "Ahmad". |
| **Density class** | `dense-table` · `roomy-form` · `glance-dashboard`. Pick one. Declared, not drifted into. |
| **States to build** | Empty, loading, error, permission-denied, truncated — which apply, and the copy for each. |
| **Reuses** | Which existing component/page in *this* codebase it copies. Naming a reuse is mandatory; "new component" needs a reason. |
| **Reference** | One screenshot or URL — an existing screen in the product, or the template's own demo page. |

### The reference is not optional
Design converges instantly against a reference image and essentially never converges from
prose. If {USER_NAME} has not given one, Vera proposes one from the template's demo pages
and gets a yes/no. One image replaces three edit rounds.

---

## 2. The Tells — how generated UI gives itself away

Walk this list before calling a screen done. Each line is a thing a person shipping
back-office software does **not** do.

- [ ] **Everything is a card.** Same radius, same shadow, same padding, edge to edge. Real
      admin UIs separate with borders and hairlines. Shadow is for things that *float* —
      dropdown, modal, popover — and nothing else.
- [ ] **Uniform weight.** Four stat tiles across, three-column grid, every block equally
      loud, regardless of what the user actually opened the page for.
- [ ] **Untouched default palette.** Bootstrap `primary` on every button, or the
      indigo→purple gradient. Gradients, glassmorphism and hero padding in a tool someone
      stares at eight hours a day.
- [ ] **The ▲ +12.5% badge** on every tile, green, on data nobody computed.
- [ ] **Placeholder content shipped.** John Doe, lorem, RM 12,345, stock avatars, a chart
      with invented values.
- [ ] **Fake symmetry.** Exactly 4 tiles, exactly 5 rows, exactly 3 columns — round numbers
      chosen for the grid, not because the data has that shape.
- [ ] **Happy path only.** No empty, no loading, no error, no permission-denied, no
      behaviour for the row that is 90 characters wide.
- [ ] **Data ignoring its own type.** Currency left-aligned, IDs in a proportional font,
      three date formats on one page, decimals that wander.
- [ ] **Bot copy.** "Welcome back! 👋" · "Manage your users here" · "No data available."
- [ ] **Emoji as icons**, or two icon sets on one screen.
- [ ] **Generic labels where the schema has real vocabulary.** Saying *Users* when the
      domain says *stockist*, *downline*, *grant ceiling*. **This is the loudest tell of
      all** — it proves nobody who understands the business laid the screen out.
- [ ] **Every button the same size and colour**, so the primary action does not lead.
- [ ] **A control that vanishes at a breakpoint.** `display:none` on a filter, an action or a
      nav rail below some width is a **removed feature**, not a responsive layout — the phone
      user simply cannot do that thing. Move it: a rail becomes a scrolling chip strip, a
      toolbar collapses into a sheet. Reserve hiding for genuinely duplicated labels.
- [ ] **Text inside an SVG that was never re-checked at width.** Chart text is in viewBox
      units, so it shrinks with the drawing — 10px in a 640-unit chart renders near 5px on a
      phone. Size it up at the breakpoint or the chart is decoration.

---

## 3. The human touch — what to do instead

1. **Steal the domain's own nouns.** Take labels verbatim from the schema and from how
   {USER_NAME} talks about the business. Vocabulary is the cheapest authenticity there is.
2. **One accent colour**, for the primary action and nothing else. Red/amber/green are
   reserved for state and never used as decoration.
3. **Border-first separation.** A hairline between rows, one border on a container. Reach
   for shadow only when something genuinely floats above the page.
4. **Density is a declared decision**, per screen, from the brief — not one padding value
   sprayed everywhere. An operator's daily table and a twice-a-month settings form are not
   the same screen and must not look like it.
5. **Numbers behave like numbers.** Right-aligned, `tabular-nums`, fixed decimals, currency
   symbol once in the column header instead of on every cell. IDs and codes monospace.
6. **Build the four states before "done"** — empty (carrying the action that fills it),
   loading, error, permission-denied.
7. **Test with the ugliest real row.** Longest name, zero-order agent, RM 1,234,567.89,
   deepest hierarchy level. Layouts break on real data, never on `foo`.
8. **Asymmetry with a reason.** The frequent action gets more room. If every block is the
   same size, no decision was made and it shows.
9. **Write the copy as the person doing the job would say it.** "No orders yet this month"
   over "No data available." Empty states are where copy is noticed most and written least.
10. **Keyboard works.** Visible focus ring, tab order matching visual order, Enter submits.
    Almost no generated UI ships this, so having it reads as care.

---

## 4. Template fidelity

When the project ships on a bought or vendored template — AdminLTE 4, Bootstrap 5 — the
template's own components **are** the design system.

- Use its real components and SCSS variables. See `11-pattern-library.md` → *Admin Template
  Design Language* for the component map and the override points.
- Hand-rolling an equivalent of something the template already provides is a tell in itself:
  a person does not rebuild what they already paid for.
- Override the template's variables once, centrally. Never fight it with per-page utility
  classes — mixed idioms on one screen are visible immediately.
- Deviate only where the domain genuinely needs it, and say so in the brief.

**Consistency with the template is not laziness. It is the human signal.**

---

## 5. Gate wiring

| Phase | What happens | Gate |
|---|---|---|
| **2 — Design** | Vera writes the Screen Brief beside Atlas's boundaries and Delta's schema | **{USER_NAME} approves schema *and* brief before any code** |
| **3 — Build** | Luna implements to the approved brief; Vera on responsive + a11y | Deviation from the brief is raised, not absorbed |
| **4 — Test** | Probe screenshots every new/changed screen at **1280** and **390**, and attaches them | The design is *seen* before {USER_NAME} sees it |
| **5 — Review** | Vera reads the built screen against her own brief and walks §2 Tells | Findings go to the author, not to {USER_NAME} |

### Phase 4 is the one that changes the most
Nobody was ever looking at the output. `claude-in-chrome` was scoped to "genuine browser
journeys" only, so {USER_NAME} was the first pair of eyes on every screen, every time.
A screenshot at two widths costs one tool call and catches the majority of what came back
as edit rounds.

---

## 6. Interactive dashboard benchmark — Power BI's model, AdminLTE's shell

> **The benchmark is Power BI's *interaction model*, never Power BI's default styling.**
> Those defaults are as recognisable as any generated UI: auto-titles like "Sum of Amount by
> Month" (the lorem ipsum of BI), the stock blue-on-grey palette, six identical KPI tiles in a
> row, decorative donuts and gauges, decimals wandering to `12.34567M`, a legend on a
> two-series chart. Copy the behaviour. Leave the look.
>
> **Confidence:** the Power BI feature names below are long-stable (bookmarks, drill-through,
> field parameters, report-page tooltips). Verify against current docs before quoting them to
> a client.

### 6.1 Why Power BI is the right bar

A hand-built Laravel dashboard is almost always a **wall of static numbers**. Someone asks
"why is that figure high?" and there is nowhere to click. Power BI's whole value is that the
question has an answer one click away. That is the bar — not the chart types.

### 6.2 The model, mapped to this stack

| Power BI behaviour | What it does | AdminLTE / Laravel implementation |
|---|---|---|
| **Slicers** | Persistent filter controls, visible, always | A filter bar whose state lives in the **query string** |
| **Cross-filter** | Click a bar → every other visual re-filters | Shared filter state → Inertia partial reload (`only:`) or Blade fragment swap |
| **Drill-down** | Year → Quarter → Month inside one visual | A level in the filter state; same route, same card |
| **Drill-through** | Right-click a point → detail page carrying the context, with a back button | A detail route taking the same query string + a breadcrumb back |
| **Focus mode** | Expand one visual to full page | `card` → modal, or a `?focus=` param |
| **Show as table / Export** | Reveal the rows behind any visual | A `card-tools` toggle + the existing server-side export |
| **Field parameters** | User swaps the measure or dimension | A `<select>` bound to filter state — one chart becomes five |
| **Report-page tooltips** | Hover gives a mini-report, not a number | A popover fetching a small partial on demand |
| **Bookmarks** | Save and name a filter state | `saved_views` table: user, name, filter JSON |
| **Conditional formatting** | In-cell data bars, colour scales, KPI arrows | CSS bars in the cell — cheapest polish there is |
| **Reset to default** | Clear every filter | One link back to the bare route. Always forgotten |
| **Row-level security** | Users see only their rows | Already solved — tenant scope + RBAC |

**AdminLTE's `card-tools` slot *is* Power BI's visual header.** Focus, show-as-table, export
and refresh belong there, on every card, identically. That one habit does more for the
"real product" feel than any chart library.

### 6.3 Build order — effort against value

**Tier 1 — always, on any dashboard. Cheap, and their absence is what reads as unfinished.**
- Filter bar in the query string · Reset link · Show-as-table + export on every card
- In-cell data bars and right-aligned tabular numerics
- Per-card empty and loading states (a dashboard filters to nothing constantly)

**Tier 2 — when the dashboard is opened daily.**
- Cross-filtering · Drill-through with a breadcrumb back · Field parameters · Focus mode

**Tier 3 — only when {USER_NAME} asks for it by name.**
- Saved views · Report-page tooltips · Small multiples

**Never:** natural-language Q&A, animated or 3D chart types, decorative gauges and donuts.

### 6.4 Two rules that decide whether it works

**The latency budget.** A filter click must repaint in **under 300 ms**, a drill-through in
under a second. Power BI feels fast because it queries pre-aggregated columnar data; a Laravel
dashboard firing twelve live `GROUP BY`s per click will feel worse than no interaction at all.
Pre-aggregate into summary tables, index the date column, cache the expensive tiles, and hand
it to Indra before shipping. **If a click cannot be made fast, remove the click** — an honest
static dashboard beats an interactive one that stalls.

**Filter state belongs in the URL.** This is the one place to *beat* the benchmark: sharing a
filtered view is genuinely awkward in Power BI, and it is free here. Query-string state means
every filtered view is a shareable link, the browser Back button behaves, the page survives a
refresh, and a bug report arrives as a URL that reproduces it. Never hold dashboard filter
state only in component memory.

### 6.5 The reference

**Live:** https://claude.ai/code/artifact/4de678c0-d2e7-47e8-8a90-e8fb347e5b61
*(Visual treatment reskinned toward Metronic, 2026-09-04, at {USER_NAME}'s direction —
interaction model unchanged.)*
**Source:** [`references/dashboard-benchmark.html`](./references/dashboard-benchmark.html)

A dispatch console for a parcel operation — deliberately tied to no project, so it stays
reusable. It is the standing reference for any dashboard Screen Brief under §1: point at it
instead of describing a dashboard in prose.

What it demonstrates, in the Tier order of §6.3 — filter state in the URL · active-filter
chips, individually removable · reset · cross-filter from the depot rail *and* from the chart
bars · a field parameter that reswings every panel onto a different measure · drill-through to
a consignment with a breadcrumb back and filters preserved · focus mode · show-as-table and
CSV on the card header · in-cell data bars with tabular right-aligned figures · a real empty
state carrying its own way out.

It also obeys §2 and §3 on purpose, and the choices are worth reading as the worked example:
two loud figures rather than a row of six · a hairline-divided summary band instead of cards ·
one ochre accent confined to interactive and selected state · status shown as a **labelled**
pill so colour is never the only channel · depot, consignment, route, SLA breach as the
vocabulary. A neutral reference still has to be **specific** — labelled *Users / Items /
Total* it would have taught the exact tell §2 warns about.

### 6.6 The benchmark set — {USER_NAME}'s references, read 2026-09-04

Five references, given by {USER_NAME}. Four are admin dashboards; the fifth is something else
(see below). Read what each is *for* before copying anything out of it.

| # | Reference | What it is | Take | Leave |
|---|---|---|---|---|
| 1 | [AdminLTE v4 · Dashboard v2](https://adminlte.io/themes/v4/index2.html) | Free Bootstrap 5 admin, the stack we actually ship on | The skeleton: `card` + `card-header` + `card-tools`, `small-box` / `info-box`, sidebar `nav-treeview` | Its **composition** — nine unrelated widgets stacked because it is selling widgets |
| 2 | [UBold](https://themes.coderthemes.com/ubold/bootstrap/index.html) | Modern Bootstrap, e-commerce console | Status badges as a *system* — Active / Low Stock / Out of Stock / Limited; Export CSV sitting in the header; the product grid card | Four equal-weight KPI tiles |
| 3 | [TailAdmin CRM](https://demo.tailadmin.com/crm) | Tailwind CRM console | **Three** KPIs, not six, each with a signed delta vs last month; the Monthly / Quarterly / Annually grain toggle; goals as progress against a figure | Percentage deltas on every tile regardless of whether the comparison means anything |
| 4 | [Metronic Tailwind demo1](https://keenthemes.com/metronic/tailwind/demo1/) | The most refined of the five | Restraint: consistent padding, subtle card separation, avatar stacks with `+N`, a headline number *with its source breakdown underneath*, an actionable widget (next meeting → Join) | It is a workspace home, not a metrics dashboard — do not copy its shape onto an analytics screen |
| 5 | [Angulr landing](https://flatfull.com/themes/angulr/landing) | **A marketing landing page**, not a dashboard | Landing-page structure for a *client-facing site* | Everything else — see the note |

**On #5 — confirmed by {USER_NAME} 2026-09-04: Angulr is the landing-page reference.**
It is not an admin demo. It is a mid-2010s flat-design marketing page selling a $21
ThemeForest bundle — hero, value props, testimonials, pricing CTA. So the set is really
**two benchmarks in one list**, and they must never be crossed:

| Surface | Reference | Density |
|---|---|---|
| Console / dashboard / back-office | #1–#4 | Working density, §6.3 |
| Public marketing page for a product | #5 | Landing density — hero, CTA, testimonials |

Marketing-page conventions (a big hero, centred copy, generous vertical rhythm, a pricing CTA)
are **tells** when they appear on a console — §2 flags hero padding for exactly this reason.
The reverse also holds: a landing page built at console density reads as a settings screen.
Ask which surface the brief is for before reaching for either half of this list.

### 6.7 What the five agree on — and the one thing none of them do

**Shared conventions.** All four dashboards independently land on the same shell, which is why
these are safe defaults rather than one vendor's opinion: sidebar + topbar with collapsible
nested nav · a KPI row carrying a delta against the prior period · the card as the unit of
composition, with a header and a tools slot · **status shown as a labelled badge, never bare
colour** · one primary table with avatars, badges and per-row actions · an export affordance ·
a light/dark toggle. Ship all seven and the screen already reads as a product.

**Where they disagree, TailAdmin is right.** KPI counts run 3 (TailAdmin) to 4 (AdminLTE,
UBold). Three with meaningful deltas beats four for the sake of the grid — and it matches §1's
rule that only what someone acts on gets to be loud.

**The gap, and it is the whole point of §6.** Click a chart segment in any of the five and
**nothing else on the page changes.** None of them cross-filter. None drill through. None hold
filter state in the URL. They are component showcases — beautiful, disciplined, static.

> **So the bar is split, and neither half covers the other:**
> these five set the **visual** benchmark; **Power BI sets the behavioural one** (§6.1–§6.4).
> A screen that matches AdminLTE's look and Power BI's behaviour is the target. Matching only
> the first is where most admin panels stop, which is exactly why they feel dead to use.

The **composition trap** is worth naming separately. Every one of these demos exists to display
the vendor's component library, so it stacks widgets that answer no single question — AdminLTE's
Dashboard v2 puts CPU traffic, a chat thread, member avatars, an orders table and browser-usage
stats on one page. Copy that structure and the screen inherits a catalogue's logic instead of a
job's. Take the components; compose them from the Screen Brief (§1).

---

## 7. When this protocol does not apply

- **T0** work and copy-only changes.
- Internal tooling nobody but Iris reads.
- A screen explicitly specified by {USER_NAME} down to the layout — then the spec *is* the
  brief, and Vera verifies against it rather than authoring it.

Everything else with a user-facing surface: brief first, then build.
