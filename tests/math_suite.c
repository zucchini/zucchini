#include <stdlib.h>
#include <check.h>
#include "my_math.h"

// Define a test case with the provided checked fixtures which contains a
// single test, func. Name the test case after the function.
#define suite_add_test(suite, setup_fixture, teardown_fixture, func) { \
    TCase *tc = tcase_create(#func); \
    tcase_add_checked_fixture(tc, setup_fixture, teardown_fixture); \
    tcase_add_test(tc, func); \
    suite_add_tcase(s, tc); \
}

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

Suite *math_suite() {
    Suite *s = suite_create("math");

    // add() tests
    suite_add_test(s, NULL, NULL, test_math_add_positive);
    suite_add_test(s, NULL, NULL, test_math_add_zero);
    suite_add_test(s, NULL, NULL, test_math_add_negative);

    // multiply() tests
    suite_add_test(s, setup_math_multiply, teardown_math_multiply, test_math_multiply_positive);
    suite_add_test(s, setup_math_multiply, teardown_math_multiply, test_math_multiply_zero);
    suite_add_test(s, setup_math_multiply, teardown_math_multiply, test_math_multiply_negative);

    return s;
}
