"""
Utilities for gradescope autograding.
"""

import os
import json
from fractions import Fraction
from zipfile import ZipFile, ZIP_DEFLATED

from . import __version__ as ZUCCHINI_VERSION
from .constants import ASSIGNMENT_CONFIG_FILE, ASSIGNMENT_FILES_DIRECTORY
from .utils import ConfigDictMixin, ConfigDictNoMangleMixin, \
                   datetime_from_string, recursive_get_using_string


class GradescopeMetadata(object):
    """
    Parse the metadata as described in:
    https://gradescope-autograders.readthedocs.io/en/latest/submission_metadata/
    """

    _ATTRS = [
        ('student_name', 'users.0.name', str),
        ('submission_date', 'created_at', datetime_from_string),
        ('due_date', 'assignment.due_date', datetime_from_string),
        # The nested int(float(..)) deal is because int('100.0')
        # explodes
        ('total_points', 'assignment.outline.0.weight',
            lambda pts: int(float(pts))),
    ]

    def __init__(self, json_dict):
        for attr, key, type_ in self._ATTRS:
            val = recursive_get_using_string(json_dict, key)
            setattr(self, attr, type_(val))

    @classmethod
    def from_json_path(cls, json_path):
        with open(json_path, 'r') as json_fp:
            return cls(json.load(json_fp))


class GradescopeAutograderTestOutput(ConfigDictNoMangleMixin, ConfigDictMixin):
    """
    Output of a single test in Gradescope JSON.
    """

    def __init__(self, name=None, score=None, max_score=None, output=None):
        self.name = name
        self.score = score
        self.max_score = max_score
        self.output = output


class GradescopeAutograderOutput(ConfigDictNoMangleMixin, ConfigDictMixin):
    """
    Hold Gradescope Autograder output as described in
    https://gradescope-autograders.readthedocs.io/en/latest/specs/#output-format
    """

    def __init__(self, score=None, tests=None, extra_data=None):
        self.score = score
        self.tests = [GradescopeAutograderTestOutput.from_config_dict(test)
                      for test in tests] if tests is not None else None
        self.extra_data = extra_data

    def to_config_dict(self, *args):
        dict_ = super(GradescopeAutograderOutput, self).to_config_dict(*args)
        if dict_.get('tests', None):
            dict_['tests'] = [test.to_config_dict() for test in dict_['tests']]
        return dict_

    @staticmethod
    def _two_decimals(grade, frac):
        """Convert a fraction to string with two decimal points"""
        return '{:.02f}'.format(grade.to_float(frac))

    @classmethod
    def from_grade(cls, grade):
        """
        Convert a grading_manager.Grade to Gradescope JSON.
        """

        score = grade.score()
        tests = []
        # Store the component grades in the extra_data field
        extra_data = {'component_grades': grade.serialized_component_grades()}

        computed_grade = grade.computed_grade()

        # Add penalties
        for penalty in computed_grade.penalties:
            if penalty.points_delta != 0:
                # Hack: Display -37 as 0/37 and +37 as 37/37
                fake_max_score = cls._two_decimals(
                    grade, abs(penalty.points_delta))
                fake_score = cls._two_decimals(grade, Fraction(0)) \
                    if penalty.points_delta < 0 else fake_max_score
                test = GradescopeAutograderTestOutput(
                    name=penalty.name,
                    score=fake_score,
                    max_score=fake_max_score)
                tests.append(test)

        # Add actual test results
        for component in computed_grade.components:
            if component.error:
                test = GradescopeAutograderTestOutput(
                    name=component.name,
                    score=cls._two_decimals(grade, component.points_got),
                    max_score=cls._two_decimals(
                        grade, component.points_possible),
                    output='{}\n{}'.format(component.error,
                                           component.error_verbose or ''))
                tests.append(test)
            else:
                for part in component.parts:
                    if part.deductions:
                        deductions = 'Deductions: {}\n\n'.format(
                            ', '.join(part.deductions))
                    else:
                        deductions = ''

                    test = GradescopeAutograderTestOutput(
                        name='{}: {}'.format(component.name, part.name),
                        score=cls._two_decimals(grade, part.points_got),
                        max_score=cls._two_decimals(
                            grade, part.points_possible),
                        output=deductions + part.log)
                    tests.append(test)

        return cls(score=score, tests=tests, extra_data=extra_data)

    def to_json_stream(self, fp):
        json.dump(self.to_config_dict(), fp)


SETUP_SH = r'''#!/bin/bash
# THIS FILE WAS GENERATED BY ZUCCHINI
set -e

cd /autograder/source
# Prevent apt from prompting for input and hanging the build
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-pip python3-wheel {prereqs}
pip3 install {pip_install_arg}
{extra_setup_commands}
'''


RUN_AUTOGRADER = r'''#!/bin/bash
# THIS FILE WAS GENERATED BY ZUCCHINI
set -e
set -o pipefail

cd /autograder/source
zucc flatten /autograder/submission
{grade_cmd_prefix}zucc grade-submission /autograder/submission \
    | zucc gradescope bridge /autograder/submission_metadata.json \
    > /autograder/results/results.json
'''


RUN_GRAPHICAL_SH = r'''#!/bin/bash

cat >xorg.conf <<'EOF'
# This xorg configuration file is meant to be used by xpra
# to start a dummy X11 server.
# For details, please see:
# https://xpra.org/Xdummy.html

Section "ServerFlags"
  Option "DontVTSwitch" "true"
  Option "AllowMouseOpenFail" "true"
  Option "PciForceNone" "true"
  Option "AutoEnableDevices" "false"
  Option "AutoAddDevices" "false"
EndSection

Section "Device"
  Identifier "dummy_videocard"
  Driver "dummy"
  Option "ConstantDPI" "true"
  VideoRam 192000
EndSection

Section "Monitor"
  Identifier "dummy_monitor"
  HorizSync   5.0 - 1000.0
  VertRefresh 5.0 - 200.0
  Modeline "1024x768" 18.71 1024 1056 1120 1152 768 786 789 807
EndSection

Section "Screen"
  Identifier "dummy_screen"
  Device "dummy_videocard"
  Monitor "dummy_monitor"
  DefaultDepth 24
  SubSection "Display"
    Viewport 0 0
    Depth 24
    Modes "1024x768"
    Virtual 1024 768
  EndSubSection
EndSection
EOF

/usr/lib/xorg/Xorg -noreset -logfile ./xorg.log -config ./xorg.conf :69 \
    >/dev/null 2>&1 &

xorg_pid=$!

export DISPLAY=:69
"$@"

exitcode=$?

kill "$xorg_pid" || {
    printf 'did not kill Xorg!\n' >&2
    exit 1
}

exit $exitcode'''


class GradescopeAutograderZip(object):
    """
    Generates a Gradesope autograder zip file from which Gradescope
    generates a Docker image for grading.
    """

    def __init__(self, path='.', prerequisites=None, extra_setup_commands=None,
                 needs_display=False, wheel_path=None):
        self.path = path
        self.prerequisites = prerequisites or []
        self.extra_setup_commands = extra_setup_commands or []
        self.needs_display = needs_display
        self.wheel_path = wheel_path

        # Need this for
        if self.needs_display:
            prerequisites.append('xserver-xorg-video-dummy')

    def _relative_path(self, abspath):
        """
        Convert an absolute path to an assignment file to a path
        relative to self.path.
        """
        return os.path.relpath(abspath, self.path)

    def _real_path(self, relpath):
        """
        Convert a relative path to an assignment file to an absolute
        path.
        """
        return os.path.join(self.path, relpath)

    def _write_file(self, file_path, zipfile, real_path=None):
        """
        Add a file to the generated zip file. file_path is the
        destination path in the .zip file. If real_path is not provided,
        it will be self.path/file_path.
        """
        if real_path is None:
            real_path = self._real_path(file_path)
        zipfile.write(real_path, file_path)

    def _write_string(self, string, path, zipfile):
        """
        Add a file to the generated zip file. file_path should be relative to
        self.path.
        """
        zipfile.writestr(path, string)

    def _write_dir(self, dir_path, zipfile):
        """
        Recursively add a directory to the generated zip file. dir_path
        should be relative to self.path.
        """

        real_path = self._real_path(dir_path)

        for dirpath, _, filenames in os.walk(real_path):
            for filename in filenames:
                relpath = self._relative_path(os.path.join(dirpath, filename))
                self._write_file(relpath, zipfile)

    def write_zip(self, file):
        """
        Write the autograder .zip to file. If file is a file-like
        object, write it there, otherwise it should be a string
        designating the destination path.
        """

        with ZipFile(file, 'w', ZIP_DEFLATED) as zipfile:
            self._write_file(ASSIGNMENT_CONFIG_FILE, zipfile)

            grading_files = self._real_path(ASSIGNMENT_FILES_DIRECTORY)
            if os.path.exists(grading_files):
                self._write_dir(ASSIGNMENT_FILES_DIRECTORY, zipfile)

            if self.needs_display:
                self._write_string(RUN_GRAPHICAL_SH, 'run_graphical.sh',
                                   zipfile)
                grade_cmd_prefix = 'bash run_graphical.sh '
            else:
                grade_cmd_prefix = ''

            run_autograder = RUN_AUTOGRADER.format(
                grade_cmd_prefix=grade_cmd_prefix)
            self._write_string(run_autograder, 'run_autograder', zipfile)

            if self.wheel_path is None:
                pip_install_arg = 'zucchini==' + ZUCCHINI_VERSION
            else:
                # Can't just name it `zucchini.whl' or something because
                # this upsets pip
                wheel_filename = os.path.basename(self.wheel_path)
                self._write_file(wheel_filename, zipfile,
                                 real_path=self.wheel_path)
                pip_install_arg = wheel_filename

            extra_setup_commands = '\n'.join(self.extra_setup_commands)
            setup_sh = SETUP_SH.format(
                pip_install_arg=pip_install_arg,
                prereqs=' '.join(self.prerequisites),
                extra_setup_commands=extra_setup_commands)
            self._write_string(setup_sh, 'setup.sh', zipfile)
