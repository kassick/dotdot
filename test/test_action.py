from pathlib import Path
import pytest
import os

from dotdot.actions import SymlinkAction

# @pytest.fixture
# def mock_home(monkeypatch):
#     monkeypatch.setenv('HOME', os.getcwd())


def test_final_paths_updates_object_path():
    action = SymlinkAction(package_path='pkg/path', source='a_file', destination='.a_file')

    result = action.materialize()

    assert result == SymlinkAction(
        package_path=str(Path.home()),
        source=os.path.abspath('pkg/path/a_file'),
        destination=os.path.expanduser('~/.a_file')
    )

def test_final_paths_ignores_non_local_object():
    action = SymlinkAction(
        package_path='pkg/path',
        source='http://some.file/at/path',
        destination='.a_file',
        source_is_local=False
    )

    result = action.materialize()

    assert result == SymlinkAction(
        package_path=str(Path.home()),
        source='http://some.file/at/path',
        destination=os.path.expanduser('~/.a_file'),
        source_is_local=False
    )
