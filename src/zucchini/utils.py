import dataclasses
import itertools
from pathlib import Path
import shlex
from typing import Annotated, TypeAlias
import os
import shutil
import subprocess

from pydantic import BaseModel, BeforeValidator, ConfigDict

from .exceptions import BrokenSubmissionError

@dataclasses.dataclass(init=False, slots=True)
class RunCommandResult:
    """
    A wrapper around `subprocess.CompletedProcess` to better support the needs of Zucchini graders.
    """

    returncode: int
    """The command's return code."""

    stdout: str
    """STDOUT, as a print-safe string"""

    stderr: str | None
    """
    STDERR, as a print-safe string (if it exists).
    STDERR will only exist if stderr was set to `subprocess.PIPE`.
    """

    def __init__(self, p: subprocess.CompletedProcess[bytes]):
        self.returncode = p.returncode
        self.stdout = p.stdout.decode(errors="backslashreplace")
        self.stderr = p.stderr.decode(errors="backslashreplace") if p.stderr is not None else None

    def check_returncode(self, acceptable_error_codes: set[int] = { 0 }):
        """
        Checks the return code, raising `BrokenSubmissionError` if not an acceptable error code.

        Parameters
        ----------
        acceptable_error_codes : set[int], optional
            The acceptable error codes (by default, { 0 })

        Raises
        ------
        BrokenSubmissionError
            When return code is not in the `acceptable_error_codes` set.
        """
        if self.returncode not in acceptable_error_codes:
            if self.stderr is None:
                verbose = self.stdout
            else:
                verbose = "\n".join([self.stdout, self.stderr])

            raise BrokenSubmissionError(
                f"grader command exited with exit code {self.returncode}.",
                verbose=verbose
            )

def run_command(
        cmd, *,
        cwd: Path | None = None,
        timeout: float | None = None,
        stderr = None,
        input = None,
    ):
    """
    Synchronously runs the command with `subprocess.run` and processes the output for grader use.

    Parameters
    ----------
    cmd
        The command, in `shlex.split` format
    cwd : Path
        The path of the current directory (cwd)
    timeout : float, optional
        The timeout before the command is canceled, by default None
    stderr
        Place to write STDERR. By default, it is piped into the STDOUT
        (which is itself piped as the output of this function).
    input
        Input to pass to the command (as STDIN).
    Returns
    -------
    RunCommandResult
        A result type which provides the result of the command execution.

    Raises
    ------
    BrokenSubmissionError
        If a timeout occurs.
    """
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=stderr or subprocess.STDOUT,
            timeout=timeout,
            input=input
        )
    except subprocess.TimeoutExpired:
        raise BrokenSubmissionError(f"grader timed out after {timeout} seconds")
    
    return RunCommandResult(p)

def _as_shlex_cmd(s: str | list[str]) -> list[str]:
    if isinstance(s, list):
        return s
    return shlex.split(s)
ShlexCommand: TypeAlias = Annotated[list[str], BeforeValidator(_as_shlex_cmd)]
"""
Pydantic validator which accepts strings (and lists of strings) which act as script commands,
and exposes the field as a split script command (as if from `shlex.split`).
"""

def sanitize_path(path: os.PathLike[str] | str) -> Path:
    """
    Convert an untrusted path to a relative path.
    """

    # Remove intermediate ..s
    normpath = Path(os.path.normpath(path))
    if normpath.is_absolute():
        # Remove absolute paths
        return Path(*normpath.parts[1:])
    else:
        # Remove leading ..s in relative paths
        parts = itertools.dropwhile(lambda p: p == os.path.pardir, normpath.parts)
        return Path(*parts)

def _copy_no_symlinks(src: os.PathLike[str] | str, dst: os.PathLike[str] | str):
    """
    Copies the source file to the destination (like `shutil.copy2`),
    but errors if source is a symlink.
    """
    if Path(src).is_symlink():
        raise ValueError(f"Cannot copy: {src} is a symlink")
    
    return shutil.copy2(src, dst)
def copy_globs(globs: list[str], src_dir: os.PathLike[str], dest_dir: os.PathLike[str]):
    """
    Copy files matched by `globs` (a list of glob strings) from src_dir
    to dest_dir, maintaining directories if possible.
    """

    src_dir = Path(src_dir)
    dest_dir = Path(dest_dir)
    files_to_copy: list[Path] = []

    # Do a first pass to check for missing files. This way, we don't
    # copy a bunch of files only to blow up when we can't find a
    # later file.
    for file_glob in globs:
        old_len = len(files_to_copy)
        files_to_copy += src_dir.glob(file_glob)

        if len(files_to_copy) - old_len == 0: # No new files were added
            raise FileNotFoundError(f"missing file {file_glob!r}")

    for src_file in files_to_copy:
        rel_path = src_file.relative_to(src_dir)
        dest = dest_dir / rel_path

        if src_file.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_file, dest, copy_function=_copy_no_symlinks, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            _copy_no_symlinks(src_file, dest)

class KebabModel(BaseModel):
    """
    A `pydantic.BaseModel`, 
    which converts snake case fields to kebab case (`_` => `-`) in serialization.
    """
    model_config = ConfigDict(alias_generator=lambda field: field.replace("_", "-"))
