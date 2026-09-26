"""Project resolution — fuzzy match user input to project folder.

Resolving to the WRONG project is worse than failing, because a write to the
wrong story looks like it succeeded. FUZZY_THRESHOLD (40, shared with
screenplay title matching) is far too permissive here: at 40 an unrelated name
like "ghost" scores 72 against a short slug and is accepted. PROJECT_THRESHOLD
is tuned for this job — see the table in tasks/task_21*/final_tools.
"""
from pathlib import Path
from rapidfuzz import fuzz, process
from core.constants import FUZZY_THRESHOLD

# Stricter than FUZZY_THRESHOLD on purpose, and local to this module: a miss
# here silently writes to the wrong project, whereas a screenplay title miss
# just fails to find a candidate. 75 keeps every plausible near-match
# ("the children" -> save-the-children, 75) while rejecting unrelated input
# ("ghost", 72; "a totally unrelated phrase", 45).
PROJECT_THRESHOLD = 75


def resolve_project(user_input: str, vault_path: Path) -> Path:
    """Resolve user input to a project folder path.
    
    1. Direct path (if user_input is an existing directory)
    2. Exact slug match
    3. Fuzzy match on slug + project name
    4. No match → raise ValueError
    """
    # Direct path — if user_input is an existing directory, use it
    direct = Path(user_input)
    if direct.is_dir():
        return direct
    
    projects_dir = vault_path / "projects"
    
    if not projects_dir.exists():
        raise ValueError(f"No projects directory found at {projects_dir}")
    
    # Exact slug match
    exact = projects_dir / user_input
    if exact.is_dir():
        return exact
    
    # Fuzzy match on slug + project name
    candidates = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        candidates.append((project_dir.name, project_dir))
        
        # Also match on the DB project name
        db_path = project_dir / ".story" / "story.db"
        if db_path.exists():
            import sqlite3
            conn = None
            try:
                conn = sqlite3.connect(str(db_path))
                row = conn.execute(
                    "SELECT name FROM entities WHERE type='project' LIMIT 1"
                ).fetchone()
                if row and row[0]:
                    candidates.append((row[0], project_dir))
            except sqlite3.Error:
                pass
            finally:
                if conn is not None:
                    conn.close()
    
    if not candidates:
        raise ValueError(f"No projects found in {projects_dir}")
    
    names = [c[0] for c in candidates]
    result = process.extractOne(user_input, names, scorer=fuzz.WRatio)
    
    if result and result[1] >= PROJECT_THRESHOLD:
        matched_name = result[0]
        for name, path in candidates:
            if name == matched_name:
                return path
    
    # No match → suggest similar or list all
    available = sorted(set(names))
    raise ValueError(
        f"No project matching '{user_input}'. "
        f"Available projects: {', '.join(available)}"
    )
