// Example test file
//
// Warning: much the structure of this file is shamelessly copypasted from
// https://libcheck.github.io/check/doc/check_html/check_3.html

#include <stdio.h>
#include <stdlib.h>
#include <check.h>
#include "my_math.h"

static int *important_number;

//
// add() tests
//
START_TEST(test_math_add_positive) {
    ck_assert_int_eq(add(4,3), 7);
}
END_TEST

START_TEST(test_math_add_zero) {
    ck_assert_int_eq(add(100,0), 100);
}
END_TEST

START_TEST(test_math_add_negative) {
    ck_assert_int_eq(add(-1,-50), -51);
}
END_TEST

//
// multiply() tests
//
void setup_math_multiply(void) {
    important_number = malloc(sizeof (int));
    *important_number = 37;
}

void teardown_math_multiply(void) {
    free(important_number);
}

START_TEST(test_math_multiply_positive) {
    ck_assert_int_eq(multiply(4,3), 12);
}
END_TEST

START_TEST(test_math_multiply_zero) {
    ck_assert_int_eq(multiply(7,0), 0);
}
END_TEST

START_TEST(test_math_multiply_negative) {
    ck_assert_int_eq(multiply(10,-30), -300);
}
END_TEST

Suite *list_suite() {
    Suite *s;
    TCase *tc;

    s = suite_create("math");

    // add() tests
    tc = tcase_create("add");
    tcase_add_test(tc, test_math_add_positive);
    tcase_add_test(tc, test_math_add_zero);
    tcase_add_test(tc, test_math_add_negative);
    suite_add_tcase(s, tc);

    // push_front() tests
    tc = tcase_create("multiply");
    tcase_add_checked_fixture(tc, setup_math_multiply, teardown_math_multiply);
    tcase_add_test(tc, test_math_multiply_positive);
    tcase_add_test(tc, test_math_multiply_zero);
    tcase_add_test(tc, test_math_multiply_negative);
    suite_add_tcase(s, tc);

    return s;
}

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

    Suite *s = list_suite();

    if (testcase && !suite_tcase(s, testcase)) {
        print_usage(argv[0]);
        fprintf(stderr, "\n%s: error: `%s' is not a test case\n", argv[0], testcase);
        return 2;
    }

    SRunner *sr = srunner_create(s);
    srunner_run(sr, "math", testcase, CK_VERBOSE);
    srunner_free(sr);
    return 0;
}
