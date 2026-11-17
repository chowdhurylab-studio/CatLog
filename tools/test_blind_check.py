#!/usr/bin/env python3
"""Offline tests of what blind_check counts as a reading agent opening a forbidden file: python3 tools/test_blind_check.py
A name that only leaves a file out (grep -v, find -not -path, --exclude, rg '!' globs) opens nothing; any other mention
still counts."""
import sys, unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import human_review as hr  # noqa: E402


def named(command=None, **inp):
    call = {'type': 'tool_use', 'name': 'Bash' if command is not None else 'Other',
            'input': {'command': command, **inp} if command is not None else inp}
    return sorted(set(hr.FORBIDDEN.findall(hr._named(call))))


class Exclusions(unittest.TestCase):
    def test_reader_33431826(self):  # the false alarm that started this (2026-10-26)
        cmd = ('ls papers 2>/dev/null | grep -i 33431826; ls -d */ | head -50; find . -maxdepth 3 -name "*33431826*" '
               '-not -path "./work/old/*" 2>/dev/null | grep -v -E "dbcheck|db_unmatched|site_build|catlog_wide" | head -30')
        self.assertEqual(named(cmd, description='Find supplement and paper files for this PMID'), [])

    def test_inverted_grep_patterns(self):
        for cmd in ("ls work | grep -vE 'db_values.tsv|catlog_wide'", 'ls work | grep -Ev "(catlog_wide|db_unmatched)"',
                    'ls work | grep -v -e db_unmatched -e catlog_wide', 'ls work | grep -ve catlog_wide',
                    'ls work | grep --invert-match catlog_wide', 'ls | xargs grep -v catlog_wide',
                    'ls work | grep -v --regexp=catlog_wide', 'ls work | egrep -v "human_review/|exposed.tsv"',
                    'ls work | rg -v catlog_wide', 'ls work | grep -v -- catlog_wide'):
            self.assertEqual(named(cmd), [], cmd)

    def test_inverted_grep_still_reads_its_files(self):
        self.assertEqual(named('grep -v foo work/db_unmatched.tsv'), ['db_unmatched'])
        self.assertEqual(named('grep -v -A 2 x catlog_wide.csv'), ['catlog_wide'])
        self.assertEqual(named('grep -v -f work/db_unmatched.tsv x.txt'), ['db_unmatched'])  # a pattern file is read
        self.assertEqual(named('grep -v -e x catlog_wide.csv'), ['catlog_wide'])
        self.assertEqual(named('grep -vE x catlog_wide.csv'), ['catlog_wide'])  # -E takes no value in grep

    def test_plain_mentions_still_count(self):
        self.assertEqual(named('grep catlog_wide prompts/read.md'), ['catlog_wide'])  # a search for it, not a leaving out
        self.assertEqual(named('cat catlog_wide.csv | grep -v x'), ['catlog_wide'])
        self.assertEqual(named("find . -name 'catlog_wide*'"), ['catlog_wide'])
        self.assertEqual(named('ls work | grep -v catlog_wide; cat work/db_unmatched.tsv'), ['db_unmatched'])
        self.assertEqual(named('ls work | grep -v catlog_wide\ncat work/db_unmatched.tsv'), ['db_unmatched'])
        self.assertEqual(named('grep -v catlog_wide x.txt && head catlog_wide.csv'), ['catlog_wide'])
        self.assertEqual(named("rg foo -g 'catlog_wide*'"), ['catlog_wide'])

    def test_find_exclusions(self):
        for cmd in ("find . -name '*.json' -not -path './work/old/dbcheck*'", "find . ! -name 'catlog_wide*'",
                    'find . -path ./site_build/ -prune -o -print',
                    r"find . -not \( -path '*catlog_wide*' -o -path '*db_unmatched*' \) -print",
                    r"find . \( -name 'catlog_wide*' -o -path ./human_review/ \) -prune -o -type f -print"):
            self.assertEqual(named(cmd), [], cmd)

    def test_exclude_options(self):
        for cmd in ('grep -rn foo . --exclude=catlog_wide.csv --exclude-dir=human_review',
                    'grep -rn foo . --exclude catlog_wide.csv', "rg foo -g '!catlog_wide*'", "rg foo --glob='!db_unmatched*'",
                    'tar --exclude catlog_wide.csv -czf /tmp/x.tgz texts'):
            self.assertEqual(named(cmd), [], cmd)
        self.assertEqual(named('grep -rn foo . --exclude-from=work/db_unmatched.tsv'), ['db_unmatched'])  # read

    def test_reads_that_look_like_exclusions(self):  # the 2026-10-26 review: each really reads the file
        cases = [
            ("grep -rn Km -g '!*.pdf,catlog_wide*' .", ['catlog_wide']),  # ugrep reads the positive part of a list
            ("grep -rn Km --glob='!*.pdf,db_unmatched*' .", ['db_unmatched']),
            ("find . -name 'catlog_wide.csv' -prune -exec head -5 {} \\;", ['catlog_wide']),  # -prune without -o
            ("find . -name 'catlog_wide*' -prune", ['catlog_wide']),
            ('cat $(find . -name catlog_wide.csv -prune)', ['catlog_wide']),
            (r"find . \( -name 'db_unmatched*' -o -name 'catlog_wide*' \) -prune -exec cat {} +", ['catlog_wide', 'db_unmatched']),
            ("find . ! -path './catlog_wide.csv' -prune -o -print", ['catlog_wide']),  # prunes all but it
            ('grep -n -e --exclude work/db_unmatched.tsv', ['db_unmatched']),  # --exclude as the pattern
            ('grep -n -- --exclude work/db_unmatched.tsv', ['db_unmatched']),
            ('rg -n -F -- --exclude catlog_wide.csv', ['catlog_wide']),
            ("grep -rn -- '--exclude-dir' human_review/notes.md", ['human_review/']),
            ('grep -rv --exclude-from work/db_unmatched.tsv Km texts/', ['db_unmatched']),  # an option not known
            ('rg -v --ignore-file work/db_unmatched.tsv Km texts/', ['db_unmatched']),
            ('grep -v --neg-regexp=foo work/db_unmatched.tsv', ['db_unmatched']),
            ('grep -vO txt foo work/db_unmatched.tsv', ['db_unmatched']),  # -O: a value in ugrep, none in BSD grep
            ('grep -v "$(cat work/db_unmatched.tsv)" texts/123.txt', ['db_unmatched']),  # a quoted substitution runs
            ('grep -v -e "$(cut -f2 work/db_unmatched.tsv | head -1)" x', ['db_unmatched']),
            ('grep -v "`head -1 catlog_wide.csv`" x', ['catlog_wide']),
            ('find . -not -name "$(head -1 work/dbcheck_123.task.json)"', ['work/dbcheck']),
            ("grep -v $'can\\'t' work/db_unmatched.tsv  # skip what's unreadable", ['db_unmatched']),  # $'' quoting
            ("find . -not -not -name 'catlog_wide*'", ['catlog_wide']),  # double negation
            (r"find . ! \( ! -name 'catlog_wide*' \)", ['catlog_wide']),
        ]
        for cmd, want in cases:
            self.assertEqual(named(cmd), want, cmd)
        self.assertEqual(named(pattern='Km', path='/x/catlog-v2', glob='!*.pdf,catlog_wide*'), ['catlog_wide'])  # Grep tool
        self.assertEqual(named(pattern='Km', path='/x/catlog-v2', glob='!*.pdf catlog_wide*'), ['catlog_wide'])
        self.assertEqual(named('ls', file='work/db_unmatched.tsv'), ['db_unmatched'])  # other keys of a command call count

    def test_review_folder_without_slash(self):
        self.assertEqual(named('find human_review -type f -exec cat {} +'), ['human_review'])
        self.assertEqual(named('cd /home/x/catlog-v2 && ls human_review'), ['human_review'])
        self.assertEqual(named('cat human_review/decisions.jsonl'), ['decisions.jsonl', 'human_review/'])  # label kept
        self.assertEqual(named(file_path='/home/x/catlog-v2/human_review'), ['human_review'])
        self.assertEqual(named('sed -n 1,40p tools/human_review.py'), [])  # the code, not the review data
        self.assertEqual(named('ls | grep -v human_review'), [])

    def test_unsplittable_command_counts_whole(self):
        self.assertEqual(named("ls work | grep -v catlog_wide # it's"), ['catlog_wide'])

    def test_other_tools(self):
        self.assertEqual(named(file_path='/home/x/catlog-v2/catlog_wide.csv'), ['catlog_wide'])
        self.assertEqual(named(pattern='Km', path='/home/x/catlog-v2', glob='!catlog_wide*'), [])
        self.assertEqual(named(pattern='Km', path='/home/x/catlog-v2/work/db_unmatched.tsv'), ['db_unmatched'])


if __name__ == '__main__':
    unittest.main()
