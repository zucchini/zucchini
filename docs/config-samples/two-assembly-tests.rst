============================
Two-Component LC3Test Sample
============================

This assignment features two components, both of which are assembly code files
that can be graded using provided lc3test configurations.

Sample configuration:

.. code:: yaml

    name: LC3 Assembly Homework with Two Components
    author: Austin Adams
    canvas:
      course-id: 1
      assignment-id: 1
    components:
      - name: LC-3 Factorial implementation
        weight: 1
        files: factorial.asm
        grader-files: factorial_test.xml
        backend: LC3TestGrader
        backend-options:
          assembly-file: factorial.asm
          test-file: factorial_test.xml
          runs: 128

      - name: LC-3 Bitvector implementation
        weight: 1
        files: bitvector.asm
        grader-files: bitvector_test.xml
        backend: LC3TestGrader
        backend-options:
          assembly-file: bitvector.asm
          test-file: bitvector_test.xml
          runs: 128
