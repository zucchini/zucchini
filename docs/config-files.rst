==================
Config File Format
==================

What shall be in the config file?

Component configuration:

.. code:: yaml

    name: Homework 1
    author: Austin Adams
    canvas:
      course-id: 1
      assignment-id: 1
    components:
      - name: malloc()
        weight: 2
        files: my_malloc.c
        grading-files: tests/*
        backend: docker
        backend-options:
          backend: libcheck
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
      - name: Headshot image
        weight: 1
        files: headshot.jpg
        backend:
          name: open-file
        prompts:
          - question: Is the image an acceptable image of the student?
            type: boolean
      - name: XOR circuit
        weight: 1
        files: xor.circ
        grading-files: hw1checker.jar brandonsim.jar
        backend: logisim
        backend-options:
          logisim-jar: brandonsim.jar
        prompts:
        - question: Has the student used any banned components?
          weight: 5
        - question: Has the student successfully connected the inputs to the output?
          weight: 2
        - question: Does the circuit produce the intended result?
          weight: 5
      - name: LC-3 BitVector implementation
        weight: 5
        files: bitvector.asm
        grader-files: bitvector_test.xml
        backend: lc3test
        backend-options:
          runs: 128
