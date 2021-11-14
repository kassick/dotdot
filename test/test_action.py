from pathlib import Path
import sys
from unittest import TestCase
from _pytest.monkeypatch import MonkeyPatch
import pytest
import yaml
import os

from dotdot.actions import SymlinkAction

@pytest.fixture
def mock_home(monkeypatch):
    monkeypatch.setenv('HOME', os.getcwd())


def test_final_paths_updates_object_path(mock_home):
    action = SymlinkAction(package_path='pkg/path', source='a_file', destination='.a_file')

    result = action.materialize()

    assert result == SymlinkAction(
        package_path=str(Path.home()),
        source='pkg/path/a_file',
        destination='~/.a_file'
    )

def test_final_paths_ignores_non_local_object(mock_home):
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
        destination='~/.a_file',
        source_is_local=False
    )

# def test_final_paths_ignores_empty_destination(mock_home):
#     action = SymlinkAction(
#         'http://some.file/at/path',
#         None,
#         source_is_local=False
#     )

#     result = action.to_final_paths('pkg/path')

#     assert result == SymlinkAction(
#         'http://some.file/at/path',
#         None,
#         source_is_local=False
#     )
