from __future__ import annotations

import os
import os.path
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence, Type, TypeVar, Union

from dotdot.exceptions import InvalidActionDescription, InvalidActionType
from dotdot.spec import SPEC_FILE_NAME


def mk_backup_name(file_name: str) -> str:
    """creates a backup file name for a given file"""
    name = os.path.basename(file_name)
    dir_name = os.path.dirname(file_name)
    dir_name = os.path.expanduser(dir_name)

    bk_name = f'{name}.bk'
    if bk_name[0] == '.':
        bk_name = '_' + bk_name[1:]

    i = 1
    attempt = bk_name

    while os.path.exists(os.path.join(dir_name, attempt)):
        attempt = f'{bk_name}.{i}'
        i += 1

        if i > 10:
            raise Exception(f'Too many backup files for {file_name}')

    return os.path.join(dir_name, attempt)


TBaseAction = TypeVar('TBaseAction', bound='BaseAction')
@dataclass
class BaseAction:
    package_path: str

    def msg(self):
        raise Exception('not implemented')

    def execute(self, dry_run=False):
        """Executes the action"""
        raise Exception('not implemented')

    def materialize(self: TBaseAction, package_path: str) -> TBaseAction:
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


TSrcDestAction = TypeVar('TSrcDestAction', bound='SrcDestAction')
@dataclass
class SrcDestAction(BaseAction):
    """An action that has a source and a destination

    source is relative to a package base path

    destination is relative to the users's home
    """

    # file or folder path relative to the package data path ; or URL
    source: str = ""

    # where the object should be stored, relative to the user's home
    destination: str = ""

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
                cls(package_path=package_path,
                    source=_file,
                    destination=mk_dst(_file))
                for _file in package_contents
                if _file != SPEC_FILE_NAME
            ]

        return [cls(package_path=package_path,
                    source=src,
                    destination=dst)
                ]

    @classmethod
    def parse_entries(cls, package_path: str, entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            parsed
            for e in entries
            for parsed in cls.parse_one_entry(package_path, e)
        ]

    def materialize(self: TSrcDestAction) -> TSrcDestAction:
        """
        Makes an action paths absolute
        """

        if self.source_is_local:
            pkg_abs_path = os.path.abspath(self.package_path)
            pkg_path_from_home = os.path.relpath(pkg_abs_path, Path.home())
            object_path = os.path.join(pkg_path_from_home, self.source)
        else:
            object_path = self.source

        dest_abs_path = self.destination
        if not os.path.isabs(dest_abs_path):
            dest_abs_path = os.path.join('~', dest_abs_path)

        return type(self)(
            package_path=self.package_path,
            source=object_path,
            destination=dest_abs_path,
            source_is_local=self.source_is_local
        )

@dataclass
class SymlinkAction(SrcDestAction):
    """An action that symlinks a file to the a destination"""

    def msg(self) -> str:
        return f'SYMLINK {self.destination} -> {self.source}'

    def execute(self, dry_run=False):

        if not dry_run:
            dst = os.path.expanduser(self.destination)
            if os.path.exists(dst):
                new_name = mk_backup_name(dst)
                print('Backing up', dst, 'to', new_name)

                os.rename(dst, new_name)

                # TODO BACK UP

            os.symlink(self.source, dst)


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

    _actions: List[BaseAction] = field(default_factory=list)


    def _create_sub_actions(self):
        print('sub actions!')
        return self

    def materialize(self) -> SymlinkRecursiveAction:
        materialized = super().materialize()

        materialized._create_sub_actions()

        return materialized


    def execute(self, dry_run=False):
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

            return [GitCloneAction(package_path=package_path,
                                   source=src,
                                   destination=dst,
                                   branch=branch)
                    ]

    def execute(self, dry_run=False):
        print('git clone', self)


@dataclass
class ExecuteAction(BaseAction):
    cmds: Sequence[str] = field(default_factory=list)

    def execute(self, dry_run=False):
        print('execute', self)

    @classmethod
    def parse_entries(cls, package_path: str, entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        invalid_entries = [e for e in entries if not isinstance(e, str)]
        if invalid_entries:
            raise InvalidActionDescription(f'execute action expects strings, received {invalid_entries}')

        return [
            ExecuteAction(package_path=package_path, cmds=entries)
        ]


def action_class_from_str(s: str) -> Type[BaseAction]:
    s = s.lower()

    if s == 'link': return SymlinkAction
    elif s == 'link_recursively': return SymlinkRecursiveAction
    elif s == 'git_clone': return GitCloneAction
    elif s == 'execute': return ExecuteAction
    else:
        raise InvalidActionType(s)
