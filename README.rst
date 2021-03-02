========
Zucchini
========


.. image:: https://img.shields.io/pypi/v/zucchini.svg
        :target: https://pypi.python.org/pypi/zucchini

.. image:: https://travis-ci.com/zucchini/zucchini.svg?branch=master
        :target: https://travis-ci.com/zucchini/zucchini

.. image:: https://readthedocs.org/projects/zucchini/badge/?version=latest
        :target: https://zucchini.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/zucchini/zucchini/shield.svg
     :target: https://pyup.io/repos/github/zucchini/zucchini/
     :alt: Updates


Zucchini is an automatic grader tool for use in grading programming assignments.


* Free software: Apache Software License 2.0
* Documentation: https://zucchini.readthedocs.io.


Installation
------------

::

   $ pip install --user zucchini
   $ zucc --help


Getting Started with Development
--------------------------------

After cloning this repo and installing virtualenv, run

::

   $ virtualenv -p python3 venv
   $ . venv/bin/activate
   $ pip install -r requirements.txt
   $ pip install -r requirements_dev.txt
   $ zucc --help

Features
--------

* Unified grading infrastructure: eliminates maintenance load of ad-hoc
  per-assignment graders
* Separates test results from computed grades: graders provide test
  results which are stored on disk, and then zucchini calculates grade
  based on the weight of each test. That is, graders do not perform
  grade calculation; they only gather information about students' work
* Simple configuration: update one YAML file and store your graders in
  git repositories for all your TAs
* Relative weighting: no more twiddling with weights to get them to add
  up to 100
* Import submissions from Gradescope, Canvas Assignments, or Canvas
  Quizzes
* No more copy-and-pasting grades and commments: automated upload of
  Canvas grades and gradelogs
* Flatten (extract) archived submissions
* Gradescope integration: generate a Gradescope autograder tarball for
  an assignment with one command

Credits
---------

* Austin Adams (@ausbin) for creating lc3grade, which eventually became
  zucchini
* Cem Gokmen (@skyman) for suggesting converting lc3grade into a
  generalized autograder for more than just C and LC-3 homeworks, and
  creating the initial structure of zucchini
* Patrick Tam (@pjztam) for implementing a bunch of graders, gradelogs,
  and gradelog upload
* Kexin Zhang (@kexin-zhang) for exploring Canvas bulk submission
  downloads and for creating the demo downloader, which changed our
  lives
* Travis Adams (@travis-adams) for nothing
