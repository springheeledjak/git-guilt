# git-guilt
How To Lose Contributors And Alienate Coworkers

*TODO*: Convert this into a proper `pip` module that autoinstalls to
`.gitconfig`.

You'll probably want to run `pip install -r requirements.txt` before running the
script.

```
usage: git-guilt [-h] [-s] [-g] [-f] [-j] ...

grep the source tree using git-grep, and list each user who has written a
matching line with per-user counts. Any arguments other than the options here
are passed to git-grep.

positional arguments:
  grep_args

optional arguments:
  -h, --help            show this help message and exit
  -s, --scores          Print scores. This is the default.
  -g, --annotated-grep  Print annotated grep output. Not compatible with -j.
  -f, --files           Print the per-user list of files.
  -j, --json            Output as json instead of text.
```
