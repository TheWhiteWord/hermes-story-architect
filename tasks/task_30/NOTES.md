# NOTES on SKILL/REFERENCES

## General Notes

- Generally Overly Verbose. Treating this as was documentation for an human, but is not. Is a SKill for an agent.
eg:
"The section *names* are not here. `story_describe` reports them per type, and
they are a closed set — a name that is not on that list is rejected by the write
path, so there is nothing to look up and nothing to guess."
Where we have:
- "The section *names* are not here" - No need to know what is not here, only need to know what is here.
- "story_describe` reports them per type, and they are a closed set — a name that is not on that list is rejected by the write
path, so there is nothing to look up and nothing to guess." - consequences overexplained. "they are a closed set" already means that  "a name that is not on that list is rejected by the write
path" and than " so there is nothing to look up and nothing to guess" is just filler text. 

## MODEL
### ENTITY SECTIONS
Overly Verbose
eg:
"The section *names* are not here. `story_describe` reports them per type, and
they are a closed set — a name that is not on that list is rejected by the write
path, so there is nothing to look up and nothing to guess."

can be something like:

"use 'story_describe' to report them. Sections are not customizable"


## USER NOTES

redesigned "dramatic role" to state only if is one of plot role, transition, non-event.
If dramatic role is set to plot role than the plot role must be filled
If is set to transition, non-event than no plot roles can be added.

Stub_scenes
PLanned , which is defauikt creates a stubbed scene,usefull for planning stages.
"status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, drafted, written, locked"},

