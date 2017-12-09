// Student tester
// (see grader.c for details on how this differs from the grader)

#include <stdio.h>
#include <check.h>
#include "math_suite.h"

void print_usage(char *progname) {
    fprintf(stderr, "usage: %s [testcase]\n", progname);
}

int main(int argc, char **argv) {
    char *testcase;

    if (argc-1 > 1) {
        print_usage(argv[0]);
        return 1;
    } else if (argc-1 == 1) {
        testcase = argv[1];
    } else {
        testcase = NULL;
    }

    Suite *s = math_suite();

    if (testcase && !suite_tcase(s, testcase)) {
        print_usage(argv[0]);
        fprintf(stderr, "\n%s: error: `%s' is not a test case\n", argv[0], testcase);
        return 2;
    }

    SRunner *sr = srunner_create(s);
    srunner_run(sr, NULL, testcase, CK_ENV);
    srunner_free(sr);
    return 0;
}
