# Student Makefile
# Students should not modify this unless they like the number 0

HFILES = math_suite.h
OFILES = math_suite.c tests.c my_math.c

CC = gcc
CHECK_LIBS = $(shell pkg-config --cflags --libs check)
CFLAGS = -std=c99 -pedantic -Wall -Werror -Wextra -g
VALGRIND_FLAGS = --leak-check=full --error-exitcode=1 --show-leak-kinds=all --errors-for-leak-kinds=all

.PHONY: default run-tests run-gdb run-valgrind clean

default: run-tests

tests: $(OFILES) $(HFILES)
	$(CC) $(CFLAGS) $(OFILES) -o $@ $(CHECK_LIBS)

%.o: %.c $(HFILES)
	$(CC) -c $(CFLAGS) $(TEST_CFLAGS) $<

run-tests: tests
	./tests

run-gdb: tests
	CK_FORK=no gdb ./tests

run-valgrind: tests
	CK_FORK=no valgrind $(VALGRIND_FLAGS) ./tests

clean:
	rm -f tests *.o
