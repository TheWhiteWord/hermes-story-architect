## What We Realized
Current problem: Scenes only exist as parsed output from a screenplay. Scene identity = heading string (fragile — "INT. HOUSE. NIGHT" can appear multiple times). Scene metadata can't exist independently because there's no persistent scene storage.

Key insight: The screenplay should be an import source, not the working document. Parse once → generate scene files → script view becomes an ordered assembly of those files. Editing happens at the file level; the script view re-renders.

This means scenes need to be first-class entities before we can build structure (acts, sequences) or character arcs on top of them.

## WHAT WE DONT NEED
- backward compatibility (we are developing the app righ now, no existing project exist if not for test purpose)
- to focus our attention into the reintegration of the full feature of retreiving scenes from an exiting script. we should only do this as a separate reintegration once the we solve the issue of: Scenes need to exist before screenplay exists (planning-first workflow), so taht its reintragration is yo match the new acrchitecture. But a separate concern.
