=====================================
Overview of the Zucchini Architecture
=====================================

How Farms Work
--------------

Right now, zucchini supports grading through two methods - with a
locally available configuration file and test suite, or using “farms” -
git repos that contain metadata about graders and configurations.

For a given class, for example, the instructor may choose to maintain a
single Git repo - a farm - that will contain metadata about all of the
course’s assignments. Once graders tap into this farm, they will be able
to fetch grading configurations and grading files using git
automatically and start grading right away without having to download or
update any assignment files.

This behavior is managed by the [[Farm Manager|farm-manager]] and the only
method of tapping is through Git.

How Loading Works
-----------------

For grading to be possible, zucchini requires the assignment submissions
to be in a precise directory structure. More information about this
requirement is available in the [[Directory Structure|directory-structure]]
page.

As a result, loaders that implement the
[[Loader Interface|loading/loader-interface]]are required to go from arbitrary
data sources, like Git and zip / tar archive files, to the zucchini directory
structure.

Loaders that are currently available include:
* [[Sakai Loader|loading/sakai-loader]]
* [[Canvas Loader|loading/canvas-loader]]

How Grading Works
-----------------

The grading process is managed by the
[[Grading Manager|grading/grading-manager]] class, with each rubric item being
delegated to a Grader that implements the
[[Grader Interface|grading/grader-interface]].

Current implementations of the Grader Interface include:

-  [[Prompt Grader|grading/prompt-grader]]
-  [[Open-File Grader|grading/open-file-grader]]
-  [[LC3Test Grader|grading/lc3test-grader]]
-  [[LibCheck Grader|grading/libcheck-grader]]
-  [[JUnit Grader|grading/junit-grader]]
-  [[Docker Wrapper Grader|grading/docker-wrapper-grader]]

How Exporting Works
-------------------

Once grading is done, you will need to export your grades. The export
process is managed by the [[Export Manager|exporting/export-manager]] class, which
gathers the submissions’ grades from individual folders into a single
dictionary for use by the exporter backends, which have to implement the
[[Exporter Interface|exporting/exporter-interface]]. Currently, the supported
exporter backends are as follows:

-  [[CSV Exporter|exporting/csv-exporter]]
-  [[TXT Exporter|exporting/txt-exporter]]

