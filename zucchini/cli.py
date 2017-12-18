# -*- coding: utf-8 -*-

"""Command-line interface to zucchini."""

import click


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

@main.command('run-grader')
def run_grader():
    """
    Grade the submission held in a directory.

    Useful for grading an individual submission component in a docker
    container.
    """
    pass


@main.command()
def export():
    """Export grades for uploading."""
    pass


if __name__ == "__main__":
    main()
