import os

import yaml
import git

ASSIGNMENT_CONFIG = ".zucchini.yml"

# This class contains the Assignment configuration for the local file
class Assignment(object):
    def __init__(self, root):
        # Confirm the presence of a git repo here
        try:
            self.repo = git.Repo(root)
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("This directory is not a valid git repository.")

        configFilePath = os.path.join(root, ASSIGNMENT_CONFIG)

        if not os.path.exists(configFilePath):
            raise ValueError("This directory is not a valid Zucchini assignment: the Zucchini config is missing.")

        # TODO: Parse the whole thing here

