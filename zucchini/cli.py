# -*- coding: utf-8 -*-

"""Command-line interface to zucchini."""
import os
import sys
import csv
import shutil

import click

from .utils import mkdir_p, CANVAS_URL, CANVAS_TOKEN
from .grading_manager import GradingManager
from .zucchini import ZucchiniState
from .canvas import CanvasAPIError, CanvasNotFoundError, CanvasInternalError
from .constants import APP_NAME, USER_CONFIG, DEFAULT_SUBMISSION_DIRECTORY, \
                       SUBMISSION_FILES_DIRECTORY
from .submission import Submission
from .flatten import flatten

pass_state = click.make_pass_decorator(ZucchiniState)


def setup_handler():
    config_dir = click.get_app_dir(APP_NAME, force_posix=True, roaming=True)
    mkdir_p(config_dir)

    config_path = os.path.join(config_dir, USER_CONFIG)

    click.echo("Zucchini will now set up your user configuration, overwriting "
               "any existing settings.")

    new_conf = {}
    for required_field in ZucchiniState.REQUIRED_CONFIG_FIELDS:
        new_conf[required_field[0]] = click.prompt(required_field[1],
                                                   type=required_field[2])

    new_conf['canvas_url'] = click.prompt('Canvas URL (press enter to skip '
                                          'Canvas configuration)',
                                          type=CANVAS_URL, default='')
    if new_conf['canvas_url']:
        new_conf['canvas_token'] = click.prompt(
            'Canvas API token (To generate one, go to {}/profile/settings and '
            'choose "New Access Token")'
            .format(new_conf['canvas_url']), type=CANVAS_TOKEN)
    else:
        click.echo('Skipping canvas configuration...')
        new_conf['canvas_token'] = ''

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
    """
    zucchini, a fun autograder for the whole family.

    \b
    example workflow:
        $ zucc farm add https://some/git/repo/url.git my-farm
        $ zucc init my-farm/my-assignment
        $ cd my-assignment
        $ zucc load canvas
        $ zucc grade
        $ zucc export canvas

    documentation: https://zucchini.readthedocs.io/
    """

    config_dir = click.get_app_dir(APP_NAME, force_posix=True, roaming=True)
    mkdir_p(config_dir)

    config_path = os.path.join(config_dir, USER_CONFIG)

    try:
        with click.open_file(config_path, 'r') as cfg_file:
            ctx.obj = ZucchiniState.load_from_config(cfg_file, config_dir,
                                                     assignment)
    except:  # noqa
        # TODO: Maybe better handling here, is it corrupt or nonexistent?
        click.echo("We need to set up your configuration before doing any "
                   "other work.")
        setup_handler()
        click.echo("Configuration set up successfully! Please retry your "
                   "original command now.")
        raise SystemExit()  # TODO: Use better exception
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


@cli.group()
@click.option('-t', '--to-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory in which to put submissions loaded.",
              type=click.Path(file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@pass_state
def load(state, to_dir):
    """Load student submissions."""

    state.submission_dir = to_dir


@load.command('sakai')
@pass_state
def load_sakai(state):
    """Load student submissions from Sakai"""
    raise NotImplementedError


@load.command('canvas')
@click.option('--section', '-s', type=lambda s: s.lower(), metavar='SECTION',
              help='section id, substring of section name, or "all"')
@pass_state
def load_canvas(state, section=None):
    """Load student submissions from Canvas"""

    course_id = state.get_assignment().canvas_course_id
    if course_id is None:
        raise click.ClickException('Need to configure canvas in assignment '
                                   'config')

    api = state.canvas_api()
    try:
        sections = tuple(api.list_sections(course_id))
    except CanvasNotFoundError:
        raise click.ClickException('Canvas reports no course with id {}'
                                   .format(course_id))
    except CanvasInternalError:
        raise click.ClickException('Canvas reported an internal error (5xx '
                                   'status code). Try again later?')
    except CanvasAPIError as err:
        raise click.ClickException(str(err))

    if not sections:
        raise click.ClickException('No sections, so no students! Bailing out')

    section_chosen = None

    # Find a section matching criteria (either id or substring of section name)
    while True:
        error_message = None

        # If this is not their first attempt, print an error describing
        # why we're prompting again
        if section is not None:
            if section == 'all':
                break

            # First, try to find a match by id
            try:
                section_id = int(section)
                id_matches = [s for s in sections if section_id == s.id]

                if id_matches:
                    # Assume a section id is unique
                    section_chosen, = id_matches
                    break
            except ValueError:
                # Not an integer
                pass

            # Now, try to find a match by name
            name_matches = [s for s in sections if section in s.name.lower()]

            if len(name_matches) == 1:
                section_chosen, = name_matches
                break
            elif len(name_matches) > 1:
                error_message = 'More than one section matches. Try again? ' \
                                '(Canvas is an extremely good website and ' \
                                'allows duplicate section names, so you may ' \
                                'have to supply an id.)'
            else:
                error_message = 'No sections match. Try again?'

        click.echo('List of sections:')
        for s in sections:
            click.echo(str(s))

        # Print the error message _after_ the list of sections. Even if
        # there are tons of sections, we still want the user to see the
        # error message.
        if error_message:
            click.echo(error_message)

        section = click.prompt('Choose a section (name or id)',
                               default='all', type=lambda s: s.lower())

    assignment_id = state.get_assignment().canvas_assignment_id

    # If they specified "all", use all submissions in the course,
    # otherwise use just those from one section
    if section_chosen is None:
        submissions = api.list_submissions(course_id, assignment_id)
    else:
        submissions = api.list_section_submissions(section_chosen.id,
                                                   assignment_id)

    click.echo('Downloading submissions from Canvas...')
    # Need to iterate over the list of submissions so that click can
    # call len(iterator) to know how to progress the progress bar
    with click.progressbar(list(submissions)) as bar:
        for canvas_submission in bar:
            student_name = canvas_submission.user.sortable_name
            base_dir = os.path.join(state.submission_dir, student_name)
            # Remove submission if it already exists
            shutil.rmtree(base_dir, ignore_errors=True)

            files_dir = os.path.join(base_dir, SUBMISSION_FILES_DIRECTORY)
            mkdir_p(files_dir)
            canvas_submission.download(files_dir)
            flatten(files_dir)

            # Create initial meta.json in submission dir
            submission = Submission(student_name, state.get_assignment(),
                                    base_dir, graded=False,
                                    id=canvas_submission.user_id,
                                    submission_time=canvas_submission.time())
            submission.initialize_metadata()


def print_grades(grades, grader_name):
    """Display grades, an iterable of Grade instances, in a pager."""
    grades = sorted(grades,
                    key=lambda grade: grade.student_name())
    # Length of longest name
    max_name_len = max(len(grade.student_name()) for grade in grades)

    grade_report = '\n'.join(
        '{:<{max_name_len}}\t{}\t{}'.format(
            grade.student_name(),
            grade.score() if grade.graded() else '(ungraded)',
            grade.breakdown(grader_name) if grade.graded() else '',
            max_name_len=max_name_len)
        for grade in grades)
    click.echo_via_pager('grade report:\n\n' + grade_report)


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

    grading_manager = GradingManager(state.get_assignment(), from_dir)

    click.echo('Grading submissions...')

    if grading_manager.is_interactive():
        grades = grading_manager.grade()
    else:
        # Show a progress bar iff all components are non-interactive.
        # This way, we know prompts won't mess up our progress bar.
        with click.progressbar(grading_manager.grade(),
                               grading_manager.submission_count()) as bar:
            grades = list(bar)

    print_grades(grades, state.user_name)


@cli.command('show-grades')
@click.option('-f', '--from-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory to read submissions from.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@pass_state
def show_grades(state, from_dir):
    """Print the grade for all submissions."""
    grading_manager = GradingManager(state.get_assignment(), from_dir)
    print_grades(grading_manager.grades(), state.user_name)


@cli.group()
@click.option('-f', '--from-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory to read submissions from.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@pass_state
def export(state, from_dir):
    """Export grades for uploading."""

    grading_manager = GradingManager(state.get_assignment(), from_dir)
    state.grades = list(grade for grade in grading_manager.grades()
                        if grade.graded())


@export.command('csv')
@click.option('--out-file', '-o', help='Where to write the CSV. Default is '
                                       'stdout',
              type=click.Path(file_okay=True, dir_okay=False,
                              resolve_path=True))
@pass_state
def export_csv(state, out_file=None):
    """Export grades to an Excel CSV."""

    if out_file is None:
        csvfile = sys.stdout
    else:
        csvfile = open(out_file, 'w')

    try:
        writer = csv.writer(csvfile)
        for grade in state.grades:
            writer.writerow([grade.student_name(), grade.score(),
                             grade.breakdown(state.user_name)])
    finally:
        if out_file is not None:
            csvfile.close()


@export.command('canvas')
@pass_state
def export_canvas(state):
    """Upload grades to Canvas."""

    api = state.canvas_api()
    course_id = state.get_assignment().canvas_course_id
    assignment_id = state.get_assignment().canvas_assignment_id

    if None in (course_id, assignment_id):
        raise click.ClickException('Need to configure canvas in assignment '
                                   'config')

    click.echo('Uploading grades to canvas...')
    with click.progressbar(state.grades) as bar:
        for grade in bar:
            # Submissions not from canvas won't have an id set, so skip them
            if grade.student_id() is not None:
                breakdown = grade.breakdown(state.user_name)
                api.set_submission_grade(course_id, assignment_id,
                                         grade.student_id(), grade.score(),
                                         comment=breakdown)


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


@cli.group('canvas-api')
def canvas_api():
    """Talk to the Canvas API (low-level interface)."""
    pass


@canvas_api.command('courses')
@pass_state
def canvas_api_courses(state):
    """List Canvas courses"""

    api = state.canvas_api()
    for course in api.list_courses():
        click.echo(str(course))


@canvas_api.command('assignments')
@click.argument('course-id')
@pass_state
def canvas_api_assignments(state, course_id):
    """List assignments in a Canvas course"""

    api = state.canvas_api()
    for assign in api.list_assignments(course_id):
        click.echo(str(assign))


@canvas_api.command('sections')
@click.argument('course-id')
@pass_state
def canvas_api_sections(state, course_id):
    """List sections in a Canvas course"""

    api = state.canvas_api()
    for section in api.list_sections(course_id):
        click.echo(str(section))


@canvas_api.command('section-students')
@click.argument('course-id')
@click.argument('section-id')
@pass_state
def canvas_api_section_students(state, course_id, section_id):
    """List students in a Canvas section"""

    api = state.canvas_api()
    for student in api.list_section_students(course_id, section_id):
        click.echo(str(student))


@canvas_api.command('submissions')
@click.argument('course-id')
@click.argument('assignment-id')
@pass_state
def canvas_api_submissions(state, course_id, assignment_id):
    """List submissions for a Canvas assignment"""

    api = state.canvas_api()
    for submission in api.list_submissions(course_id, assignment_id):
        click.echo(str(submission))


@canvas_api.command('download')
@click.argument('course-id')
@click.argument('assignment-id')
@click.argument('user-id')
@click.argument('dest-directory')
@pass_state
def canvas_api_download(state, course_id, assignment_id, user_id,
                        dest_directory):
    """Download a submission"""

    api = state.canvas_api()
    submission = api.get_submission(course_id, assignment_id, user_id)
    submission.download(dest_directory)


@canvas_api.command('grade')
@click.argument('course-id')
@click.argument('assignment-id')
@click.argument('user-id')
@click.argument('grade')
@click.option('--comment', help='Add TEXT as a new grading comment')
@pass_state
def canvas_api_grade(state, course_id, assignment_id, user_id, grade,
                     comment=None):
    """
    Grade a submission.

    Warning: supplying --comment adds a new grade comment; it does not update
    existing comments. Thus, every time you run `zucc canvas grade ...
    --comment hello', you will add a brand new comment "hello." This is because
    the canvas API cannot edit or delete submission comments; it can only add
    them.
    """

    api = state.canvas_api()
    api.set_submission_grade(course_id, assignment_id, user_id, grade, comment)


@cli.command('flatten')
@click.argument('dir-path')
@click.option('--remove-canvas-suffixes/--keep-canvas-suffixes',
              default=True,
              help="Remove canvas resubmission suffixes (-1, -2, -3, etc.). "
                   "Useful if you have filenames that end in -1, -2.")
@pass_state
def flatten_(self, dir_path, remove_canvas_suffixes):
    """
    Flatten archives in a directory.

    Not as good, but behaves similarly to Marie's classic
    SubmissionFix.py script. Give it a directory and it will extract all
    of the archives in the top level, removing a common directory prefix
    from them if it exists. Checks for malicious archives like zipbombs
    and forged archive filenames.
    """
    flatten(dir_path, remove_canvas_suffixes)


if __name__ == "__main__":
    cli()
