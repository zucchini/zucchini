# -*- coding: utf-8 -*-

"""This file contains the ZucchiniState class that provides context for the
grader. The context should include the grader's local configuration,
the Assignment object related to the assignment in the present directory if
one exists, and an instance of the FarmManager class."""

import os

import yaml

from .canvas import CanvasAPI
from .amazon import AmazonAPI
from .utils import ConfigDictMixin
from .assignment import Assignment
from .farms import FarmManager
from .constants import FARM_DIRECTORY


class ZucchiniConfig(ConfigDictMixin):
    """Holds user configuration from user.yml"""

    def __init__(self, config_directory, user_name, user_email, canvas_url='',
                 canvas_token='', aws_access_key_id='',
                 aws_secret_access_key='', aws_s3_bucket_name=''):
        self.config_directory = config_directory

        self.user_name = user_name
        self.user_email = user_email

        self.canvas_url = canvas_url
        self.canvas_token = canvas_token

        self.farm_manager = FarmManager(
            os.path.join(config_directory, FARM_DIRECTORY))

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_s3_bucket_name = aws_s3_bucket_name


class ZucchiniState(object):
    def __init__(self, assignment_directory):
        self.assignment_directory = assignment_directory
        self.submission_dir = None
        self._assignment = None
        self._config = None

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

        if not self._config or not self._config.canvas_url or \
                not self._config.canvas_token:
            raise ValueError('The Canvas API is not configured!')

        return CanvasAPI(self._config.canvas_url, self._config.canvas_token)

    def get_amazon_api(self):
        """
        Return an AmazonAPI instance configured according to the user's global
        configuration.
        """

        if not self._config or \
                not self._config.aws_access_key_id or \
                not self._config.aws_secret_access_key or \
                not self._config.aws_s3_bucket_name:
            raise ValueError('The Amazon API is not configured')

        return AmazonAPI(
            self._config.aws_access_key_id,
            self._config.aws_secret_access_key,
            self._config.aws_s3_bucket_name)

    @property
    def user_name(self):
        return self._config.user_name

    @property
    def farm_manager(self):
        return self._config.farm_manager

    def save_config_to_file(self, config_file):
        config_dict = self._config.to_config_dict('config_directory')
        yaml.safe_dump(config_dict, config_file, default_flow_style=False)

    def load_config_from_dict(self, config_dict, config_directory):
        """Load user configuation from a dictionary."""
        self._config = ZucchiniConfig.from_config_dict(
            config_dict, config_directory=config_directory)

    def load_config_from_file(self, config_file, config_directory):
        """Load user configuration from a file-like object as yaml."""
        config_dict = yaml.safe_load(config_file)
        self.load_config_from_dict(config_dict, config_directory)
