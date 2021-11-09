from pathlib import Path
from unittest import TestCase
from _pytest.monkeypatch import MonkeyPatch
import yaml

from dot import dot as dotdot
from dot.dot import SrcDestAction, SymlinkAction

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

    def test_parse_one_entry_text(self):

        link_single_entry = self.single_entry_text['actions'][0]['link']
        result = SrcDestAction.parse_one_entry(link_single_entry, SymlinkAction)

        expected = SymlinkAction('a_file', '.a_file')

        assert result == expected

    def test_parse_one_entry_dict(self):

        # this format has a list as link value, take the first entry
        link_single_entry = self.single_entry_dict['actions'][0]['link'][0]
        result = SrcDestAction.parse_one_entry(link_single_entry, SymlinkAction)

        expected = SymlinkAction('a_file', 'some_file')

        assert result == expected

    def test_parse_single_entry_text(self):
        link_entry = self.single_entry_text['actions'][0]['link']

        result = SrcDestAction.parse_entries(link_entry, SymlinkAction)

        expected = [
            SymlinkAction('a_file', '.a_file')
        ]

        assert result == expected

    def test_parse_multiple_entries_text(self):
        link_entry = self.multiple_entries_text['actions'][0]['link']

        result = SrcDestAction.parse_entries(link_entry, SymlinkAction)

        expected = [
            SymlinkAction('a_file', '.a_file'),
            SymlinkAction('other_file', '.other_file'),
            SymlinkAction('yet_another', '.yet_another'),
        ]

        assert result == expected

    def test_parse_single_entry_dict(self):
        link_entry = self.single_entry_dict['actions'][0]['link']

        result = SrcDestAction.parse_entries(link_entry, SymlinkAction)

        expected = [
            SymlinkAction('a_file', 'some_file')
        ]

        assert result == expected

    def test_parse_multiple_entries_dict(self):
        link_entry = self.multiple_entries_dict['actions'][0]['link']

        result = SrcDestAction.parse_entries(link_entry, SymlinkAction)

        expected = [
            SymlinkAction('a_file', 'some_file'),
            SymlinkAction('other_file', 'other_file_dest'),
        ]

        assert result == expected
