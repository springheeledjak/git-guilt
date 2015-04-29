#!/usr/bin/env python2.7

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from itertools import chain, groupby, ifilter, imap
from operator import itemgetter

from lazypy import delay, force

def grep(*args):
    try:
        out = subprocess.check_output(['git', 'grep', '-n'] + list(args))
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            return None
        raise e

    return out.strip().split('\n')

def blame(path, *line_numbers):
    line_ranges = chain.from_iterable(['-L', '%d,%d' % (n, n)] for n in line_numbers)
    out = subprocess.check_output(['git', 'blame', '--line-porcelain'] + list(line_ranges) + [path])
    return out.strip().split('\n')

def get_author_counts(path, *line_numbers):
    lines = blame(path, *line_numbers)
    return Counter(
        line.split(' ', 1)[1]
        for line in lines
        if line.startswith('author ')
    )

def annotate_blame(path, *line_numbers):
    line_ranges = chain.from_iterable(['-L', '%d,%d' % (n, n)] for n in line_numbers)
    return subprocess.check_output(['git', 'blame', '-f'] + list(line_ranges) + [path])

# TODO(toli): make the output less ugly
def annotate_grep(grep_args):
    lines = grep(*grep_args)
    numbered = sorted(get_linenum_map(lines).iteritems())
    blames = [
        annotate_blame(path, *line_numbers)
        for path, line_numbers in numbered
    ]
    return ''.join(blames)

# TODO(toli)
#def annotate_grep(grep_args):
#    lines = grep(*grep_args)
#    numbered = sorted(get_line_map(lines).iteritems())
#    blames = (
#        blame(path, *line_numbers)
#        for path, line_numbers, _ in numbered
#    )

def get_line_map(grep_lines):
    pieces = (line.split(':') for line in grep_lines)
    groups = groupby(pieces, itemgetter(0))
    return dict(
        (path, list((int(e[1]), e[2]) for e in g))
        for path, g in groups
    )

def get_linenum_map(grep_lines):
    return dict(
        (path, list(num for num, _ in pieces))
        for (path, pieces) in get_line_map(grep_lines).iteritems()
    )

def merge_counters(acc, new):
    acc.update(new)
    return acc

def get_scores(*grep_args):
    lines = grep(*grep_args)
    if lines is None:
        return None

    author_to_files = defaultdict(list)

    counts = dict(
        (path, get_author_counts(path, *nums))
        for path, nums in get_linenum_map(lines).iteritems()
    )

    author_counter = reduce(merge_counters, counts.itervalues(), Counter())

    for path, counter in counts.iteritems():
        for author in counter.iterkeys():
            author_to_files[author].append(path)

    return author_counter, author_to_files

def build_parser():
    parser = argparse.ArgumentParser(
        prog = 'git-guilt',
        description = ' '.join([
            "grep the source tree using git-grep, and list each user who has",
            "written a matching line with per-user counts.",
            "Any arguments other than the options here are passed to git-grep."
        ]),
    )

    parser.add_argument('-s', '--scores',
        help = 'Print scores. This is the default.',
        action = 'store_true'
    )
    parser.add_argument('-g', '--annotated-grep',
        help = 'Print annotated grep output. Not compatible with -j.',
        action = 'store_true',
        dest = 'grep'
    )
    parser.add_argument('-f', '--files',
        help = 'Print the per-user list of files.',
        action = 'store_true'
    )
    parser.add_argument('-j', '--json', help = 'Output as json instead of text.', action = 'store_true')
    parser.add_argument('grep_args', nargs = argparse.REMAINDER)

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()
    if len(args.grep_args) == 0:
        parser.print_help()
        return 1
    if args.grep and args.json:
        print "Illegal options: cannot use both -j and -g."
        parser.print_help()
        return 2

    lazy_scores = delay(get_scores, args.grep_args)
    scores = delay(lambda: sorted(lazy_scores[0].iteritems(), key = itemgetter(1))[::-1])
    author_to_files = delay(lambda: lazy_scores[1])

    # By default, we only want to print the scores (the -s argument) unless
    # others are explicitly given.
    print_scores = args.scores or not (args.scores or args.files or args.grep)
    print_grep = args.grep
    print_files = args.files
    print_json = args.json

    if print_scores or print_files:
        if force(lazy_scores) is None:
            return 1

    if print_json:
        data = {}
        if print_scores:
            data['scores'] = scores
        if print_files:
            data['files'] = author_to_files

        print json.dumps(data, sort_keys = True, indent = 4)
        return 0

    if print_scores:
        print "High score list:"
        for author, score in scores:
            print "    %s with a score of %d" % (author, score)
        print

    if print_grep:
        print annotate_grep(args.grep_args)

    if print_files:
        print "Files touched by authors:"
        for author, files in sorted(force(author_to_files).iteritems()):
            print '\n    %s:' % author
            for f in files:
                print (' ' * 8) + f

    return 0

if __name__ == '__main__':
    main()
