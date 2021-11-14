from __future__ import annotations

import os
import os.path
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence, Type, TypeVar, Union

from dotdot.exceptions import InvalidActionDescription, InvalidActionType
from dotdot.spec import SPEC_FILE_NAME
from git.repo import Repo

# ############
# Action store
__ACTION_STORE = {}


def action(name):

    def annotation(cls):
        if name in __ACTION_STORE:
            raise Exception(f'Error: Duplicated action {name}')

        __ACTION_STORE[name] = cls

        return cls

    return annotation


def get_actions_help() -> dict:
    return {
        action: action_cls.__doc__ for action,
        action_cls in __ACTION_STORE.items()
    }


def action_class_from_str(s: str) -> Type[BaseAction]:
    s = s.lower()

    try:
        return __ACTION_STORE[s]
    except KeyError:
        raise InvalidActionType(s)


# #################
# Utility functions
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

# #######
# Actions


@dataclass
class BaseAction:
    """
    Base Action class.
    """

    package_path: str

    def msg(self) -> str:
        return str(self)

    def execute(self):
        """Executes the action"""
        print('EXECUTING BASE for', type(self))
        raise Exception('not implemented')

    def materialize(self: TBaseAction) -> TBaseAction:
        """Returns a new action with the paths adjusted to package_path and
        $HOME

        - any source file will be adjusted to be relative to the user's $HOME
          Executing the tool from the path ~/src/dotfiles , with a package in
          dots/pkg1, an action on the file `file1` would have the file
          reference adjusted to ~/src/dotfiles/dots/pkg1/file1

        - any destination path will be prefixed with ~/
        """
        return self

    @classmethod
    def parse_entries(
            cls,
            package_path: str,
            entries: Union[str,
                           Sequence[Any]]) -> Sequence[BaseAction]:
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
    def parse_one_entry(
            cls,
            package_path: str,
            entry: Union[str,
                         dict[str,
                              str]]) -> Sequence[BaseAction]:
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
                cls(
                    package_path=package_path,
                    source=_file,
                    destination=mk_dst(_file))
                for _file in package_contents
                if _file != SPEC_FILE_NAME
            ]

        return [cls(package_path=package_path, source=src, destination=dst)]

    @classmethod
    def parse_entries(
            cls,
            package_path: str,
            entries: Union[str,
                           Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            parsed for e in entries
            for parsed in cls.parse_one_entry(package_path,
                                              e)
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
            source_is_local=self.source_is_local)


@action('link')
@dataclass
class SymlinkAction(SrcDestAction):
    """Symlinks a file or directory to a destination

    Links `file` to ~/.file
      - link: file

    Links `file1` to ~/.file1, `file2` to ~/.file2
      - link:
          - file1
          - file2

    Links `file1` to ~/.file1, `file2` to ~/some/path/file2
      - link:
          - file1
          - from: file2
            to: some/path/file2
    """

    def msg(self) -> str:
        return f'SYMLINK {self.destination} -> {self.source}'

    def execute(self):
        dst = os.path.expanduser(self.destination)
        if os.path.exists(dst):
            # it it's a link pointing to the same path as we want to link
            # there's nothing to do
            if os.path.islink(dst) and os.readlink(dst) == self.source:
                print('LINK ALREADY IN PLACE -- SKIPPING')
                return

            new_name = mk_backup_name(dst)
            print('BACK UP', dst, 'TO', new_name)

            os.rename(dst, new_name)

        os.symlink(self.source, dst)


@action('copy')
@dataclass
class CopyAction(SrcDestAction):
    """Copies a file or directory to a destination

    Copies `file` to ~/.file
      - copy: file

    Copies `file1` to ~/.file1, `file2` to ~/.file2
      - copy:
          - file1
          - file2

    Copies `file1` to ~/.file1, `file2` to ~/some/path/file2
      - copy:
          - file1
          - from: file2
            to: some/path/file2
    """

    def msg(self) -> str:
        return f'COPY {self.destination} -> {self.source}'

    def execute(self):
        # src in a SrcDestAction is always either an absolute path or
        # relative to the user's home, but while copying we're not
        # at the user's home, so we need to manipulate the path to make
        # it absolute
        src = os.path.expanduser(self.source)
        if not os.path.isabs(src):
            src = os.path.join(Path.home(), self.source)

        dst = os.path.expanduser(self.destination)
        if os.path.exists(dst):
            new_name = mk_backup_name(dst)
            print('Backing up', dst, 'to', new_name)

            os.rename(dst, new_name)

        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:

            shutil.copy(src, dst)


@action('mkdir')
@dataclass
class MkdirAction(BaseAction):
    """Creates a directory tree

    Creates directories ~/.local/, if it doesn't already exist, and directory
    share under ~/.local
        - mkdir: .local/share

    Creates directories ~/.local/share and ~/.local/etc
        - mkdir:
            - .local/share
            - .local/etc
    """

    target_dir: str = ""

    def msg(self):
        return f'MKDIR {self.target_dir}'

    def materialize(self) -> MkdirAction:
        path = os.path.expanduser(self.target_dir)
        if not os.path.isabs(path):
            path = os.path.join('~', self.target_dir)

        return MkdirAction(package_path=str(Path.home()), target_dir=path)

    def execute(self):
        target = os.path.expanduser(self.target_dir)
        if os.path.exists(target):
            if not os.path.isdir(target):
                raise Exception(
                    f'can not create path {target}: it exists as a file')
            pass
        else:
            os.makedirs(target)

    @classmethod
    def parse_entries(
            cls,
            package_path: str,
            entries: Union[str,
                           Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            MkdirAction(str(Path.home()),
                        target_dir=entry) for entry in entries
        ]


@action('link_recursively')
@dataclass
class SymlinkRecursiveAction(SrcDestAction):
    """Symlinks all files, recursively

    Given the following tree on the dot folder:
    - dir1/subdir1/file1
    - dir1/file2
    - dir2/subdir2/file3

    Creates links ~/.dir1/subdir1/file1 , ~/.dir1/file2
        - link_recursively: dir1


    Creates links ~/.dir1/subdir1/file1 , ~/.dir1/file2 , ~/.dir2/subdir2/file3
        - link_recursively:
            - dir1
            - dir2

    Creates ~/.elsewhere/else/subdir1/file1 and ~/.elsewhere/else/file2
        - link_recursively:
            - from: dir1
              to: .elsewhere/else

    Creates ~/.elsewhere/else/file3
        - link_recursively:
            - from: dir2/subdir2
              to: .elsewhere/else
    """

    _actions: List[BaseAction] = field(default_factory=list)

    def msg(self) -> str:
        lines = [f'SYMLINK RECUSRIVELY {self.destination} -> {self.source}']

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
            raise InvalidActionDescription(
                f'can not recursively symlink external url {self.source}')

        recurse_origin = os.path.join(self.package_path, self.source)

        for root, directories, files in os.walk(recurse_origin):
            link_src_dir = os.path.relpath(root, recurse_origin)

            for file_name in files:
                src_file = os.path.join(self.source, link_src_dir, file_name)
                src_file = os.path.normpath(src_file)

                dst_path = os.path.normpath(
                    os.path.join(self.destination,
                                 link_src_dir))
                dst = os.path.join(dst_path, file_name)

                mkdir_action = MkdirAction(
                    package_path='~',
                    target_dir=dst_path)
                link_action = SymlinkAction(
                    package_path=self.package_path,
                    source=src_file,
                    destination=dst)

                self._actions.append(mkdir_action)
                self._actions.append(link_action)

    def materialize(self):
        materialized = super().materialize()
        materialized._actions = [a.materialize() for a in self._actions]

        return materialized

    def execute(self):
        for action in self._actions:
            print('-', action.msg())
            action.execute()


@action('git_clone')
@dataclass
class GitCloneAction(SrcDestAction):
    """Clones a git repository

    When the destination path does not exist,
        - git_clone:
          - from: git@url/path
            to: some/path
    will create the path and clone the repo, using either `main` or `master` as
    the branch

    When the destination path does not exist,
        - git_clone:
          - from: git@url/path
            to: some/path
            branch: develop
    will create the path and clone the repo, using either `develop` as the
    branch

    If destination exists but it's not a git repo, the tool will initialize it
    as an empty repo.

    When the destination is an existing repopath exists, this action will try
    to pull changes from the remote. Depending on the state of the repo,
    though, the baviour may change:

    - No `branch` specified:
        - local ref is `main`, remote has ref `main`:
          pull changes
        - local ref is `master`, remote has ref `main`:
          checkout `main` and pull changes
        - local ref is `master', remote has ref `master`, but not `main`:
          pull changes
        - local ref is `new-feature`, remote has ref `main`:
          checkout `main`, pull changes - Branch `develop` defined in the spec:
          always checkout `develop` and pull from the origin
    """

    branch: Optional[str] = None
    source_is_local: bool = False

    def msg(self) -> str:
        s = f'GITCLONE FROM {self.source} TO {self.destination}'
        if self.branch:
            s += f' AT BRANCH {self.branch}'

        return s

    @classmethod
    def parse_one_entry(
            cls,
            package_path: str,
            entry: Union[str,
                         dict[str,
                              str]]) -> Sequence[BaseAction]:
        if isinstance(entry, str):
            raise InvalidActionDescription(
                'git_clone requires a dict with fields url and to')
        else:
            try:
                src = entry['url']
                dst = entry['to']
            except KeyError as e:
                raise InvalidActionDescription(
                    f'Missing gitclone field {e.args[0]}')

            branch = entry.get('branch')

            return [
                GitCloneAction(
                    package_path=package_path,
                    source=src,
                    destination=dst,
                    branch=branch,
                    source_is_local=False)
            ]

    def execute(self):
        if os.path.isfile(self.destination):
            raise Exception(
                f"Can not initialize a git repo at {self.destination}: "
                "it's a file"
            )

        # create or load the repo
        try:
            repo = Repo(self.destination)
        except Exception:
            print(f'- Initialize repo at {self.destination}')
            repo = Repo.init(self.destination)
            repo.create_remote('origin', self.source)

        if not len(repo.remotes):
            # bare repo, use origin
            dot_remote = repo.create_remote('origin', self.source)
        else:
            # find remote by url or create one
            try:
                dot_remote = next(
                    remote for remote in repo.remotes
                    if remote.url == self.source)
            except Exception:
                print(f'- Add remote {self.source}')
                dot_remote = repo.create_remote('from_dot_setup', self.source)

        print('- Fetching changes')
        dot_remote.fetch()

        # find by branch name
        if self.branch:
            branch_names = [self.branch]
        else:
            branch_names = [repo.head.ref.name, 'main', 'master']

        remote_head = None
        local_head = None

        for branch_name in branch_names:
            # locate the remote head
            # skip if not found
            try:
                remote_head = dot_remote.refs[branch_name]
            except Exception:
                continue

            # locate or create local head and set it to track the remote head
            try:
                local_head = repo.refs[branch_name]
            except Exception:
                remote_head.checkout()
                local_head = repo.create_head(f'refs/heads/{branch_name}')
                local_head.set_tracking_branch(remote_head)

            # found both heads
            break

        print(f'- Checking out ref {local_head.name}')
        local_head.checkout()

        print('- Pulling changes from remote')
        dot_remote.pull()


@action('execute')
@dataclass
class ExecuteAction(BaseAction):
    """Executes commands under a new shell

    The command will be executed on the same path as the spec file

    Executes command `cmd`
        - execute: cmd

    Executes commands `cmd1`, `cmd2` and `cmd3`, stopping the execution if
    any command fails:
        - execute:
            - cmd1
            - cmd2
            - cmd3


    The execution checks for the exist-status after the execution of every item
    under the `execute` rule.

    Executes `cmd1` and `cmd2`, but does not pause execution if `cmd1` fails:
        - execute:
            - |
                cmd1
                cmd2
            - cmd3

    Every 'execute:' rule runs under a shell. You can use variables and control
    flow, but every item under execute must be an independent command, so if,
    for, case, etc must be given as a single item.
        - execute:
            - read GUESS
            - |
                if [ "$GUESS" == 'correct' ]; then
                   echo Correct
                else
                   false
                fi
            - echo You get a prize
    """

    cmds: Sequence[str] = field(default_factory=list)

    def msg(self) -> str:
        lines = ['EXECUTE']
        for cmd in self.cmds:
            _cmds = cmd.split('\n')
            lines.append(f'- {_cmds[0]}')
            lines.extend(f'  {_cmd}' for _cmd in _cmds[1:])

        return '\n'.join(lines)

    def execute(self):

        def fail_guard_generator():
            for cmd in self.cmds:
                yield cmd
                yield '''
                if [ $? != 0 ] ; then
                    echo Failed to execute last command ;
                    exit 1;
                fi
                '''

        cmds = fail_guard_generator()

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
    def parse_entries(
            cls,
            package_path: str,
            entries: Union[str,
                           Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        invalid_entries = [e for e in entries if not isinstance(e, str)]
        if invalid_entries:
            raise InvalidActionDescription(
                f'execute action expects strings, received {invalid_entries}')

        return [ExecuteAction(package_path=package_path, cmds=entries)]
