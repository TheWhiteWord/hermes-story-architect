---
id: central-room-day-beats
scene: central-room-day
type: scene_beats
driver: kael
scene_objective: Find out whether the door was ever locked.
turning_point: The handle turns. The lock was never engaged.
true_character:
- character: kael
  dilemma: Open the door and become the one who broke it, or leave it shut and stay innocent of it.
  choice_reveals: He needs the truth more than he needs to be innocent of it.
changes:
- entity: kael
  change: No longer believes the door was locked; suspects the story he was told was the lock.
- entity: the-central-room
  change: Stops being a boundary and becomes an exit.
beats:
- action:
    by: kael
    surface: Hand flat on the door
    subtext: testing whether it will hold
  reaction:
    by: kael
    surface: It turns
    subtext: discovering his own prison was agreed, not built
  gap: He expected resistance and got none.
- action:
    by: the-central-room
    surface: The room beyond is lit
    subtext: offering a version of home back to him
  reaction:
    by: kael
    surface: He steps back
    subtext: refusing the bargain the room is making
---

## Notes

The lock is the scene's whole mechanism: the door was never locked, so the
cage was agreement. The gap opens in the first beat — action and reaction
both Kael, which is why the exchange draws it as inner conflict — and the
second beat puts the room itself on a lane, so the circumstance is a
participant rather than scenery.
