#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `zucchini` package."""

from fractions import Fraction
from io import StringIO
import os
from textwrap import dedent
from zucchini import cli
from zucchini.grades import AssignmentGrade

def test_grade_basic(tmp_path, capsys):
    with open(tmp_path / "zucchini.toml", "w") as f:
        f.write(dedent("""\
        name = "Project 12"
        
        [[components]]
        name = "Main Component"
        weight = 100
        backend = { kind = "MultiCommandGrader" }
        parts = [
            { summary = "Passes", command = "true", weight = 1 }
        ]
        """))
    
    os.chdir(tmp_path)
    cli.app(["grade"], result_action="return_value")
    
    # Check STDOUT is round-trippable as Grade:
    stdout = capsys.readouterr().out
    print(AssignmentGrade.model_validate_json(stdout))

def test_export_basic(monkeypatch):
    grade = AssignmentGrade(
        name="Project 13",
        raw_score=Fraction(1),
        final_score=Fraction(1),
        max_points=Fraction(100),
        components=[],
        penalties=[]
    )

    monkeypatch.setattr("sys.stdin", StringIO(grade.model_dump_json()))
    cli.app(["export", "--format", "local"], result_action="return_value")
