# -*- coding: utf-8 -*-

"""Command-line interface to zucchini."""
import os

import click

from .utils import mkdir_p
from .grading_manager import GradingManager
from .zucchini import ZucchiniState
from .constants import APP_NAME, USER_CONFIG, DEFAULT_SUBMISSION_DIRECTORY

pass_state = click.make_pass_decorator(ZucchiniState)


def setup_handler():
    config_dir = click.get_app_dir(APP_NAME, force_posix=True, roaming=True)
    mkdir_p(config_dir)

    config_path = os.path.join(config_dir, USER_CONFIG)

    click.echo("Zucchini will now set up your user configuration, overwriting"
               "any existing settings.")

    new_conf = {}
    for required_field in ZucchiniState.REQUIRED_CONFIG_FIELDS:
        new_conf[required_field[0]] = click.prompt(required_field[1],
                                                   type=required_field[2])

    with click.open_file(config_path, 'w') as cfg_file:
        ZucchiniState.save_config(cfg_file, new_conf)


@click.group()
@click.option('-a', '--assignment', default='.',
              help="Path of the directory containing the Zucchini assignment.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@click.pass_context
def cli(ctx, assignment):
    """zucchini, a fun autograder for the whole family."""

    config_dir = click.get_app_dir(APP_NAME, force_posix=True, roaming=True)
    mkdir_p(config_dir)

    config_path = os.path.join(config_dir, USER_CONFIG)

    try:
        with click.open_file(config_path, 'r') as cfg_file:
            ctx.obj = ZucchiniState.load_from_config(cfg_file, config_dir,
                                                     assignment)
    except:  # noqa
        # TODO: Maybe better handling here, is it corrupt or nonexistent?
        click.echo("We need to set up your configuration before doing any"
                   "other work.")
        setup_handler()
        click.echo("Configuration set up successfully! Please retry your"
                   "original command now.")
        raise click.Abort()  # TODO: Use better exception
        # TODO: The way we handle this here makes it impossible to have a setup
        # or reset command. We kinda need one.


@cli.command()
@pass_state
def update(state):
    """Update all farms."""
    # TODO: Add support for single-farm listing
    click.echo("Updating farms...")
    state.farm_manager.update_all_farms()
    click.echo("Successfully updated all farms.")
    # TODO: Add stats about # configurations etc


@cli.command('list')
@pass_state
def list_assignments(state):
    """Update all farms and list downloadable assignments."""
    # TODO: Add support for single-farm listing
    # TODO: also potentially do this by invoking the update cmd
    click.echo("Updating farms...")
    state.farm_manager.update_all_farms()
    click.echo("Successfully updated all farms.\n")

    click.echo("Available assignments:")
    assignments = state.farm_manager.list_farm_assignments()
    click.echo("\n".join(["%s: %s" % x for x in assignments]))


@cli.command()
@click.argument('assignment-name')
@click.option('-t', '--target', default='.',
              help="Path of the directory to clone the zucchini assignment"
                   "folder into.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@pass_state
def init(state, assignment_name, target):
    """Configure an assignment for grading."""
    state.farm_manager.clone_farm_assignment(assignment_name, target)
    click.echo("Successfully initialized %s into %s." % (assignment_name,
                                                         target))


@cli.command()
@click.option('-f', '--from-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory to read submissions from.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@pass_state
def grade(state, from_dir):
    """Grade submissions."""

    # TODO: We need to validate the assignment object

    # At this point, the assignment object is loaded. We need a GradingManager

    # TODO: We need to set up the submission filtering function to pass to the
    # grading manager

    grading_manager = GradingManager(state.assignment, from_dir)
    grading_manager.grade()


@cli.command()
@pass_state
def export(state):
    """Export grades for uploading."""
    pass


@cli.group()
def farm():
    """Manage zucchini farms."""
    pass


@farm.command('add')
@click.argument('farm-url')
@click.argument('farm-name')
@pass_state
def add_farm(state, farm_url, farm_name):
    state.farm_manager.add_farm(farm_url, farm_name)
    click.echo("Successfully added farm %s" % farm_name)


@farm.command('recache')
@click.argument('farm-name')
@pass_state
def recache_farm(state, farm_name):
    state.farm_manager.recache_farm(farm_name)
    click.echo("Successfully recached farm %s" % farm_name)


@farm.command('list')
@pass_state
def list_farms(state):
    farms = state.farm_manager.list_farms()
    click.echo("\n".join(farms))


@farm.command('remove')
@click.argument('farm-name')
@pass_state
def remove_farm(state, farm_name):
    state.farm_manager.remove_farm(farm_name)
    click.echo("Successfully removed farm %s" % farm_name)


if __name__ == "__main__":
    cli()
