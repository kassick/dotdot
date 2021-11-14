import os
import pytest

from dotdot.pkg import Package
from dotdot.actions import GitCloneAction, SymlinkAction, SymlinkRecursiveAction, ExecuteAction, CopyAction


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
        variants={'default'},
        actions=[
            SymlinkAction(
                'test/dots/pkg1',
                source='file1',
                destination='.file1'),
            CopyAction(
                'test/dots/pkg1',
                source='file1',
                destination='file1_again'),
            SymlinkRecursiveAction(
                package_path='test/dots/pkg1',
                source='dir1',
                destination='.dir1'),
            SymlinkAction(
                package_path='test/dots/pkg1',
                source='dir1/file_in_dir_1',
                destination='.dir1/file_in_dir_1',
            ),
            SymlinkAction(
                package_path='test/dots/pkg1',
                source='dir1/subdir1/file_in_subdir1',
                destination='.dir1/subdir1/file_in_subdir1',
            ),
            SymlinkRecursiveAction(
                package_path='test/dots/pkg1',
                source='dir2',
                destination='user_dir_2'),
            ExecuteAction(
                package_path='test/dots/pkg1',
                cmds=[
                    'echo cmd1',
                    'echo cmd2',
                    ('echo cmd3\n'
                     '[ "a" == "b" ]\n'
                     'echo cmd4\n')
                ]),
            ExecuteAction(package_path='test/dots/pkg1',
                          cmds=['./cmd.sh']),
            GitCloneAction(
                package_path='test/dots/pkg1',
                source='https://github.com/kassick/evil-iedit-state',
                destination='tmp/evil-iedit-state')
        ])

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
        variants={'default'},
        actions=[
            SymlinkAction('test/dots',
                          'pkg2',
                          '.pkg2'),
        ])

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
        variants={'default'},
        actions=[
            SymlinkAction('afile',
                          '.afile'),
            SymlinkAction('other_file',
                          '.other_file')
        ])

    assert expected == pkg


def test_scan(mock_home):
    pkgs, errors = Package.scan('test/dots')

    pkg_names = {(pkg.name) for pkg in pkgs}
    expected = {'pkg1', 'pkg2', 'pkg3', 'pkg6_variants'}

    assert pkg_names == expected


def test_variant(mock_home):
    pkg_path = 'test/dots/pkg6_variants'
    result = Package.from_dot_path(pkg_path, variant='fedora')

    def exe(cmds):
        return ExecuteAction(pkg_path, cmds)

    expected = Package(
        'pkg6_variants',
        'A Package with variants',
        pkg_path,
        variants={'fedora',
                  'ubuntu',
                  'default'},
        actions=[
            exe(['echo fedora only first']),
            exe(['echo cmd1']),
            exe(['echo cmd2\necho cmd3\n']),
            exe(['echo fedora only last'])
        ])

    assert result == expected
