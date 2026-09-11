"""Project resolution — fuzzy match user input to project folder."""
from pathlib import Path
from rapidfuzz import fuzz, process
from core.constants import FUZZY_THRESHOLD


def resolve_project(user_input: str, vault_path: Path) -> Path:
    """Resolve user input to a project folder path.
    
    1. Exact slug match
    2. Fuzzy match on slug + project name
    3. No match → raise ValueError
    """
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
        
        # Also match on project name
        project_md = project_dir / "project.md"
        if project_md.exists():
            import frontmatter
            post = frontmatter.load(project_md)
            if "name" in post.metadata:
                candidates.append((post.metadata["name"], project_dir))
    
    if not candidates:
        raise ValueError(f"No projects found in {projects_dir}")
    
    names = [c[0] for c in candidates]
    result = process.extractOne(user_input, names, scorer=fuzz.WRatio)
    
    if result and result[1] >= FUZZY_THRESHOLD:
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
