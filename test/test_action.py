from pathlib import Path
import sys
from unittest import TestCase
from _pytest.monkeypatch import MonkeyPatch
import pytest
import yaml
import os

from dot import dot as dotdot
from dot.dot import SymlinkAction

@pytest.fixture
def mock_home(monkeypatch):
    monkeypatch.setenv('HOME', os.getcwd())


def test_final_paths_updates_object_path(mock_home):
    action = SymlinkAction('a_file', '.a_file')

    result = action.to_final_paths('pkg/path')

    assert result == SymlinkAction(
        'pkg/path/a_file',
        '~/.a_file')

def test_final_paths_ignores_non_local_object(mock_home):
    action = SymlinkAction(
        'http://some.file/at/path',
        '.a_file',
        source_is_local=False
    )

    result = action.to_final_paths('pkg/path')

    assert result == SymlinkAction(
        'http://some.file/at/path',
        '~/.a_file',
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
