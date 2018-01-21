"""Interface with the Canvas through its REST API"""

import os
import re
import requests
import shutil
from collections import namedtuple

from .utils import datetime_from_string

# json.load() started throwing JSONDecodeError instead of ValueError
# back in Python 3.5, so catch ValueError instead for earlier versions
try:
    from json import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class CanvasAPIError(Exception):
    """Raised for bad responses to API requests"""
    pass


class CanvasNotFoundError(CanvasAPIError):
    """Raised when a request 404s"""
    pass


class CanvasInternalError(CanvasAPIError):
    """Raised when a response is a 5xx"""
    pass


class CanvasMalformedResponseError(CanvasAPIError):
    """Raised when a response contains invalid JSON"""
    pass


class CanvasCourse(namedtuple('CanvasCourse', ('api_', 'id', 'name'))):
    """Hold Course info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)

    @property
    def assignments(self):
        return self.api_.list_assignments(self.course_id)

    @property
    def sections(self):
        return self.api_.list_sections(self.course_id)


class CanvasAssignment(namedtuple('CanvasAssignment',
                       ('api_', 'id', 'name', 'course_id'))):
    """Hold assignment info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)

    @property
    def course(self):
        return self.api_.get_course(self.course_id)


class CanvasSection(namedtuple('CanvasSection',
                    ('api_', 'id', 'name', 'course_id'))):
    """Hold section info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)

    @property
    def course(self):
        return self.api_.get_course(self.course_id)


class CanvasUser(namedtuple('CanvasUser',
                 ('api_', 'id', 'name', 'sortable_name'))):
    """Hold user info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)


class CanvasSubmissionAttachment(namedtuple('CanvasSubmission',
                                 ('api_', 'id', 'filename', 'url'))):
    """Hold information about a submitted file"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}\t{}' \
               .format(self.id, self.filename, self.url)

    def download(self, directory):
        """
        Download this attachment with the name provided by the student
        to the directory provided.
        """
        # Canvas sanitizes the input filename, it seems
        path = os.path.join(directory, self.filename)
        self.api_._download_file(self.url, path)


class CanvasSubmission(namedtuple('CanvasSubmission',
                       ('api_', 'id', 'late', 'user_id', 'user', 'attachments',
                        'seconds_late', 'attempt'))):
    """Hold assignment info"""
    __slots__ = ()
    _defaults = {'attachments': []}
    _sub_entities = {'user': CanvasUser}
    _sub_entity_lists = {'attachments': CanvasSubmissionAttachment}

    def __str__(self):
        attachments = ', '.join(attachment.filename
                                for attachment in self.attachments)
        return 'id={}\t{}late\t{}\t{}' \
               .format(self.id, '' if self.late else 'not ', self.user,
                       attachments)

    def no_submission(self):
        """Return True iff the student did not submit."""
        return self.attempt is None

    def time(self):
        """Return the submission time as a naive datetime object."""
        if self.submitted_at is None:
            return self.submitted_at
        else:
            return datetime_from_string(self.submitted_at)

    def download(self, directory):
        """
        Download all the attachments for this submission to the given
        directory.
        """
        for attachment in self.attachments:
            attachment.download(directory)


class CanvasAPI(object):
    """
    Represent a connection to the Canvas REST API.

    Currently does not support OAuth2 because Canvas OAuth2 would be a
    mess with Zucchini. We'd have to register it as a "Developer Key"
    with OIT and then pass around a `client_id' and `client_secret'.
    Much easier to be a little shady with the terms of service and get
    'er done.
    """

    LINK_REGEX = re.compile(r'<(?P<link>.+?)>; rel="(?P<rel>.+?)"(,|$)')

    def __init__(self, url, token):
        self.url = url.rstrip('/')
        self.token = token

    def _parse_links(self, link_header):
        """
        Convert the contents of a link header into a dictionary of
        rel->link. See
        https://canvas.instructure.com/doc/api/file.pagination.html for
        more information.
        """

        return {match.group('rel'): match.group('link')
                for match in self.LINK_REGEX.finditer(link_header)}

    def _to_entity(self, entity_json, entity_class):
        """Convert a JSON object to an instance of the provided entity class"""

        if hasattr(entity_class, '_defaults'):
            defaults = entity_class._defaults
        else:
            defaults = {}

        args = {}
        for field in entity_class._fields:
            # Ignore the special api_ field used to give the instance a
            # back-reference to this class
            if field == 'api_':
                continue

            if field in entity_json:
                args[field] = entity_json[field]
            elif field in defaults:
                args[field] = defaults[field]
            else:
                raise CanvasMalformedResponseError(
                    'response is missing required field {}'.format(field))

        if hasattr(entity_class, '_sub_entities'):
            for field, class_ in entity_class._sub_entities.items():
                args[field] = self._to_entity(args[field], class_)

        if hasattr(entity_class, '_sub_entity_lists'):
            for field, class_ in entity_class._sub_entity_lists.items():
                args[field] = [self._to_entity(entity, class_)
                               for entity in args[field]]

        return entity_class(api_=self, **args)

    def _url(self, name):
        """Return the URL of an endpoint named `name'"""
        return '{}/api/v1/{}'.format(self.url, name)

    def _headers(self):
        """Return authentication headers"""
        return {'authorization': 'Bearer {}'.format(self.token)}

    def _request(self, url, method='get', json=None, stream=False):
        """
        Attempt to request the URL url, raising exceptions in error
        conditions
        """
        resp = requests.request(method, url, headers=self._headers(),
                                json=json, stream=stream)

        if resp.status_code == 404:
            raise CanvasNotFoundError()
        elif resp.status_code >= 500 and resp.status_code < 600:
            raise CanvasInternalError()
        elif resp.status_code != 200:
            raise CanvasAPIError('unexpected response code {}'
                                 .format(resp.status_code))
        return resp

    def _put(self, name, json):
        self._request(self._url(name), method='put', json=json)

    def _get_json(self, name):
        """
        Make a request to a Canvas API endpoint and return the JSON.
        """
        try:
            return self._request(self._url(name)).json()
        except JSONDecodeError as err:
            raise CanvasMalformedResponseError(err)

    def _get(self, name, entity_class):
        """
        Make a request to a Canvas API endpoint and convert the JSON
        entity in the response to an instance of `entity_class'.
        """

        return self._to_entity(self._get_json(name), entity_class)

    def _gets(self, name, entity_class):
        """
        Make a request to a Canvas API endpoint, de-paginate the
        response, and convert each JSON entity to an instance of
        `entity_class'.
        """

        link = self._url(name)

        while link:
            resp = self._request(link)

            if 'link' in resp.headers:
                link = self._parse_links(resp.headers['link']) \
                           .get('next', None)
            else:
                link = None

            try:
                json = resp.json()
            except JSONDecodeError as err:
                raise CanvasMalformedResponseError(err)

            for entity_json in json:
                yield self._to_entity(entity_json, entity_class)

    def _download_file(self, url, path):
        """Download the file at `url' to `path'."""

        with self._request(url, stream=True) as response, \
                open(path, 'wb') as downloaded_file:
            shutil.copyfileobj(response.raw, downloaded_file)

    def list_courses(self):
        """
        Return an iterator of CanvasCourse instances of all the active
        courses this user can see.
        """

        return self._gets('courses', CanvasCourse)

    def get_course(self, course_id):
        """
        Return a CanvasCourse instance corresponding to the given
        course id.
        """

        return self._get('courses/{}'.format(course_id), CanvasCourse)

    def get_user(self, course_id):
        """
        Return a CanvasCourse instance corresponding to the given
        course id.
        """

        return self._get('users/{}'.format(course_id), CanvasUser)

    def list_assignments(self, course_id):
        """
        Return an iterator of instances of all the assignments in the
        given course.
        """

        return self._gets('courses/{}/assignments'.format(course_id),
                          CanvasAssignment)

    def list_sections(self, course_id):
        """
        Return an iterator of instances of all the sections in the
        given course.
        """

        return self._gets('courses/{}/sections'.format(course_id),
                          CanvasSection)

    def list_section_students(self, course_id, section_id):
        """
        Return an iterator of instances of all the sections in the
        given course.
        """

        # XXX sections/{}?include=students crashes Canvas, so avoid for now
        section = self._get_json('courses/{}/sections/{}?include=students'
                                 .format(course_id, section_id))

        for student_json in section['students']:
            yield self._to_entity(student_json, CanvasUser)

    def list_submissions(self, course_id, assignment_id):
        """
        Return an iterator of instances of all the submissions in the
        given course for the given assignment.
        """

        return self._gets('courses/{}/assignments/{}/submissions?include=user'
                          .format(course_id, assignment_id), CanvasSubmission)

    def list_section_submissions(self, section_id, assignment_id):
        """
        Return an iterator of instances of all the submissions in the
        given section for the given assignment.
        """

        return self._gets('sections/{}/assignments/{}/submissions?include=user'
                          .format(section_id, assignment_id), CanvasSubmission)

    def get_submission(self, course_id, assignment_id, user_id):
        """
        Return a CanvasSubmission instance for the given user in the
        given assignment.
        """
        return self._get(('courses/{}/assignments/{}/submissions/{}'
                         '?include=user')
                         .format(course_id, assignment_id, user_id),
                         CanvasSubmission)

    def set_submission_grade(self, course_id, assignment_id, user_id, grade,
                             comment=None):
        """
        Set the grade and optionally add a comment to the submission for
        the given user in the given assignment.

        Warning: specifying `comment' will add a new comment, not edit
        an existing one. So every time you call this method with
        comment='XYZ', you will add a new comment.
        """

        json = {'submission': {'posted_grade': '{}%'.format(grade)},
                'comment': {}}

        if comment is not None:
            json['comment']['text_comment'] = comment

        self._put('courses/{}/assignments/{}/submissions/{}'
                  .format(course_id, assignment_id, user_id), json)

    def add_submission_comment(self, course_id, assignment_id, user_id,
                               comment, files):
        """
        Adds a comment with optional file(s) attached to a submission

        Info on uploading a file for comments. Warning! it's a very
        involved process
        https://canvas.instructure.com/doc/api/submission_comments.html

        :param course_id: int canvas course id
        :param assignment_id: int canvas assignment id
        :param user_id: int canvas user_id
        :param comment: string comment that will be added to submission
        :param files: (optional) List of (paths to files, file mime type)
        tuples that will be attached to comment
        :return:

        wow wouldn't it be great if you could auto detect the mime type?
        yeah that would be great but windows doesn't have the binary
        needed for python-magic to work
        """

        session = requests.Session()
        session.headers = self._headers()

        file_ids = []

        for file in files or []:

            # Step 1: tell canvas about file upload
            file_path, mime_type = file
            part_1_dict = {
                'name': os.path.basename(file_path),
                'size': os.stat(file_path).st_size,
                'content_type': mime_type
            }

            part_1_resp = session.post(
                self._url('courses/%s/assignments/%s/submissions/%s/comments/'
                          'files' % (course_id, assignment_id, user_id)),
                json=part_1_dict
            )

            part_1_resp.raise_for_status()

            # Step 2: Upload the file data to the URL given in the
            # previous response

            # construct form
            with open(file_path, 'rb') as f:
                file_contents = f.read()
            upload_params = list(part_1_resp.json()['upload_params'].items())
            upload_params.append(('file', file_contents))

            part_2_resp = requests.post(
                part_1_resp.json()['upload_url'],
                files=upload_params
            )

            part_2_resp.raise_for_status()

            file_ids.append(part_2_resp.json()['id'])

        # make the comment
        part_3_req = {
            'comment': {
                'text_comment': comment,
                'file_ids': file_ids
            }
        }
        part_3_resp = session.put(
            self._url('courses/%s/assignments/%s/submissions/%s' %
                      (course_id, assignment_id, user_id)),
            json=part_3_req
        )

        part_3_resp.raise_for_status()
