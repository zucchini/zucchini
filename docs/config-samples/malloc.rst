==========================
Libcheck Assignment Sample
==========================

This assignment has a single .c file being graded using libcheck tests which
 are individually weighted.

The tests are run on a separate docker container for each student to prevent
 arbitrary code execution on the grader's computer.

Sample configuration:

.. code:: yaml

    name: Malloc Homework
    author: Austin Adams
    canvas:
      course-id: 1
      assignment-id: 1
    components:
      - name: malloc()
        weight: 2
        files: my_math.c
        grading-files: tests/*
        backend: DockerWrapperGrader
        backend-options:
          components:
            backend: LibCheckGrader
            backend-options:
              timeout: 5
              build-cmd: make
              run-cmd: ./tests {test} {logfile}
              valgrind-cmd: valgrind --quiet --leak-check=full --error-exitcode=1 --show-leak-kinds=all --errors-for-leak-kinds=all ./tests {test} {logfile}
              tests:
              - name: test_malloc_malloc_initial
                weight: 3
              - name: test_malloc_malloc_initial_sbrked
                weight: 3
              - name: test_malloc_malloc_sbrk_merge
                weight: 3
              - name: test_malloc_malloc_perfect1
                weight: 3
              - name: test_malloc_malloc_perfect2
                weight: 3
              - name: test_malloc_malloc_perfect3
                weight: 3
              - name: test_malloc_malloc_split1
                weight: 3
              - name: test_malloc_malloc_split2
                weight: 3
              - name: test_malloc_malloc_split3
                weight: 3
              - name: test_malloc_malloc_waste1
                weight: 3
              - name: test_malloc_malloc_waste2
                weight: 3
              - name: test_malloc_malloc_waste3
                weight: 3
              - name: test_malloc_malloc_zero
                weight: 3
              - name: test_malloc_malloc_toobig
                weight: 3
              - name: test_malloc_malloc_oom
                weight: 3
              - name: test_malloc_free_null
                weight: 2
              - name: test_malloc_free_bad_meta_canary
                weight: 2
              - name: test_malloc_free_bad_trailing_canary
                weight: 2
              - name: test_malloc_free_empty_freelist
                weight: 2
              - name: test_malloc_free_no_merge1
                weight: 2
              - name: test_malloc_free_no_merge2
                weight: 2
              - name: test_malloc_free_left_merge1
                weight: 2
              - name: test_malloc_free_left_merge2
                weight: 2
              - name: test_malloc_free_left_merge3
                weight: 2
              - name: test_malloc_free_right_merge1
                weight: 2
              - name: test_malloc_free_right_merge2
                weight: 2
              - name: test_malloc_free_right_merge3
                weight: 2
              - name: test_malloc_free_double_merge1
                weight: 2
              - name: test_malloc_free_double_merge2
                weight: 2
              - name: test_malloc_free_double_merge3
                weight: 2
              - name: test_malloc_calloc_initial
                weight: 1
              - name: test_malloc_calloc_zero
                weight: 1
              - name: test_malloc_calloc_clobber_errno
                weight: 1
              - name: test_malloc_calloc_actually_zeroed
                weight: 0
              - name: test_malloc_realloc_initial
                weight: 1
              - name: test_malloc_realloc_zero
                weight: 1
              - name: test_malloc_realloc_copy
                weight: 1
              - name: test_malloc_realloc_copy_smaller
                weight: 1
              - name: test_malloc_realloc_free
                weight: 1
              - name: test_malloc_realloc_toobig
                weight: 1
              - name: test_malloc_realloc_bad_meta_canary
                weight: 1
              - name: test_malloc_realloc_bad_trailing_canary
                weight: 1
