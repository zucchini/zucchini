# Crafted with love by Austin Adams for CS 2110, Spring 2k17

CC = gcc
CHECK_LIBS = $(shell pkg-config --cflags --libs check)
HFILES = my_math.h
OFILES = my_math.o tests.o

CFLAGS = -std=c99 -pedantic -Wall -Werror -Wextra -g

.PHONY: default clean

default: tests

tests: $(OFILES) $(HFILES)
	$(CC) $(CFLAGS) $(OFILES) -o $@ $(CHECK_LIBS)

my_math.o: my_math.c my_math.h
	$(CC) -c $< $(CFLAGS) -o $@

%.o: %.c $(HFILES)
	$(CC) -c $(CFLAGS) $(TEST_CFLAGS) $<

clean:
	rm -f tests *.o
