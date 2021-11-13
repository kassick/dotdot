from __future__ import annotations

import os
import os.path
import subprocess
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


def _norm_path(pth: str) -> str:
    pth = os.path.expanduser(pth)
    pth = os.path.abspath(pth)
    pth = os.path.normpath(pth)

    return pth


TBaseAction = TypeVar('TBaseAction', bound='BaseAction')
@dataclass
class BaseAction:
    package_path: str

    def msg(self) -> str:
        return str(self)

    def execute(self, dry_run=False):
        """Executes the action"""
        print('EXECUTING BASE for', type(self))
        raise Exception('not implemented')

    def materialize(self: TBaseAction) -> TBaseAction:
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

        dest_abs_path = self.destination
        if not os.path.isabs(dest_abs_path):
            dest_abs_path = os.path.join('~', dest_abs_path)

        dest_dirname = os.path.dirname(os.path.expanduser(dest_abs_path))

        if self.source_is_local:
            pkg_abs_path = os.path.abspath(self.package_path)
            pkg_path_from_home = os.path.relpath(pkg_abs_path, dest_dirname)
            object_path = os.path.join(pkg_path_from_home, self.source)
        else:
            object_path = self.source


        return type(self)(
            package_path=str(Path.home()),
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
class MkdirAction(BaseAction):
    target_dir: str = ""

    def msg(self):
        return f'MKDIR {self.target_dir}'

    def materialize(self) -> MkdirAction:
        if os.path.isabs(self.target_dir):
            return self

        path = os.path.join('~', self.target_dir)

        return MkdirAction(package_path=str(Path.home()),
                           target_dir=path)

    def execute(self, dry_run=False):
        if not dry_run:
            target = os.path.expanduser(self.target_dir)
            if os.path.exists(target):
                if not os.path.isdir(target):
                    raise Exception(f'can not create path {target}: it exists as a file')
                pass
            else:
                os.mkdir(target)

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

    def msg(self) -> str:
        lines = [
            f'SYMLINK RECUSRIVELY {self.destination} -> {self.source}'
        ]

        lines.extend(f'- {action.msg()}' for action in self._actions)

        return '\n'.join(lines)

    def __post_init__(self):
        '''
        link_recursively: dir1

        self.src: dir1
        self.dst: .dir1

        dir1 contains file1, file2
        '''

        if not self.source_is_local:
            raise InvalidActionDescription(f'can not recursively symlink external url {self.source}')

        recurse_origin = os.path.join(self.package_path, self.source)

        for root, directories, files in os.walk(recurse_origin):
            link_src_dir = os.path.relpath(root, recurse_origin)

            for file_name in files:
                src_file = os.path.join(self.source, link_src_dir, file_name)
                src_file = os.path.normpath(src_file)

                dst_path = os.path.normpath(os.path.join(self.destination, link_src_dir))
                dst = os.path.join(dst_path, file_name)

                mkdir_action = MkdirAction(package_path='~', target_dir=dst_path)
                link_action = SymlinkAction(
                    package_path=self.package_path,
                    source=src_file,
                    destination=dst
                )

                self._actions.append(mkdir_action)
                self._actions.append(link_action)

    def materialize(self):
        materialized = super().materialize()
        materialized._actions = [a.materialize() for a in self._actions]

        return materialized

    def execute(self, dry_run=False):
        for action in self._actions:
            print('-', action.msg())
            action.execute(dry_run)


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

    def msg(self) -> str:
        lines = ['EXECUTE']
        for cmd in self.cmds:
            _cmds = cmd.split('\n')
            lines.append(f'- {_cmds[0]}')
            lines.extend(f'  {_cmd}' for _cmd in _cmds[1:])

        return '\n'.join(lines)

    def execute(self, dry_run=False):
        if dry_run: return

        def fail_guard_generator():
            for cmd in self.cmds:
                yield cmd
                cmd = fr'cmd'
                yield f'if [ $? != 0 ] ; then echo Failed to execute command \\" \'{cmd}\' \\"; exit 1; fi'

        cmds = list(fail_guard_generator())

        cur_dir = os.getcwd()
        try:
            os.chdir(os.path.abspath(self.package_path))
            script = '\n'.join(cmds)
            input = script.encode('utf-8')
            result = subprocess.run(['sh'], input=input)

            if result.returncode != 0:
                raise Exception('Failed during execute action')
        finally:
            os.chdir(cur_dir)


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
