import os
import shutil
import re

import git
import yaml

from .utils import mkdir_p
from .constants import FARM_ASSIGNMENT_NAME_REGEX, FARM_IDENTIFIER_FILE


class FarmAssignment(object):
    """A farm assignment is an assignment on a farm that can be downloaded.
    The file here is a simple .yml file that contains just a name, maintainer,
    and a Git URL for the assignment."""

    def __init__(self, name, maintainer, url):
        self.name = name
        self.maintainer = maintainer
        self.url = url

    def clone(self, path):
        return git.Repo.clone_from(url=self.url, to_path=path)
        # TODO: Why return a repo? We need success info

    def __str__(self):
        return "%s (Maintainer: %s)" % (self.name, self.maintainer)


class Farm(object):
    def __init__(self, path):
        self.path = path

        self.repo = git.Repo(self.path)
        self.farm_assignments = dict()

        self._parse_assignments()

    def _parse_assignments(self):
        self.farm_assignments = dict()

        # Let's read the directory structure here
        for root, subdirs, files in os.walk(self.path):
            for file_name in files:
                match = re.match(FARM_ASSIGNMENT_NAME_REGEX, file_name)

                if match is not None:  # This might be an assignment
                    try:
                        file_path = os.path.join(root, file_name)
                        with open(file_path, 'r') as config_file:
                            config = yaml.safe_load(config_file)
                            assignment = FarmAssignment(**config)

                            slug = os.path.splitext(
                                os.path.relpath(file_path, self.path))[0]
                            self.farm_assignments[slug] = assignment
                    except:  # noqa
                        # TODO: Do something here: the load failed
                        pass

    def get_farm_assignment_by_name(self, assignment_name):
        return self.farm_assignments[assignment_name]

    def update(self):
        """Call Git Pull on the repository to update its contents"""
        self.repo.remotes.origin.pull()
        # TODO: Get some info here about the fetch status
        self._parse_assignments()

    def list_assignments(self):
        return sorted(self.farm_assignments.items(), key=lambda x: x[0])


class FarmManager(object):
    def __init__(self, farm_root):
        self.root = farm_root

        # Generate our farms dir if it doesnt exist yet
        mkdir_p(self.root)

        self.farms = {}
        self._parse_farms()

    def _parse_farms(self):
        self.farms = {}

        farms = [name for name in os.listdir(self.root) if
                 os.path.isdir(os.path.join(self.root, name))]
        self.farms = {name: Farm(os.path.join(self.root, name)) for name in
                      farms}

    def get_farm_by_name(self, name):
        return self.farms[name]

    def get_path_for_farm_name(self, farm_name):
        return os.path.join(self.root, farm_name)

    def farm_exists(self, farm_name):
        return os.path.exists(self.get_path_for_farm_name(farm_name))

    def list_farms(self):
        return sorted(self.farms.keys())

    def list_farm_assignments(self):
        assignments = []
        for farm_name, farm in self.farms.items():
            assignments += [("%s/%s" % (farm_name, x[0]), x[1]) for x in
                            farm.list_assignments()]

        return sorted(assignments, key=lambda x: x[0])

    def list_farm_assignments_by_farm(self, farm_name):
        farm = self.get_farm_by_name(farm_name)
        return farm.list_assignments()

    def clone_farm_assignment(self, assignment_name, path):
        parsed_name = assignment_name.split('/', 1)

        if len(parsed_name) != 2:
            raise ValueError("You need to specify assignment names in"
                             "farm/assignment format.")

        farm, assignment = parsed_name

        clone_path = os.path.join(path, assignment.split('/')[-1])
        self.get_farm_by_name(farm).get_farm_assignment_by_name(
            assignment).clone(clone_path)

    def add_farm(self, farm_url, farm_name):
        if self.farm_exists(farm_name):
            raise ValueError("A farm by this name already exists.")

        path = self.get_path_for_farm_name(farm_name)
        repo = git.Repo.clone_from(url=farm_url, to_path=path)

        if repo is None:
            raise ValueError("Could not add farm: is the URL valid?")

        if not os.path.exists(os.path.join(path, FARM_IDENTIFIER_FILE)):
            shutil.rmtree(path)
            raise ValueError("The given git repo is not a valid zucchini "
                             "farm.")

        self._parse_farms()

    def update_farm(self, farm_name):
        farm = self.get_farm_by_name(farm_name)
        farm.update()

    def update_all_farms(self):
        for farm in self.farms.values():
            farm.update()

    def recache_farm(self, farm_name):
        # TODO: FIX THIS
        # farm = self.get_farm_by_name(farm_name)

        # farm_url = farm.repo.remotes.origin.urls[0] <--- the problem

        # self.remove_farm(farm_name)
        # self.add_farm(farm_url, farm_name)

        pass

    def remove_farm(self, farm_name):
        farm = self.get_farm_by_name(farm_name)
        shutil.rmtree(farm.path)

        self._parse_farms()
