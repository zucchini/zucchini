# Grader Makefile

HFILES = math_suite.h
OFILES = math_suite.c tests.c my_math.c

CC = gcc
CHECK_LIBS = $(shell pkg-config --cflags --libs check)
CFLAGS = -std=c99 -pedantic -Wall -Werror -Wextra -g

.PHONY: clean

tests: $(OFILES) $(HFILES)
	$(CC) $(CFLAGS) $(OFILES) -o $@ $(CHECK_LIBS)

%.o: %.c $(HFILES)
	$(CC) -c $(CFLAGS) $(TEST_CFLAGS) $<

clean:
	rm -f tests *.o *.log
