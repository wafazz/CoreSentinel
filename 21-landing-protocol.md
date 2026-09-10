# Landing Page Protocol
> The public-surface gate. Runs in Phase 2 **before any section is built**, verified again in Phase 4 and 5.
> Owner: **Vera**. Applies to every landing page, marketing site, pricing page and public template.

## Why this exists

[20-design-protocol.md](./20-design-protocol.md) is a **console** protocol. Its Screen Brief asks
"who opens this hourly", its density classes are `dense-table` / `roomy-form` /
`glance-dashboard`, and its §2 Tells list flags **hero padding as a defect**. All correct — for
back-office software.

Landing pages got four lines: reference #5 in §6.6, a two-row density table, and a warning that
the two surfaces must never be crossed. That is a *density marker*, not a standard. The reference
behind it is a mid-2010s flat-design ThemeForest page, described in that protocol's own words as
selling a $21 bundle.

So the public surface has been built with no gate at all, while the console has seven sections and
a live benchmark. Worse: **applying §2 of the design protocol to a landing page points the wrong
way** — a hero, generous vertical rhythm and a pricing CTA are tells on a console and are the
job on a landing page.

**Rule: no public-facing section is built before its Landing Brief is approved.**

---

## 1. Read the system first

This is the section that makes the rest work, and it comes before the brief, not after.

A landing page is not a design exercise. It is **a claim about a system that already exists**, and
almost everything the page needs to say is already written down in the codebase. Designing one
from prose — or from a reference image alone — produces a page that describes a generic product,
which is the deepest tell there is.

Before writing a single brief field, Vera reads these, in this order, and writes down what she found:

| Read | Extract | Feeds |
|---|---|---|
| **Migrations / schema** | The domain nouns, verbatim. `stockist`, `downline`, `consignment`, `grant ceiling`, `SLA breach` | Every headline, label and feature name |
| **Routes / controllers** | What the product actually *does* — the verbs that have code behind them | The claim, the feature section |
| **The plans / pricing / subscription tables** | Real tier names, real prices, real limits, real currency | §6.3 pricing, and whether a pricing section is even honest yet |
| **Roles / permissions / guards** | Who the audiences genuinely are | Who the page is addressed to; whether it needs one page or two |
| **Existing components + the installed template** | What already exists to reuse, and the design language already paid for | §8, and the reuse field of the brief |
| **Config / locale / currency** | Product name, locale, `MYR` vs `USD`, date format | Copy, number formatting, legal footer |
| **Feature/E2E tests** | The journeys that are actually proven to work | Claims you are allowed to make |
| **`Planning.md`, `README`, the project file under `Projects/`** | Positioning, the problem statement, who it was built for | The headline and the problem section |

Three rules follow from this, and they are the difference between a real page and a template fill:

1. **Steal the domain's own nouns** — the same rule as
   [20-design-protocol.md](./20-design-protocol.md) §3.1, and it matters *more* here. A console
   labelled *Users* is sloppy; a landing page labelled *Users* when the schema says `stockist` is
   selling someone else's product.
2. **Never claim what the tests do not cover.** If there is no passing test for the export, the
   page does not say "one-click export". Marketing copy that outruns the build is a support
   ticket with a countdown on it. Where a claim is aspirational, say so in the brief and let
   {USER_NAME} decide — do not decide silently.
3. **Real numbers or no numbers.** Pull counts, tiers and limits from the database or the config.
   A landing page with invented figures is the §5 tell that costs the most trust, because unlike a
   layout flaw it is a false statement.

**Gate on this section:** the brief must name, for every claim, where in the system it came from.
A claim with no source is a claim that gets cut.

---

## 2. The Landing Brief

One per page. Under a page. Written by Vera in Phase 2, approved by {USER_NAME} alongside the
schema — the same gate the Screen Brief uses. The console fields do not transfer; these replace them.

| Field | What it must answer |
|---|---|
| **Surface** | Landing · pricing · docs home · template demo. Each has a different section order (§3). Declared, not drifted into. |
| **Who is arriving, and from where** | Cold search, an ad, a referral, a QR on a flyer? Traffic source sets how much context the hero has to rebuild before it can ask for anything. |
| **What they believe on arrival** | The objection or misconception the page exists to move. If there is none, the page is a brochure and should be one section long. |
| **The one conversion action** | Exactly one. It gets the accent colour, the strongest position, and every repeat of the CTA (§6.1). A second co-equal action is a decision nobody made. |
| **The claim, in one sentence** | What this is and who it is for, in the domain's own words (§1). If it takes two sentences, the positioning is not settled and the page cannot be. |
| **Proof available** | Named customers? Real figures? A demo? A screenshot of the actual product? List what genuinely exists — §6.2 builds only from this list. |
| **Sections, in order** | From §3. Name them. Anything not on the list is cut, not "nice to have". |
| **Reuses** | Which existing component, partial or template block this copies. Mandatory, same as the console brief — "new component" needs a reason. |
| **Reference** | One screenshot or URL. Non-negotiable, for the reason [20-design-protocol.md](./20-design-protocol.md) §1 gives: design converges against an image and essentially never converges from prose. |
| **Claim sources** | Per §1's gate — where each factual claim came from in the system. |

---

## 3. Section order and the fold

### 3.1 The default order

Not a law, but the deviation goes in the brief with a reason. Sections are **cut** from this list,
never reordered casually — the order is an argument, and shuffling it breaks the argument.

1. **Nav** — thin, the conversion action repeated at the right, nothing else fighting it
2. **Hero** — the claim, one supporting sentence, one CTA, one proof anchor
3. **Proof strip** — named logos or two real figures. Cut it entirely if neither exists (§6.2)
4. **The problem** — stated in the visitor's words, not the product's
5. **How it works** — three steps. Four is a process diagram, and nobody reads those
6. **Feature depth** — grouped by outcome, not by module. The schema's nouns, §1
7. **Social proof** — real, attributed (§6.2)
8. **Pricing** — real tiers from the plans table (§6.3)
9. **FAQ** — the actual objections from §2's brief field, not invented questions
10. **Final CTA** — the same action as the hero, restated
11. **Footer** — legal, contact, the real company entity

### 3.2 The fold

Above the fold, on a 390px viewport, the page must answer three things without a scroll: **what
this is**, **who it is for**, and **what to do next**. A hero that needs a scroll to become
intelligible has already lost the visitor who arrived from an ad.

Test it at 390 × 664 (an iPhone with browser chrome), not at 390 × 844. The chrome is real.

### 3.3 Section rhythm

Vertical space is what separates a landing page from a settings screen. Use it deliberately:

| Breakpoint | Section padding (block) |
|---|---|
| ≥ 992px | 96px |
| 768–991px | 72px |
| < 768px | 56px |

Container max-width **1200–1440px** with auto margins. A landing page with no max-width container
stretches to 2560px on a wide monitor and reads as an unstyled document — this is one of the most
common and most fixable faults.

---

## 4. The scales — type, space, colour

Declared once, centrally, as variables. The console protocol's §4 rule holds here without change:
override the template's variables at one point, never fight it with per-section utility classes.

### 4.1 Type

Base **16px**, body ratio **1.25** (major third). The display step is fluid because a hero
headline set at a fixed size is either small on a monitor or broken on a phone.

```css
--fs-caption:  0.75rem;   /* 12 */
--fs-small:    0.875rem;  /* 14 */
--fs-body:     1rem;      /* 16 */
--fs-body-lg:  1.125rem;  /* 18  — the landing default; 16 is a console size */
--fs-h5:       1.25rem;   /* 20 */
--fs-h4:       1.563rem;  /* 25 */
--fs-h3:       1.953rem;  /* 31 */
--fs-h2:       2.441rem;  /* 39 */
--fs-h1:       3.052rem;  /* 49 */
--fs-display:  clamp(2.5rem, 6vw + 1rem, 4.5rem);
```

| Role | Line height | Weight | Tracking |
|---|---|---|---|
| Display | 1.05 | 700 | −0.02em |
| H1 | 1.15 | 700 | −0.01em |
| H2–H3 | 1.25 | 600 | 0 |
| Body | 1.6 | 400 | 0 |
| Link | — | 500 | 0 |
| Button | — | 600 | 0 |
| All caps | — | 600 | +0.05em |

**Measure: 65–75 characters.** Set `max-width: 65ch` on prose blocks. Full-width body text at
1440px is unreadable and is the fastest way to make a page look unedited.

**Two typefaces maximum**, and body text never below 16px. On a public page, type is the entire
craft signal — it is the first thing that reads as considered or not.

### 4.2 Space

4px base. The same scale the console uses, so one system spans both surfaces:

```css
--space-1: 0.25rem;  --space-2: 0.5rem;   --space-3: 0.75rem;  --space-4: 1rem;
--space-6: 1.5rem;   --space-8: 2rem;     --space-12: 3rem;    --space-16: 4rem;
--space-24: 6rem;    --space-32: 8rem;
```

Every gap, pad and margin resolves to a step. A one-off `padding: 37px` is where a layout starts
to drift, and drift is visible long before anyone can name it.

### 4.3 Colour

**60 / 30 / 10.** Dominant neutral 60%, secondary surface 30%, accent 10% and no more. The accent
is the conversion action and interactive state — nothing decorative gets it. Red, amber and green
stay reserved for state, exactly as [20-design-protocol.md](./20-design-protocol.md) §3.2 has it.

Contrast is a gate, not a preference — WCAG 2.2 AA:

| Element | Minimum |
|---|---|
| Body text | 4.5 : 1 |
| Large text (≥ 24px, or ≥ 19px bold) | 3 : 1 |
| UI components, focus rings, chart marks | 3 : 1 |

Colour is never the only channel. A status, a plan tier or a "recommended" badge carries a label
too — the same rule the dashboard benchmark obeys with its labelled pills.

### 4.4 Motion

150–300ms, `transform` and `opacity` only — never `top`, `left`, `width` or `height`, which force
layout on every frame. Honour `prefers-reduced-motion: reduce` by dropping to opacity or nothing.
Motion on a landing page is punctuation. A page that animates on every scroll boundary is a page
that cannot be read.

---

## 5. The Tells — landing edition

[20-design-protocol.md](./20-design-protocol.md) §2 does **not** apply here — several of its items
invert on a public surface. This is the list to walk before calling a landing page done.

- [ ] **A hero that says nothing.** "Elevate your workflow." "Seamless solutions for modern teams."
      Vocabulary with no product behind it. §1 exists to prevent exactly this — the schema has real
      nouns, use them.
- [ ] **Two co-equal CTAs.** Two buttons, same size, same weight, side by side. The visitor now has
      a decision instead of an action. One primary; a secondary is a text link or it is cut.
- [ ] **Unnamed social proof.** "Trusted by 500+ teams" with grey placeholder logos, or testimonials
      from stock avatars with invented names and companies. This is not a design flaw, it is a
      false statement on a public page.
- [ ] **Numbers with no source.** "10,000+ users", "99.9% uptime", a counter that animates up on
      scroll. §1 rule 3: real numbers or no numbers.
- [ ] **Three equal pricing tiers with nothing recommended.** No guidance is a decision deferred to
      someone with less information than you.
- [ ] **The scroll cue.** A bouncing chevron, "Scroll to explore", a mouse-wheel icon. Content
      pulls; furniture does not.
- [ ] **Everything centred.** Centred hero, centred headings, centred body copy in a 900px column.
      Centred body text is measurably harder to read — the ragged left edge destroys line tracking.
- [ ] **Gradient mesh background blobs**, glassmorphic floating cards, the indigo→purple wash. The
      single most recognisable generated-page fingerprint there is.
- [ ] **Emoji as feature icons**, or two icon sets on one page.
- [ ] **`height: 100vh` on the hero.** On iOS Safari the toolbar collapse changes `vh` mid-scroll
      and the layout jumps. Use `100svh` / `100dvh`, or `min-height` with real content sizing.
- [ ] **CTAs at ragged heights across a card group.** Different content lengths push each button to
      a different Y. Pin them to the card bottom so they form one line. Same for feature lists in a
      pricing table — every column's list starts at the same Y or the comparison is unreadable.
- [ ] **No max-width container** — §3.3.
- [ ] **A testimonial carousel with dots.** Nobody clicks the dots. Show them at once, or show one.
- [ ] **An FAQ that answers no real objection.** "What is [product]?" is not an objection. The brief
      named the actual one — answer that.
- [ ] **Placeholder content shipped.** Lorem, John Doe, RM 12,345, a stock hero photo of a team
      high-fiving. Carried over from the console protocol unchanged, because it is fatal on both.
- [ ] **Console density on a public page.** 14px body, tight padding, hairline-divided rows. The
      inverse of the cross-over error [20-design-protocol.md](./20-design-protocol.md) §6.6 warns
      about, and just as visible.

---

## 6. Conversion mechanics

### 6.1 One action, repeated

One conversion action, from the brief. It appears in the nav, in the hero, and at the final CTA —
**the same words every time**. "Start free trial" in the hero and "Get started" in the nav are two
actions to a reader, however obvious the equivalence is to you.

Repetition is not redundancy: a visitor decides at an unpredictable scroll depth and needs the
action within reach when they do. Repeat it; never vary it.

### 6.2 Proof, or silence

Build only from the brief's *Proof available* list. The hierarchy, strongest first:

1. Named customer with role and company, ideally with a specific outcome
2. A real figure from the system, with its basis stated
3. A screenshot of the actual product, current
4. A named logo you have permission to show

**If none exists, ship no proof section.** An honest page with no testimonials outperforms one with
invented ones, because invented proof is discovered exactly once and then everything else on the
page is suspect too.

### 6.3 Pricing

Tiers, names, prices, limits and currency come from the plans table (§1) — never from the design.
One tier carries a **recommended** marker, chosen deliberately and shown with the accent plus a
label, not with extra height alone. State the billing period, the currency and what happens at the
limit. If tax handling differs by market, say which.

If the plans table does not exist yet, the page does not get a pricing section. Say so in the brief.

### 6.4 Forms

Every field is a cost. Ask for what is needed to deliver the next step and nothing else — an email
field alone converts better than the same form with "company size" attached. Label above the input,
never placeholder-as-label (it vanishes on focus and fails screen readers). Errors sit next to the
field that caused them and say what to do.

Keyboard works: visible focus ring, tab order matching visual order, Enter submits. Carried from
[20-design-protocol.md](./20-design-protocol.md) §3.10, and it applies to every public form.

---

## 7. Performance budget

The console has its 300 ms click budget ([20-design-protocol.md](./20-design-protocol.md) §6.4).
The public surface has this one, and it is stricter, because a console user has already committed
and a landing-page visitor has not.

| Metric | Budget | What breaks it |
|---|---|---|
| **LCP** | ≤ 2.5s | An unoptimised hero image; a webfont blocking the headline |
| **CLS** | ≤ 0.1 | Images with no dimensions; a font swap reflowing the hero; late-injected banners |
| **INP** | ≤ 200ms | Scroll-driven animation libraries doing layout work |
| **JS** | ≤ 100KB gzipped | A carousel library, an animation library and an analytics bundle on a static page |

Non-negotiables:

- **Every image declares `width` and `height`, or `aspect-ratio`.** This one line prevents the
  majority of real-world CLS.
- **Preload the LCP image and the display font.** `font-display: swap`, and keep the fallback
  metrically close or the swap *is* the layout shift.
- Serve modern formats with real dimensions — no 3000px hero scaled down in CSS.
- Defer anything not needed for the first screen.

**A landing page is the one surface where a stranger decides in under three seconds.** If a
section cannot be made fast, cut the section — the same trade the console protocol makes when it
says an honest static dashboard beats an interactive one that stalls.

---

## 8. Stack translation

CS ships on Bootstrap 5 / Blade / AdminLTE 4 and Inertia + Vue. Most public design guidance in
circulation — including everything in the source surveyed for §11 — is written in Tailwind utility
syntax and shadcn component APIs. **The prose rules transfer; the code does not.**

| Concept | Tailwind idiom | This stack |
|---|---|---|
| Section rhythm | `py-24 md:py-32` | `$spacer` multiples in SCSS, or a `.section` utility defined once |
| Container | `max-w-7xl mx-auto px-6` | `.container` with `$container-max-widths` set |
| Type scale | `text-5xl` | `$font-size-base` + `$h1-font-size`… overridden once |
| Accent | `bg-indigo-600` | `$primary` overridden in `_variables.scss` |
| Grid | `grid grid-cols-3 gap-8` | `.row` / `.col-lg-4` with `$grid-gutter-width` |
| Component | `npx shadcn add card` | The template's own card partial |

§4 of [20-design-protocol.md](./20-design-protocol.md) applies unchanged and is worth restating:
**hand-rolling an equivalent of something the template already provides is a tell in itself.**
Override centrally, once. Mixed idioms on one page are visible immediately.

---

## 9. Gate wiring

| Phase | What happens | Gate |
|---|---|---|
| **1 — Research** | Scout returns the §1 system read — domain nouns, routes, plans, roles, reusable components | Scout is read-only; **Iris records** the findings into the brief |
| **2 — Design** | Vera writes the Landing Brief (§2) beside Atlas's boundaries and Delta's schema | **{USER_NAME} approves the schema *and* the brief before any code** |
| **3 — Build** | Luna implements to the approved brief; Vera on responsive, contrast and keyboard | Deviation from the brief is raised, not absorbed |
| **4 — Test** | Probe screenshots at **1280** and **390**, and measures §7 against a real build — not a dev server | The page is *seen and measured* before {USER_NAME} sees it |
| **5 — Review** | Vera walks §5 Tells and re-reads every claim against §1's sources | Findings go to the author, not to {USER_NAME} |
| **6 — Security** | Aegis on headers and form endpoints; Cipher on any public form — it is unauthenticated input from the open internet | Rate limit and CSRF on every public form, no exceptions |

**Phase 6 is not optional here.** A landing page's contact form is the only unauthenticated,
publicly-reachable write path most of these projects have.

---

## 10. When this protocol does not apply

- **T0** work and copy-only edits to an approved page.
- Any authenticated surface — that is [20-design-protocol.md](./20-design-protocol.md), and the two
  must not be crossed in either direction (§6.6 there).
- A page {USER_NAME} has specified down to the section — then the spec *is* the brief, and Vera
  verifies against it rather than authoring it.

Everything else with a public URL: brief first, then build.

---

## 11. Provenance

Compiled 2026-09-10 from a survey of [Payoss/UIUX-high-taste-skill](https://github.com/Payoss/UIUX-high-taste-skill)
(21 skills, 333 files), plus WCAG 2.2 AA and the Core Web Vitals thresholds.

**Nothing in this file is copied from that repository, deliberately.** The survey found that 7 of
the 21 skills carry no licence file or grant of any kind, 6 of 7 in another group carry
contradictory licence metadata (frontmatter `MIT`, one physical `Apache-2.0`, a third party named
in the README), and 2 more have no licence at all. CoreSentinel is a public repository; vendoring
unlicensed prose into it is not a defensible position. What is reproduced here are facts and
conventions that are not anyone's property — a 1.25 major-third ratio, a 4px base unit, the 60/30/10
allocation, WCAG contrast minimums, Core Web Vitals budgets — restated in this system's own terms.

Three things the survey established, recorded so nobody repeats the search:

- The one skill built for this exact purpose is **hollow**: `mrgoonie-ui-ux-pro-max` advertises a
  `landing` search domain over 161 palettes and 57 font pairings, and ships with empty `data/` and
  `scripts/` directories. There is nothing behind the index.
- **No skill in the collection designs from an existing system.** The nearest thing is a
  compatibility check — read the framework so the build does not break. §1 of this protocol is
  therefore original to CS and is the part with no upstream equivalent.
- The collection **contradicts itself** on fonts (one group defaults to Inter, four ban it by name),
  on colour (one prescribes neon cyan, three ban it), and on whether scales should be tokenised at
  all. It is an aggregation, not a system. Merging it wholesale would import the contradictions.

Where a genuinely useful specific rule originated there — bottom-pinning CTAs across a card group,
aligning pricing feature lists to a common Y, `100vh` breaking on iOS Safari — it is a statement of
fact about how browsers and layouts behave, and is restated as such in §5.
