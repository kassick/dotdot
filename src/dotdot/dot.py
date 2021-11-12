from __future__ import annotations

import os
import os.path
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

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
    actions: Sequence[BaseAction]

    @staticmethod
    def _from_dot_file(path: str) -> Package:
        # The most simple type of dot:
        # the path is the file or folder that must be symlinked to the home path

        base_name = os.path.basename(path)
        package_path = os.path.dirname(path)
        dest = f'.{base_name}'

        output_actions = [SymlinkAction(base_name, dest)
                            #.to_final_paths(os.path.dirname(path))
                            ]

        return Package(base_name, None, package_path, output_actions)

    @staticmethod
    def _from_dot_directory(path: str) -> Package:
        # a bunch of files or folders that must be symlinked
        base_name = os.path.basename(path)

        output_actions = []
        for source in os.listdir(path):
            dest = f'.{source}'

            output_actions.append(SymlinkAction(source, dest)
                                  #.to_final_paths(path)
                                  )

        return Package(base_name, None, path, output_actions)

    @staticmethod
    def from_dot_path(path: str) -> Package:

        metadata_file = os.path.join(path, SPEC_FILE_NAME)
        if os.path.isfile(metadata_file):
            # parse a yaml containing the name and actions to be performed
            with open(metadata_file, 'r') as fh:
                data = yaml.safe_load(fh)

            description = data.get('description') or os.path.basename(path)
            list = data.get('actions') or []

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

                    action_class = action_class_from_str(key)
                    entries = action_class.parse_entries(path, entry)
                    output_actions.extend(entries)

            return Package(
                os.path.basename(path),
                description,
                path,
                output_actions
                #[act.to_final_paths(path) for act in output_actions]
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
