"""Interface with the Canvas through its REST API"""

import re
import requests
from collections import namedtuple


class CanvasCourse(namedtuple('CanvasCourse', ('id', 'name'))):
    """Hold Course info"""
    __slots__ = ()

    def __str__(self):
        return 'id={}\t{}'.format(self.id, self.name)


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

    def _get(self, name, entity_class):
        """
        Make a request to a Canvas API endpoint, de-paginate the
        response, and convert each JSON entity to an instance of
        `entity_class'.
        """

        link = '{}/api/v1/{}'.format(self.url, name)
        headers = {'authorization': 'Bearer {}'.format(self.token)}

        while link:
            resp = requests.get(link, headers=headers)
            link = self._parse_links(resp.headers['link']).get('next', None)
            for entity in resp.json():
                args = {field: entity[field] for field in entity_class._fields}
                yield entity_class(**args)

    def list_courses(self):
        """
        Return an iterator of CanvasCourse instances of all the active
        courses this user can see.
        """

        return self._get('courses', CanvasCourse)
