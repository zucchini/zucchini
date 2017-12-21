"""Interface with the Canvas through its REST API"""

import re
import requests
from collections import namedtuple


class CanvasCourse(namedtuple('CanvasCourse', ('api_', 'id', 'name'))):
    """Hold Course info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)

    @property
    def assignments(self):
        return self.api_.list_assignments(self.course_id)


class CanvasAssignment(namedtuple('CanvasCourse',
                       ('api_', 'id', 'name', 'course_id'))):
    """Hold assignment info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)

    @property
    def course(self):
        return self.api_.get_course(self.course_id)


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
        return entity_class(api_=self, **args)

    def _url(self, name):
        """Return the URL of an endpoint named `name'"""
        return '{}/api/v1/{}'.format(self.url, name)

    def _headers(self):
        """Return authentication headers"""
        return {'authorization': 'Bearer {}'.format(self.token)}

    def _get(self, name, entity_class):
        """
        Make a request to a Canvas API endpoint and convert the JSON
        entity in the response to an instance of `entity_class'.
        """

        resp = requests.get(self._url(name), headers=self._headers())

        return self._to_entity(resp.json(), entity_class)

    def _gets(self, name, entity_class):
        """
        Make a request to a Canvas API endpoint, de-paginate the
        response, and convert each JSON entity to an instance of
        `entity_class'.
        """

        link = self._url(name)
        headers = self._headers()

        while link:
            resp = requests.get(link, headers=headers)

            if 'link' in resp.headers:
                link = self._parse_links(resp.headers['link']) \
                           .get('next', None)
            else:
                link = None

            for entity_json in resp.json():
                yield self._to_entity(entity_json, entity_class)

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

    def list_assignments(self, course_id):
        """
        Return an iterator of instances of all the assignments in the
        given course.
        """

        return self._gets('courses/{}/assignments'.format(course_id),
                          CanvasAssignment)
