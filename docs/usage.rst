=====
Usage
=====

Before following this guide, make sure you've installed zucchini as
described in :doc:`installation`.

---------------------
Grading an Assignment
---------------------

The following section is written as a zucchini workflow that would be used
by a TA in a course that already has a zucchini farm set up (as an example,
we will use the sample zucchini farm), that an instructor or TA has already
prepared the assignment and linked to it on the farm (as an example, we will
use the sample zucchini JUnit assignment), and that student submissions are
available in directory (as an example, we will use sample submissions on a
git repo).

Note that this tutorial expects that you are on either Linux or OSX, that you
have access to the terminal (Terminal.app on OSX), that you have installed a
Python distribution that's >=3.4 (we recommend Anaconda for beginners), that you
have git installed, that you have JDK 1.8 or higher installed and linked to your
path, and that you have gradle installed.

Let’s start by installing zucchini

::

    pip install zucchini

We set up our workspace by entering our identity details:

::

    zucc setup

Then we add the farm for the metadata repository created by our
instructor. We name it ``cs1337-fall1970``:

::

    zucc farm add https://github.com/zucchini/sample-farm.git cs1337-fall1970

Then we make a new directory for our grading and change into it.

::

    mkdir zuccsample && cd zuccsample

We list the assignments on our farms to find the one we’re looking for:

::

    zucc list

From the output of this, we find that our assignment is called ``junit/stacks-queues``.
We use ``zucc init`` to make zucchini pull the assignment configuration into a new
directory which will have the assignment's name. We use our farm’s name as well as the
assignment’s name on the farm. Note that detailed information about this assignment,
which tests a Stack and Queue implementation using JUnit, can be found on the `repository
page <https://github.com/zucchini/sample-assignment>`_ for the assignment.

::

    zucc init cs1337-fall1970/junit/stacks-queues

Then, we download the sample submissions:

::

    git clone https://github.com/zucchini/sample-assignment-submissions.git

Now we change into our assignment directory, and make zucchini load the submissions
we just downloaded. Note that in a real workflow, submissions would likely be loaded
through LMS integration modules such as Canvas. Also note that the `-d` flag for the
path loader is used to make zucchini use the directory name (e.g. `Alice`) as the
submitting student's name as well.

::

    cd stacks-queues
    zucc load path -d ../sample-assignment-submissions/Alice
    zucc load path -d ../sample-assignment-submissions/Bob
    zucc load path -d ../sample-assignment-submissions/Charlie
    zucc load path -d ../sample-assignment-submissions/Dave
    zucc load path -d ../sample-assignment-submissions/Eve

Then, we start the grading process. This will grade each submission separately and
save their results in their folders into the submissions' meta.json files. Once the
grading is done, a text editor will open to show the newly updated grades. Hit `:q`
close it.

::

    zucc grade

Now that we’re done grading, we want to exports the grades our students received. Note
that in a real workflow, this would also likely be done through LMS integration modules
such as Canvas, which allow for grades to be saved directly onto students' accounts.

::

    zucc export csv > grades.csv

And we’re done! The grades can be found in the CSV file.

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
    dpi=200
    ordering=out

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
    dpi=200
    ordering=out

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

^^^^^^^
Weights
^^^^^^^

Zucchini weights components and parts relatively. That is, a component
:math:`i` is worth :math:`\frac{\text{weight}_i}{\sum_k \text{weight}_k}` of the grade.

So for the following assignment:

.. graphviz::

   digraph {
    dpi=200
    ordering=out

    a  [shape=box, label="Homework 8"]
    c1 [shape=box, label="fsm.sim (One-hot subcircuit)\nweight: 3"]
    c2 [shape=box, label="fsm.sim (Reduced subcircuit)\nweight: 1"]
    c3 [shape=box, label="BitVector.java\nweight: 2"]

    a -> c1
    a -> c2
    a -> c3
   }

the rubric is actually:

============================ =======
Component                    Percent
============================ =======
fsm.sim (One-hot subcircuit) 50%
fsm.sim (Reduced subcircuit) 16.67%
BitVector.java               33.33%
============================ =======

Parts have the same relationship with their parent components. So a part
:math:`j` of a component :math:`i` is worth
:math:`\frac{\text{weight}_i}{\sum_k \text{weight}_k} \times
\frac{\text{weight}_j}{\sum_l \text{weight}_l}` of the grade.

Don't let the decimal points above mislead you: Zucchini calculates
grades with rational numbers internally, so you you don't need to worry
about floating point screwing up or perfect submissions getting a 99.99
or anything like that (lc3grade had this problem).

We added relative weighting because we didn't enjoy twiddling with
weights until they summed to 100. If you do, you can make all the
weights add up to 100:

.. graphviz::

   digraph {
    dpi=200
    ordering=out

    a  [shape=box, label="Homework 8"]
    c1 [shape=box, label="fsm.sim (One-hot subcircuit)\nweight: 50"]
    c2 [shape=box, label="fsm.sim (Reduced subcircuit)\nweight: 16"]
    c3 [shape=box, label="BitVector.java\nweight: 34"]

    a -> c1
    a -> c2
    a -> c3
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
``zucchini.yml`` looks like

.. code-block:: yaml

   name: Homework X # required
   author: Michael Lin # required
   due-date: 2018-06-24T18:00:00-04:00
   canvas:
     course-id: 2607
     assignment-id: 8685
   penalties:
   - name: LATE
     backend: LatePenalizer
     backend-options:
       penalties:
       - after: 1h
         penalty: 25pts
   components: # required
   - name: Finite State Machine # required
     weight: 2 # required
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
   - name: Fully reduced
     weight: 1
     backend: CommandGrader
     backend-options:
       command: "java -cp hwX-tester.jar com.ra4king.circuitsim.gui.CircuitSim fsm.sim"
     files: [fsm.sim]
     grading-files: [hwX-tester.jar]
     parts:
     - text: "banned gates?"
       answer-type: bool
       weight: 2
     - text: "number of incorrect SOP expressions"
       answer-type: int
       answer-range: [0, 5]
       weight: 3

You can find a full list of graders at :py:mod:`zucchini.graders`.

^^^^^
Farms
^^^^^

Before Zucchini, grading for us meant hunting down the grader archive on
either Slack, Google Drive, or GitHub. Adding to the confusion,
sometimes these different sources would get out of sync, forcing TAs to
regrade their section all over again. Zucchini offers a solution to this
you're probably already comfortable with: git.

TODO: Finish
