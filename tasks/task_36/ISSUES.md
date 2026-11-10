# ISSUE TICKETS

## ISSUE 1 - TOOL OUTPUT TRUNCATION (MEDIUM PRIORITY) [parially solved - commit `3c9c6974f0e9594af0ef9a1ebe1a8e81bfd87b8e`]

Need to check if tool outputs are being truncted , or if they are ony truncated in the report. The tool output is being truncated in the report, but not sure if they are truncated in the tool output to the llm itself.

**Fix:**
Patch file;
- Under budget, nothing changes. Small projects get the same output as before, key for key (tested).
- Over budget, trailing sequences compact.
    - They become id/title/status rows (or scene_count in dramatic_elements).
    - Nothing is removed.
    - A detail block names exactly which sequences were compacted and gives the call that expands them (tested).
- sequence= is now on the base map and dramatic_elements. An explicit sequence is always answered in full, regardless of budget. act= works on the base map too.
- Budget: STORY_ARCHITECT_MAX_RESPONSE_CHARS, default 35000. Set it somewhat under Hermes’s threshold: about 15000 for a 32k-token model, 30000 for 65k, and the default is fine from 128k up.

## ISSUE 2 - EDITOR UI  (LOW PRIORITY) - [SOLVED in commit `e5811d805f5b8e2bcdc7e0e410461c5c04248e30`]

Elements voices shown at the side of the script page they are not alllined with one another and some are appearing over the scipt page itself. Also the minimum spacing of the script page in the edit to the left edge can be reduced (probably half) so taht when other views are opened they can push the script view further in (to the left).

**Fix:**: Gutter marks removed

## ISSUE 3 - SCRIPT VIEW (HIGH PRIORITY) - [SOLVED in commit `0f0ae7bb0aa108d16eb8043971b01f47c96ecd55`]

The script in the demo is showing a scene that was created during a live test run and later deleted. Such scene no longer exist. The agent checked if was soft deleted and it was not. Either the agent has no way to check for soft deleted scenes or the scene was deleted and somehow the script view is still showing it. INterestengly this seems to be only showing up in the script view and not in the data from db.

**Fix:** excluded soft-deleted scenes from screenplay text assembly

## ISSUE 4 - SCRIPT STATISTICS (HIGH PRIORITY) [SOLVED in commit `c65958b0d7598bbe670b5951e6105869c01b8fcc`]

THe last tab of the script statistcis not showing any data. This was working, but something must have been broken during either the integration of the editor with the script view or the chat ui. mportantly this is the only tab that gathers data from the db and not from the script parsing. The other tabs are working fine.

**Fix:** injected STRUCTURAL_STATS so structure tab populates

## ISSUE 5 - EDITOR FUNCTIONALITY (LOW PRIORITY) 

- Heading allows for free text. Need to reason on why is that. Issue is taht a free text heading that is properly formatted, if uses not existing location, does not recognize it as a location, and does not show the chip for the location. However hte suer can do the same by adding a location from the side pannel, so the free text seems to be a way to bypass the location check. Need to reason on this and decide if it is a bug or a feature.
- Tab key circles only between Parentetical and Dialogue. It should also circle through the other elements. Unsure if that is by design for some reason i can't think of, or if it is a bug. Need to check with the team.

## ISSUE 6 - EDITOR FUNCTIONALITY (MEDIUM PRIORITY)

- if an element exist is not possible to change its type. The only way to do that is to delete the element and create a new one. This is not ideal, as it can be frustrating for the user. Tab key is supposed to allow for changing the type of an element, but it is not working for evey element(see ISSUE 5). Ideallly, if an element in the script is entered and the user clicks on the any of the element types in the in the left side pannel, the element should change to that type.
- Right now there is no way for a user to undo/redo an edit between saves. WOuld be good to have the classic ctrl+z and ctrl+y functionality to undo/redo edits. This shoud affect: creation of an element, deletion of an element, and editing of an element, of a paste,. Does not necessary need to cover the undo/redo of a save, as that is already covered by the server side functionality. The "save" stage of undos and redos may be limited to full elements states: an elemet taht is created, removed , or edited, and than exited saves a new state of the element. Eg: create a new element and write some text, than undoing it will remove the element. If the user saves, then the undo/redo stack is cleared.
COnsiderations need to be made if git can be used to manage the undo/redo stack. COnsiderations are: ease of integration, using of existing open source libraries, dependencies weight, and performance. The undo/redo stack should be limited to a certain number of edits, and should not be persisted between sessions. The undo/redo stack should be cleared when the user saves the script. The undo/redo stack should be cleared when the user navigates away from the script editor. NOt sure, outside my expertise, but git seems to be a good candidate for this, as it is already used in the project, and it is a well known and well tested library. However, it may be overkill for this use case, and may introduce unnecessary complexity. Need to reason on this and decide if it is a good idea or not. MAybe open source libraries that implement undo/redo stacks can be used instead of git, as they may be more lightweight and easier to integrate. Need to research this and decide on the best approach.

## ISSEUE 7 - ASK HERMES BUTTON (MEDIUM PRIORITY)

- I tested the ask hermes button, and while id does send teh message to the agent (visible in the chat history of both the app and heremes desktop), the subsequent tool calls and response are not passed to the app in chat. These are happenning, but they are only visible in the hermes desktop chat.