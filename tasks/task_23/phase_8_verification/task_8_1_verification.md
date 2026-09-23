# Task 8.1: Verification & Edge Cases

## Goal
Verify the complete relationship refactor works end-to-end and handle edge cases.

## Steps

### 8.1.1: Full test suite
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -m pytest tests/ -x -q
```
- **Expected**: All tests pass

### 8.1.2: Manual end-to-end test
- **Action**: Create a test project with 2 characters + 1 asymmetric relationship:
```bash
# 1. Create project
python -c "
from tools.story_create import handler
import json
result = handler({
    'entity_type': 'project',
    'slug': 'test-rel',
    'project': '/tmp',
    'frontmatter': {'name': 'Test Rel', 'logline': 'Testing relationships'},
    'vault_path': '/tmp'
})
print(json.loads(result))
"

# 2. Create characters
python -c "
from tools.story_create import handler
import json
handler({
    'entity_type': 'character',
    'slug': 'alice',
    'project': '/tmp/projects/test-rel',
    'frontmatter': {'name': 'Alice', 'story_role': 'Protagonist', 'one_sentence': 'A test character'},
    'vault_path': '/tmp'
})
handler({
    'entity_type': 'character',
    'slug': 'bob',
    'project': '/tmp/projects/test-rel',
    'frontmatter': {'name': 'Bob', 'story_role': 'Supporting', 'one_sentence': 'Another test character'},
    'vault_path': '/tmp'
})
"

# 3. Create asymmetric relationship
python -c "
from tools.story_create import handler
import json
result = handler({
    'entity_type': 'relationship',
    'slug': 'alice-bob',
    'project': '/tmp/projects/test-rel',
    'frontmatter': {
        'name': 'Alice & Bob',
        'characters': ['alice', 'bob'],
        'perspectives': {
            'alice': {'label': 'Friend', 'feeling': 'Trusts him', 'type': 'ally', 'strength': 0.8},
            'bob': {'label': 'Acquaintance', 'feeling': 'Wary of her', 'type': 'rival', 'strength': -0.3, 'secret': True}
        },
        'status': 'active'
    },
    'vault_path': '/tmp'
})
print(json.loads(result))
"

# 4. Load and verify
python -c "
from tools.story_load import handler
import json
result = json.loads(handler({'project': '/tmp/projects/test-rel', 'vault_path': '/tmp'}))
print('Characters:', [c['name'] for c in result['characters']])
print('Relationships:', list(result.get('relationships', {}).keys()))
for c in result['characters']:
    if c['id'] == 'alice':
        print('Alice relationships:', c.get('relationships', []))
"

# 5. Export and verify relationships folder
python -c "
from tools.story_export import handler
import json
result = handler({'project': '/tmp/projects/test-rel', 'vault_path': '/tmp'})
print(json.loads(result))
"
ls /tmp/projects/test-rel/relationships/

# 6. Re-import and verify
python -c "
from tools.story_import import handler
import json
result = handler({'project': '/tmp/projects/test-rel', 'vault_path': '/tmp'})
print(json.loads(result))
"

# 7. Dashboard
python -c "
from tools.story_dashboard import handler
import json
result = handler({'project': '/tmp/projects/test-rel', 'vault_path': '/tmp'})
print(json.loads(result))
"
```

### 8.1.3: Edge case — Delete one character
- **Action**: Delete a character that has a relationship
- **Expected**: Relationship entity remains but references a non-existent character (broken reference)
- **Alternative**: Cascade-delete the relationship (if desired — needs implementation decision)
- **Note**: The plan doesn't specify cascade behavior. Document current behavior.

### 8.1.4: Edge case — Three characters, triangle relationships
- **Action**: Create 3 characters with 3 relationships (A-B, B-C, A-C)
- **Expected**: `story_data.relationships` has 3 entries, graph shows triangle

### 8.1.5: Edge case — Same pair, multiple relationships
- **Action**: Create two relationships between the same pair (e.g., `alice-bob` and `alice-bob-2`)
- **Expected**: Both appear as separate relationship entities
- **Note**: This is a key advantage over the old system (PK was `(from_id, to_id, kind)`)

### 8.1.6: Edge case — Computed field guard
- **Action**: Attempt to create/edit a character with `relationships` field
- **Expected**: Field is silently ignored (skipped by computed guard)
```bash
python -c "
from tools.story_create import handler
import json
# Try to create character with relationships field
result = handler({
    'entity_type': 'character',
    'slug': 'test-guard',
    'project': '/tmp/projects/test-rel',
    'frontmatter': {
        'name': 'Test Guard',
        'story_role': 'Minor',
        'relationships': [{'with': 'alice', 'label': 'Hacker'}]  # Should be ignored
    },
    'vault_path': '/tmp'
})
print(json.loads(result))
# Verify the relationships field was NOT set
"
```

### 8.1.7: Naming convention verification
- **Action**: Grep for any remaining `char_rels` references:
```bash
grep -rn "char_rels" --include="*.py" .
```
- **Expected**: No results (all removed in Phase 4)

- **Action**: Grep for any remaining `character_relationship` references:
```bash
grep -rn "character_relationship" --include="*.py" .
```
- **Expected**: Only in migration/compatibility comments, not in active code paths

- **Action**: Verify all entity types use consistent naming:
```bash
grep -rn "relationship" --include="*.py" core/ tools/ | grep -v test | grep -v ".pyc"
```

### 8.1.8: Code maintenance check
- **Action**: Verify no dead code remains:
```bash
# Check for unused imports
python -m pyflakes core/ tools/ 2>/dev/null || echo "pyflakes not available"

# Check for relationship-related TODOs
grep -rn "TODO.*relationship" --include="*.py" .
grep -rn "FIXME.*relationship" --include="*.py" .
```

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -m pytest tests/ -x -q
grep -rn "char_rels" --include="*.py" . && echo "FAIL: char_rels still present" || echo "PASS: no char_rels references"
grep -rn "character_relationship" --include="*.py" . && echo "FAIL: character_relationship still present" || echo "PASS: no character_relationship references"
```

## Checklist
- [ ] Full test suite passes
- [ ] End-to-end create → load → export → re-import → dashboard works
- [ ] Asymmetric relationships show correctly in load output
- [ ] Computed field guard works (relationships ignored on create/edit)
- [ ] Delete character edge case documented
- [ ] Triangle relationships work
- [ ] Multiple relationships per pair work
- [ ] No `char_rels` references remain
- [ ] No `character_relationship` references in active code
- [ ] Naming conventions consistent
- [ ] No dead code or TODOs related to relationships

## Notes
- This phase is the final gate — do not merge until all checks pass
- Edge cases should be documented in SKILL.md if they reveal user-facing behavior
- Consider adding a migration guide if existing projects have old-style relationships
