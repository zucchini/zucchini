import os
import sys
import csv
import shutil
import time
import boto3

from zucchini.utils import mkdir_p, CANVAS_URL, CANVAS_TOKEN
from zucchini.grading_manager import GradingManager
from zucchini.zucchini import ZucchiniState
from zucchini.canvas import CanvasAPIError, CanvasNotFoundError, CanvasInternalError
from zucchini.constants import APP_NAME, USER_CONFIG, DEFAULT_SUBMISSION_DIRECTORY, \
                       SUBMISSION_FILES_DIRECTORY, SUBMISSION_GRADELOG_FILE
from zucchini.submission import Submission
from zucchini.flatten import flatten
from zucchini.cli import print_grades
from zucchini.amazon import AmazonAPI

# setup zucchini to connect to test instance
state = ZucchiniState("Patrick Tam", "pjztam@gatech.edu", "zucc_config_test", "",
                      "https://canvas.zucchini.services", "50bdCFTkWqZeh3Kn6Zaqu1wCnB59AwuhrylEzjjzIiaEirzZyL3hdKkbIZrpiAzB")
state.submission_dir = DEFAULT_SUBMISSION_DIRECTORY



# called this once to add my first farm REMOVE
# state.farm_manager.add_farm("https://github.gatech.edu/CS2110/zucchini-spring2018.git", "spring2018")

# state.farm_manager.update_all_farms()
farms = state.farm_manager.list_farms()
print(farms)
#
assignments = state.farm_manager.list_farm_assignments()
print(assignments)

# called this once to get far assignment REMOVE
# state.farm_manager.clone_farm_assignment("spring2018/hw1", "")

#load canvas
os.chdir('./hw1')
course_id = state.get_assignment().canvas_course_id
print(course_id)

api = state.canvas_api()
api2 = AmazonAPI('AKIAJOSMYTNSTQEDITWA', 'Sf71mQS/WA0tnwW1iOE48mcVFPE61RfI6FewWYan', 'cs2110-zucchini-gradelogs')

sections = tuple(api.list_sections(course_id))
assignment_id = state.get_assignment().canvas_assignment_id
submissions = api.list_submissions(course_id, assignment_id)

# grab submissions REMOVE TO REUSE
# for canvas_submission in list(submissions):
#     student_name = canvas_submission.user.sortable_name
#     base_dir = os.path.join(state.submission_dir, student_name)
#     # Remove submission if it already exists
#     shutil.rmtree(base_dir, ignore_errors=True)
#
#     files_dir = os.path.join(base_dir, SUBMISSION_FILES_DIRECTORY)
#     mkdir_p(files_dir)
#     canvas_submission.download(files_dir)
#     flatten(files_dir)
#
#     # Create initial meta.json in submission dir
#     submission = Submission(
#         student_name, state.get_assignment(), base_dir, graded=False,
#         id=canvas_submission.user_id,
#         seconds_late=canvas_submission.seconds_late)
#     submission.initialize_metadata()
#     print(".", end="")
# print("")

start_time = time.time()
grading_manager = GradingManager(state.get_assignment(), DEFAULT_SUBMISSION_DIRECTORY)
grades = grading_manager.grade()

# grades2 = state.grades
grades = sorted(grades, key=lambda grade: grade.student_name())
for grade in grades:
    # gradelog_path = os.path.join(grade._submission.path, SUBMISSION_GRADELOG_FILE)
    # api.add_submission_comment(course_id, assignment_id, grade._submission.id, "stuff", [(gradelog_path, 'text/plain')])
    grade.write_grade()
    grade.generate_gradelog()
    if grade.student_id() is not None:
        # api.set_submission_grade(course_id, assignment_id,
        #                          grade.student_id(), grade.score())
        breakdown = grade.breakdown(state.user_name)

        # for non working canvas uploads
        file_url = api2.upload_file_s3(grade.get_gradelog_path(), 'text/plain')
        api.add_submission_comment(
            course_id, assignment_id, grade.student_id(),
            breakdown + '\n' + file_url + '\n', None)

        # for working canvas uploads
        # api.add_submission_comment(
        #     course_id, assignment_id, grade.student_id(),
        #     breakdown, [(grade.get_gradelog_path(), 'text/plain')])


print_grades(grades, state.user_name)


print("x")
elapsed_time = time.time() - start_time
print("%.20f" % elapsed_time)
