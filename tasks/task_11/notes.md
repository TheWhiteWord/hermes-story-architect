## LOCATION EXTENDED VIEW

- Right now we render only one_sentence (form the index) and name it in here as "DESCRIPTION". We want "DESCRIPTION" to be "IN ONE SENTENCE" instead
- We want also the actual sections , taken form the notes to render (eg: DESCRIPTION, HYSTORY, SCENES, etc etc) Note that these do not need to be in the index. these must be rendered on request and taken form the existing notes. Sections may vary, they are not hardcoded sections, they depend on what the agnet/user write them.


## CHARACTER EXTENDED VIEW
- we want to add story_role (eg: Supporting, Protagonist etc etc..) as appears for the characther in index.
- we keep the APPEARS IN section as it is. Good.
- We want also the actual sections , taken form the notes to render (eg: PERSONALITY, BACKGROUND, VOICE, etc etc) Note that these do not need to be in the index. these must be rendered on request and taken form the existing notes. Sections may vary, they are not hardcoded sections, they depend on what the agnet/user write them.


## PLOT EXTENDED VIEW
- Right now the SETUPS and PAYOFFS are not rendering correctly: they show as [object Object]. We wnat to show the scened and numbers and to be links that open the corrrect scene and number extended view if clicked.
- We want also the actual sections , taken form the notes to render (eg: SUMMARY, OBSTACLES, STAKES, etc etc) Note that these do not need to be in the index. these must be rendered on request and taken form the existing notes. Sections may vary, they are not hardcoded sections, they depend on what the agnet/user write them.

## WORLD EXTENDED VIEW
- Right now we render only one_sentence (form the index) and name it in here as "SETTNG". We want "SETTING" to be "IN ONE SENTENCE" instead
- We want also the actual sections , taken form the notes to render (eg: SUMMARY, OBSTACLES, STAKES, etc etc) Note that these do not need to be in the index. these must be rendered on request and taken form the existing notes. Sections may vary, they are not hardcoded sections, they depend on what the agnet/user write them.


## NOTE
Since all the above changes realted to the integration of the actual sections form the notes share similar logic we may want to consider one helpr or implementation for all rather than duclicate code, if possible or optimal.