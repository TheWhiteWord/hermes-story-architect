# Fountain Syntax Cheat Sheet

Adapted from Better Fountain's built-in cheatsheet (piersdeseilligny.betterfountain).

## Scenes

| Syntax | Description | Example |
|--------|-------------|---------|
| `INT.` | Indoor scene | `INT. BRICK'S ROOM - DAY` |
| `EXT.` | Outdoor scene | `EXT. BRICK'S POOL - DAY` |
| `EST.` | Establishing scene | `EST. CITY - NIGHT` |
| `INT./EXT.` | Indoor and Outdoor scene | `INT./EXT. RONNA'S CAR - NIGHT [DRIVING]` |
| `I/E.` | Indoor and Outdoor scene | `I/E. RONNA'S CAR - NIGHT [DRIVING]` |
| `TO:` | Transitions should be upper case, ending in `TO:` | `CUT TO:` |
| Action | Any paragraph that doesn't meet criteria for another element | `They drink long and well from the beers.` |

## Dialogues

| Syntax | Description | Example |
|--------|-------------|---------|
| `CHARACTER` | Character names should be in upper case | `STEEL` |
| Dialogue | Any text following a Character or Parenthetical element | `The man's a myth!` |
| `(parenthetical)` | Parentheticals follow a Character or Dialogue element, wrapped in `()` | `(starting the engine)` |
| `^` | Dual dialogue: add caret `^` after second Character | `STEEL ^` |
| `~` | Lyric lines start with a tilde `~` | `~Willy Wonka! Willy Wonka!~` |

## Emphasis

| Syntax | Description | Example |
|--------|-------------|---------|
| Title Page | Optional, first thing in document. `key: value` format | `Title: BRICK & STEEL` |
| `>CENTERED TEXT<` | Centered text bracketed with `> <` | `>THE END<` |
| `*italics*` | Italicize text | `*italics*` |
| `**bold**` | Bold text | `**bold**` |
| `***bold italics***` | Bold and italics | `***bold italics***` |
| `_underline_` | Underline text | `_underline_` |
| `===` | Page break (3+ consecutive `=` signs) | `===` |

## Misc.

| Syntax | Description | Example |
|--------|-------------|---------|
| `[[ notes ]]` | Note: enclose text with double brackets | `[[Or did we think of actual names?]]` |
| `/* ignore text */` | Boneyard (comment): Fountain ignores this text | `/* INT. GARAGE - DAY */` |
| `#` | Section: precede line with one or more `#` | `# Act` |
| `=` | Synopsis: single line prefixed by `=` | `= Set up the characters and story.` |

## Complete Example

```
Title:    _**BRICK & STEEL**_
          _**FULL RETIRED**_
Credit:   Written by
Author:   Stu Maschwitz
Source:   Story by KTM
Draft date: 1/20/2012

# Act I

= Set up the characters and the story.

INT. DAVE'S APARTMENT - DAY

Dave is standing in the open window looking out at the pouring rain.

                DAVE
            (cheerfully)
        Nice day for it!

                CUT TO:

EXT. BRICK'S POOL - DAY

Steel, in the middle of a heated phone call:

                STEEL
            They're coming out of the woodwork!
            (pause)
        No, everybody we've put away!
            (pause)
        Point Blank Sniper?

.SNIPER SCOPE POV

From what seems like only INCHES AWAY. _Steel's face FILLS the *Leupold Mark 4* scope_.

                STEEL
            The man's a myth!

Steel turns and looks straight into the cross-hairs.

                STEEL
            (oh crap)
        Hello...

                CUT TO:

.OPENING TITLES

> BRICK BRADDOCK <
& DICK STEEL IN <

> BRICK & STEEL <
FULL RETIRED <

SMASH CUT TO:

EXT. WOODEN SHACK - DAY

COGNITO, the criminal mastermind, is SLAMMED against the wall.

                COGNITO
        Woah woah woah, Brick and Steel!

                STEEL
        Who's coming after us?

COGNITO
Everyone's coming after you mate! Scorpio, The Boy Band, Sparrow, Point Blank Sniper...

                CUT TO:

INT. GARAGE - DAY

BRICK and STEEL get into Mom's PORSCHE, Steel at the wheel.

                BRICK
        This is everybody we've ever put away.

                STEEL
            (starting the engine)
        So much for retirement!

They speed off. To destiny!

                CUT TO:

EXT. PALATIAL MANSION - DAY

> BURN TO PINK.

> THE END <
```

## Dual Dialogue Example

```
                BRICK
        Screw retirement.

                STEEL ^
        Screw retirement.
```

## Notes and Comments

```
This is the home of THE BOY BAND, AKA DAN and JACK[[Or did we think of actual names for these guys?]]. They too are drinking beer.

[[It was supposed to be Vietnamese, right?]]

/*
INT. GARAGE - DAY

BRICK and STEEL get into Mom's PORSCHE, Steel at the wheel.
*/
```

## Sections and Synopses

```
# Act I

= Set up the characters and the story.

## Sequence

INT. SCENE IN HOUSE - DAY

# Act II

= The conflict escalates.

INT. ANOTHER SCENE - NIGHT
```
