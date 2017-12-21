"""Interface with the Canvas through its REST API"""

import os
import re
import requests
import shutil
from collections import namedtuple

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
                 ('api_', 'id', 'name'))):
    """Hold user info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)


class CanvasSubmissionAttachment(namedtuple('CanvasSubmission',
                                 ('api_', 'id', 'display_name', 'url'))):
    """Hold information about a submitted file"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}\t{}' \
               .format(self.id, self.display_name, self.url)

    def download(self, directory):
        """
        Download this attachment with the name provided by the student
        to the directory provided.
        """
        # XXX Make sure they didn't put characters in the display_name
        #     such that it's `../../../../../etc/passwd' or something.
        #     I don't know if Canvas checks for this.
        path = os.path.join(directory, self.display_name)
        self.api_._download_file(self.url, path)


class CanvasSubmission(namedtuple('CanvasSubmission',
                       ('api_', 'id', 'late', 'user_id', 'attachments'))):
    """Hold assignment info"""
    __slots__ = ()
    _sub_entities = {'attachments': CanvasSubmissionAttachment}

    def __str__(self):
        attachments = ', '.join(attachment.display_name
                                for attachment in self.attachments)
        return 'id={}\t{}late\t{}\t{}' \
               .format(self.id, '' if self.late else 'not ', self.user,
                       attachments)

    @property
    def user(self):
        return self.api_.get_user(self.user_id)

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
        args = {field: entity_json[field] for field in entity_class._fields
                if field != 'api_'}

        if hasattr(entity_class, '_sub_entities'):
            for field, class_ in entity_class._sub_entities.items():
                args[field] = [self._to_entity(entity, class_)
                               for entity in args[field]]

        return entity_class(api_=self, **args)

    def _url(self, name):
        """Return the URL of an endpoint named `name'"""
        return '{}/api/v1/{}'.format(self.url, name)

    def _headers(self):
        """Return authentication headers"""
        return {'authorization': 'Bearer {}'.format(self.token)}

    def _request(self, url, stream=False):
        """
        Attempt to request the URL url, raising exceptions in error
        conditions
        """
        resp = requests.get(url, headers=self._headers(), stream=stream)

        if resp.status_code == 404:
            raise CanvasNotFoundError()
        elif resp.status_code >= 500 and resp.status_code < 600:
            raise CanvasInternalError()

        return resp

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

        return self._gets('courses/{}/assignments/{}/submissions'
                          .format(course_id, assignment_id), CanvasSubmission)

    def list_section_submissions(self, section_id, assignment_id):
        """
        Return an iterator of instances of all the submissions in the
        given section for the given assignment.
        """

        return self._gets('sections/{}/assignments/{}/submissions'
                          .format(section_id, assignment_id), CanvasSubmission)

    def get_submission(self, course_id, assignment_id, user_id):
        """
        Return a CanvasSubmission instance for the given user in the
        given assignment.
        """
        return self._get('courses/{}/assignments/{}/submissions/{}'
                         .format(course_id, assignment_id, user_id),
                         CanvasSubmission)
