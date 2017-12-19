Welcome to the zucchini-refactor wiki!

Getting Started
---------------

Take a look at the [[Example Zucchini Workflow]] we provide, or view [[a
complete list|Zucchini CLI]] of all Zucchini command line options.

How Taps Work
-------------

Right now, zucchini supports grading through two methods - with a
locally available configuration file and test suite, or using “taps” -
git repos that contain metadata about graders and configurations.

For a given class, for example, the instructor may choose to maintain a
single Git repo - a tap - that will contain metadata about all of the
course’s assignments. Once graders tap into this repo, they will be able
to fetch grading configurations and grading files using git
automatically and start grading right away without having to download or
update any assignment files.

This behavior is managed by the [[Tap Manager|Tap Manager]] and the only
method of tapping is through Git.

How Loading Works
-----------------

For grading to be possible, zucchini requires the assignment submissions
to be in a precise directory structure. More information about this
requirement is available in the [[Directory Structure|Directory
Structure]] page.

As a result, loaders that implement the [[Loader Interface|Loader
Interface]] are required to go from arbitrary data sources, like Git and
zip / tar archive files, to the zucchini directory structure.

Loaders that are currently available include: \* [[Sakai Loader|Sakai
Loader]]

How Grading Works
-----------------

The grading process is managed by the [[Grading Manager|Grading
Manager]] class, with each rubric item being delegated to a Grader that
implements the [[Grader Interface|Grader Interface]].

Current implementations of the Grader Interface include:

-  [[Prompt Grader|Prompt Grader]]
-  [[Open-File Grader|Open-File Grader]]
-  [[LC3 Grader|LC3 Grader]]
-  [[LibCheck Grader|LibCheck Grader]]
-  [[JUnit Grader|JUnit Grader]]
-  [[Docker Wrapper Grader|Docker Wrapper Grader]]

How Exporting Works
-------------------

Once grading is done, you will need to export your grades. The export
process is managed by the [[Export Manager|Export Manager]] class, which
gathers the submissions’ grades from individual folders into a single
dictionary for use by the exporter backends, which have to implement the
[[Exporter Interface|Exporter Interface]]. Currently, the supported
exporter backends are as follows:

-  [[CSV Exporter|CSV Exporter]]
-  [[TXT Exporter|TXT Exporter]]

How Config Files Work
---------------------

Config Files are not too relevant for graders, but they are the most
important to-do list item for an instructor when creating a
zucchini-compatible assignment to be graded. Information about config
file structure and options is available in the [[Config Files|Config
Files]] page.
