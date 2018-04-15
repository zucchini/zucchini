# -*- coding: utf-8 -*-

"""Command-line interface to zucchini."""
import os
import sys
import csv
import shutil
from functools import update_wrapper

import click

from .utils import mkdir_p, CANVAS_URL, CANVAS_TOKEN, \
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, \
    queue, run_thread
from .grading_manager import GradingManager
from .filter import FilterBuilder
from .zucchini import ZucchiniState
from .canvas import CanvasAPIError, CanvasNotFoundError, CanvasInternalError
from .constants import APP_NAME, USER_CONFIG, DEFAULT_SUBMISSION_DIRECTORY, \
                       SUBMISSION_FILES_DIRECTORY
from .submission import Submission
from .flatten import flatten, ArchiveError
from .loaders import CanvasArchiveLoader, GradescopeLoader

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

    # for amazon
    new_conf['aws_access_key_id'] = click.prompt(
        'AWS Access Key ID (press enter to skip AWS configuration)',
        type=AWS_ACCESS_KEY_ID, default='')
    if new_conf['aws_access_key_id']:
        new_conf['aws_secret_access_key'] = click.prompt(
            'Amazon Secret Access Key', type=AWS_SECRET_ACCESS_KEY)
        new_conf['aws_s3_bucket_name'] = click.prompt(
            'Amazon S3 Bucket Name', type=AWS_BUCKET_NAME)
    else:
        click.echo('Skipping canvas configuration...')
        new_conf['aws_secret_access_key'] = ''
        new_conf['aws_s3_bucket_name'] = ''

    with click.open_file(config_path, 'w') as cfg_file:
        ZucchiniState.save_config(cfg_file, new_conf)


def filter_options(canvas):
    """
    Decorator which adds common filtering options to a subcommand. If
    canvas=True, use only options supported by the Canvas API.
    """
    filter_options = {
        'student': click.option('-s', '--student', metavar='NAME',
                                multiple=True, help='Filter by student name'),
        'not_student': click.option('-S', '--not-student', metavar='NAME',
                                    multiple=True,
                                    help='Exclude student by name'),
        'broken': click.option('-b/-B', '--broken/--not-broken', default=None,
                               help='Filter for broken submissions'),
    }
    filter_add_methods = {'student': FilterBuilder.add_student_name,
                          'not_student': FilterBuilder.add_not_student_name,
                          'broken': FilterBuilder.add_broken}
    if canvas:
        filters = ('student', 'not_student')
    else:
        filters = ('student', 'not_student', 'broken')

    def decorator(func):
        def replacement(*args, **kwargs):
            filter_builder = FilterBuilder.new_canvas() \
                             if canvas else FilterBuilder.new_meta()
            for filter_ in filters:
                terms = kwargs.pop(filter_)
                add_method = filter_add_methods[filter_]
                if terms is not None:
                    if isinstance(terms, (list, tuple)):
                        for term in terms:
                            add_method(filter_builder, term)
                    else:
                        add_method(filter_builder, terms)

            kwargs['filter'] = filter_builder
            func(*args, **kwargs)

        for filter_ in reversed(filters):
            replacement = filter_options[filter_](replacement)

        # Without update_wrapper() here, click gets confused and puts
        # a replacement subcommand in the help output
        return update_wrapper(replacement, func)

    return decorator


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
def setup(state):
    """Runs setup again"""
    click.echo("running setup again")
    click.echo("Name: %s" % state.user_name)
    click.echo("Email: %s" % state.user_email)
    click.echo("Canvas URL: %s" % state.canvas_url)
    click.echo("Token: %s" % state.canvas_token)
    click.echo("AWS Access Key ID: %s" % state.aws_access_key_id)
    click.echo("AWS Secret Access Key: %s" % state.aws_secret_access_key)
    click.echo("S3 Bucket name: %s" % state.aws_s3_bucket_name)
    setup_handler()
    click.echo("setup has finished")


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
    """Load submissions from Sakai"""
    raise NotImplementedError


@load.command('gradescope')
@click.argument('export-zipfile',
                type=click.Path(file_okay=True, dir_okay=True, readable=True,
                                resolve_path=True))
@pass_state
def load_gradescope(state, export_zipfile):
    """Load submissions from Gradescope"""
    with GradescopeLoader(export_zipfile) as loader:
        with click.progressbar(list(loader.submissions.items())) as bar:
            for submission_id, student_name in bar:
                base_dir = os.path.join(state.submission_dir, student_name)
                # Remove submission if it already exists
                shutil.rmtree(base_dir, ignore_errors=True)

                files_dir = os.path.join(base_dir, SUBMISSION_FILES_DIRECTORY)
                mkdir_p(files_dir)

                loader.extract_files(submission_id, files_dir)

                # Create initial meta.json in submission dir
                submission = Submission(
                    student_name, state.get_assignment(), base_dir,
                    graded=False, id=submission_id)
                submission.initialize_metadata()


def choose_section(sections, section=None):
    """
    Prompt and return a CanvasSection object or None
    """

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

    return section_chosen


def canvas_setup(state, section):
    """
    Check configuration for the Canvas API.

    Return a tuple of (CanvasAPI instance, course id, assignment id,
    CanvasSection instance or None).
    """

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

    section_chosen = choose_section(sections, section)
    assignment_id = state.get_assignment().canvas_assignment_id

    return (api, course_id, assignment_id, section_chosen)


@load.command('canvas')
@click.option('--section', '-e', type=lambda s: s.lower(), metavar='SECTION',
              help='section id, substring of section name, or "all"')
@click.option('--max-archive-size', type=int, metavar='BYTES',
              help='maximum size of archive to extract')
@filter_options(canvas=True)
@pass_state
def load_canvas(state, section, max_archive_size, filter):
    """Load submissions from Canvas"""

    api, course_id, assignment_id, section_chosen = \
        canvas_setup(state, section)

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
            if not filter(canvas_submission):
                continue

            student_name = canvas_submission.user.sortable_name
            base_dir = os.path.join(state.submission_dir, student_name)
            # Remove submission if it already exists
            shutil.rmtree(base_dir, ignore_errors=True)

            files_dir = os.path.join(base_dir, SUBMISSION_FILES_DIRECTORY)
            mkdir_p(files_dir)

            if canvas_submission.no_submission():
                error = 'No submission!'
            else:
                error = None
                canvas_submission.download(files_dir)
                try:
                    flatten(files_dir, max_archive_size=max_archive_size)
                except ArchiveError as err:
                    error = str(err)

            # Create initial meta.json in submission dir
            submission = Submission(
                student_name, state.get_assignment(), base_dir, graded=False,
                id=canvas_submission.user_id,
                seconds_late=canvas_submission.seconds_late,
                error=error)
            submission.initialize_metadata()


@load.command('canvas-archive')
@click.argument('bulk-zipfile',
                type=click.Path(file_okay=True, dir_okay=True, readable=True,
                                resolve_path=True))
@click.option('--section', '-e', type=lambda s: s.lower(), metavar='SECTION',
              help='section id, substring of section name, or "all"')
@click.option('--max-archive-size', type=int, metavar='BYTES',
              help='maximum size of archive to extract')
@filter_options(canvas=True)
@pass_state
def load_canvas_archive(state, bulk_zipfile, section, max_archive_size,
                        filter):
    """
    Load submissions from Canvas bulk download
    """

    api, course_id, assignment_id, section_chosen = \
        canvas_setup(state, section)

    # TODO: Implement extraction for all students
    if section_chosen is None:
        raise click.ClickException('Please specify a section to extract. '
                                   'Extracting all is not implemented yet')
    else:
        students = list(
            api.list_section_students(course_id, section_chosen.id))

    click.echo('Extracting bulk Canvas submissions...')

    with CanvasArchiveLoader(bulk_zipfile) as loader:
        with click.progressbar(students) as bar:
            for student in bar:
                base_dir = os.path.join(state.submission_dir,
                                        student.sortable_name)
                # Remove submission if it already exists
                shutil.rmtree(base_dir, ignore_errors=True)

                files_dir = os.path.join(base_dir, SUBMISSION_FILES_DIRECTORY)
                mkdir_p(files_dir)

                if not loader.has_submission(student.id):
                    error = 'No submission!'
                else:
                    error = None
                    loader.extract_files(student.id, files_dir)
                    try:
                        flatten(files_dir, max_archive_size=max_archive_size)
                    except ArchiveError as err:
                        error = str(err)

                # Create initial meta.json in submission dir
                submission = Submission(
                    student.sortable_name, state.get_assignment(), base_dir,
                    graded=False, id=student.id, error=error)
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
            # If the assignment is ungradable, show a 0 instead of
            # "(ungraded)"
            grade.score() if not grade.gradable() or grade.graded()
            else '(ungraded)',
            grade.breakdown(grader_name)
            if not grade.gradable() or grade.graded() else '',
            max_name_len=max_name_len)
        for grade in grades)
    click.echo_via_pager('grade report:\n\n' + grade_report)


@cli.command()
@click.option('-f', '--from-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory to read submissions from.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@filter_options(canvas=False)
@pass_state
def grade(state, from_dir, filter):
    """Grade submissions."""
    # At this point, the assignment object is loaded. We need a GradingManager
    grading_manager = GradingManager(state.get_assignment(), from_dir, filter)

    if not grading_manager.submission_count():
        raise click.ClickException('no submissions match the filter given!')

    click.echo('Grading submissions...')

    if grading_manager.has_interactive():
        if grading_manager.has_noninteractive():
            # Since we have both interactive an non-interactive
            # components, we want to let the user grade the interactive
            # components while the non-interactive components are
            # running.
            grade_queue = queue.Queue()
            thread = run_thread(grading_manager.grade, (False,), grade_queue)

            click.echo('First, grading interactive components...')
            grades = list(grading_manager.grade(interactive=True))
            click.echo('Finishing off grading noninteractive components...')

            with click.progressbar(length=grading_manager.submission_count()) \
                    as bar:
                for i in bar:
                    noninter_grade = grade_queue.get()
                    if isinstance(noninter_grade, Exception):
                        raise noninter_grade
                    grades[i].update(noninter_grade)

            # Should have exited by now, but just in case
            thread.join()
        else:
            # If all the components are interactive, just grade them
            # here in the main thread
            grades = list(grading_manager.grade())
    else:
        # If all components are noninteractive, just do the progress bar
        # in the main thread here.
        with click.progressbar(grading_manager.grade(),
                               grading_manager.submission_count()) as bar:
            grades = list(bar)

    # Need to do this now to handle non-interactive and interactive
    # running in parallel earlier
    for grade in grades:
        grade.write_grade()
        grade.generate_gradelog()
    print_grades(grades, state.user_name)


@cli.command('show-grades')
@click.option('-f', '--from-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory to read submissions from.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@filter_options(canvas=False)
@pass_state
def show_grades(state, from_dir, filter):
    """Print the grade for all submissions."""
    grading_manager = GradingManager(state.get_assignment(), from_dir, filter)

    if not grading_manager.submission_count():
        raise click.ClickException('no submissions match the filter given!')

    print_grades(grading_manager.grades(), state.user_name)


@cli.group()
@click.option('-f', '--from-dir', default=DEFAULT_SUBMISSION_DIRECTORY,
              help="Path of the directory to read submissions from.",
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              writable=True, readable=True,
                              resolve_path=True))
@filter_options(canvas=False)
@pass_state
def export(state, from_dir, filter):
    """Export grades for uploading."""

    grading_manager = GradingManager(state.get_assignment(), from_dir, filter)

    if not grading_manager.submission_count():
        raise click.ClickException('no submissions match the filter given!')

    state.grades = [grade for grade in grading_manager.grades()
                    if grade.grade_ready()]


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


@export.command('canvas-grades')
@pass_state
def export_canvas_grades(state):
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
                api.set_submission_grade(course_id, assignment_id,
                                         grade.student_id(), grade.score())


@export.command('canvas-comments')
@click.option('--gradelog-upload', '-g', help='Where to upload Gradelog file',
              type=click.Choice(['none', 'canvas', 's3']))
@pass_state
def export_canvas_comments(state, gradelog_upload):
    """Add Canvas submission comments with gradelog and breakdown"""
    if gradelog_upload is None:
        click.echo('gradelog_upload flag is mandatory')
        return

    click.echo('Gradelog upload type: ' + gradelog_upload)

    api = state.canvas_api()
    course_id = state.get_assignment().canvas_course_id
    assignment_id = state.get_assignment().canvas_assignment_id

    if None in (course_id, assignment_id):
        raise click.ClickException('Need to configure canvas in assignment '
                                   'config')

    click.echo('Uploading submission comments to canvas...')
    with click.progressbar(state.grades) as bar:
        for grade in bar:
            # Submissions not from canvas won't have an id set, so skip them
            if grade.student_id() is not None:
                breakdown = grade.breakdown(state.user_name)
                gradelog_hash = grade.get_gradelog_hash()
                gradelog_path = grade.get_gradelog_path()
                student_id = grade.student_id()

                if gradelog_upload == 'none':
                    api.add_submission_comment(
                        course_id, assignment_id, student_id,
                        breakdown,
                        None
                    )
                elif gradelog_upload == 'canvas':
                    api.add_submission_comment(
                        course_id, assignment_id, student_id,
                        breakdown + '\n\n' + gradelog_hash,
                        [(gradelog_path, 'text/plain')]
                    )
                elif gradelog_upload == 's3':
                    file_url = state.get_amazon_api().upload_file_s3(
                        gradelog_path, 'text/plain'
                    )
                    api.add_submission_comment(
                        course_id, assignment_id, student_id,
                        breakdown + "\n\n" + gradelog_hash + '\n\n' + file_url,
                        None
                    )


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
@click.option('--max-archive-size', type=int, metavar='BYTES',
              help='maximum size of archive to extract')
@pass_state
def flatten_(self, dir_path, max_archive_size):
    """
    Flatten archives in a directory.

    Not as good, but behaves similarly to Marie's classic
    SubmissionFix.py script. Give it a directory and it will extract all
    of the archives in the top level, removing a common directory prefix
    from them if it exists. Checks for malicious archives like zipbombs
    and forged archive filenames.
    """
    flatten(dir_path, max_archive_size=max_archive_size)


if __name__ == "__main__":
    cli()
