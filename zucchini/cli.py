# -*- coding: utf-8 -*-

"""Command-line interface to zucchini."""

import click
from .backend import BackendRunner, InvalidBackendError


@click.group()
def main(args=None):
    """zucchini, a fun autograder for the whole family."""
    pass


@main.command()
def setup():
    """Prompt for initial global config."""
    pass


@main.command()
def farm():
    """Add a farm for zucchini configuration."""
    pass


@main.command()
def list():
    """Update all farms and list all configurations."""
    pass


@main.command()
def init():
    """Configure a directory for grading."""
    pass


@main.command()
def grade():
    """Grade submissions."""
    pass


@main.command('run-backend')
@click.argument('backend')
@click.argument('directory', type=click.Path(exists=True))
@click.option('--file', multiple=True, help='submitted file')
@click.option('--grader-file', multiple=True, help='file for grading')
def run_backend(backend, directory, file, grader_file):
    """
    Run a submission through a backend.

    Useful for grading an individual submission component in a docker
    container. Will use backend alias BACKEND inside temporary grading
    directory DIRECTORY.
    """

    try:
        runner = BackendRunner(backend, files=file, grader_files=grader_file)
    except InvalidBackendError:
        raise click.BadParameter("no such backend `{}'".format(backend),
                                 param_hint='backend')

    runner.run(directory)


@main.command()
def export():
    """Export grades for uploading."""
    pass


if __name__ == "__main__":
    main()
