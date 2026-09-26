"""Test connection lifecycle — each tool call opens + closes its own connection."""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from tools.story_import import handler as import_handler
from tools.story_export import handler as export_handler
from tools.story_backup import handler as backup_handler


def test_import_does_not_leak_connections(fixture_path):
    """Import opens and closes its own connection."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        # Patch get_db to track connections
        from core import db
        original_get_db = db.get_db
        connections = []

        def tracking_get_db(project_path):
            conn = original_get_db(project_path)
            connections.append(conn)
            return conn

        with patch.object(db, 'get_db', side_effect=tracking_get_db):
            result = import_handler({"project": str(project_path), "root_path": Path(tmp)})

        data = json.loads(result)
        assert data["success"] is True

        # All connections should be closed
        for conn in connections:
            # Trying to use a closed connection raises ProgrammingError
            with pytest.raises(Exception):
                conn.execute("SELECT 1")


def test_export_does_not_leak_connections(fixture_path):
    """Export opens and closes its own connection."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        # First import
        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        from core import db
        original_get_db = db.get_db
        connections = []

        def tracking_get_db(project_path):
            conn = original_get_db(project_path)
            connections.append(conn)
            return conn

        with patch.object(db, 'get_db', side_effect=tracking_get_db):
            result = export_handler({"project": str(project_path), "root_path": Path(tmp)})

        data = json.loads(result)
        assert data["success"] is True

        for conn in connections:
            with pytest.raises(Exception):
                conn.execute("SELECT 1")


def test_backup_does_not_leak_connections(fixture_path):
    """Backup opens and closes its own connection."""
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "save-the-children"
        shutil.copytree(str(fixture_path), str(project_path))

        # First import
        import_handler({"project": str(project_path), "root_path": Path(tmp)})

        from core import db
        original_get_db = db.get_db
        connections = []

        def tracking_get_db(project_path):
            conn = original_get_db(project_path)
            connections.append(conn)
            return conn

        with patch.object(db, 'get_db', side_effect=tracking_get_db):
            result = backup_handler({"project": str(project_path), "root_path": Path(tmp)})

        data = json.loads(result)
        assert data["success"] is True

        for conn in connections:
            with pytest.raises(Exception):
                conn.execute("SELECT 1")
