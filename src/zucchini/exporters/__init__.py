from typing import Literal
from typing_extensions import override

from zucchini.grades import AssignmentGrade
from zucchini.gradescope_output_model import GradescopeOutput

from .exporter_interface import ExporterInterface, _export_str

class LocalExporter(ExporterInterface):
    @override
    @_export_str
    def export(self, grade: AssignmentGrade) -> str:
        output_arr = []
        any_errors = False
        for component in grade.components:
            if component.error:
                any_errors = True
                output_arr.append(f"ERROR: {str(component.description):45} {component.error.message:15}")
                if component.error.verbose:
                    output_arr.append(f"Details: {component.error.verbose:45}")
            else:
                for part in (component.parts or []):
                    points_got = part.points_received() * component.norm_weight * grade.max_points
                    points_max = part.norm_weight * component.norm_weight * grade.max_points
                    points = f'{float(points_got):.2f}/{float(points_max):.2f}'
                    if part.passed():
                        output_arr.append(f"TEST: {part.description:45} {'PASSED':15} ({points})")
                    else:
                        output_arr.append(f"TEST: {part.description:45} {'FAILED':15} ({points})")
                        output_arr.append(part.inner.log)
        score = f'Total score: {float(100 * grade.final_score):.2f}%'
        output_arr.append(score)
        if any_errors:
            output_arr.append('Some errors occurred; the score above may not be'
                          ' your final grade')
        
        return "\n\n".join(output_arr)

class GradescopeExporter(ExporterInterface):
    @override
    @_export_str
    def export(self, grade: AssignmentGrade) -> str:
        return GradescopeOutput.from_grade(grade).model_dump_json()
        
ExporterKey = Literal["local", "gradescope"]
EXPORTERS: dict[ExporterKey, type[ExporterInterface]] = {
    "local": LocalExporter,
    "gradescope": GradescopeExporter
}