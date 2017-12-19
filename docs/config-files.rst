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
      - weight: 2
        files: my_math.c
        grading-files: tests/*
        backend: docker
        backend-options:
          backend: libcheck
          backend-options:
            timeout: 5
            build-cmd: make
            run-cmd: ./tests {test} {logfile}
            valgrind-cmd: valgrind --quiet --leak-check=full --error-exitcode=1 --show-leak-kinds=all --errors-for-leak-kinds=all ./tests {test} {logfile}
      - weight: 1
        files: headshot.jpg
        backend:
          name: open-file
        prompts:
          - question: Is the image an acceptable image of the student?
            type: boolean
      - weight: 1
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
      - weight: 5
        files: bitvector.asm
        grader-files: bitvector_test.xml
        backend: lc3test
        backend-options:
          runs: 128
