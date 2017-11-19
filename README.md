lc3grade
========

`lc3grade.py` is a Python **3.5+** autograder for CS 2110 homeworks in LC-3 or
C. After you run `SubmissionFix.py`, run it in the directory of student
submission subdirectories to run students' code against a set of test cases
defined in `lc3grade.config`. It saves tester output in each student directory
as `gradeLog.txt`.

There is a a backend named `LC-3` for running Brandon's lc3test and another
named `C` for running [libcheck][1] test cases. To enable a backend, uncommment
its section in `lc3grade.config`.

Getting Started
---------------

 1. Download a bulk submission for your section from T-Square, but *don't*
    extract it.
 2. Run `python SubmissionFix.py bulk_download.zip tsquare` to extract the bulk
    download.
 3. Copy `lc3grade.py` and `lc3grade.config` to the same directory.
 4. Copy your tests to the same directory and add them to `lc3grade.config`.
 5. Run `python3 lc3grade.py`, entering T-Square grades as you go. Each student
    directory contains tester output in `gradeLog.txt` if they want to see
    which tests they failed.

Grading with libcheck
---------------------

Grading with libcheck is a little more involved than lc3test because you have
to write unit tests in C. The `tests/` directory contains an example of how to
write them. Each libcheck test case corresponds to a section in
`lc3grade.config`. In the case of the example in `tests/`, `lc3grade.config`
could contain the following sections (in addition to `[META]`):

    [C]
    timeout=2
    ; These will be copied from student submission directories
    cfiles=my_math.c
    tests_dir=tests
    build_cmd=make
    ; for these two, {} is replaced with the test suite to run
    run_cmd=./tests {}
    valgrind_cmd=CK_FORK=no valgrind --leak-check=full --error-exitcode=1 ./tests {}

    [add]
    description=add()
    weight=25
    leak_deduction=5

    [multiply]
    description=multiply()
    weight=75
    leak_deduction=25

[1]: https://libcheck.github.io/check/
