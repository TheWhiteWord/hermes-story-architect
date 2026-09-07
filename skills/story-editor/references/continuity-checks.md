# Continuity Checks Reference

> Categories, severity levels, and examples for self-audit before applying edits.

---

## Categories

### character_knowledge

Does this contradict what a character knows?

**Example**:
- Mara knows Victor Hale is the cartel's CFO
- Edit: Mara asks "Who is Victor Hale?"
- **Finding**: Contradicts established knowledge

**Severity**: `critical`

---

### chronology

Does this fit the chronological order?

**Example**:
- Scene 5: Mara finds the account number
- Edit: Scene 3 references the account number
- **Finding**: Timeline violation — Mara doesn't have the number yet

**Severity**: `critical`

---

### location

Does this match the location's description/rules?

**Example**:
- Kitchen: "Stainless steel, harsh fluorescent lights"
- Edit: "The kitchen is warm and cozy"
- **Finding**: Contradicts established atmosphere

**Severity**: `caution`

---

### world_rules

Does this violate established world rules?

**Example**:
- World rule: "Off-grid water extraction is a capital offense"
- Edit: Character extracts water without consequence
- **Finding**: Violates world rule

**Severity**: `critical`

---

### setups_payoffs

Does this break a setup without payoff?

**Example**:
- Scene 1: Mara's skimming is established as a secret
- Edit: Remove all references to skimming
- **Finding**: Setup without payoff — the secret was never discovered/resolved

**Severity**: `caution`

---

### voice

Does this match the character's established voice?

**Example**:
- Mara's voice: "Precise, clinical. Rarely uses contractions."
- Edit: "Like, I totally think we should, like, go there?"
- **Finding**: Contradicts established voice

**Severity**: `suggestion`

---

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| `critical` | Direct conflict with confirmed canon | Must fix before applying |
| `caution` | Likely inconsistency / weak motivation | Flag for user review |
| `suggestion` | Optional improvement | Note, but not blocking |

---

## How to Self-Audit

Before applying any edit, check each category:

1. **Character knowledge**: Does this edit make a character know/not know something they shouldn't?
2. **Chronology**: Does this edit reference events out of order?
3. **Location**: Does this edit contradict the location's description?
4. **World rules**: Does this edit violate established world rules?
5. **Setups/payoffs**: Does this edit abandon a setup without resolution?
6. **Voice**: Does this edit match the character's established voice?

Return checks as part of the proposal:

```json
"continuity_checks": [
  {
    "severity": "suggestion",
    "category": "voice",
    "finding": "Mara's voice is 'clinical and precise'. Adding 'fragments when angry' creates contrast — consider if this fits.",
    "evidence": "## Personality: Avoids conflict until cornered."
  }
]
```

---

## Citing Evidence

Always cite a source for continuity checks:

- Scene heading: `"INT. KITCHEN - NIGHT"`
- Character name: `"Mara Chen"`
- World rule: `"Water rationing is enforced by biometric scanners."`
- Location description: `"Stainless steel, harsh fluorescent lights."`

Evidence must be retrievable from the index or vault notes.
