# Frontend rebuild — report

Branch `frontend-premium-ui`, 15 commits. Scope was `frontend/src`, plus
`frontend/DESIGN.md`, this file, `frontend/tailwind.config.ts`, `frontend/package.json`
and `frontend/public/fonts/`. Nothing under `backend/` was modified, no `.sqlite` file
was touched, and the backend test suite was not run.

The direction is in [DESIGN.md](DESIGN.md) and was written before the build.

---

## 1. Watermelon

**Tools used:** `catalog_summary`, `list_categories`, `list_catalog_entries`,
`get_inspiration`, `search`, `get_catalog_entry`, `get_component`.

The catalog holds 849 entries — 516 components, 131 animated components, 189 blocks,
12 dashboards, 1 template. **It has no chat or thread layout**, so the thread itself is
authored here; what the catalog gave was a token architecture and a component grammar.

### Shortlist

| Candidate | Why it could work | Verdict |
| --- | --- | --- |
| **Tallie Dashboard** | An expense **audit** workspace: exception tracking, transaction review, and a detail sheet built from key/value evidence. Tonally identical to "verified analysis with traceable SQL". Achromatic grey ramp with a *separate* semantic status layer; Geist + Geist Mono; border-and-faint-fill surfaces with no shadows; a dark mode that elevates by lightening rather than inverting. | **Chosen** |
| **Astrix Dashboard** | AI classification metrics, a **live pipeline** — the closest analogue to our SSE stepper — and a stream-review table. One accent plus a reserved success / info / destructive triad. | Runner-up |
| **Medesk Dashboard** | The same type stack (Geist / Geist Mono / Instrument Serif). | Rejected |

Medesk was rejected because it is a tile-grid-first operations dashboard whose layout
logic fights a reading thread, and because it depends on Recharts, which would duplicate
the existing lazy-loaded Plotly renderer.

### What I took

From **Tallie**: the token architecture — an achromatic ramp plus a *separate* semantic
status layer, both as CSS custom properties; surfaces as border + faint fill with **no
shadow at rest**; the metric anatomy of quiet label → large value → trend pair; the flat
key/value evidence grammar of its detail sheet (`OverviewCard` / `MatchField` /
`MatchBlock`), which maps directly onto `computed_metrics`, `verification` and
`query_result`; and dark mode as its own ramp rather than an inversion.

From **Astrix**: the single-accent discipline and the `bg-X/10 text-X` status-pill
grammar — a pale tint with dark ink of the same hue, never a saturated fill with white
text. Its layout was not used.

### What I deliberately changed

- Dropped `--source-oracle` `#5946f9` (violet) and `--source-concur` `#ff4fa3` (pink).
  Both are banned by the brief.
- Dropped Tallie's greyscale `--chart-1..5`. Charts need one validated data hue, so the
  chart palette is computed instead (§3).
- Replaced its Instrument Serif display titles with a single grotesk. An app screen is
  not editorial; the h1 stays at 24px and no figure reaches 48px.
- Replaced its fixed-height metric cards with one container divided by 1px rules, which
  is what the app-screen study actually measures on real product screens.
- Re-derived the whole status layer so every pair is contrast- and colour-blindness-
  validated in both themes. Tallie's values were not.

The result shares Tallie's structural logic and none of its surface.

---

## 2. Direction

`design-taste-frontend`, app-screen lane. Style dealt: **`achromatic-ledger`**, seed
**1651514127**, `--kind analytics`. **No redraws.**

> The chrome holds no colour at all; money and counts are set in ink, the one chart hue
> marks the screen's main data element, and the only other hue is a small signal where a
> figure changed.

Chosen over `framed-sheet` (its tinted L-frame is chrome that means nothing for a thread
and translates poorly to dark) and `accent-ladder` (pale tints doing area work would read
decorative on a product whose entire value is credibility).

**The face**, chosen from the sheet's three options: *figures in the mono face*. Not a
styling preference — the product's claim is that each number is traceable to the SQL that
produced it, so a figure on screen and the SQL in the evidence panel are set in the same
material. **This was revised during the build** (§6).

**The signature element:** *the provenance link* — every headline figure is a control
that opens the evidence panel at the SQL or engine that produced it.

**The screen's one question:** *"What is the answer, and can I trust it?"*

### Palette — computed, not chosen

Validated with `dataviz/scripts/validate_palette.js`. Every value is measured.

| | Light | Dark |
| --- | --- | --- |
| Categorical slots 1–4 | `#1d5fbf` `#b45309` `#0b6ea8` `#7a6a00` | `#3f86e0` `#cf7a1c` `#1c7fb4` `#9d8f2a` |
| Worst adjacent CVD ΔE | **20.6** | **21.4** |
| Normal-vision ΔE | **21.9** | **23.3** |
| Six checks | all PASS | all PASS |

Four slots is the cap: an exhaustive enumeration over the permitted hue pool found no
five-slot ordering that passes in both modes. A fifth series folds to "Other" in neutral
grey rather than inventing a hue. Reserved status colours were excluded from the
categorical pool so a status colour can never impersonate a series.

**Positive / negative**

| | Positive | Negative | CVD ΔE | WCAG |
| --- | --- | --- | --- | --- |
| Light | `#0f7a5a` | `#c4242a` | 8.7 | 5.31:1 / 5.78:1 |
| Dark | `#7fd8a6` | `#dc4f4a` | 18.9 | 11.04:1 / 4.73:1 |

The dark pair was re-derived. The conventional dark green/red (`#3fc07a` / `#e5566f`)
measures **ΔE 3.1 under deuteranopia** — a hard failure the light pair does not have, and
the clearest evidence that dark has to be selected rather than flipped. Separating on
lightness rather than hue restores it, because lightness survives CVD when the red-green
axis does not.

Colour is never the only channel: every change carries a sign, a direction glyph and the
colour together, and colour says good-or-bad rather than up-or-down.

---

## 3. What changed, file by file

### New

| File | What it is |
| --- | --- |
| `lib/format.ts` | Display-only formatting. The module that enforces "never compute": grouping, currency, abbreviation with the exact value retained, intervals, and change pairs that are presented but never derived. |
| `lib/cn.ts` | `clsx` + a `tailwind-merge` extended with this project's type scale. |
| `lib/useTheme.ts` | Theme read/write off `<html data-theme>`, with an observer so the chart can re-read its colours. |
| `components/AppShell.tsx` | Icon rail, product mark, named scope, theme toggle, phone bottom bar. |
| `components/ui/Stat.tsx` | The divided stat container, the three honest absent states, the provenance link, and `splitKpis`. |
| `components/ui/Markdown.tsx` | A small markdown renderer that builds React elements — never `dangerouslySetInnerHTML`. |
| `components/ui/SqlBlock.tsx` | Tokenising SQL highlighter with copy-to-clipboard. |
| `components/ui/Disclosure.tsx`, `Notice.tsx`, `CopyButton.tsx` | Accessible primitives. |
| `components/chat/AnswerView.tsx` | Composes one complete answer. |
| `components/chat/EvidencePanel.tsx` | The twelve evidence blocks. |
| `public/fonts/*.woff2` | Geist and Geist Mono, the five weights used. |

### Rebuilt

| File | What changed |
| --- | --- |
| `app/globals.css` | Token layer: two complete theme sets, `@font-face`, focus ring, scrollbars, caret, disclosure and step-arrival motion, reduced-motion. Replaces the glassmorphism utilities. |
| `tailwind.config.ts` | Every colour resolves to a custom property; the type scale and radii are tokens. No component can hard-code a hex. |
| `app/layout.tsx` | Theme bootstrap before paint, font preloads. |
| `app/page.tsx` | Tab bar → shell + destinations. The 10-card icon-topped pipeline grid is gone. |
| `types/api.ts` | The four dropped fields declared (§4); 21 × `z.any()` → `z.unknown()`. |
| `lib/api.ts` | SSE payloads validated instead of cast; all `any` removed. |
| `components/ChatInterface.tsx` | Live step model, scroll behaviour, empty state. |
| `components/chat/*` | All seven rebuilt. |
| `components/PlotlyChartRenderer.tsx` | Palette override, theme reactivity, table fallback, leak fix. |
| `components/SchemaReadinessSection.tsx`, `ObservabilityDashboard.tsx`, `HealthReadinessCard.tsx`, `Header.tsx` | Rebuilt on the token layer. |
| `components/setup/*` (5 files) | Behaviour preserved; tokens, type scale, states and structure migrated. |

### Removed

`components/chat/ArtifactCard.tsx` and `components/chat/AnalysisArtifacts.tsx`, both
superseded by `AnswerView` + `EvidencePanel`.

---

## 4. Bugs found and fixed

These were found by designing against live payloads and by looking at the render.

1. **The app was unreachable.** `/api/v1/setup/status` returns a `database` object with
   no `status` field, but `DatabaseStatusInfoSchema` required one, so `fetchSetupStatus`
   threw on every call, the guard saw no data, and the setup wizard gated the whole
   product even with `chat_ready: true`. The field is now optional.

2. **Four fields were being silently dropped.** `MultiAgentWorkflowResultSchema` did not
   declare `management_response`, `analytical_result`, `specialist_capability` or
   `linked_values`, and zod strips undeclared keys on parse — so the REST path discarded
   the entire structured answer. All four are declared, with `linked_values` typed to the
   shape the workflow actually sends (`user_mention` / `target_table` / `target_column` /
   `exact_db_value` / `confidence`), which differs from the retrieval endpoint's
   `LinkedValue`.

3. **"No rows matched" printed over a screen full of figures.** The specialist pipelines
   return `verification.empty_result: true` while also reporting `row_count: 10` and no
   `query_result`. An empty result now requires a query that actually ran and matched
   nothing.

4. **A listener leak in the chart.** The resize cleanup was returned from inside an async
   function, so it was never called and every chart leaked a listener.

5. **The status pill rendered at its heading's size.** `tailwind-merge` cannot tell a
   custom size token (`text-label`) from a custom colour token (`text-pill-neutral-ink`)
   and dropped one of them. `lib/cn.ts` declares the scale; the 11px step was renamed
   `micro` so it no longer shares a prefix with the pill colours.

6. **An invisible primary button in dark.** `bg-[var(--primary)] text-white` is white on
   white when `--primary` is white.

7. **A full Windows path where a filename belonged**, from two copies of a path split
   that had diverged. One shared `databaseName()` helper now.

8. **Two consecutive steps both read "Running it read-only."** The specialist pipelines
   reuse one step key and put the real stage in the message as a `STAGE:` prefix, which
   is now used for the label.

9. **A tick glyph that was an emoji**, failing the gate; now an icon.

10. **Sub-millisecond gaps printed as "0.00 ms"**, which reads as broken; now "under 1 ms".

11. **The dark negative pill measured 4.14:1**, under the 4.5:1 floor this design sets
    for itself. Now 6.96:1.

12. **The telemetry filter row overflowed the canvas at 390px.**

13. **A table's text ran 202px past its frame.** In the catalog's Example column,
    `max-w-[14rem] truncate` was applied to the `<td>` — but `max-width` on a table cell
    is advisory and the table layout algorithm overrides it, so a long sample value was
    clipped by the card border instead of ellipsised. The truncation now lives on a block
    inside the cell, with the full value on hover. Found by the impeccable detector and
    confirmed by measuring the painted text against the frame.

---

## 5. What I tested, and how

Everything below was run, not assumed.

- **`npm run build`** — passes. 0 type errors under `npx tsc --noEmit`. Plotly stays out
  of the shared bundle (First Load JS 87.4 kB shared; `/` at 158 kB).
- **Real payloads.** Two live responses captured from the running backend
  (`POST /api/v1/chat/query`) — a descriptive SQL run and a churn specialist run — and
  the answer surface was designed and checked against them in a temporary preview route,
  since removed.
- **End-to-end against the production build.** A script drove a real question through the
  live UI: clicked a starter question, photographed the streaming state, waited for the
  answer, opened the evidence panel. Confirmed each time: the stepper appears while
  streaming, the answer renders, the evidence opens, and the page text contains no `NaN`,
  no `undefined`, no `N/A` and no `[object Object]`.
- **The app-screen inspector on the production build** (`next build && next start`), at
  1440 / 768 / 390:

  | Screen | Result |
  | --- | --- |
  | Thread | 0 FAIL, 1 WARN |
  | Catalog | 0 FAIL, 0 WARN |
  | Telemetry | 0 FAIL, 1 WARN |
  | System | 0 FAIL, 1 WARN |

- **Source lint** (`lint.mjs --app`): 0 FAIL.
- **The impeccable design detector** against all four live pages: **no anti-patterns**.
  Its `overused-font` rule fires on Geist and Geist Mono; both were dealt by the
  `achromatic-ledger` sheet, so the narrowest possible suppression (two `ignore-value`
  entries, with reasons) is recorded in `.impeccable/config.json`. No rule or file is
  suppressed.
- **Both themes** photographed on every screen, and the churn answer photographed in
  light and dark at 1440 and at 390.
- **Horizontal overflow** measured at 390 and 1440: `scrollWidth === clientWidth` at both.
- **Palette validation** run per theme, including the re-derivation of the dark polarity
  pair and the enumeration that established the four-slot cap.

### Remaining warnings, and why I am leaving them

- **`hero-void` on Thread (38%).** The empty-thread state. Its content is complete —
  title, four starter questions, the connected scope, the composer — and the remaining
  space is below the composer. It is the screen's one rest.
- **`below-fold` on Telemetry (4 of 42 blocks).** The 42 blocks are collapsed run rows in
  a list. A list screen's rows are below the fold by nature; the KPI strip and the stage
  breakdown, which answer the screen's question, are both above it.
- **`tiny-text` on System (48% under 13px).** The System screen is key/value rows, so
  12px labels outnumber 14px values. 12px is the study's own median for labels.
- **`mono` (38×) in the source lint.** The deliberate style decision, which the
  app-screen rules explicitly permit ("Monospace … or every figure, as one style's
  decision"), scoped in §6 below.

---

## 6. Decisions I made on your behalf

1. **Mono figures were scoped back, mid-build.** The dealt face was "every figure in
   Geist Mono". At 34px, Geist Mono gives a comma a full monospace advance, so `20,000`
   rendered as `20 , 000` — the most important element on the screen, reading as broken.
   Mono now holds everywhere alignment is the point (tables, key/value rows, SQL, IDs,
   timings) and display figures take Geist with `tabular-nums`, which still aligns digit
   for digit. Legibility of the lead figure outranks the flourish.

2. **No count-up on figures.** The brief asked for "a number settling". A count-up renders
   intermediate values the API never returned, which breaks the brief's own first rule on
   the one product where it matters most. Figures appear at their final value; a figure
   replacing another gets a 150ms opacity crossfade. This is the one brief item I did not
   implement literally, and it is recorded in DESIGN.md §8.

3. **The section identity device changed twice.** It began as a label above the headline —
   which the impeccable craft floor bans outright as an eyebrow — and is now a margin
   heading in its own lane: the section name is the real `h3`, the backend's headline is
   the statement beneath it.

4. **Currency symbols are attached conservatively.** `$` and `USD` are applied when a
   metric key ends in `_usd` or matches an explicit money pattern (`revenue`, `spend`,
   `exposure`, `amount`). Everything else renders as a bare number rather than inventing
   a unit. The patterns are in `lib/format.ts` and are worth a review against your metric
   catalogue.

5. **Good-direction inference for colour.** A change is coloured by whether it is good or
   bad, which needs to know each metric's good direction. Two keyword lists in
   `format.ts` carry this; anything unmatched renders its change in **grey** rather than
   guessing. Also worth a review.

6. **The icon rail** replaced the labelled tab bar: four destinations and a thread that
   wants the width is exactly the case a rail suits.

7. **Setup screens were migrated, not rewritten.** Their mutations, validation and routing
   are untouched; they took the design system. The deeper multi-step wizard flow would
   benefit from a proper redesign, but rewriting working connection logic was a larger
   risk than the brief warranted.

8. **I did not configure ESLint.** `npx next lint` opens an interactive setup prompt in
   this project; `npm run build` does not lint without it. Typechecking is enforced
   instead, and it is clean.

9. **Autonomy.** The impeccable skill asks to probe with a structured question before
   inferring. You said you were away and asked me not to stop, so I inferred from the
   brief and recorded each decision here instead.

---

## 7. Known issues and things still not right

**Backend data problems the interface now surfaces rather than hides.** None are mine to
fix — `backend/` was out of scope — but they are visible in the product:

1. **Successful steps are reported as failed.** On a churn run, `trace_steps` returns
   `status: "failed"` with `duration_ms: 0` for two steps whose messages describe
   successful work, on a run that succeeded. The interface reports the backend's status
   faithfully and now prints the word "failed" alongside the mark, so the state is
   unambiguous rather than a bare red glyph — but the underlying status is wrong.

2. **`verification.empty_result` contradicts `row_count`.** It arrives `true` alongside
   `row_count: 10`. The interface no longer trusts it alone (§4.3).

3. **A mislabelled KPI.** On "total revenue by month in 2025", `what.kpis` carries
   `total_revenue: 64830335.73`, which is January's figure, not the year's total. The
   interface renders the backend's key and value faithfully, so the screen reads "Total
   revenue $64.8M" for a figure that is one month. **This is the most user-visible of the
   three** and worth fixing in the composer.

4. **`plan.steps` is always `pending` with `duration_ms: 0`**, even on a successful run.
   It is labelled as the planned DAG and separated from `trace_steps`, which is the
   execution record.

**Frontend limitations:**

5. **Session history restores questions only.** `GET /memory/sessions/{id}` returns turns,
   not stored result payloads, so reopening a past thread shows the questions asked
   without their answers. Rendering past answers needs a backend endpoint that returns
   the stored workflow result.

6. **The scenario and impact sections are rendered but unverified against live data.** I
   could not get the backend to emit `scenario_section` or `impact_section` in the runs I
   drove, so those two branches are built from the schema and the other four sections'
   shape, not observed against a real payload.

7. **`model_information` and `validation_results` were empty in every payload I saw.**
   They are not rendered. If they populate, they belong in the evidence panel's Method
   block.

8. **No automated test suite for the frontend.** `npm test` is still the placeholder echo
   it was before. The verification above was manual and script-driven.

9. **The chart is Plotly's interaction model.** Hover and tooltips are Plotly's, restyled
   via `hoverlabel` but not rebuilt; the table view is the accessible route to the same
   numbers.

---

## 8. Running it

```bash
# backend (from the repository root)
python -m uvicorn backend.app.main:app --port 8001

# frontend
cd frontend
npm install
npm run dev     # http://localhost:3001
npm run build && npm run start   # production
```

---

# Round two — colour, voice, choreography and the demo surface

The first build was correct and too quiet. This round gives it colour, a business voice,
motion that explains, depth, and a presentation surface.

## A. The hard rule: no purple, violet, indigo, magenta or pink

Enforced, not asserted. A hue audit parses **every hex literal in `frontend/src`** — 89 of them
across 50 files — converts each to HSL and fails on anything in hue **248–352** at meaningful
saturation. It prints PASS on the current tree and was re-run after every palette change. The one
source of a banned hue is the backend's own `plotly_layout`, which ships `#6366f1`; the chart
renderer overrides it before Plotly ever sees it.

## B. Colour, depth and type

**Warm neutrals.** Light runs `#faf9f7` → `#1a1814`; dark is warm charcoal `#121110` → `#f7f5f2`.
Never `#000`, never `#fff` as a ground. Surfaces separate by tone *and* elevation, not only a
1px rule.

**One accent — deep teal** (`#0b6b63` light, `#5ec9bc` dark), with six named jobs and nowhere
else: active rail item, focus ring, links, selected state, the live indicator during streaming,
and the chart's main series. Chosen over champagne gold and warm amber because against warm
neutrals a warm accent is monotone — teal gives the ramp something to be warm against.

**Semantic colour for data — sage and terracotta**, as asked:

| | Positive | Negative | CVD ΔE | WCAG |
| --- | --- | --- | --- | --- |
| Light | `#417751` | `#8a3320` | **8.1** (above the ≥8 target) | 5.27:1 / 8.16:1 |
| Dark | `#a4d6b6` | `#d98264` | **14.3** | 10.85:1 / 6.18:1 |

**Chart series re-derived** with the accent's hue family leading, so the main data element and
the interface accent read as one decision: light `#169488 #1d5fbf #b45309 #0b6ea8` (CVD ΔE 19.1),
dark `#2fa89b #c9803a #3f86e0 #9d8f2a` (ΔE 12.8). All six checks pass in both modes.

**Three tonal planes** with warm-tinted elevation — offset and blur, never a glow. The
conversation sits back, stat strips and charts sit forward, the evidence panel and presentation
surface float above both.

**Type contrast.** A 44px/700 display step for the focal figure, 700 on lead headlines, 600 on
titles, 500 on figures, 400 on body. The page now has a focal point.

## C. The wording

- The surface is **"Ask the data"**; the rail reads Ask / Data / Activity / System.
- **A headline is a finding, never a row count.** "Query returned 12 rows." is replaced by the
  narrative's first real sentence — now "Monthly revenue ranged from $44.6M (Feb) to $85.5M
  (Jul)." — or, when the narrative is entirely tabular, by a description of the result's shape
  built only from values the backend sent. **No total is ever stated that the backend did not
  compute.**
- **No raw key/value pair reaches the screen.** `month: 2025-01, total_revenue: 64830335.73`
  renders as `January 2025 · $64,830,335.73` — every key humanised, every period spelled out,
  every number formatted, currency given its symbol, inline markdown stripped.

All of this lives in `lib/narrative.ts` and changes no value.

## D. A series is a series

`isSeriesResult` detects many rows of one measure; the **chart then leads**, and the answer is no
longer a single tile standing in for twelve months. A KPI whose value matches exactly one row is
labelled with that row's own scope — the `$64.8M` tile now reads **January 2025** instead of
implying a year's total.

**The chart renders.** It was in fact rendering, but three things made it look broken, all now
fixed: a grey band (the loading skeleton sitting *behind* the plot during a one-frame race),
half-year ticks like `2,022.5` (the backend sends categories as strings and Plotly inferred a
linear scale), and a duplicated in-plot title.

## E. Opening view, choreography, depth, presentation mode

**Opening view** — warehouse figures from `/schema/status`, answered-question counts and typical
latency from `/ops/metrics`, the connected database from `/ready`, and one real query supplying
an opening chart and its own figures. Suggestion cards with pointer-tracked tilt. Nothing
invented.

**Choreography** — figures count up; line charts wipe in from the left so the series traces; bars
rise from the baseline; sections arrive 55ms apart in reading order; the stepper advances per SSE
event with the running step pulsing in the accent and completed steps settling with their
duration; the evidence panel names the figure that opened it.

**Depth** — layered elevation, a few degrees of pointer-tracked tilt with a highlight that
follows the pointer, and a shared element between a tile and the evidence panel. No WebGL, no
spinning geometry, no particle fields.

**Presentation mode** — full-screen keynote: the question, each section in reading order, then
the evidence. Arrow keys, space, Home/End, Escape; a progress bar; one figure or chart per slide;
slides enter from the direction of travel. Focus trapped and restored, body scroll locked.

**Craft** — skeletons shaped like what loads, the question box focused on load (desktop only),
Cmd/Ctrl+K to return to it with the shortcut shown, copy buttons that confirm, hover states
throughout, smooth height on expand.

## F. What I tested this round

- `npm run build` passes; `tsc --noEmit` reports **0 errors**; no `any` in the codebase.
- **Hue audit: PASS** over 89 hex literals in 50 files.
- **End-to-end on the production build**, light and dark, at 1440 and 390: ask a question from
  the opening view, watch it stream, read the answer, open the evidence, enter presentation mode
  and advance a slide. Every run asserted the rendered text contains no `NaN`, no `undefined`,
  no `N/A`, no `[object Object]`, **no raw `key: value` pair**, **no "Query returned N rows"**,
  and no long float; and that `scrollWidth === clientWidth`, so the page never scrolls sideways.
- **impeccable detector: no anti-patterns** on all four live screens.
- **design-taste inspector (app rules), production build: 0 FAIL** on all four screens.
- **Source lint: 0 FAIL.**
- Palette validation re-run per mode for every new value, including the enumeration that chose
  the series ordering.

## G. Decisions I made on your behalf

1. **The count-up now exists, with three conditions.** I argued against it last round; you asked
   twice, so it is built — and made safe: the element renders its true value first (so if script
   never runs, the right number is on screen), the last frame is the API's own formatted string
   assigned directly rather than interpolated, an interrupted count restores the real figure, and
   intermediate frames carry the target's own precision so a count of 56 never flickers through
   36.266.
2. **`achromatic-ledger`'s colour move is superseded, deliberately.** Its composition, density
   and figure discipline are kept; its "no colour in the chrome at all" rule is replaced by your
   brief. Recorded in DESIGN.md §1.
3. **Teal over champagne gold**, for the reason in §B.
4. **The opening query is cached for 15 minutes** rather than re-run on every visit, so the
   landing view does not spend an LLM call per page load. It retries once.
5. **Two narrow suppressions, both documented in place:** the pointer highlight is a
   `radial-gradient` because light falling off from a point has no flat-colour equivalent
   (marked `taste-skill-ignore` on the line, under 12% alpha, hover and fine pointers only); and
   the inspector's `palette-cream` warning is allowed because it reads my warm *text* `#f7f5f2`
   as a cream *background* when the measured ground is `#121110` — a mis-attribution, and warm
   neutrals are your explicit brief.

## H. Still not right

1. **`/review-animations` could not be run.** It is reserved for explicit user invocation,
   refuses the Skill tool, and instructs that its workflow must not be replicated by other means.
   **Please run `/review-animations` yourself.** I ran `animation-performance` instead, which
   found a real defect — see below.
2. **The count-up was driving React state per frame**: four figures meant 240 renders a second,
   and the render alone blew the frame budget. Fixed to direct `textContent` writes on a ref.
   Worth knowing it existed.
3. **Frame rate is verified from code, not from a device recording.** The audit confirms every
   animation is on transform/opacity/clip-path, off the main thread where it matters, with no
   animated blur and no `transition: all`. It has **not** been profiled on a mid-range phone, and
   that is the only way to be sure.
4. **The opening query can fail.** It is one real LLM-backed call; on a slow or erroring backend
   the landing view falls back to warehouse figures and suggestions with no chart. The path is
   handled, but the demo's opening chart is not guaranteed.
5. **The backend issues from round one are unchanged** and still visible: successful trace steps
   reported as `failed`, `verification.empty_result` contradicting `row_count`, and a KPI keyed
   `total_revenue` that holds one month's figure. The interface now labels that last one with its
   real scope ("January 2025") rather than repeating the backend's implication, but the **key** is
   still the backend's.
6. **Session history still restores questions only** — no endpoint returns stored result payloads.
7. **Scenario and impact sections remain unverified against live data**; I still could not get the
   backend to emit them.
8. **No automated frontend test suite.** Verification is script-driven and manual.

---

# Round three — champagne gold, WebGL, and the demo surface

## A. What I built this round

**Champagne gold replaces teal everywhere.** Not a find-and-replace: the whole ramp was
re-derived and re-measured.

| | Accent | Muted gold | Hairline |
| --- | --- | --- | --- |
| Dark | `#e3c178` — 10.26:1 on surface, 9.29:1 on raised | `#a88449` | `#4a3d22` |
| Light | `#7a5c12` — 6.24:1 on white, 5.53:1 on raised | `#8a6a2a` | `#d8c79b` |

Gold is on the key figures, the primary chart series, links, focus rings, the active rail item,
selected states, the live indicator, and the one hairline that matters — the rule under a lead
figure.

**Dark is now the default theme.** Gold reads as light falling on dark material; on white it is
either illegible or no longer gold. Light mode takes the deepened step of the same hue family
rather than failing contrast — champagne cannot carry text at 4.5:1 on white, and the rule that
every ink tier clears 4.5:1 is not negotiable for the sake of a hue.

**Ground deepened and warmed**: `#0f0e0c` dark, `#faf8f4` light. Never `#000`.

**Chart series revalidated** with gold leading: light `#9a7b1e #1d5fbf #8c2f10 #0b6ea8`
(CVD ΔE 21.1), dark `#ab8830 #3f86e0 #b8732f #4a90d8` (ΔE 23.4). All six checks pass in both
modes. A **lone series takes the accent gold itself** — with one mark there is no adjacency to
separate, so the categorical lightness band does not bind and the drama wins — with a shallow
fill of its own colour beneath it.

**The WebGL hero.** three.js, lazy-loaded and never server-rendered: the shared bundle stays at
**87.5 kB** and nothing blocks first paint. A 2,600-point field drifts in loose formation and
resolves over 2.6s into **the real orders-by-year curve the opening query returned**. A faceted
solid rotates in the same gold light with lit edges. The whole scene follows the pointer with an
eased lag. The points are placed from API values exactly as a chart's marks are; the scene shows
no number of its own.

It is a split — words left, scene right — so legibility never depends on a scrim over a canvas.

**Where 3D is refused**, and gets the same composition without the canvas: `prefers-reduced-motion`,
a coarse pointer, fewer than four logical cores, a viewport under 1024px, or no WebGL.

**Frame budget, enforced inside the scene**: `devicePixelRatio` capped at 1.75; the loop stops
entirely when the canvas leaves the viewport or the tab is hidden and resumes where it left off;
one `BufferGeometry` updated in place, so there is no per-frame allocation.

**Depth elsewhere**: stat tiles take pointer-tracked perspective with a specular highlight that
moves with the cursor; the evidence panel hinges open about its top edge; a chart's grid and
series separate by a few pixels on pointer move. All `transform` on the element itself,
rAF-batched, disabled under reduced motion.

**No explicit `any` anywhere.** Three `onError: (err: any)` handlers in the setup forms were the
last ones; `lib/errors.ts` narrows instead.

## B. What already existed before this round

Being precise, because the brief listed things that were already built:

- The count-up, chart draw-in (line wipe, bar rise), 55ms staggered section arrival, the
  streaming stepper with per-step durations, and the shared-element evidence reveal — round two.
- Presentation mode — round two. This round it inherited gold; the mechanics are unchanged.
- The full backend-field coverage, the evidence panel, all the designed states, the figure
  rules (scope labels, uncertainty beside the number, three honest absent states), and
  chart-first for series — rounds one and two.
- Skeletons shaped like their content, Cmd/Ctrl+K, copy confirmation, hover states — round two.

What this round added to those: gold, the 3D layer, and the fixes in §D.

## C. What I tested

Everything below was run, not assumed.

- **`npm run build` passes.** `tsc --noEmit`: **0 errors**. **0 explicit `any`** (grepped).
- **Hue audit: PASS** over 101 hex literals in 53 files — nothing in hue 248–352 at meaningful
  saturation.
- **Bundle:** shared chunk 87.5 kB with three.js installed, confirming the hero is fully lazy.
- **WebGL verified running**, not just mounted: canvas present with a live drawing-buffer
  (635×423 at dpr cap).
- **Reduced motion verified**: with `prefers-reduced-motion` forced, `canvas mounted: false` and
  the hero's composition and headline still render — the fallback is real.
- **Every backend field checked on screen** by driving the churn question (richest payload) and
  the revenue question, then opening the evidence panel: 20/21 markers present on churn, and the
  one absent (`selected_tables`) is absent because that payload sends it empty — it renders on
  the revenue run. Together the two runs confirm every field renders when sent and is omitted
  when not.
- **End-to-end, dark and light, 1440 and 390**: ask from the landing view, watch it stream, read
  the answer, open the evidence, enter presentation mode, advance a slide. Every run asserted
  no `NaN`, `undefined`, `N/A`, `[object Object]`, no raw `key: value`, no "Query returned N
  rows", no long float, and `scrollWidth === clientWidth`.
- **impeccable detector: no anti-patterns** on all four live screens.
- **design-taste inspector (app rules), production build: 0 FAIL** on all four screens.
- **Source lint: 0 FAIL.**
- Every palette value validated per mode with the dataviz validator, including the enumerations
  that chose both series orderings.

## D. Defects found and fixed this round

1. **A solid gold block under every line chart.** Plotly writes colours into SVG `fill`
   attributes, where `color-mix()` does not resolve and falls back to opaque — so a 16% wash
   rendered as a solid slab. `readTokenRgba()` now produces a real `rgba()` string.
2. **The hero was never seen.** Autofocusing the composer on load scrolled straight past it;
   focus now uses `preventScroll`.
3. **The faceted solid rendered as a dark mass.** `MeshPhysicalMaterial` with `transmission`
   needs an environment map to refract anything; without one there is nothing to refract. It is
   metal with flat shading and lit edges now, which actually catches gold.
4. **The hero headline was a sentence**, wrapping to four lines at every width. "Every figure,
   proven." is three words and sets on two lines at 1440, 768 and 390.
5. **Three explicit `any`s** in the setup forms.

## E. Decisions I made on your behalf

1. **Dark is the default theme**, for the reason in §A. Light remains fully correct and is one
   click away.
2. **Light mode uses a deepened gold**, not champagne. Champagne on white measures about 1.9:1;
   shipping it would have broken WCAG AA on the product's own accent.
3. **A lone chart series uses the accent gold rather than the validated ramp slot** — justified
   because the lightness band exists to separate adjacent marks, and one series has no adjacent
   mark.
4. **The solid is metal, not glass.** Real refraction needs an environment map, which would mean
   shipping an HDRI or building a PMREM probe for one decorative element. The faceted metal
   reads as the same material at none of the cost.
5. **The hero gate is 1024px, not 768px** — matching the breakpoint at which the canvas column
   actually exists.

## F. Still not right

1. **`/review-animations` could not be run — again.** It refuses the Skill tool
   (`disable-model-invocation`) and explicitly instructs that its workflow must not be
   replicated by other means. **Please run `/review-animations` yourself.** I ran
   `animation-performance` instead across the previous and current rounds.
2. **Frame rate is verified from code and from a desktop browser, not from a device recording.**
   The WebGL loop's caps are real and I confirmed the canvas renders and that reduced motion
   skips it, but I have **not** profiled this on a mid-range phone — and the hero does not run
   on phones by design, so the thing most likely to cost frames is never on the device most
   likely to drop them.
3. **The opening query can still fail.** It is one real LLM-backed call; on a slow or erroring
   backend the landing view falls back to warehouse figures and suggestions, and the hero then
   has no series to resolve into, so it does not mount. The demo's opening scene is not
   guaranteed.
4. **The backend data problems are unchanged** and still visible: successful trace steps
   reported as `failed`, `verification.empty_result` contradicting `row_count`, and a KPI keyed
   `total_revenue` holding one month's figure. The interface labels that last one with its real
   scope rather than repeating the implication, but the key is the backend's.
5. **Session history restores questions only** — no endpoint returns stored result payloads.
6. **Scenario and impact sections remain unverified against live data.** I could not get the
   backend to emit them in any run across three rounds.
7. **No automated frontend test suite.** All verification is script-driven and manual.
8. **The `palette-cream` inspector warning is allowed, not fixed** — it reads the warm text
   `#f7f4ee` as a cream *background* when the measured ground is `#0f0e0c`. A mis-attribution,
   and warm neutrals are the brief.
