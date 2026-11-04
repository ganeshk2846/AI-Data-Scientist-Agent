# Design direction — AI for BI

The interface for a conversational data-science agent. A business user asks a question in
plain language and gets back **verified analysis**: a narrative, headline figures, a chart, a
data table, and the SQL that produced every number.

This document is the contract. It was written before the build, and the build follows it.

---

## 0. The one rule that outranks every other

**The frontend never computes, rounds, re-aggregates or infers a number.**

Every figure on screen arrives from the API and is traceable to the SQL or engine that
produced it. Formatting is presentation only — grouping digits, attaching a currency symbol,
abbreviating a magnitude. The underlying value is never altered, and the exact unrounded value
is always one hover or one evidence-panel row away.

Consequences that shaped the design:

- Figures **count up** to their value on arrival (requested explicitly). Three conditions make
  that safe: the element renders its true value first, so the count only mutates text that is
  already correct; the last frame is the API's own formatted string, assigned directly rather
  than interpolated; and an interrupted count restores the real figure. Intermediate frames
  carry the target's own precision, so a count of 56 never flickers through 36.266. See §8.
- No delta, percentage, total or trend is rendered unless the API supplied **both sides** of it.
- No arrow is drawn that was not derived from an API-supplied direction.
- Zero, null and "not evaluated" are three different states with three different renderings.
  None of them is `N/A`, `undefined`, `NaN`, or an empty tile.

---

## 1. Where the direction came from

### Watermelon

Reviewed the catalog (849 entries: 516 components, 131 animated, 189 blocks, 12 dashboards,
1 template). **There is no chat or thread layout in it** — the thread is authored here.

Shortlist and verdict:

| Candidate | Why it could work | Verdict |
| --- | --- | --- |
| **Tallie Dashboard** (`dashboards/tallie-dashboard`) | An expense-**audit** workspace: exception tracking, transaction review, a detail sheet of key/value evidence. Tonally identical to "verified analysis with traceable SQL". Achromatic grey ramp with a *separate* semantic status layer; Geist + Geist Mono; border-and-faint-fill surfaces with no shadows; a genuinely considered dark mode that elevates by lightening rather than inverting. | **Chosen** |
| **Astrix Dashboard** (`dashboards/astrix-dashboard`) | AI classification metrics, a **live pipeline** (closest analogue to our SSE stepper) and a stream review table. Single accent plus a reserved `success` / `info` / `destructive` triad. | Runner-up — colour discipline and the `bg-X/10 text-X` status-pill grammar taken, layout not |
| **Medesk Dashboard** (`dashboards/medesk-dashboard`) | Same type stack (Geist / Geist Mono / Instrument Serif). | Rejected — tile-grid-first ops layout fights a chat thread, and its Recharts dependency conflicts with our lazy Plotly renderer |

**Taken from Tallie:** the token architecture (an achromatic ramp plus a *separate* semantic
status layer as its own custom properties); surfaces as border + faint fill with **no shadow at
rest**; the metric-tile anatomy of quiet label → large value → trend pair; the flat key/value
evidence grammar of its detail sheet (`OverviewCard` / `MatchField` / `MatchBlock`), which maps
directly onto `computed_metrics`, `verification` and `query_result`; dark mode as its own ramp.

**Deliberately changed:**

- Dropped `--source-oracle` `#5946f9` (violet) and `--source-concur` `#ff4fa3` (pink) — banned here.
- Dropped its greyscale `--chart-1..5`; charts need one validated data hue (§3).
- Replaced Instrument Serif display titles with a single grotesk — app screens are not editorial.
- Replaced its fixed-height metric tiles with one divided container (§5), per the app-screen study.
- Its status layer is re-derived so every pair is contrast- and CVD-validated (§3).

### design-taste-frontend

App-screen lane. Style dealt: **`achromatic-ledger`**, seed **1651514127** (`--kind analytics`).
No redraws.

> *The chrome holds no colour at all; money and counts are set in ink, the one chart hue marks
> the screen's main data element, and the only other hue is a small signal where a figure changed.*

Chosen over `framed-sheet` (its tinted L-frame adds chrome that means nothing for a thread, and
translates poorly to dark) and `accent-ladder` (pale tints doing area work would read decorative
on a product whose entire value is credibility).

**The face** — the sheet offers three; chosen: *every figure in the mono face, as the style's
decision.* This is not a styling preference. The product's claim is that each number is traceable
to the SQL that produced it, so a figure on screen and the SQL in the evidence panel are set in
**the same material**. The typographic link *is* the argument.

> **Revised during the build.** At 34px Geist Mono gives a comma a full monospace advance, so
> `20,000` rendered as `20 , 000` — the most important element on the screen, reading as broken.
> Mono now holds wherever alignment is the point (tables, key/value rows, SQL, IDs, timings) and
> display figures take Geist with `tabular-nums`, which still aligns digit for digit. See §2.

**The signature element** — *the provenance link*: every headline figure is a control that opens
the evidence panel at the SQL or engine that produced it.

**The screen's one question:** *"What is the answer, and can I trust it?"*
The biggest thing on screen is the answer's headline figure; the second is the evidence that
backs it.

> **Superseded on colour.** `achromatic-ledger`'s move is "no colour in the chrome at all". Held
> literally it produced a screen that read as unfinished rather than restrained. The composition,
> density and figure discipline of the style are kept; the colour rule is replaced by §3 — warm
> neutrals, champagne gold as the one accent, and semantic colour reserved for data. The
> brief wins over the dealt move.

---

## 2. Typeface and type scale

Two faces, each with one job.

- **Geist** — everything that is words.
- **Geist Mono** — figures in columns, identifiers, and SQL: wherever digits must line up
  with the digits above them. Display figures take Geist with `tabular-nums` (see the note below).

Both self-hosted from `/public/fonts` with `@font-face` under their real family names, so the
dealt face actually loads and reports as "Geist" rather than a build hash. Only the five weights
the interface uses are shipped; the two regular faces are preloaded.
`font-variant-numeric: tabular-nums` on every figure.

| Role | Size | Weight | Leading | Notes |
| --- | --- | --- | --- | --- |
| Screen title (`h1`) | 24px | 600 | 1.25 | A noun. Never a greeting. 20px on phone. |
| Answer headline | 20px | 600 | 1.3 | The `management_response` section headline |
| Display figure | 44px | 700 | 0.98 | Geist, tabular. The focal point: one per answer. |
| Lead figure | 34px | 500 | 1.0 | Geist, tabular figures. |
| Sibling figure | 22px | 500 | 1.1 | Geist, tabular figures. Never larger than the lead. |
| Section title | 16px | 600 | 1.35 | Card and panel headers |
| Body | 14px | 400 | 1.55 | Narrative, table cells, nav |
| Label / meta | 12px | 400 | 1.4 | Quiet labels above figures, axis ticks, scope lines |
| Pill | 11px | 500 | 1 | Floor. Nothing on screen is smaller. |

Five working sizes plus three figure sizes. Sentence case throughout, with one exception: the
section name in the margin lane is tracked small caps, which is how a margin heading reads as
navigation rather than as content.

Weight carries the hierarchy as much as size: 700 on the display figure and the lead headline,
600 on titles and section headings, 500 on figures and controls, 400 on everything else.

Ceiling: the title never exceeds 24px and **no figure reaches 48px** — except in presentation
mode, which is a keynote surface where large type is the point (`text-slide`, clamped
2.5–5.5rem).

---

## 3. Colour

### Proportion

Warm near-black ground, **champagne gold** as the one accent, and semantic colour reserved for
data. Gold appears on the key figures, the primary chart series, links, focus rings, the active
rail item, selected states, the live indicator during streaming, and the one hairline that
matters — the rule under a lead figure. Everything else in the chrome is neutral.

The primary action stays near-black (inverted on dark) so the accent never becomes button paint.

### Warm neutral ramps

Light runs `#faf9f7` → `#1a1814`; dark runs `#121110` → `#f7f5f2`. **Never `#000` or `#fff` as a
ground.** Both ramps carry a trace of warmth so the screen reads as paper and ink rather than as
a terminal.

| | Light | Dark |
| --- | --- | --- |
| Ground | `#faf9f7` | `#121110` |
| Surface | `#ffffff` | `#1a1816` |
| Raised | `#f3f1ed` | `#232120` |
| Active | `#ebe8e3` | `#2b2826` |
| Border | `#e4e0d9` | `#2e2b28` |
| Text | `#1a1814` | `#f7f5f2` |
| Muted | `#635d54` (5.77:1) | `#b5ada2` |
| Faint | `#6f695f` (4.82:1) | `#9a9288` |

Every ink tier is measured against **the darkest surface it can land on**, not against white.

### The accent — champagne gold

| | Accent | Soft tint | Edge | Muted gold | Hairline |
| --- | --- | --- | --- | --- | --- |
| Light | `#7a5c12` (6.24:1 white, 5.53:1 raised) | `#f5edd9` | `#dcc894` | `#8a6a2a` | `#d8c79b` |
| Dark | `#e3c178` (10.26:1 surface, 9.29:1 raised) | `#2a2113` | `#574a2c` | `#a88449` | `#4a3d22` |

**Dark is the default theme.** Gold reads as light falling on dark material; on white it is
either illegible or no longer gold. Light mode therefore takes the deepened step of the same
hue family rather than failing contrast — champagne cannot carry text at 4.5:1 on white, and
the rule that every ink tier clears 4.5:1 is not negotiable for the sake of a hue.

### Semantic colour for data — sage and terracotta

| | Positive (sage) | Negative (terracotta) | CVD ΔE | WCAG |
| --- | --- | --- | --- | --- |
| Light | `#417751` | `#8a3320` | **8.1** | 5.27:1 / 8.16:1 |
| Dark | `#a4d6b6` | `#d98264` | **14.3** | 10.85:1 / 6.18:1 |

Used on deltas, trend indicators and chart series. Colour is never the only channel: every
change carries a sign, a direction glyph and the colour together, and colour says **good or bad**,
never up or down. A zero or undefined change is grey.

### Chart series

| | Slots 1–4 | Worst adjacent CVD ΔE | Normal-vision ΔE |
| --- | --- | --- | --- |
| Light | `#9a7b1e` `#1d5fbf` `#8c2f10` `#0b6ea8` | **21.1** | 26.0 |
| Dark | `#ab8830` `#3f86e0` `#b8732f` `#4a90d8` | **23.4** | 24.9 |

Slot 1 is the accent's own hue family. **A lone series takes the accent gold itself**
(`--chart-primary`): with one mark there is no adjacency to separate, so the categorical
lightness band does not bind and the drama wins. Several series take the four-slot ramp above.
Four slots is the cap; a fifth folds to neutral grey. Status colours are excluded from the
categorical pool so a status colour can never impersonate a series.

A lone series also carries a shallow fill of its own colour beneath it, so the curve sits on a
surface rather than floating on the grid. The fill is written as `rgba()`, not `color-mix()`:
Plotly puts colours straight into SVG `fill` attributes, where `color-mix()` does not resolve
and silently falls back to opaque.

### Banned, without exception

**No purple, violet, indigo, magenta or pink** — not as an accent, in charts, in gradients, in
hover or focus states, or in badges. The band is hue **248–352** at any meaningful saturation.
`scripts` in the report run a hue audit over every hex literal in `frontend/src`; it must print
PASS before any commit. This also covers the backend's own `plotly_layout`, which ships
`#6366f1`; the renderer overrides it.

### Depth

Three tonal planes plus real elevation: the conversation sits back on the ground, stat strips,
charts and the stepper sit forward on `--shadow-raised`, and the evidence panel and presentation
surface float above both on `--shadow-float`. Shadows carry an **offset and a blur**, warm-tinted
to the ramp. No glow, no gradient blob, no glass.

## 4. Space, frame and density

4px base. **One gap value — 12px — horizontally and vertically.**

| Token | Value |
| --- | --- |
| Canvas gutter | 24px desktop · 16px phone |
| Thread column | max 1200px beside the rail |
| Prose measure | 34rem (~72 characters) |
| Card padding | 20px · 16px phone |
| Gap | 12px |
| Section gap | 32px |
| Row height | 44px (table), 36px (key/value) |
| Control height | 36px · 32px in filter rows |
| Radius | card 8px · control 6px · chip 4px |

Density is **sparse**: a thread is read, not scanned.

The thread is a measured column, not full-bleed. Running text — narrative, disclaimers,
findings, next steps — is bounded by `--prose-measure` (34rem, about 72 characters at 14px).
Tables, charts and stat strips break out to the full canvas width because they are measured in
columns, not characters.

**One left edge.** Title, section headings, narrative, figure labels and table identity column
all start on the same line. Right-aligned figures in a card share one right edge.

**Cards that share a row share a bottom edge.** Where content cannot balance, the shorter card
keeps its own height (`align-items:start`) rather than stretching over a void.

---

## 5. Headline figures

The most considered thing on the screen.

**Anatomy** — one container split by 1px dividers into equal columns. Not one card per figure,
no icon in a tinted circle, no sparkline, no tinted tile.

```
quiet label            12px, --muted, sentence case
VALUE                  34px mono tabular, --text   (siblings 22px)
± interval             12px mono, --muted          (when the API supplied one)
scope / period         12px, --faint               ("2026-11 to 2026-12", "JP-Kanto")
[▲ +12.4%  vs prior 30 days]   12px, polarity colour + glyph + sign
```

**Formatting** (display only):

- Thousands separators always.
- USD fields (`total_amount_usd`, `revenue_at_risk`, `revenue_delta_usd`, …) carry the symbol
  and the code: `$36.8M USD`.
- Large magnitudes abbreviate — `$36.8M`, `150,000` — and the **exact unrounded value** is in
  the `title` attribute and in full in the evidence table.
- Percentages keep exactly the precision the API gave. No more, no less.
- Counts get no decimals.

**Uncertainty sits beside the number, never below the fold.** `confidence_interval_95`,
prediction intervals, `z_score`, `confidence_score` and MAPE render adjacent to the figure they
qualify. A forecast always shows its interval — a forecast without one is a lie, and not telling
them is this product's whole claim.

**Heterogeneous KPI values.** Measured against live payloads, `kpis` is *not* uniformly numeric:

- `what.kpis` → `{total_revenue: 64830335.73}` — scalar
- `so_what.kpis` → `{priority_segment: "At Risk", priority_exposure: 345890928.3}` — mixed string + number
- `what_next.kpis` → `{logistic_regression: {roc_auc: 0.5111, …}, random_forest: {…}}` — **nested objects**

So the renderer handles scalar, string, and nested-object values. Nested groups render as a small
titled key/value block, never as a stat tile and never as a JSON dump.

**Provenance.** Every tile is a `<button>`; activating it opens the evidence panel scrolled to
the SQL or engine that produced it, and announces the move. Keyboard reachable, visible focus.

**Three honest empty states**, never `N/A` / `undefined` / `NaN` / a blank tile:

| State | Rendering |
| --- | --- |
| Real zero | `0`, `$0.00`, `0.0%` in the normal style |
| Missing | An em dash `—` in `--faint`, at label size, not value size |
| Not evaluated | The label, then `Not evaluated` in `--faint`, with a title saying why |

---

## 6. The answer, and its sections

**The surface is "Ask the data".** Not "Thread" — the reader is a business user, not a developer.
The rail reads Ask / Data / Activity / System.

**A headline is a finding, never a row count.** When the backend's own headline is a developer
artefact ("Query returned 12 rows."), it is replaced by the narrative's first real sentence; when
the narrative is entirely tabular, by a description of the result's shape built only from values
the backend sent ("Total revenue, January 2025 to December 2025"). **No total is ever stated that
the backend did not compute.**

**No raw key/value pair ever reaches the screen.** `month: 2025-01, total_revenue: 64830335.73`
becomes `January 2025 · $64,830,335.73`: every key humanised, every period spelled out, every
number formatted, currency given its symbol. Inline markdown is stripped so an asterisk never
renders literally.

**A series leads with its chart.** When the result is many rows of one measure, the chart comes
first and a single tile is not allowed to stand in for twelve months. A figure that matches
exactly one row of a many-row result is labelled with that row's own scope ("January 2025")
rather than implying it is the whole.

`composed_answer` is the narrative, set as body prose.

`management_response` sections — **WHAT · WHY · WHAT NEXT · SO WHAT · SCENARIO · IMPACT** —
each get their own identity without shouting. The device is a **margin heading in a reserved
lane**, not a coloured card, a badge, or a label stacked above the headline:

- a 2px left rule in `--border`, becoming `--text` on the section that carries the answer;
- the section name as the section's real `h3`, 12px in `--muted`, in its own 5.5rem lane
  beside the rule — a margin heading, never a kicker above the headline;
- the backend's headline as the statement at 20px/600 in the content column;
- the content as markdown prose;
- its KPIs in the divided container of §5;
- its disclaimers last (below).

Distinguishable at a glance by position and weight, with zero colour spent. Sections with no
verified basis are **absent from the payload and absent from the DOM** — never an empty heading.
`impact_section` renders on the same footing as the five the brief names; nothing is dropped.

**Disclaimers are the honesty of the product.** They render as first-class content at body size
(14px, `--text`), not as grey fine print, in a bordered well directly under the section they
qualify, each prefixed by a small warning glyph. They are never collapsed, never truncated, and
never hidden behind a disclosure. Measured against live payloads these run to full sentences
("*Individual churn probabilities are withheld… the behavioural features are decoupled from the
status labels and carry no usable separation on this data*") and they are the most valuable text
on the screen.

**Secondary, quieter** — one 12px meta row under the answer: `specialist_capability`
(which pipeline answered), `route.intent` with `route.confidence`, `total_duration_ms` and
`query_result.execution_time_ms`. Grey, one line, no pills.

`analytical_result.findings` and `.recommended_next_steps` render as real lists.
`suggested_followups` are buttons that send the question.

---

## 7. Charts

Rendered by the existing Plotly renderer, lazy-loaded, with a table fallback.

**The backend's chart colours are overridden.** `plotly_layout` ships `#6366f1` (indigo — banned)
plus `#94a3b8` / `#1e293b` axis colours that only work on dark. The renderer replaces every
colour with validated tokens read from the live computed theme, and re-renders on theme change.
Data values are never touched — only presentation.

Rules, from the study:

- One series is the norm; **no legend for a single series** — the title names it.
- Slot 1 (`#1d5fbf` / `#3f86e0`) on the main data element. Neutral ink for comparison series.
- 3–5 horizontal gridlines, 1px, `--grid`. **No y-axis line.** Baseline is the one heavier rule.
- Y ticks on round even steps, top tick above the maximum, zero as the baseline for bars/counts.
- X labels flat, never rotated, 4–8 per chart.
- Lines 2px, straight segments, no point markers, no fill (or ≤14% flat tint).
- Bars square-cornered, 2px seam between stacked segments.
- Plot 160–220px tall on phone, up to 280px desktop.
- Axis text never larger than the data.
- `alt_text` from the spec becomes the accessible description; the table fallback is the
  non-visual route to the same numbers.
- `chart_type: "table"` or `fallback_to_table` → render the table, not an empty plot.

Never: rainbow series, a hue per bar, a dual axis, a smoothed spline, a 3D effect, chartjunk.

---

## 8. Motion

An answer **assembles**, it does not appear. Transform, opacity and clip-path only; everything
that runs while the page is busy streaming is CSS, so it stays off the main thread.

```css
--ease-out:    cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

| What | Purpose | Tool | Properties | Curve · duration |
| --- | --- | --- | --- | --- |
| Section arrival | Reading order made visible | CSS keyframes | `opacity`, `translateY(10px)` | `--ease-out` · 420ms, staggered **55ms** in order |
| Figure count-up | The number settling | rAF → `textContent` | text only | exponential ease-out · 850ms |
| Line chart draw-in | The series tracing | CSS keyframes | `clip-path: inset()` left→right | `--ease-out` · 760ms |
| Bar chart rise | Bars growing from the baseline | CSS keyframes | `scaleY` from `center bottom` | `--ease-out` · 620ms |
| Streaming step arriving | Progress being made | CSS keyframes | `opacity`, `translateY(4px)` | `--ease-out` · 260ms |
| Live indicator | Which step is running | CSS keyframes | `opacity`, `scale` + an expanding ring | `--ease-in-out` · 1.6s loop |
| Evidence expanding | Where the detail came from | CSS transition | `grid-template-rows` 0fr→1fr | `--ease-out` · 260ms |
| Pointer tilt | A surface under a light | rAF → inline `transform` | `transform`, two custom properties | 220ms settle · max 3° |
| Slide change | Direction of travel | CSS keyframes | `opacity`, `translateX(±28px)` | `--ease-out` · 380ms |
| Presentation progress | How far through | CSS transition | `scaleX` from `origin-left` | `--ease-out` · 300ms |
| Button / tile press | Feedback | CSS transition | `scale(0.97)` | `--ease-out` · 140ms |
| Drawer | Spatial consistency | CSS transition | `translateX(100%)` | `--ease-drawer` · 240ms |

**The frame budget is the constraint, not an afterthought.** The count-up writes `textContent`
on a ref rather than React state: driving state from `requestAnimationFrame` re-renders the
component every frame, and four figures on screen is 240 renders a second. Nothing animates a
layout property except the accordion, which has no transform equivalent. No animated blur. No
`transition: all`. The pointer tilt is rAF-batched and writes only to the element it is on,
never to a parent whose custom properties would recalculate every child.

**`prefers-reduced-motion: reduce`** removes all travel, scale and looping: sections appear in
place, figures show their value immediately, charts skip the wipe, tilt is disabled, and the
disclosure opens instantly. Opacity transitions stay at 120ms.

---

## 8b. The three-dimensional layer

Depth is built from light, material and parallax — never from spinning geometry for its own
sake.

**The hero** is WebGL (three.js), lazy-loaded and never server-rendered, so the shared bundle
stays at 87.5 kB and nothing blocks first paint. A 2,600-point field drifts in loose formation
and resolves over 2.6s into **the real series the opening query returned**; a faceted solid
rotates slowly in the same gold light; the whole scene follows the pointer with an eased lag.
The points are placed from API values exactly as a chart's marks are, and the scene shows no
number of its own.

It is a split — words left, scene right — so legibility never depends on a scrim over a canvas.

**Where 3D is refused.** The scene is not mounted at all for `prefers-reduced-motion`, a coarse
pointer, fewer than four logical cores, a viewport under 1024px, or a browser without WebGL.
Those get the same composition without the canvas: a fallback, not a degraded state.

**The frame budget**, enforced in the scene itself: `devicePixelRatio` capped at 1.75; the loop
stops entirely when the canvas leaves the viewport or the tab is hidden, and resumes where it
left off; one `BufferGeometry` updated in place, so there is no per-frame allocation and no
garbage for the collector to find mid-animation.

**Elsewhere**: stat tiles take a few degrees of pointer-tracked perspective with a specular
highlight that tracks the cursor across the face of the material; the evidence panel hinges open
about its top edge; and a chart's grid and series separate by a few pixels on pointer move, so
the plot has depth between its own layers. All of it is `transform` on the element itself,
rAF-batched, and disabled under reduced motion.

---

## 9. States

Every block owns its states; none is a full-screen takeover.

| State | Rendering |
| --- | --- |
| **Opening** | Before a question is asked the screen is alive: warehouse figures from `/schema/status`, answered-question counts and typical latency from `/ops/metrics`, the connected database from `/ready`, and one real query supplying an opening chart and its own figures. Suggestion cards carry the question and what it will demonstrate. Nothing on it is invented. |
| **Streaming** | The stepper shows each `trace_steps` entry as it arrives: name, status glyph, and `duration_ms` right-aligned in mono once complete. Running step has a quiet pulsing dot. Progress is visible as steps accumulate, not as a bar. (`trace_steps` repeats `step` values, so rows key on index, never on name.) |
| **Clarification** | `clarification.question` as the heading, `options[]` as real buttons (label + description, sending `inferred_query`), and `default_interpretation` named plainly as what happens if they do nothing. Not an error. |
| **Refusal** | `answerability.refusal_reason` in plain words, `available_alternatives` as suggestion buttons. Styled as a notice, not an error — the agent declining to guess is the product working. |
| **Empty result** | "No rows matched" naming the window queried, from `verification.empty_result` / `row_count: 0`. The frame and header stay. |
| **Loading** | The final layout with each value replaced by a flat grey bar at its real size. No shimmer, no spinner, no layout shift when data lands. |
| **Error** | Inside the block that failed. One sentence naming what failed, and a Retry text button. |
| **Backend unreachable** | A single quiet notice in the thread with the base URL and a Retry. The rest of the screen keeps its frame. |

---

## 10. Evidence panel

The product's credibility, so it is designed rather than appended. One disclosure per answer,
closed by default, opening into a panel of labelled blocks:

1. **`sanitized_sql`** — mono, syntax-highlighted, copy-to-clipboard. When the run produced no
   SQL (a specialist engine path) the block says so plainly instead of rendering empty.
2. **`analytical_result.executed_queries`** — all of them, numbered, each independently copyable.
3. **`analytical_result.computed_metrics`** — a readable key/value view, never a JSON dump.
   Scalars as rows; arrays of objects as a real table; `confidence_interval_95: [lo, hi]` as an
   interval beside its metric; nested objects as titled sub-blocks.
4. **`selected_methods`** and **`confidence_score`**.
5. **`query_result`** — a proper data table: sticky header, right-aligned tabular numbers,
   12px grey sentence-case headers, no zebra, `row_count` and a `truncated` notice.
6. **`verification`** — `checks_passed`, `warnings`, `empty_result`.
7. **`limitations`**, **`plan.steps`**, **`selected_tables`**, **`linked_values`**,
   **`repair_attempts`**.

`plan.steps` arrives with every status `pending` and `duration_ms: 0` even on a successful run —
it is the *planned* DAG, not an execution record. It is labelled as the plan, and `trace_steps`
is labelled as what actually ran. Rendering the plan as live status would be a lie.

---

## 11. Shell

**Icon rail**, 56px, on the page ground with a 1px edge. Four destinations — Thread, Catalog,
Telemetry, System — each a 16px outline icon on a 44px pitch, with a tooltip and an accessible
name. The active item is marked by ink brightness and a 2px left rule, never a coloured pill.
Utilities (theme, settings) sit at the bottom after a gap.

The product's mark and name sit at the top of the rail, and the scope — the connected database
and the active model — is named in the thread header. A screen whose product cannot be named
from a screenshot reads as a template.

On phone the rail becomes a 4-item bottom bar with short labels, and the thread takes the
full width.

**Presentation mode** is a separate surface: a full-screen keynote of one answer — the question,
each section in reading order, then the evidence. Arrow keys, space, Home/End and Escape drive
it; a progress bar shows how far through the room is; one figure or chart per slide. Focus is
trapped and restored on exit, and body scroll is locked while it is open. It is the only place
type is allowed past the app-screen ceiling, because a keynote is read from the back of a room.

---

## 12. Accessibility

- Strict TypeScript, no `any`.
- Landmarks: `banner`, `navigation`, `main`, `complementary`. One `h1` per screen; headings nest
  without skipping.
- Every control keyboard reachable in reading order, with a **visible** focus ring —
  2px `--text` offset 2px, never removed, never animated.
- Icon-only controls carry `aria-label`; the rail's tooltips are not the accessible name.
- Streaming updates land in an `aria-live="polite"` region; the live region announces the step,
  not every character.
- The evidence disclosure is a real `button` with `aria-expanded` / `aria-controls`.
- Tables use `<th scope>`; the chart's `alt_text` is its description and the table fallback is
  the equivalent non-visual route.
- Every text tier clears **4.5:1** on the surface it sits on, in both modes, placeholders
  included. Measured: `--muted` `#6b6b6b` on `#ffffff` = 5.33:1, on `#f8f8f8` = 5.02:1;
  `#b4b4b4` on `#111111` = 9.11:1.
- Colour is never the sole carrier of meaning (§3).
- Responsive from 360px. Tables scroll inside their own frame; the page never scrolls sideways.

---

## 13. What this design refuses

Gradient blobs · glassmorphism · neon glows · emoji in headings · three-column feature grids ·
centred hero text · drop shadows on resting surfaces · cards nested in cards · decoration
carrying no information · zebra tables · uppercase tracked headers · icons in tinted circles ·
sparklines on KPIs · rainbow charts · dual axes · a coloured sidebar · navy or slate darks ·
saturated status chips with white text · pagination under a short list · `N/A` · a figure at
48px · a count-up on a verified number.

Restraint reads as expensive. The space that opening up leaves is filled with the product's own
substance: the real figures at their real size, the uncertainty beside them, and the SQL that
proves them.
