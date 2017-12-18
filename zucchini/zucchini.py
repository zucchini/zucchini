# -*- coding: utf-8 -*-

"""This file contains the ZucchiniState class that provides context for the grader.
The context should include the grader's local configuration, the Assignment object related
to the assignment in the present directory if one exists, and an instance of the FarmManager class."""

import os

import yaml

from utils import EmailParamType
from assignment import Assignment
from farms import FarmManager
from constants import FARM_DIRECTORY

class ZucchiniState(object):
    REQUIRED_CONFIG_FIELDS = [
        ("user_name", "Grader Name", str),
        ("user_email", "Grader Email", EmailParamType())
    ]

    def __init__(self, user_name, user_email, config_directory, assignment_directory):
        self.config_directory = config_directory

        self.user_name = user_name
        self.user_email = user_email

        self.assignment = None
        self.assignmentError = None

        try:
            self.assignment = Assignment(assignment_directory)
        except ValueError as e:
            self.assignmentError = e
            # TODO: I can imagine this being an antipattern, but we need to tolerate missing assignments

        self.farm_manager = FarmManager(os.path.join(config_directory, FARM_DIRECTORY))

    @staticmethod
    def save_config(cfg_file, cfg_dict):
        # Make sure all the necessary fields are included
        for x in ZucchiniState.REQUIRED_CONFIG_FIELDS:
            if x[0] not in cfg_dict:
                raise ValueError("Config field %s is not included in the config that is being saved." % x[1])

        yaml.safe_dump(cfg_dict, cfg_file, default_flow_style=False)

    @staticmethod
    def load_from_config(config_file, config_directory, assignment_directory):
        config = yaml.safe_load(config_file)

        config['config_directory'] = config_directory
        config['assignment_directory'] = assignment_directory

        return ZucchiniState(**config)
