from typing import Sequence
from unittest import TestCase

import yaml

from dotdot.actions import (ExecuteAction, GitCloneAction,
    InvalidActionDescription, SymlinkAction)
from dotdot.spec import SPEC_FILE_NAME


class TestParseSrcDestEntry(TestCase):
    def setUp(self):

        self.single_entry_text = yaml.safe_load(
            """
            actions:
            - link: a_file
            """
        )

        self.multiple_entries_text = yaml.safe_load(
            """
            actions:
            - link:
              - a_file
              - other_file
              - yet_another
            """
        )

        self.single_entry_dict = yaml.safe_load(
            """
            actions:
            - link:
              - from: a_file
                to: some_file
            """
        )

        self.multiple_entries_dict = yaml.safe_load(
            """
            actions:
            - link:
              - from: a_file
                to: some_file
              - from: other_file
                to: other_file_dest
            """
        )

        self.single_entry_wildcard_text = yaml.safe_load(
            # links every file `f` to their corresponting `~/.{f}`
            """
            actions:
            - link: '*'
            """
        )

        self.single_entry_wildcard_dict = yaml.safe_load(
            # links every file `f` to the corresponding `~/.local/share/{f}`
            """
            actions:
            - link:
              - from: '*'
                to: .local/share
            """
        )

    def test_parse_one_entry_text(self):

        link_single_entry = self.single_entry_text['actions'][0]['link']
        result = SymlinkAction.parse_one_entry('some_path', link_single_entry)

        expected = [SymlinkAction(package_path='some_path', source='a_file', destination='.a_file')]

        assert result == expected

    def test_parse_one_entry_dict(self):

        # this format has a list as link value, take the first entry
        link_single_entry = self.single_entry_dict['actions'][0]['link'][0]
        result = SymlinkAction.parse_one_entry('some_path', link_single_entry)

        expected = [SymlinkAction(package_path='some_path', source='a_file', destination='some_file')]

        assert result == expected

    def test_parse_single_entry_text(self):
        link_entry = self.single_entry_text['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction(package_path='some_path', source='a_file', destination='.a_file')
        ]

        assert result == expected

    def test_parse_multiple_entries_text(self):
        link_entry = self.multiple_entries_text['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction(package_path='some_path', source='a_file', destination='.a_file'),
            SymlinkAction(package_path='some_path', source='other_file', destination='.other_file'),
            SymlinkAction(package_path='some_path', source='yet_another', destination='.yet_another'),
        ]

        assert result == expected

    def test_parse_single_entry_dict(self):
        link_entry = self.single_entry_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction(package_path='some_path', source='a_file', destination='some_file')
        ]

        assert result == expected

    def test_parse_multiple_entries_dict(self):
        link_entry = self.multiple_entries_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction(package_path='some_path', source='a_file', destination='some_file'),
            SymlinkAction(package_path='some_path', source='other_file', destination='other_file_dest'),
        ]

        assert result == expected

    def test_parse_single_entry_wildcard_text(self):
        link_entry = self.single_entry_wildcard_text['actions'][0]['link']

        result = SymlinkAction.parse_entries('test/dots/pkg3', link_entry)

        expected = [
            SymlinkAction(package_path='test/dots/pkg3', source='afile', destination='.afile'),
            SymlinkAction(package_path='test/dots/pkg3', source='other_file', destination='.other_file'),
        ]

        assert result == expected

    def test_parse_single_entry_wildcard_dict(self):
        link_entry = self.single_entry_wildcard_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('test/dots/pkg3', link_entry)

        expected = [
            SymlinkAction(package_path='test/dots/pkg3', source='afile', destination='.local/share/afile'),
            SymlinkAction(package_path='test/dots/pkg3', source='other_file', destination='.local/share/other_file'),
        ]

        assert result == expected

    def test_parse_single_entry_wildcard_ignores_spec_file(self):
        # spec.yaml can not exist in the list
        link_entry = self.single_entry_wildcard_dict['actions'][0]['link']

        result: Sequence[SymlinkAction] = SymlinkAction.parse_entries('test/dots/pkg1', link_entry)  # type: ignore
        files = {l.source for l in result}

        assert SPEC_FILE_NAME not in files


class TestParseGitClone(TestCase):
    def setUp(self):

        self.invalid_entry_str = yaml.safe_load(
            """
            actions:
            - gitclone: git@url:/path
            """
        )

        self.invalid_entry_dict = yaml.safe_load(
            """
            actions:
            - gitclone:
              - from: git@url:/path
                to: .local/repo
            """
        )

        self.entry_without_branch = yaml.safe_load(
            """
            actions:
            - gitclone:
              - url: git@url:/path
                to: .local/repo
            """
        )

        self.entry_with_branch = yaml.safe_load(
            """
            actions:
            - gitclone:
              - url: git@url:/path
                to: .local/repo
                branch: main
            """
        )

    def test_parse_one_entry_raises_with_str(self):

        entry = self.invalid_entry_str['actions'][0]['gitclone']

        with self.assertRaises(InvalidActionDescription):
            GitCloneAction.parse_one_entry('some_path', entry)

    def test_parse_one_entry_raises_with_dict(self):

        entry = self.invalid_entry_dict['actions'][0]['gitclone'][0]

        with self.assertRaises(InvalidActionDescription):
            GitCloneAction.parse_one_entry('some_path', entry)

    def test_parse_one_entry_accepts_fields(self):

        entry = self.entry_without_branch['actions'][0]['gitclone'][0]

        result = GitCloneAction.parse_one_entry('some_path', entry)

        expected = [GitCloneAction(package_path='some_path',
                                   source='git@url:/path',
                                   destination='.local/repo',
                                   branch=None)
                    ]

        assert result == expected

    def test_parse_one_entry_accepts_fields_with_branch(self):

        entry = self.entry_with_branch['actions'][0]['gitclone'][0]

        result = GitCloneAction.parse_one_entry('some_path', entry)

        expected = [GitCloneAction(package_path='some_path',
                                   source='git@url:/path',
                                   destination='.local/repo',
                                   branch='main')]

        assert result == expected


class TestParseExecute(TestCase):

    def setUp(self):
        self.entry_single_cmd = yaml.safe_load(
            """
            actions:
            - execute: ls
            """
        )

        self.entry_multiple_cmds = yaml.safe_load(
            """
            actions:
            - execute:
              - export VAR=value
              - ls $VAR
            """
        )

    def test_parse_single_entry(self):
        entry = self.entry_single_cmd['actions'][0]['execute']
        result = ExecuteAction.parse_entries('some_path', entry)
        expected = [ExecuteAction(package_path='some_path', cmds=['ls'])]

        assert result == expected

    def test_parse_multiple_entries(self):
        entry = self.entry_multiple_cmds['actions'][0]['execute']
        result = ExecuteAction.parse_entries('some_path', entry)
        expected = [ExecuteAction(package_path='some_path', cmds=['export VAR=value', 'ls $VAR'])]

        assert result == expected
