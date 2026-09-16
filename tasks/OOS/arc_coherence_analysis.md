# Arc Coherence Analysis — Specialist Brief

**Context:** We're building a story architecture plugin. We need to validate whether character arcs and structural arcs are coherent with each other — using the numeric data we already capture. This brief explains the system, the data available, and the open questions we need help answering.

---

## The Two Arc Systems

**Structural arc** = the value journey of the story at each scale:
- Project (overall) → Act → Sequence → Scene
- Each has a `value` (e.g., Trust, Justice) and `value_open`/`value_close` charges (`positive`, `negative`, `mixed`, `ironic`)
- Higher levels = larger reversals

**Character arc** = the interior value journey of each character:
- Protagonist (always), Antagonist (usually), Supporting (selectively)
- Encoded as "beats" — each beat has `action`, `gap`, `choice`, `shift`
- Each beat has a numeric `y` value (-1.0 to +1.0) representing value charge
- Beats map to scenes via a `scene` field

---

## The Link

A character's beats occur **within** scenes. Scenes live inside sequences → acts → project. So the structural container surrounds the character's arc.

The theory (McKee): **Structure's job** is to apply progressive pressure. **Character's job** is to make credible choices under that pressure. The character arc is *not separate* from structural values — it's the interior experience of the external pressure.

The values don't need to match word-for-word. They need to *rhyme* thematically. "Trust → Betrayal" at project level might play as "Certainty → Doubt" in Act 1, "Loyalty → Treason" in Act 2.

---

## The Numeric Encoding

| Charge String | Numeric |
|---------------|---------|
| positive | +1.0 |
| mixed (leaning positive) | +0.5 |
| mixed (neutral) | 0.0 |
| mixed (leaning negative) | -0.5 |
| negative | -1.0 |
| ironic | true charge + irony flag |

Each beat stores:
- `y` = ending charge after this beat
- `order` = position in the character's arc
- `is_crisis` / `is_climax` = major reversal markers

---

## The Core Question

**Can we use character arc math to validate structural arc coherence?**

We're not looking for absolute proof — just indicators that something might be off.

### Possible checks

1. **Directional alignment at act level** — If Act 2's structural value goes `positive → negative`, does the protagonist's net `y` movement within that act go negative? If not, is the arc out of phase with structure?

2. **Escalation matching** — Should the largest `|Δy|` per act trend upward (Act 1 < Act 2 < Act 3)? If Act 1 has a -0.9 swing and Act 3 has +0.2, the arc peaks too early.

3. **Crisis/climax placement** — Does the protagonist's `is_crisis` beat land in a structurally climactic scene? Does `is_climax` land in Act 3's climax? If not, the arc and structure are out of phase.

4. **Controlling idea sanity** — Net `y` movement for the protagonist should have the same sign as the project's `value_at_open → value_at_close`. A down-ending story shouldn't leave the protagonist at +0.8.

### What the math can't catch

- Whether "Trust → Betrayal" and "Justice → Injustice" rhyme thematically (linguistic, not numeric)
- Whether a character's choices are credible under pressure
- Whether the antagonist is a worthy opponent

---

## Open Question: Which Characters Matter?

We capture arcs for characters who have them (`arc_type`: positive, negative, flat, ironic, absent). The question: **whose arcs should the analysis consider?**

- **Protagonist** — obviously. Their arc IS the main value journey.
- **Antagonist** — their arc often mirrors or opposes the protagonist. Should we check that antagonist `y` movement *diverges* from protagonist at structural climaxes? Or converges (corruption arc)?
- **Supporting characters with arcs** — their arcs should *resonate* with or *contrast* the protagonist's meaningfully. But not all supporting arcs need to align — some exist to show alternative responses to the same structural pressure.

**Possible approach:** Weight by narrative importance. Protagonist = full weight. Antagonist = partial. Supporting = light touch, only checking for obvious misalignment.

---

## Visualization

The existing dashboard plots character arcs as `(x, y)` curves where `x` = narrative position, `y` = value charge.

**Proposed additions:**

1. **Structural act bands** — Shade the background by act (Act 1 / Act 2 / Act 3). This shows which structural container each beat falls in.

2. **Multi-character overlay** — Plot protagonist, antagonist, and key supporting arcs as separate lines on the same graph. Divergence/convergence points become visible.

3. **Crisis/climax markers** — Mark the protagonist's `is_crisis` and `is_climax` beats on the curve. Check if they align with act boundaries.

4. **Net movement indicators** — Show the net `y` delta per act as a bar or annotation. Quick visual check: are acts escalating?

---

## What We Need From You

1. **Feasibility** — Is aggregating character arc `y` values within structural containers a valid heuristic? What are the theoretical pitfalls?

2. **Character selection** — Which characters should the analysis include? Just protagonist? Protagonist + antagonist? All characters with arcs? How to weight them?

3. **Specific metrics** — Beyond the four checks listed above, are there standard coherence metrics from narratology or story theory we should consider?

4. **Visualization design** — What's the clearest way to present arc coherence (or incoherence) to a writer? Multi-line graphs? Divergence heatmaps? Annotated timelines?

5. **Thresholds** — When does a "misalignment" become a real problem vs. intentional artistic choice? How do we avoid false positives?

---

## Constraints

- We're not changing the data model. All analysis happens on existing fields.
- The output should be **indicative, not prescriptive**. Flag potential issues; don't auto-fix.
- Visualization must work within a static HTML dashboard (no real-time rendering engine).

--------------------------
------------------------

## SPECIALIST RESPONSE

I've read through the brief carefully. This is a well-thought-out system — the numeric encoding of value charges is a clever bridge between qualitative story theory and computable heuristics. Let me work through your five questions.

---

**1. Feasibility of aggregating y-values within structural containers**

Yes, it's a valid heuristic — with one important caveat. The `y` value at any beat represents the *current state* of a character's interior charge, not the magnitude of change. So the right thing to aggregate is always `Δy` (delta between beats within a container), not raw `y`. Summing raw y-values would be meaningless; net movement within an act is what carries signal.

The main theoretical pitfall is what you might call the *recovery problem*: a character could swing -0.8 then +0.7 within a single act, producing a net delta of -0.1 — which looks like a quiet act. But dramatically it was turbulent. So alongside net `Δy`, you should also capture **peak absolute swing** per act (the largest single beat-to-beat jump). Both together tell you more than either alone.

A second pitfall: beats don't have equal dramatic weight. A beat early in an act and a beat late in an act both contribute equally to your net delta, but the late one lands closer to an act turning point and should arguably carry more weight. You could apply a simple positional weight (beats later in the act weighted higher) if you find raw net delta produces too many false positives.

---

**2. Character selection and weighting**

Your instinct to weight by narrative importance is right. My suggestion:

- **Protagonist** — full weight, always included. Their arc is the controlling arc.
- **Antagonist** — include, but the coherence check is *inverted*. You're not looking for alignment with structure; you're looking for *meaningful opposition*. At structural climaxes, the antagonist's `y` should be moving in the opposite direction from the protagonist, or converging toward them (for corruption arcs). A divergence metric makes more sense here than an alignment metric.
- **Supporting characters** — only include those with `arc_type` that isn't `absent` or `flat`. And even then, only flag *severe* misalignment (e.g., a supporting character whose net arc movement contradicts the controlling idea). Their role is often to show alternative responses to the same pressure, so moderate misalignment is expected and intentional.

The cleanest implementation: run full checks on protagonist, a lighter inverted check on antagonist, and a single "controlling idea sanity" check on key supporting arcs. Don't let supporting arcs add noise to the main coherence score.

---

**3. Additional coherence metrics**

Beyond your four, here are three worth considering:

**Midpoint check.** Classical three-act structure has a midpoint (the "false peak" or "mirror moment") where the protagonist's trajectory reverses or accelerates. If your beats include a positional midpoint marker, check whether there's a notable `Δy` spike there. A flat protagonist arc at the structural midpoint often signals a pacing problem.

**Antagonist pressure gradient.** If the antagonist arc is captured, you can compute whether antagonist pressure (net negative `Δy` imposed on protagonist, inferred from structural scenes they share) escalates act over act. Constant antagonist pressure is a structural weakness even if the protagonist arc looks right.

**Arc completion ratio.** Does the protagonist reach a `y` value at the final beat that's consistent with their arc type? A `positive` arc should end meaningfully above its starting `y`. A `negative` arc should end below. This is different from controlling idea sanity — it's checking internal arc consistency, not structural alignment. Simple check: `(y_final - y_initial)` should have the expected sign for the declared `arc_type`.

---

**4. Visualization design**

For a static HTML dashboard, I'd prioritize clarity over density. My recommendations:

The **multi-line overlay with act bands** is your anchor view — it's the most informative single view you can build. Protagonist as a bold line, antagonist as a dashed line in a contrasting color, supporting arcs as thin low-opacity lines. Act bands as shaded regions. Crisis/climax markers as vertical tick marks or icons on the protagonist line. This view lets a writer see everything at once.

Add a **per-act delta summary bar** below the main chart — a small horizontal bar chart showing net `Δy` per act for the protagonist. This makes escalation (or lack of it) immediately visible without requiring the writer to read the curves.

For flagged issues, avoid inline annotations on the chart itself — they get crowded. Instead, use a **sidebar alert list** with short plain-language descriptions ("Act 1 net movement is larger than Act 3 — arc may peak too early") that link back to the relevant act band on hover. The chart stays clean; the issues are readable.

Divergence heatmaps are appealing but add cognitive load. I'd reserve them for a secondary "deep analysis" view rather than the main dashboard.

---

**5. Thresholds and avoiding false positives**

This is the hardest problem. My honest answer: start with generous thresholds and tighten them based on user feedback, because the cost of a false positive (a writer trusting a flag that's actually intentional) is higher than a false negative.

Some concrete starting points:

- **Directional misalignment**: only flag if the protagonist's net `Δy` sign *opposes* the structural container's direction AND the absolute delta is > 0.3. Small opposing movements are noise.
- **Escalation**: only flag if Act 1's peak swing is more than 1.5× Act 3's. A moderate imbalance might be intentional (a quieter third act is a valid choice in some genres).
- **Crisis/climax placement**: this is your most reliable check — it's binary and structural. Flag if `is_crisis` falls in Act 3 or `is_climax` falls outside Act 3. That's almost always a genuine problem.
- **Controlling idea sanity**: flag if protagonist `y_final` and the project's `value_at_close` have opposite signs. This one has the fewest false positives — it's a hard logical contradiction.

The key framing for the writer: present all flags as *questions*, not verdicts. "Act 2's protagonist movement appears to go against the structural pressure — is this intentional?" is much better than "Arc coherence error in Act 2." The tool is a conversation partner, not a linter.

---

Happy to go deeper on any of these, or to sketch out the visualization logic in more concrete terms if that would help.

---------------
-----------------

## FOLLOW UP QUESTIONS

Three follow-up questions worth asking (if you want to probe further):

Antagonist pressure gradient — the specialist said "inferred from structural scenes they share" but that's underspecified. How do we actually compute "antagonist pressure" from our data? Is it just the antagonist's y movement in scenes where they appear with the protagonist? Or something more nuanced?

Midpoint marker — we don't have a positional midpoint field. Should we derive it from act structure (Act 2's structural midpoint), or is this a YAGNI metric we can skip for now?

Positional weighting — the specialist suggested weighting late-act beats higher. Is this worth implementing in v1, or does raw net delta + peak swing cover enough that this is premature optimization?

------------------------
-----------------

## SPECIALIST RESPONSE to follow up

Good follow-ups. Let me be direct on each.

---

**Antagonist pressure gradient**

"Inferred from structural scenes they share" was underspecified — you're right to push on it.

The honest answer is that your data model probably can't support a genuine pressure computation without additions. Here's why: "pressure" implies directionality — the antagonist is doing something *to* the protagonist. But your beat data captures each character's interior `y` movement independently. You can't tell from `y` alone whether the antagonist's negative movement *caused* the protagonist's negative movement in the same scene, or whether they just happened to both go negative.

What you can actually compute from existing fields: **co-presence correlation**. For scenes where both protagonist and antagonist have beats, compare their `Δy` values. If antagonist `Δy` is consistently negative when protagonist `Δy` is also negative, that's *consistent with* pressure — but it could also just be that both characters are responding to the same structural event. It's a weak signal.

My recommendation: don't implement antagonist pressure gradient in v1. The data model doesn't support it cleanly, and a weak proxy metric is worse than no metric — it'll produce confusing output. If this becomes important later, the right fix is a data model addition: a `scene_interaction` field that tags beats as *reactive* (caused by another character's action) vs. *self-generated*. With that, you can compute real pressure. Without it, you're guessing.

What you *can* do with antagonist data right now is the simpler divergence check I mentioned: do protagonist and antagonist `y` values move in meaningfully opposite directions at structural climaxes? That's computable and useful.

---

**Midpoint marker**

YAGNI, skip it for v1.

Here's the reasoning: the midpoint is analytically valuable but structurally ambiguous. In classical three-act structure it sits at the Act 2 center, but in four-act or sequence-level analysis it shifts. Without a dedicated field, you'd have to derive it — and any derivation will be wrong for stories that don't follow a clean three-act proportion. A false midpoint marker is worse than none because it anchors the writer's attention to the wrong beat.

More importantly, your three reliable checks (escalation, crisis/climax placement, controlling idea sanity) already catch the most common midpoint-related problems indirectly. A protagonist arc that peaks too early shows up in escalation. A misplaced climax shows up in crisis/climax placement. The midpoint check adds marginal coverage at meaningful implementation cost.

If you do want to revisit it later, the right approach is a simple boolean field on scenes — `is_structural_midpoint` — set by the writer, not derived. Don't try to compute it.

---

**Positional weighting**

Skip it for v1. Raw net delta plus peak swing covers enough, and positional weighting introduces a parameter you'll need to justify and tune.

The practical problem: any weighting scheme you choose (linear ramp, exponential, step function at the act's final beat) will be arbitrary until you have real stories to calibrate against. If you ship positional weighting and it's miscalibrated, it'll produce confusing results that are hard to debug because the weighting is invisible to the writer. Net delta and peak swing are transparent — a writer can look at their beats and understand why a flag fired.

There's also a theoretical argument against it: late-act beats being "more important" is a default assumption, but it breaks for acts that deliberately build to a quiet late moment (a denouement beat, a false resolution). You'd be encoding a structural preference into the metric.

The time to add positional weighting is when you have enough real data to identify specific false positives that it would fix. Until then it's premature optimization, exactly as you suspected.

---

**Net summary for v1 scope:**

| Metric | v1 status |
|---|---|
| Directional alignment per act | Include |
| Escalation (net delta + peak swing) | Include |
| Crisis/climax placement | Include |
| Controlling idea sanity | Include |
| Antagonist divergence check | Include (simple version) |
| Antagonist pressure gradient | Defer — needs data model change |
| Midpoint check | Defer — needs explicit field |
| Positional weighting | Defer — needs calibration data |

That's a coherent v1 scope with four solid checks plus a lightweight antagonist check. Everything deferred has a clear reason and a clear path forward if you need it later.