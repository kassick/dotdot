from __future__ import annotations

import os
import os.path
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Union

import yaml


METADATA_FILE = 'spec.yaml'

class InvalidActionType(Exception): pass

# class ActionType(Enum):
#     EXECUTE = 0
#     SYMLINK = 1
#     SYMLINK_RECURSIVELY = 2
#     GIT_CLONE = 3

#     def is_src_dst(self):
#         return self in {ActionType.SYMLINK,
#                         ActionType.SYMLINK_RECURSIVELY,
#                         ActionType.GIT_CLONE
#                         }

#     @staticmethod
#     def from_str(s: str) -> ActionType:
#         s = s.lower()

#         if s == 'link': return ActionType.SYMLINK
#         elif s == 'link_recursively': return ActionType.SYMLINK_RECURSIVELY
#         elif s == 'execute': return ActionType.EXECUTE
#         elif s == 'git_clone': return ActionType.GIT_CLONE
#         else:
#             raise InvalidActionType(f'Invalid action {s}')



class BaseAction:
    def execute(self): raise Exception('not implemented')
    def to_final_paths(self, package_path: str) -> BaseAction:
        return self

    @staticmethod
    def parse_entries(entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        raise Exception('not implemented')


@dataclass
class SrcDestAction(BaseAction):
    # file or folder path relative to the package data path ; or URL
    source: str

    # where the object should be stored, relative to the user's home
    destination: str

    # whether object_path is local
    source_is_local: bool = True

    @staticmethod
    def parse_one_entry(entry: Union[str, dict[str, str]], cls: Callable) -> BaseAction:
        if isinstance(entry, str):
            src = entry
            dst = f'.{entry}'
        else:
            src = entry['from']
            dst = entry['to']

        print('parsing one entry', entry, 'builder is ', cls)
        return cls(src, dst)

    @staticmethod
    def parse_entries(entries: Union[str, Sequence[Any]], cls: Callable) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            SrcDestAction.parse_one_entry(e, cls)
            for e in entries
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

        dest_abs_path = os.path.join('~', self.destination)

        return type(self)(
            object_path,
            dest_abs_path,
            source_is_local=self.source_is_local
        )

@dataclass
class SymlinkAction(SrcDestAction):
    def execute(self):
        print('symlink', self)


@dataclass
class SymlinkRecursiveAction(SrcDestAction):
    def execute(self):
        print('symlink recursive', self)


@dataclass
class GitCloneAction(SrcDestAction):
    def execute(self):
        print('git clone', self)


@dataclass
class ExecuteAction(BaseAction):
    cmd: str

    def execute(self):
        print('execute', self)

    @staticmethod
    def parse_entries(entries: Union[str, Sequence[Any]]) -> Sequence[BaseAction]:
        if isinstance(entries, str):
            entries = [entries]

        return [
            ExecuteAction(cmd)
            for cmd in entries
        ]
def entries_parser_from_str(s: str) -> Callable:
    s = s.lower()

    if s == 'link': return lambda e: SrcDestAction.parse_entries(e, SymlinkAction)
    elif s == 'link_recursively': return lambda e: SrcDestAction.parse_entries(e, SymlinkRecursiveAction)
    elif s == 'git_clone': return lambda e: SrcDestAction.parse_entries(e, GitCloneAction)
    elif s == 'execute': return ExecuteAction.parse_entries
    else:
        raise InvalidActionType(f'Invalid action {s}')


# @dataclass
# class Action:
#     # file or folder path relative to the package data path ; or URL
#     source: str

#     # where the object should be stored, relative to the user's home
#     destination: Optional[str]

#     action_type: ActionType

#     # whether object_path is local
#     source_is_local: bool = True

#     def to_final_paths(self, package_path: str) -> Action:
#         """
#         Makes an action paths absolute
#         """

#         if self.source_is_local:
#             pkg_abs_path = os.path.abspath(package_path)
#             pkg_path_from_home = os.path.relpath(pkg_abs_path, Path.home())
#             object_path = os.path.join(pkg_path_from_home, self.source)
#         else:
#             object_path = self.source

#         if self.destination:
#             dest_abs_path = os.path.join('~', self.destination)
#         else:
#             dest_abs_path = None

#         return Action(
#             object_path,
#             dest_abs_path,
#             self.action_type,
#             source_is_local=self.source_is_local
#         )


# def parse_one_entry(entry: Union[str, dict[str, str]], action_type: ActionType) -> Action:
#     if isinstance(entry, str):
#         src = entry
#         dst = f'.{entry}'
#     else:
#         src = entry['from']
#         dst = entry['to']

#     return Action(src, dst, action_type)


# def parse_src_dst_entry(
#         entries: Union[str, Sequence[Union[str, dict]]],
#         action_type: ActionType
# ) -> Sequence[Action]:
#     if isinstance(entries, str):
#         entries = [entries]

#     return [
#         parse_one_entry(e, action_type)
#         for e in entries
#     ]


@dataclass
class Package:
    name: str
    actions: Sequence[BaseAction]

    @staticmethod
    def from_dot_folder(path: str) -> Package:
        print('cwd', os.getcwd())
        base_name = os.path.basename(path)

        metadata_file = os.path.join(path, METADATA_FILE)
        if not os.path.isfile(metadata_file):

            if os.path.isfile(path):
                # The most simple type of dot:
                # the path is the file or folder that must be symlinked to the home path

                dest = f'.{path}'
                output_actions = [SymlinkAction(path, dest)#.to_final_paths(os.path.dirname(path))
                                  ]

                return Package(base_name, output_actions)
            elif os.path.isdir(path):
                # a bunch of files or folders that must be symlinked

                output_actions = []
                for source in os.listdir(path):
                    dest = f'.{source}'

                    output_actions.append(SymlinkAction(source, dest)#.to_final_paths(path)
                                          )

                return Package(base_name, output_actions)
        else:
            # parse a yaml containing the name and actions to be performed
            with open(metadata_file, 'r') as fh:
                data = yaml.safe_load(fh)

            name = data['name'] or base_name
            list = data['actions'] or []

            output_actions = []

            # input_actions_list is a list of dictionaries
            # dictionary can be a simple entry
            #    ex. {"link": "some_file"}
            # a list of text entries
            #    ex. {"link": ["file1", "file2"]}
            # a list of dictionary entries
            #    ex {"link": [
            #                 {"from": "source_path", "to": "dst_path"},
            #                 {"from": "source_path", "to": "dst_path"},
            #                ]
            #       }
            for action_input_dict in list:
                for key, entry in action_input_dict.items():
                    # lift entry to normalize it as a list
                    if isinstance(entry, str):
                        entry = [entry]

                    action_parser = entries_parser_from_str(key)
                    output_actions.extend(action_parser(entry))


                    # for entry in list:
                    #     if action_type == ActionType.EXECUTE:
                    #         output_actions.append(Action(entry, None, action_type))
                    #     elif action_type == ActionType.SYMLINK:
                    #         if isinstance(entry, str):
                    #             dest = os.path.join(Path.home(), f'.{os.path.basename(entry)}')
                    #             output_actions.append(Action(entry, dest, action_type))
                    #         elif isinstance(entry, Sequence):
                    #             for sub_entry in entry:
                    #                 if isinstance(sub_entry, str):
                    #                     src = entry
                    #                     dest = os.path.join(Path.home(), f'.{os.path.basename(sub_entry)}')
                    #                 elif isinstance(sub_entry, dict):
                    #                     src = os.path.join(os.path.dirname(entry))
                    #                     sub_entry['source']

            return Package(
                name,
                output_actions #[act.to_final_paths(path) for act in output_actions]
            )
            # for action_input_dict in list:
            #     for key, entry in action_input_dict.items():
            #         # lift entry to normalize it as a list
            #         if isinstance(entry, str):
            #             entry = [entry]

            #         action_cls =
            #         action_type = ActionType.from_str(key)
            #         if action_type.is_src_dst():
            #             output_actions.extend(parse_src_dst_entry(entry, action_type))
            #         elif action_type == ActionType.EXECUTE:
            #             raise Exception('execute not implemented')
            #         else:
            #             raise InvalidActionType(f'action type {action_type} not supported')


            #         # for entry in list:
            #         #     if action_type == ActionType.EXECUTE:
            #         #         output_actions.append(Action(entry, None, action_type))
            #         #     elif action_type == ActionType.SYMLINK:
            #         #         if isinstance(entry, str):
            #         #             dest = os.path.join(Path.home(), f'.{os.path.basename(entry)}')
            #         #             output_actions.append(Action(entry, dest, action_type))
            #         #         elif isinstance(entry, Sequence):
            #         #             for sub_entry in entry:
            #         #                 if isinstance(sub_entry, str):
            #         #                     src = entry
            #         #                     dest = os.path.join(Path.home(), f'.{os.path.basename(sub_entry)}')
            #         #                 elif isinstance(sub_entry, dict):
            #         #                     src = os.path.join(os.path.dirname(entry))
            #         #                     sub_entry['source']

            # return Package(
            #     name,
            #     [act.to_final_paths(path) for act in output_actions]
            # )
