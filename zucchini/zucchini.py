# -*- coding: utf-8 -*-

"""This file contains the ZucchiniState class that provides context for the
grader. The context should include the grader's local configuration,
the Assignment object related to the assignment in the present directory if
one exists, and an instance of the FarmManager class."""

import os

import yaml

from .canvas import CanvasAPI
from .amazon import AmazonAPI
from .utils import EmailParamType
from .assignment import Assignment
from .farms import FarmManager
from .constants import FARM_DIRECTORY


class ZucchiniState(object):
    REQUIRED_CONFIG_FIELDS = [
        ("user_name", "Grader Name", str),
        ("user_email", "Grader Email", EmailParamType())
    ]

    def __init__(self, user_name, user_email, config_directory,
                 assignment_directory, canvas_url='', canvas_token='',
                 aws_access_key_id='', aws_secret_access_key='',
                 aws_s3_bucket_name=''):
        self.config_directory = config_directory

        self.user_name = user_name
        self.user_email = user_email

        self.canvas_url = canvas_url
        self.canvas_token = canvas_token

        self.assignment_directory = assignment_directory
        self._assignment = None

        self.submission_dir = None

        self.farm_manager = FarmManager(
            os.path.join(config_directory, FARM_DIRECTORY))

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_s3_bucket_name = aws_s3_bucket_name

    def get_assignment(self):
        """
        Return an Assignment instance based on the configuration for this
        assignment.
        """

        if self._assignment is None:
            self._assignment = Assignment(self.assignment_directory)

        return self._assignment

    def canvas_api(self):
        """
        Return a CanvasAPI instance configured according to the user's global
        configuration.
        """

        if not self.canvas_url or not self.canvas_token:
            raise ValueError('The Canvas API is not configured!')

        return CanvasAPI(self.canvas_url, self.canvas_token)

    def get_amazon_api(self):
        """
        Return an AmazonAPI instance configured according to the user's global
        configuration.
        """

        if not self.aws_access_key_id or \
            not self.aws_secret_access_key or \
                not self.aws_s3_bucket_name:
                    raise ValueError(
                        'The Amazon API is not configured')

        return AmazonAPI(
            self.aws_access_key_id,
            self.aws_secret_access_key,
            self.aws_s3_bucket_name)

    @staticmethod
    def save_config(cfg_file, cfg_dict):
        # Make sure all the necessary fields are included
        for x in ZucchiniState.REQUIRED_CONFIG_FIELDS:
            if x[0] not in cfg_dict:
                raise ValueError("Config field %s is not included in the "
                                 "config that is being saved." % x[1])

        yaml.safe_dump(cfg_dict, cfg_file, default_flow_style=False)

    @staticmethod
    def load_from_config(config_file, config_directory, assignment_directory):
        config = yaml.safe_load(config_file)

        config['config_directory'] = config_directory
        config['assignment_directory'] = assignment_directory

        return ZucchiniState(**config)
