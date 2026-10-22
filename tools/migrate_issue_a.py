"""One-time migration: old milestone flags/pointers → plot roles.

NOT part of the application. Run once against existing projects:
    python -m tools.migrate_issue_a --project <path> --dry-run
    python -m tools.migrate_issue_a --project <path> --apply
"""
import argparse
import json
import sys
from pathlib import Path

# Removed fields per entity type
REMOVED_FIELDS = {
    "scene": ["is_inciting_incident", "is_sequence_climax", "is_act_climax", "is_story_climax"],
    "project": ["inciting_incident_scene_id", "story_climax_scene_id"],
    "act": ["act_climax_scene_id"],
    "sequence": ["seq_climax_scene_id"],
}

# Flags that are NOT carried over (position follows from theory)
NOT_CARRIED_OVER = ["is_sequence_climax", "is_act_climax"]


def migrate(project_path: Path, dry_run: bool = True) -> dict:
    from core.db import get_db

    conn = get_db(project_path)
    try:
        report = {
            "project": project_path.name,
            "dry_run": dry_run,
            "actions": [],
            "warnings": [],
            "not_migrated": [],
        }

        # Find main plot
        main_plot = None
        for plot_id, plot_extra_json in conn.execute(
            "SELECT id, extra FROM entities WHERE type='plot' AND is_deleted=0"
        ):
            plot_extra = json.loads(plot_extra_json or "{}")
            if plot_extra.get("plot_scope") == "main":
                main_plot = plot_id
                break

        if not main_plot:
            report["warnings"].append(
                "No main plot found — story-level milestones cannot be migrated"
            )

        # Read project extra
        proj_row = conn.execute(
            "SELECT extra FROM entities WHERE type='project' AND is_deleted=0 LIMIT 1"
        ).fetchone()
        proj_extra = json.loads(proj_row[0]) if proj_row and proj_row[0] else {}

        # Read all scenes
        scenes = {}
        for scene_id, scene_extra_json in conn.execute(
            "SELECT id, extra FROM entities WHERE type='scene' AND is_deleted=0"
        ):
            scenes[scene_id] = json.loads(scene_extra_json or "{}")

        # Check each scene
        for scene_id, extra in scenes.items():
            # Check inciting incident
            if extra.get("is_inciting_incident"):
                if not main_plot:
                    report["warnings"].append(
                        f"Scene '{scene_id}' has is_inciting_incident=True but no main plot — cannot migrate"
                    )
                else:
                    existing = conn.execute(
                        "SELECT 1 FROM relations WHERE from_id=? AND to_id=? AND kind='plot_inciting_incident'",
                        (main_plot, scene_id)
                    ).fetchone()
                    if not existing:
                        report["actions"].append(
                            f"ADD inciting_incident role: {main_plot} -> {scene_id}"
                        )
                        if not dry_run:
                            conn.execute(
                                "INSERT INTO relations (from_id, to_id, kind, note, \"order\") VALUES (?, ?, ?, '', 1)",
                                (main_plot, scene_id, "plot_inciting_incident")
                            )
                    else:
                        report["actions"].append(
                            f"SKIP inciting_incident role: {main_plot} -> {scene_id} (already exists)"
                        )

                # Check conflict with project pointer
                pointer = proj_extra.get("inciting_incident_scene_id")
                if pointer and pointer != scene_id:
                    report["warnings"].append(
                        f"CONFLICT: scene '{scene_id}' has is_inciting_incident=True "
                        f"but project.inciting_incident_scene_id='{pointer}'"
                    )

            # Check story climax
            if extra.get("is_story_climax"):
                if not main_plot:
                    report["warnings"].append(
                        f"Scene '{scene_id}' has is_story_climax=True but no main plot — cannot migrate"
                    )
                else:
                    existing = conn.execute(
                        "SELECT 1 FROM relations WHERE from_id=? AND to_id=? AND kind='plot_climax'",
                        (main_plot, scene_id)
                    ).fetchone()
                    if not existing:
                        report["actions"].append(
                            f"ADD climax role: {main_plot} -> {scene_id}"
                        )
                        if not dry_run:
                            conn.execute(
                                "INSERT INTO relations (from_id, to_id, kind, note, \"order\") VALUES (?, ?, ?, '', 1)",
                                (main_plot, scene_id, "plot_climax")
                            )
                    else:
                        report["actions"].append(
                            f"SKIP climax role: {main_plot} -> {scene_id} (already exists)"
                        )

                pointer = proj_extra.get("story_climax_scene_id")
                if pointer and pointer != scene_id:
                    report["warnings"].append(
                        f"CONFLICT: scene '{scene_id}' has is_story_climax=True "
                        f"but project.story_climax_scene_id='{pointer}'"
                    )

            # Report not-carried-over flags
            for flag in NOT_CARRIED_OVER:
                if extra.get(flag):
                    report["not_migrated"].append(
                        f"Scene '{scene_id}' has {flag}=True — not migrated (position follows from theory)"
                    )

        # Check project pointer conflicts (pointer set but no flag)
        if proj_extra.get("inciting_incident_scene_id"):
            pointer = proj_extra["inciting_incident_scene_id"]
            if pointer in scenes and not scenes[pointer].get("is_inciting_incident"):
                report["warnings"].append(
                    f"CONFLICT: project.inciting_incident_scene_id='{pointer}' "
                    f"but scene '{pointer}' has is_inciting_incident=False"
                )

        if proj_extra.get("story_climax_scene_id"):
            pointer = proj_extra["story_climax_scene_id"]
            if pointer in scenes and not scenes[pointer].get("is_story_climax"):
                report["warnings"].append(
                    f"CONFLICT: project.story_climax_scene_id='{pointer}' "
                    f"but scene '{pointer}' has is_story_climax=False"
                )

        # Strip removed fields
        if not dry_run:
            for entity_type, fields in REMOVED_FIELDS.items():
                for entity_id, extra_json in conn.execute(
                    "SELECT id, extra FROM entities WHERE type=? AND is_deleted=0",
                    (entity_type,)
                ):
                    extra = json.loads(extra_json or "{}")
                    changed = False
                    for field in fields:
                        if field in extra:
                            del extra[field]
                            changed = True
                    if changed:
                        conn.execute(
                            "UPDATE entities SET extra=? WHERE id=?",
                            (json.dumps(extra), entity_id)
                        )

            conn.commit()

        return report
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate old milestone flags to plot roles")
    parser.add_argument("--project", required=True, help="Project path")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not change anything")
    parser.add_argument("--apply", action="store_true", help="Apply the migration")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Specify --dry-run or --apply", file=sys.stderr)
        sys.exit(1)

    dry_run = args.dry_run
    project_path = Path(args.project)

    if not project_path.exists():
        print(f"Project not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    report = migrate(project_path, dry_run=dry_run)

    print(f"Migration report for {report['project']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print()

    if report["actions"]:
        print("Actions:")
        for action in report["actions"]:
            print(f"  {action}")
        print()

    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"  {warning}")
        print()

    if report["not_migrated"]:
        print("Not migrated:")
        for item in report["not_migrated"]:
            print(f"  {item}")
        print()

    if not report["actions"] and not report["warnings"] and not report["not_migrated"]:
        print("Nothing to migrate.")


if __name__ == "__main__":
    main()
