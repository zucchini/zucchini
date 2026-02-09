import dataclasses
import datetime
from pathlib import Path

@dataclasses.dataclass
class Submission:
    submission_dir: Path
    submit_date: datetime.datetime | None
