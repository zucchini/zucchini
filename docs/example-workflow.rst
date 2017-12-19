=========================
Example Zucchini Workflow
=========================

The following is a zucchini workflow that would be used for grading an
assignment, Homework Zero, for a fictional class CS 1337 at Utopia Tech.
We assume that Utopia Tech uses Sakai and that we have downloaded
student submissions into the ~/Downloads/ directory as
bulk_download.zip. We also assume that Docker is installed and that we
have non-sudo access to the Docker daemon.

Let’s start by installing zucchini

::

    pip install zucchini

We set up our workspace by entering our identity details:

::

    zucc setup

Then we add the farm for the metadata repository created by our
instructor. We name it ``cs1337-fall1970``:

::

    zucc farm https://github.utopiatech.edu/cs1337/fall1970.git cs1337-fall1970

We list the assignments on our farms to find the one we’re looking for:

::

    zucc list

From the output of this, we find that it’s HW0 that we’re trying to
grade. We use ``zucc init`` to create a directory with the HW0 grading
configuration. This will download the config.yml file into our directory
as well as filling the ``grader/`` directory with the grader files. We
use our farm’s name as well as the assignment’s name on the farm.

::

    zucc init cs1337-fall1970/hw0 hw0-grading
    cd hw0-grading

Then, we load the submissions we downloaded. This will unpack and
flatten the submissions, putting them in the correct directory structure
in the ``submissions/`` directory.

::

    zucc load sakai ~/Downloads/bulk_download.zip

Then, we start the grading process. Running the grade command without a
config file name will use by default config.yml file in the current
directory. This will grade each submission separately and put their
results in their folders as JSON files.

::

    zucc grade

If ``zucc grade`` prints out that some submissions are broken, we can
interactively step through and fix them with

::

    zucc grade --fix

Now that we’re done grading, we want to export our grades in a CSV
format to be entered on our Sakai site:

::

    zucc export csv grades.csv

And we’re done!
