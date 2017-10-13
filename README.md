lc3grade
========

`lc3grade.py` is a Python **3** autograder for CS 2110 LC-3 homeworks. After
you run `SubmissionFix.py`, run it in the directory of student submission
subdirectories to run students' LC-3 assembly against a set of lc3tests defined
in `lc3grade.config`. It saves lc3test output in each student directory as
`gradeLog.txt`.

Getting Started
---------------

 1. Download a bulk submission for your section from T-Square, but *don't*
    extract it.
 2. Run `python SubmissionFix.py bulk_download.zip tsquare` to extract the bulk
    download.
 3. Copy `lc3grade.py` and `lc3grade.config` to the same directory.
 4. Copy your tests to the same directory and add them to `lc3grade.config`.
 5. Run `python3 lc3grade.py`, entering T-Square grades as you go. Each student
    directory contains lc3test output in `gradeLog.txt` if they want to see
    which tests they failed.
