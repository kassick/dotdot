from __future__ import annotations

import os
import os.path
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, Type, Union

from dotdot.exceptions import InvalidActionDescription, InvalidActionType
from dotdot.spec import SPEC_FILE_NAME


class BaseAction:
    def execute(self):
        """Executes the action"""
        raise Exception('not implemented')

    def to_final_paths(self, package_path: str) -> BaseAction:
        """Returns a new action with the paths adjusted to package_path and $HOME

        - any source file will be adjusted to be relative to the user's $HOME
          Executing the tool from the path ~/src/dotfiles , with a package in
          dots/pkg1, an action on the file `file1` would have the file reference
          adjusted to ~/src/dotfiles/dots/pkg1/file1

        - any destination path will be prefixed with ~/
        """
        return self

    @classmethod
    def parse_entries(cls, package_path: str, entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        """Parses an action entry list and returns the base actions"""
        raise Exception('not implemented')


@dataclass
class SrcDestAction(BaseAction):
    """An action that has a source and a destination

    source is relative to a package base path

    destination is relative to the users's home
    """

    # file or folder path relative to the package data path ; or URL
    source: str

    # where the object should be stored, relative to the user's home
    destination: str

    # whether object_path is local
    source_is_local: bool = True

    @classmethod
    def parse_one_entry(cls, package_path: str, entry: Union[str, dict[str, str]]) -> Sequence[BaseAction]:
        if isinstance(entry, str):
            src = entry
            dst = f'.{entry}'
        else:
            src = entry['from']
            dst = entry['to']

        if src == '*':
            has_destination = dst != '.*'
            package_contents = os.listdir(package_path)

            def mk_dst(_path):
                if has_destination:
                    return os.path.join(dst, _path)
                else:
                    return f'.{_path}'

            return [
                cls(_file, mk_dst(_file))
                for _file in package_contents
                if _file != SPEC_FILE_NAME
            ]

        return [cls(src, dst)]

    @classmethod
    def parse_entries(cls, package_path: str, entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            parsed
            for e in entries
            for parsed in cls.parse_one_entry(package_path, e)
        ]

    def to_final_paths(self, package_path: str) -> BaseAction:
        """
        Makes an action paths absolute
        """

        if self.source_is_local:
            pkg_abs_path = os.path.abspath(package_path)
            pkg_path_from_home = os.path.relpath(pkg_abs_path, Path.home())
            object_path = os.path.join(pkg_path_from_home, self.source)
        else:
            object_path = self.source

        dest_abs_path = self.destination
        if not os.path.isabs(dest_abs_path):
            dest_abs_path = os.path.join('~', dest_abs_path)

        return type(self)(
            object_path,
            dest_abs_path,
            source_is_local=self.source_is_local
        )

@dataclass
class SymlinkAction(SrcDestAction):
    """An action that symlinks a file to the a destination"""
    def execute(self):
        print('symlink', self)


@dataclass
class SymlinkRecursiveAction(SrcDestAction):
    """An action that symlinks all files inside a folder (recursively) to the
    corresponding paths on the destination

    Given a folder with this structure:
      folder1/file1
      folder1/subfolder1/file2
      folder1/subfolder1/file3

    SymlinkRecursiveAction('folder1', 'dest_folder_1') will generate the
    following symlinks and path structure:
      ~/dest_folder_1/file1 -> ~/$PACKAGE_PATH/folder1/file1
      ~/dest_folder_1/subfolder1/file2 -> ~/$PACKAGE_PATH/folder1/subfolder1/file2
      ~/dest_folder_1/subfolder1/file3 -> ~/$PACKAGE_PATH/folder1/subfolder1/file3

    where $PACKAGE_PATH is the path of the package containing folder1

    """
    def execute(self):
        print('symlink recursive', self)


@dataclass
class GitCloneAction(SrcDestAction):
    """An action that clones or updates a git repository to a given folder

    TODO: How to add branch?
    TODO: Maybe override parse_one_entry? adding

          |    actions:
          |    - gitclone: git@some.repo/path/last

          would symlink to ~/git@some.repo/path instead of ~/last, so we probably need
          to really rewrite the classmethod
    """
    branch: Optional[str] = None

    @classmethod
    def parse_one_entry(cls, package_path: str, entry: Union[str, dict[str, str]]) -> Sequence[BaseAction]:
        if isinstance(entry, str):
            raise InvalidActionDescription(f'gitclone requires a dict with fields url and to')
        else:
            try:
                src = entry['url']
                dst = entry['to']
            except KeyError as e:
                raise InvalidActionDescription(f'Missing gitclone field {e.args[0]}')

            branch = entry.get('branch')

            return [GitCloneAction(src, dst, branch=branch)]

    def execute(self):
        print('git clone', self)


@dataclass
class ExecuteAction(BaseAction):
    cmd: str

    def execute(self):
        print('execute', self)

    @classmethod
    def parse_entries(cls, package_path: str, entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            ExecuteAction(cmd)
            for cmd in entries
        ]


def action_class_from_str(s: str) -> Type[BaseAction]:
    s = s.lower()

    if s == 'link': return SymlinkAction
    elif s == 'link_recursively': return SymlinkRecursiveAction
    elif s == 'git_clone': return GitCloneAction
    elif s == 'execute': return ExecuteAction
    else:
        raise InvalidActionType(s)
