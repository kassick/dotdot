from unittest import TestCase
import yaml

from dot.dot import GitCloneAction, InvalidActionDescription, SymlinkAction

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
            """
            actions:
            - link: '*'
            """
        )

        self.single_entry_wildcard_dict = yaml.safe_load(
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

        expected = [SymlinkAction('a_file', '.a_file')]

        assert result == expected

    def test_parse_one_entry_dict(self):

        # this format has a list as link value, take the first entry
        link_single_entry = self.single_entry_dict['actions'][0]['link'][0]
        result = SymlinkAction.parse_one_entry('some_path', link_single_entry)

        expected = [SymlinkAction('a_file', 'some_file')]

        assert result == expected

    def test_parse_single_entry_text(self):
        link_entry = self.single_entry_text['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction('a_file', '.a_file')
        ]

        assert result == expected

    def test_parse_multiple_entries_text(self):
        link_entry = self.multiple_entries_text['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction('a_file', '.a_file'),
            SymlinkAction('other_file', '.other_file'),
            SymlinkAction('yet_another', '.yet_another'),
        ]

        assert result == expected

    def test_parse_single_entry_dict(self):
        link_entry = self.single_entry_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction('a_file', 'some_file')
        ]

        assert result == expected

    def test_parse_multiple_entries_dict(self):
        link_entry = self.multiple_entries_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('some_path', link_entry)

        expected = [
            SymlinkAction('a_file', 'some_file'),
            SymlinkAction('other_file', 'other_file_dest'),
        ]

        assert result == expected

    def test_parse_single_entry_wildcard_text(self):
        link_entry = self.single_entry_wildcard_text['actions'][0]['link']

        result = SymlinkAction.parse_entries('test/dots/pkg3', link_entry)

        expected = [
            SymlinkAction('afile', '.afile'),
            SymlinkAction('other_file', '.other_file'),
        ]

        assert result == expected

    def test_parse_single_entry_wildcard_dict(self):
        link_entry = self.single_entry_wildcard_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('test/dots/pkg3', link_entry)

        expected = [
            SymlinkAction('afile', '.local/share/afile'),
            SymlinkAction('other_file', '.local/share/other_file'),
        ]

        assert result == expected

    def test_parse_single_entry_wildcard_ignores_spec(self):
        link_entry = self.single_entry_wildcard_dict['actions'][0]['link']

        result = SymlinkAction.parse_entries('test/dots/pkg1', link_entry)

        expected = []

        assert result == expected



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
        print(entry)

        with self.assertRaises(InvalidActionDescription):
            GitCloneAction.parse_one_entry('some_path', entry)

    def test_parse_one_entry_accepts_fields(self):

        entry = self.entry_without_branch['actions'][0]['gitclone'][0]

        result = GitCloneAction.parse_one_entry('some_path', entry)

        expected = [GitCloneAction('git@url:/path', '.local/repo', branch=None)]

        assert result == expected

    def test_parse_one_entry_accepts_fields_with_branch(self):

        entry = self.entry_with_branch['actions'][0]['gitclone'][0]

        result = GitCloneAction.parse_one_entry('some_path', entry)

        expected = [GitCloneAction('git@url:/path', '.local/repo', branch='main')]

        assert result == expected
