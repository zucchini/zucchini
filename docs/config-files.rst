==================
Config File Format
==================

Configuration files need to be valid YAML files that contain the following
fields:

.. code:: yaml

    name: # Friendly name for the assignment
    author: # Author's name (and email if possible)
    components:
      - name: # Friendly name for the component
        weight: # Weight of the component (integer)
        files: # Files that need to be copied from the submission folder
        grading-files: # Files that need to be copied from the grading folder
        backend: # Name of the Python class for the grader (e.g. PromptGrader)
        backend-options:
          # The grader backend's options come here - these are listed on the grader's docs
