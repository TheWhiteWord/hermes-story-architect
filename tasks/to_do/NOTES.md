# REMINDERS WORK TO DO

## SKILL

- One skill multiple refereces vs Multiple skills? To decide
- CONTEXT_SKILL.md  is good, but mya have steal infoo about presenting the preview_md. NOw the app does taht automatically with a card. TO fix in skill and verify where that is still mentioned erronously (the skill  creation must have seen it somewhere)

## SETUP

- we have been too heavy on removing basic functionalities in hermes agent creation . We may want to reintroduce: Memory.md (usefull so the agent cna improve) - consider what skills fro basic heremes agent creation are usefull and keep them (minimal), 
- consider which basic tools are usefull (consideration about terminal use and utility tools, like read file etc.. we want to avoid agent to use those instead teh mcp, yet they may be usefull.. not sure here)

## VERSIONING (general)

- Issue with soft delete as agent ahs no way to look at what sof deleted entoties exist
- No way to save a "draft". for draft i mean the whole project state not only the script.
- no basic functionality in script editing tool, like undo, redo (possily with usual keybindings ctrl+z etc..)
- can these allbe resoluted aslo with the backup strategy we have already existing?

## MANUAL CREATION (in progress task_37)

- Need to implement manual creation of entities form the ui (bypasses the agent, no drafts direct writes), so taht an user can manually create these
- Overlay similar to the memory one. All avaible non comoputed fields and sections avaible. They need descriptions that are suitable for human (in fiels taht erase as input goes in?)
- some can be selection from avaible keys (eg: One of... only the avaibel ones are presented)
- subfield too. DO trey appear once the primary field is inserted?