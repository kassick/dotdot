import os
import pytest

from dotdot.dot import Package
from dotdot.actions import SymlinkAction, SymlinkRecursiveAction, ExecuteAction

@pytest.fixture
def mock_home(monkeypatch):
    monkeypatch.setenv('HOME', os.getcwd())

def test_load_from_folder(mock_home):
    pkg = Package.from_dot_path('test/dots/pkg1')

    # The returned paths are absolute, but since we do not want

    expected = Package(
        'pkg1',
        'package1',
        'test/dots/pkg1',
        [SymlinkAction('test/dots/pkg1', source='file1', destination='.file1'),
         SymlinkRecursiveAction(package_path='test/dots/pkg1', source='dir1', destination='.dir1'),
         SymlinkRecursiveAction(package_path='test/dots/pkg1', source='dir2', destination='user_dir_2'),
         ExecuteAction(package_path='test/dots/pkg1',
                       cmds=['echo cmd1',
                             'echo cmd2',
                             ('echo cmd3\n'
                              '[ "a" == "b" ]\n'
                              'echo cmd4\n'
                              )
                             ]
                       ),
         ExecuteAction(package_path='test/dots/pkg1', cmds=['./cmd.sh'])
         ]
    )

    assert expected == pkg


def test_load_from_file(mock_home):
    # pkg2 is a simple file
    # actions should symlink the file pkg2 on test/dots to ~/.pkg2
    pkg = Package.from_dot_path('test/dots/pkg2')

    # The returned paths are absolute, but since we do not want

    expected = Package(
        'pkg2',
        None,
        'test/dots',
        [SymlinkAction('pkg2', '.pkg2'),
         ]
    )

    assert expected == pkg


def test_load_from_folder_with_no_spec(mock_home):
    # pkg3 is a folder without spec
    # default action is to assume that there'd be a symlink every file under
    # the path
    pkg = Package.from_dot_path('test/dots/pkg3')

    # The returned paths are absolute, but since we do not want

    expected = Package(
        'pkg3',
        None,
        'test/dots/pkg3',
        [SymlinkAction('afile', '.afile'),
         SymlinkAction('other_file', '.other_file')
         ]
    )

    assert expected == pkg


def test_scan(mock_home):
    pkgs, errors = Package.scan('test/dots')

    pkg_names = {(pkg.name) for pkg in pkgs}
    expected = {'pkg1', 'pkg2', 'pkg3'}

    assert pkg_names == expected
