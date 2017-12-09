#include <check.h>
#include <stdio.h>
#include "math_suite.h"

void print_usage(char *progname) {
    fprintf(stderr, "usage: %s [<testcase> [<logfile>]]\n", progname);
}

int main(int argc, char **argv) {
    char *testcase = NULL;
    char *logfile = "tests.log";

    if (argc-1 > 2) {
        print_usage(argv[0]);
        return 1;
    } else {
        if (argc-1 >= 1) {
            testcase = argv[1];
        }
        // Allow supplying the log file on the command line to allow running
        // tests concurrently
        if (argc-1 >= 2) {
            logfile = argv[2];
        }
    }

    Suite *s = math_suite();

    if (testcase && !suite_tcase(s, testcase)) {
        print_usage(argv[0]);
        fprintf(stderr, "\n%s: error: `%s' is not a test case\n", argv[0], testcase);
        return 2;
    }

    SRunner *sr = srunner_create(s);
    srunner_set_log(sr, logfile);
    // lc3grade discards the output of the tester, so don't bother printing
    // anything. (Reading the test results from a log file prevents students
    // from just printf()ing themselves to a 100. However, they could probably
    // guess that the log file is file descriptor 3 and write to it, but I
    // doubt they'd try that hard.)
    srunner_run(sr, NULL, testcase, CK_SILENT);
    srunner_free(sr);
    return 0;
}
