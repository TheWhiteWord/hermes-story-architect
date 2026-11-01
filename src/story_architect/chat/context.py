"""Harness-agnostic bootstrap builder for the chat agent."""
from __future__ import annotations


def build_bootstrap(project_slug: str, project_name: str, attachments: list | None = None) -> str:
    attachments = attachments or []
    parts = [
        "You are working inside Story Architect, a local screenwriting and story-development app. "
        f'The user has the project "{project_name}" ({project_slug}) open in the app and is talking to you in its side panel. '
        'Read and change the project only through the story tools (MCP server "story"); don\'t guess project facts. '
        "Propose changes by staging a draft: the app shows each draft to the user as a card with Approve and Reject buttons. "
        "Commit only after the user approves (you will be told), unless they explicitly ask you to apply changes directly. "
        "Call action=list at session start for open drafts."
        "Never claim a change was made unless a tool confirmed it. Use dashboard_link when pointing the user at a place in the app.",
    ]
    if attachments:
        labels = ", ".join(f"{a.get('kind', '')}:{a.get('id', '')} ({a.get('label', '')})" for a in attachments)
        parts.append(f"The user attached these parts of the app to their message: {labels}. Use the tools to read them if relevant.")
    return " ".join(parts)
