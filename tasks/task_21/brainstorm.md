
## 0. INITIAL toughts
- content of Story_Load is all te model get right now to know anbout the story.
- content of Story_Load must have a method that is coherent for the model to target retrieval. Is that slugs? id of some sort? Title? Any other? This should be defined so follows a coherent pattern. Could also be "if not slug than id, if neither than title" (exmample only, best standard based on current code is priority- dont reinvent waht is already the general pattern, unless there is a real reason to do so). What matter is that: A) there is a choerent pattern. B) Story Load provides the "hook" so the pattern cna be exercised.

## 1. What the model should be able to get a part form what already gets form Stroy_load?

- a) Full entities: Frontamatter + sections 
Usefull when wanting a full picture of a single entity. Both defined values (frontamtter) and the notes on elaboration of those (sections - these may be decision, remainign questions, defined toughts etc etc). Must include also empty or default fields or sections to uderstand what has not been developed yet. 
  - Only one at the time
  
- b) Partial entities: Frontmatter + selected sections
Usefull when wanting a focused picture of one single entity. Focus on one aspect of it. Still frontmatter as a whole for generalized understanding and than only selected sections for the focus. Must include also empty or default fields and sections to uderstand what has not been developed yet. 
  - Only one at the time

- c) Structured only: Frontmatter (must include section list)
Usefull when wanting an understanding of what has been defined. Its  is a more genral view of an entity that deos not require focused attention to itself , but generally to relate it to other exiting ones
  - multiple at the time
  - cross entities

- d) Partial Structured: Selected frontmatter field/s (SEE MORE BELOW in 3.)
Specific details about an entity values. Needed for things like targeted decisions and changes or specific relational comparison
  - multiple at the time (one or more for each entity and for multiple entities)
  - can also be one single section for one entity
  - cross entities

### Entities level "unfilled"
Is important that when we pass structured and section content we also pass the empty and defauklt fields.(see 1.) We should not omit thsoe fields there, as this allows us to skip having an unfilled list as entity level, while allowing the model to clearly see what has been left unfilled, or not set (default vlaues that state not set, already express this in the very sentence they pass)


## 2. The ARC special cases (structural and relational elements)

### ARC
Characthers ARCs are made of:
- entity arc
- multiple entotitie beats

THes should be retrieve individually (see 1.)
Howevere these should also be retrived in a way that exposed their relations for which the model can get astructural understanding of an arc.
There should be a way to get an arc for a character that shows the whole structure of it.

This is basically a complex c) case (see 1.) where:
Structured only: Frontmatter
Multiple at the time
preorganized to hirechy and squencing.
 Such as:
 Arc x (frontmatter) contains beats (frontmatters) - no sections

 This is basically a focused retrival on a structural element taht focuses on its overall shape and relations

### STORY VALUE
Same idea as above could and probably shoulb be used for structural value (set in project.md and expressed in each act, sequence, scene - different form characther act value wich is alreadty tracked in the arc) as those have haevy relational impact.
Ability to track a value across acts, sequences and scenes in one single call.
For each act individually or all acts (all story)

### STRUCTURAL ELEMENTS
Same as above, strcutural elements such as dramatic_role inciting incident, climax, sequence climax, story climax should be trackeable as one individual retival for a single act or multiple acts so that structural elemnt integrity and verifications and decision can be made. 
Ability to track a structurla elements across acts, sequences and scenes in one single call.
For each act idividually or all acts (all story)
All existing scenes should appear (in the most compact way (id or title _ needs to match our retrival patters for scenes , see section 0. of this doc)
Drammatic function should always be included, even if empty for each.
Organized is a structured manner Act taht incldues sequences taht includes scenes. Dteils on each level about existing field values. (similar to the current way we prtesnet the act/sequence/scene structure on story_load, but minimal and focsed on structural elements)

#### STRUCTURAL ELEMENTS with plots
This should have an option for full structural elements taht:
THis should also include plots values (setups, crisis, climax, payoffs) and differentiate by plot type (main plot vs subplot)
This would be useful to make sure that structural elements are not only consisten on a story level, but they also match at some level the plot structural elements. Even thou a subplot, or a main plot may non necessarely match their climax, some of them shouold always match (eg: main plot climax geenrally matches story climax).
We dont need to do this verufication ourself, but the existance of this presentation of the data allows the model to reason on this aspect

NOTE: no need to expose FALSE values, TRUE only. (eg: is_story_climax=true is meaningfull, while is_story_climax=false is not. THese false or positive are already exposed at scene level)

## 3. Partial Structured: Selected frontmatter field/s

Instead of pasing single fields, we could consider grouping them in such a way that we optimized for both exposure oflimited ammount of fields (a compromise to single field load) while at teh same time allowing us to provide a sltuoin that allows fo some level of relation between fields to be mantaind, and also functions that cna be than resued in more complex solutions above

FOr example, if the agent want to look at the field "arc_value" for a character, instead of passing that single fiels we could pass all of:

      "arc_type": "(value)" or "" or "Default",
      "arc_value": "(value)" or "" or "Default",
      "arc_value_at_open": "(value)" or "" or "Default",
      "arc_value_at_close": "(value)" or "" or "Default"

So thsi way we cna group all fields based on some categorization and gain:
- have less paramathers the llm needs to ba aware
- mantain a level of relationship the llm may wrongly ignore
- maybe help pther more complex functions

And lose:
- specific granularity to single field level
- add more context (acccaptable if solves more porblems than creates and is well categorized so the grouping is not too big)

## 4. Unfilled fields

Right now we have all Unfilled fields at Story_load level

We should consider movign that functionality to a specific retrival or load check and remove it from the Story_load payload.


## QUESTIONS STILL REMAINING
1) Which of these functionalitooes above belong to story_load and which to Story_retieve? There is  a case to be made that Stroy_load may have to handle all of SECTION 2 and 3, as they are relational
2) is there any real need to distinguis story load from story_retrieve? Should be instead one tool?
3) How doe we handle: 1- retrival/load (depending on above questions) for each entity type (characters, word, scene, etc etc), but laso multiple retrivals with an elegant soution?
4) How do we handle
      "arc_value_at_close": "(value)" or "" or "Default"

So thsi way we cna group all fields based on some categorization and gain:
- have less paramathers the llm needs to ba aware
- mantain a level of relationship the llm may wrongly ignore
- maybe help pther more complex functions

And lose:
- specific granularity to single field level
- add more context (acccaptable if solves more porblems than creates and is well categorized so the grouping is not too bi)


































































































































