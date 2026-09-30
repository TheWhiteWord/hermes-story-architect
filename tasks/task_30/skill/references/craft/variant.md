# Variant

*The same world or the same place, with a change the story cares about.*

Applies to `world` and `location` alike. → `theory/world-and-place.md`

**A variant is a diff on a base, and both records stay live.** The base is
still a world, the variant is still a world, and the story uses each as the
one it is. Nothing merges them and nothing is inherited on read — the two are
separate records and a scene points at whichever one it means. What
`variant_of` does is tell the *writer* that this one was not invented from
nothing.

Which is the whole point, and the reason the field exists: **a burnt forest
is still that forest.** The rock by the river is still there. What is not
still true is the flowers, the smell, what the trees were doing to the light.
A variant records what the change did, and inherits the rest by being a
variant.

## Deciding it

**Write the variant with its base in front of you, and record the difference.**
Not the whole thing again. A variant that restates the base in full has lost
the reason to exist and will drift from it; a variant that assumes the change
is universal is unreadable. Which fields the change actually touches is the
judgement, and it is the whole of it.

- **What is inherited is not restated.** The base's rules, its period, its
  power, the geography — all still true, and all still readable on the base.
  State what the change did to them and leave the rest there.
- **What the change touched is stated, even if it is a small thing.** A
  variant whose fields are all empty and whose sections carry the whole
  difference is harder to read than one that names the two rules that
  changed. Sections carry reasoning, fields carry the fact.
- **A base has `variant_of` empty.** That is what makes it the base, and it is
  the only thing that distinguishes it from a world nobody has varied yet.

**When a variant is warranted.** When the story treats the changed state as a
thing with its own description, rather than as a moment inside the existing
one. The question is whether the base's description is still good enough — if
it is, there is no variant, and the difference is a note or a line in a scene.

The occasions that keep coming up, given as illustration and not as a closed
list:

- **a mental state the story gives its own rules** — a dream, or any altered
  state the characters behave inside as if it were a place with conventions
  of its own
- **an event that alters the conditions** — a fire, a collapse, an invasion
- **a jump in time** — a different century, or the same place decades on
- others, and the reasoning is the same whatever the occasion is

**The two tests are not the same, and that is deliberate.**

- **World** — is the story far enough into this state that it needs describing
  in its own right? This is a question about the story's centre of gravity. A
  world the characters argue with, bargain in, and are hurt by is one; a world
  visited once is not.
- **Location** — does the changed state need a description of its own, or is
  the base's still good enough? A room that burned needs a new record; a
  bedroom where someone wakes and sees a vision is the same room.

**The failure is a variant for every difference.** A variant per dream, per
flashback, per time jump turns the mechanism into noise and the base stops
meaning anything. The threshold is what makes the base worth having.

## Consistency

- **A variant and its base are two records about the same thing, and nothing
  compares them.** A variant that contradicts its base is not caught by any
  write, and a base edited later can drift out from under a variant that was
  written against it. When either changes, read the other.

- **A scene naming a world or location is naming one record.** A scene in the
  burnt forest names the variant, not the base, and a character whose goal
  depends on the forest being intact is reading a fact that the variant has
  invalidated. The variant is a different place as far as the store is
  concerned, and the story is what tells you which one the scene means. →
  `scene-design.md`

- **A world variant and a location variant are independent.** The forest
  burns and the world's climate does not change; a room burns inside a city
  that does. Each is judged on its own, and neither implies the other.
