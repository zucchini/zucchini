=====
Usage
=====

Before following this guide, make sure you've installed zucchini as
described in :doc:`installation`.

----------------------
Creating an Assignment
----------------------

^^^^^^^^^^^^^^^^^^^^^^^^
Anatomy of an Assignment
^^^^^^^^^^^^^^^^^^^^^^^^

A Zucchini assignment consists of a list of components, each of which
itself consists of a list of parts. Like this:

.. graphviz::

   digraph {
    size="8,8"
    dpi=200

    a  [shape=box, label="Assignment"]
    c1 [shape=box, label="Component"]
    c2 [shape=box, label="Component"]
    c3 [shape=box, label="Component"]
    p1 [shape=box, label="Part"]
    p2 [shape=box, label="Part"]
    p3 [shape=box, label="Part"]
    p4 [shape=box, label="Part"]
    p5 [shape=box, label="Part"]
    p6 [shape=box, label="Part"]
    p7 [shape=box, label="Part"]
    p8 [shape=box, label="Part"]
    p9 [shape=box, label="Part"]

    a  -> c1
    c1 -> p1
    c1 -> p2

    a  -> c2
    c2 -> p3
    c2 -> p4
    c2 -> p5
    c2 -> p6

    a  -> c3
    c3 -> p7
    c3 -> p8
    c3 -> p9
   }

Zucchini aims to streamline the process of converting a student's
submission to a grade in the gradebook, and an assignment instructs
Zucchini how to perform this conversion. Indeed, Zucchini downloads
submissions, posts grades, and checks due dates for entire assignments,
even if they consist of multiple components.

Components represent the smallest pieces of an assignment that Zucchini
can grade independently. Usually, this means each independent file in
the submission has its own component. Examples of components:

* A test class which tests a particular class in the submission in a
  JUnit-based grader
* A test suite in a Libcheck-based grader
* A subcircuit in a CircuitSim circuit
* A set of prompts in a prompt grader

Parts represent the smallest result in grading a component that deserves
its own weight. We generalized parts because we noticed all of our
backends had them. Examples of parts:

* A test method in a JUnit-based grader
* A test in a test suite in a Libcheck-based grader
* A test of a subcircuit in a CircuitSim circuit
* A prompt in a prompt grader

Now, here is a concrete example of the diagram above for a homework with
a CircuitSim circuit ``fsm.sim`` and a Java file ``BitVector.java``:

.. graphviz::

   digraph {
    size="8,8"
    dpi=200

    a  [shape=box, label="Homework 8"]

    c1 [shape=box, label="fsm.sim (One-hot subcircuit)"]
    p1 [shape=box, label="transitions"]
    p2 [shape=box, label="outputs"]

    c2 [shape=box, label="fsm.sim (Reduced subcircuit)"]
    p3 [shape=box, label="transitions"]
    p4 [shape=box, label="outputs"]
    p5 [shape=box, label="gateCount"]
    p6 [shape=box, label="coolness"]

    c3 [shape=box, label="BitVector.java"]
    p7 [shape=box, label="set"]
    p8 [shape=box, label="clear"]
    p9 [shape=box, label="isSet"]

    a  -> c1
    c1 -> p1
    c1 -> p2

    a  -> c2
    c2 -> p3
    c2 -> p4
    c2 -> p5
    c2 -> p6

    a  -> c3
    c3 -> p7
    c3 -> p8
    c3 -> p9
   }

^^^^^^^^^^^^^^^^^^^^^^^^
Assignment Configuration
^^^^^^^^^^^^^^^^^^^^^^^^

The directory structure for an assignment ``my_assignment`` looks like::

   my_assignment/
       zucchini.yml
       grading-files/
           some-grader-jar.jar
           some-grader-file.sh
       submissions/
           Sood, Sanjay/
               meta.json
               gradelog.txt
               files/
                   fsm.sim
           Lin, Michael/
               meta.json
               gradelog.txt
               files/
                   fsm.sim

You need to create only ``zucchini.yml`` and optionally
``grading-files/``. Zucchini will generate ``submissions/``.
``zucchini.yml`` looks like::

   name: Homework X # required
   author: Austin Adams # required
   due-date: 2018-06-24T18:00:00-04:00
   components: # required
   - name: Finite State Machine # required
     weight: 1 # required
     backend: CircuitSimGrader # required
     backend-options:
       grader-jar: hwX-tester.jar
       test-class: FsmTests
     files: [fsm.sim]
     grading-files: [hwX-tester.jar]
     parts: # required
     - {test: clockConnected,  weight: 1}
     - {test: resetConnected,  weight: 1}
     - {test: enableConnected, weight: 1}
     - {test: outputA,         weight: 5}
     - {test: transition,      weight: 10}

^^^^^
Farms
^^^^^

Before Zucchini, grading for us meant hunting down the grader archive on
either Slack, Google Drive, or GitHub. Adding to the confusion,
sometimes these different sources would get out of sync, forcing TAs to
regrade their section all over again. Zucchini offers a solution to this
you're probably already comfortable with: git.

TODO: Finish
