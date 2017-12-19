============================
Open File and Logisim Sample
============================

This assignment features two components: a headshot photo which will be
opened by the grader and confirmed, as well as a

Sample configuration:

.. code:: yaml

    name: Headshot and XOR Homework
    author: Austin Adams
    canvas:
      course-id: 1
      assignment-id: 1
    components:
      - name: Headshot image
        weight: 1
        files: headshot.jpg
        backend: OpenFileGrader
        backend-options:
          file-name: headshot.jpg
          prompts:
            - text: Is the image an acceptable image of the student?
              type: boolean
              weight: 1

      - name: XOR circuit
        weight: 3
        files: xor.circ
        grading-files: [hw1checker.jar, brandonsim.jar]
        backend: LogisimGrader
        backend-options:
          logisim-jar: brandonsim.jar
          circuit-file: xor.circ
          prompts:
            - question: Has the student used any banned components?
              type: boolean
              weight: 5
            - question: Has the student successfully connected the inputs to the output?
              type: boolean
              weight: 2
            - question: Does the circuit produce the intended result?
              type: boolean
              weight: 5
