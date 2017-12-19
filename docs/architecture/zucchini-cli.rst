================
The Zucchini CLI
================

Set the user configuration: what’s your name? etc. and reset if
necessary. Run by default on first run.

::

    zucc setup

Tap into a Git repo to be able to use configs from it using the tap name
that you set:

::

    zucc farm add <git-repo-url> <tap-name>
    zucc farm remove <tap-name>
    zucc farm recache <tap-name> # Equivalent to untapping tap-name and then
    tapping its URL again as tap-name

List the assignments available for grading

::

    zucc list [<tap-name>]

Update the taps

::

    zucc update [<tap-name>]

Load submissions using a loader:

::

    zucc load <loader-name> [<loader-parameters>]

    # Example with the Sakai loader:
    zucc load sakai bulk_download.zip

Start grading using a config found on one of the taps (this will
automatically update the tap)

::

    zucc grade <tap-name>/<assignment-name>

Export existing grading results using one of the exporters:

::

    zucc export <exporter-name> [<exporter-parameters>]

    # Example with the CSV exporter:
    zucc export csv hw11.csv
