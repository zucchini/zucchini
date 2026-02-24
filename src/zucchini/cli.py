from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Annotated, Literal, TextIO
from cyclopts import App, Parameter
import tomli

from zucchini.exporters import EXPORTERS, ExporterKey

from .assignment import Assignment, AssignmentConfig, AssignmentMetadata
from .grades import AssignmentGrade
from .gradescope import GradescopeMetadata

from .submission import Submission

app = App(
    help="A fun autograder management system for the whole family.",
    help_format="md",
    help_formatter="plain",
    help_on_error=True,
)

ASSIGNMENT_FILES_DIR = "grading-files"
ASSIGNMENT_CONFIG_TOML = "zucchini.toml"
ASSIGNMENT_CONFIG_JSON = "zucchini.json"

def _get_assignment_cfg(grading_dir: Path) -> AssignmentConfig:
    # Try reading from TOML
    try:
        with open(grading_dir / ASSIGNMENT_CONFIG_TOML, "rb") as f:
            data = tomli.load(f) 
            return AssignmentConfig.model_validate(data)
    except FileNotFoundError:
        pass

    # Try reading from JSON
    try:
        with open(grading_dir / ASSIGNMENT_CONFIG_JSON, "rb") as f:
            return AssignmentConfig.model_validate_json(f.read())
    except FileNotFoundError:
        pass

    raise FileNotFoundError(f"Missing configuration file {ASSIGNMENT_CONFIG_TOML} in {grading_dir}")
def _get_assignment(submission_dir: Path, grading_dir: Path, gs_metadata_fp: Path) -> tuple[Assignment, Submission]:
    # Get metadata:
    submission_created_at = None
    metadata = AssignmentMetadata()

    # Load metadata from Gradescope submission_metadata.json file:
    try:
        with open(gs_metadata_fp, "rb") as f:
            gs_metadata = GradescopeMetadata.model_validate_json(f.read())
            
            metadata = gs_metadata.as_metadata()
            submission_created_at = gs_metadata.created_at
    except FileNotFoundError:
        pass

    # Get config:
    config = _get_assignment_cfg(grading_dir)
    return (
        Assignment(config, grading_dir / ASSIGNMENT_FILES_DIR, metadata),
        Submission(submission_dir, submission_created_at)
    )

@contextmanager
def _io_manage(path: Path | None, fallback: TextIO, rw: Literal["r", "w"]):
    resource = open(path, rw) if path is not None else fallback
    try:
        yield resource
    finally:
        if resource is not fallback:
            resource.close()

@app.command
def grade(
    submission_path: Path = Path("/autograder/submission"),
    metadata_path: Path = Path("/autograder/submission_metadata.json"),
    *,
    autograder_path: Path = Path("."),
    output_: Annotated[Path | None, Parameter(alias="-o")] = None,
):
    """
    Grades a submission, located at the specified submission path.

    Parameters
    ----------
    submission_path : Path, optional
        The path of the submission files.
    
    metadata_path : Path, optional
        The path of the submission metadata.

        This is produced by Gradescope and is typically called "submission_metadata.json".

    autograder_path : Path, optional
        The path the autograder is located.

        This path should contain a Zucchini configuration file (zucchini.toml)
        and a "grading-files/" folder which contains the autograder test cases.
    
    output : Path, optional
        The output path to use. If unspecified, this defaults to sys.stdout.
    """
    assignment, submission = _get_assignment(submission_path, autograder_path, metadata_path)
    grade = assignment.grade(submission)
    with _io_manage(output_, sys.stdout, "w") as out:
        print(grade.model_dump_json(), file=out)

@app.command()
def export(
    format_: ExporterKey,
    *,
    input_: Annotated[Path | None, Parameter(alias="-i")] = None,
    output_: Annotated[Path | None, Parameter(alias="-o")] = None
):
    """
    Converts a Zucchini component grades result (which would be obtained from "zucc grade")
    and converts it to some supported export format.
    
    Parameters
    ----------
    format_ : ExporterKey
        The format to use.

        - The "local" format is useful for terminals, displaying results in a printable format.
        - The "gradescope" format is useful for Gradescope, displaying results in the JSON format Gradescope requires.

    input_ : Path, optional
        The input path to use. If unspecified, this defaults to sys.stdin.

    output_ : Path, optional
        The output path to use. If unspecified, this defaults to sys.stdout.
    """
    with _io_manage(input_, sys.stdin, "r") as inp:
        grade = AssignmentGrade.model_validate_json(inp.read())

    Exporter = EXPORTERS.get(format_)
    if Exporter is None:
        raise ValueError(f"Invalid format {format_!r}")
    exporter = Exporter()
    
    with _io_manage(output_, sys.stdout, "w") as out:
        exporter.export(grade, out)
        print(file=out)

if __name__ == "__main__":
    app()