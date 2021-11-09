from pathlib import Path
from unittest import TestCase
from _pytest.monkeypatch import MonkeyPatch
import yaml
import os
import pytest

from dot import dot as dotdot
from dot.dot import ExecuteAction, Package, SymlinkAction, SymlinkRecursiveAction

@pytest.fixture
def mock_home(monkeypatch):
    monkeypatch.setenv('HOME', os.getcwd())

def test_load_from_folder(mock_home):
    pkg = Package.from_dot_folder('test/dots/pkg1')

    # The returned paths are absolute, but since we do not want

    expected = Package(
        'package1',
        [SymlinkAction('file1', '.file1'),
         SymlinkRecursiveAction('dir1', '.dir1'),
         SymlinkRecursiveAction('dir2', 'user_dir_2'),
         ExecuteAction('cmd1'),
         ExecuteAction('cmd2'),
         ExecuteAction('./cmd')
         ]
    )

    assert expected == pkg
