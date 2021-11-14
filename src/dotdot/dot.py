from __future__ import annotations

import os
import os.path
from dataclasses import dataclass
from typing import Optional, Sequence, Set, Tuple

import yaml
from yaml.error import YAMLError

from dotdot.actions import BaseAction, SymlinkAction, action_class_from_str
from dotdot.exceptions import InvalidActionType, InvalidPackageException
from dotdot.spec import SPEC_FILE_NAME


@dataclass
class Package:
    name: str
    description: Optional[str]
    package_path: str
    variants: Set[str]
    actions: Sequence[BaseAction]

    @staticmethod
    def _from_dot_file(path: str) -> Package:
        # The most simple type of dot:
        # the path is the file or folder that must be symlinked to the home path

        base_name = os.path.basename(path)
        package_path = os.path.dirname(path)
        dest = f'.{base_name}'

        actions = [SymlinkAction(package_path=package_path, source=base_name, destination=dest)]
        print(actions)
        print(package_path)

        return Package(base_name, None, package_path, variants={'default'}, actions=actions)

    @staticmethod
    def _from_dot_directory(path: str) -> Package:
        # a bunch of files or folders that must be symlinked
        base_name = os.path.basename(path)

        actions = []
        for source in os.listdir(path):
            dest = f'.{source}'

            actions.append(SymlinkAction(source, dest))

        return Package(base_name, None, path, variants={'default'}, actions=actions)

    @staticmethod
    def from_dot_path(path: str, variant: Optional[str] = None) -> Package:

        # default variant is always default
        variant = variant or 'default'

        metadata_file = os.path.join(path, SPEC_FILE_NAME)
        if os.path.isfile(metadata_file):

            dot_name = os.path.basename(path)

            # parse a yaml containing the name and actions to be performed
            with open(metadata_file, 'r') as fh:
                data: dict = yaml.safe_load(fh)

            description = data.get('description') or os.path.basename(path)

            # check for variants
            # if the key does not exist, create a default variant from the actions entry
            variants = data.get('variants')
            variants = variants or {'default': data.get('actions', [])}

            try:
                actions_list = variants[variant]
            except KeyError:
                raise InvalidPackageException(f"Package {dot_name} does not contain a variant named `{variant}\'")

            # flatten the action list, in case we have nested actions list
            def action_iterator(actions):
                for action in actions:
                    if isinstance(action, list):
                        yield from action_iterator(action)
                    else:
                        yield action

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
            for action_input_dict in action_iterator(actions_list):
                for key, entry in action_input_dict.items():
                    # lift entry to normalize it as a list
                    if isinstance(entry, str):
                        entry = [entry]

                    action_class = action_class_from_str(key)
                    entries = action_class.parse_entries(path, entry)
                    output_actions.extend(entries)

            return Package(
                dot_name,
                description,
                path,
                variants=set(variants.keys()),
                actions=output_actions
            )

        else:
            # simple file, link it to home
            if os.path.isfile(path): return Package._from_dot_file(path)
            # folder without spec, link all files
            elif os.path.isdir(path): return Package._from_dot_directory(path)
            else:
                raise InvalidPackageException(
                    f'path {path} does not contain a valid package'
                )

    @staticmethod
    def scan(path: str) -> Tuple[Sequence[Package], Sequence[Tuple[str, Exception]]]:
        """Scans a path for dots and """
        contents = os.listdir(path)

        results = []
        errors = []
        for dot in contents:
            dot_path = os.path.join(path, dot)
            try:
                results.append(Package.from_dot_path(dot_path))
            except Exception as e:
                errors.append((dot, e))

        return results, errors
