#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Aim of this module is to interface to idealista[*] web API.

[*] http://developers.idealista.com/access-request

[DOC] https://files.mycloud.com/home.php?brand=webfiles&seuuid=7ebb08719667e6379cc716892fe5e7ab&name=idealista

"""

import requests, base64, time
# from swissknife.log import timeLoggerDecorator, setUpGenericLogger
import json
import pyproj
from shapely.geometry import Point
from simplejson import JSONDecodeError

NOTSET = None

myproj = pyproj.Proj("epsg:3857")

# logger = setUpGenericLogger("debug")

# apikey = base64.b64encode(b':'.join([b"your_APIKEY", b"your_SECRET"]))

base_url = 'https://api.idealista.com'

propertyTypes = [
    "homes", "offices", "premises",
    # "garages", "bedrooms"
]

operations = [
    "sale",
    "rent"
]

codes = {
    'unauthorized': 401
}

settings = {
    "apikey": NOTSET,
    "apisecret": NOTSET
}

def get_credentials():
    assert not NOTSET in settings.values(), "ERROR! apikey and apisecret are required to get credentials."
    return base64.b64encode(
        b'{apikey}:{apisecret}'.format(**settings)
    ).decode('utf-8')

def webcall(func):
    """ """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result.status_code==200:
            return result.json()
        else:
            try:
                message = result.json().get('message', 'Unknown error.')
                # logger.error("HTTP code: {}. Message: {}".format(
                #     result.status_code,
                #     message
                # ))
                raise Exception(message)
            except JSONDecodeError:
                raise Exception(result.text)

    return wrapper

def webcalltogettoken(func):
    """ """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result.status_code==200:
            response = result.json()
            try:
                error = response['error']
            except KeyError:
                return response
            else:
                message = response.get('error_description', 'Unknown error.')
                status_code = codes.get(error, 400)
                # logger.error("HTTP code: {}. Message: {}".format(
                #     status_code,
                #     message
                # ))
                raise Exception(message)
        else:
            message = result.text
            # status_code = codes.get(error, 400)
            # logger.error("HTTP code: {}. Message: {}".format(
            #     result.status_code,
            #     message
            # ))
            raise Exception(message)
    return wrapper

def tokencacher(func):
    def wrapper(*args, **kwargs):
        try:
            assert not current.cache.disk.storage is None and current.cache.disk.storage[func.__name__]
        except (KeyError, AssertionError,) as err:
            now = time.time()
            res = current.cache.disk(func.__name__, lambda: func(*args, **kwargs), time_expire=.001)
            after = now+res["expires_in"]
            current.cache.disk.storage[func.__name__] = (after, current.cache.disk.storage[func.__name__][1])
        else:
            res = current.cache.disk(func.__name__, lambda: func(*args, **kwargs), time_expire=.001)
        return res
    return wrapper

@tokencacher
@webcalltogettoken
def get_token():
    service = 'oauth/token'
    headers = {
        'Authorization': 'Basic {}'.format(get_credentials()),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials', 'scope': 'read'}
    return requests.post('{}/{}'.format(base_url, service),
        headers = headers,
        data = data
    )

@webcall
def call_idealista(
    lon, lat,
    distance = 1000,
    country='es',
    propertyType = 'homes',
    operation = 'sale',
    maxItems = 50,
    order = 'distance',
    sort = 'asc',
    **kw
):

    center = "{lat:-f},{lon:-f}".format(**vars())

    service = '3.5/{country}/search'.format(**vars())
    res = get_token()
    url = '{}/{}'.format(base_url, service)

    headers = {
        'Authorization': '{} {}'.format(res['token_type'].capitalize(), res['access_token']),
    }

    data = dict(
        locale = country,
        language = country,
        propertyType = propertyType,
        operation = operation,
        maxItems = maxItems,
        order = order,
        distance = distance,
        sort = sort
    )

    data.update(kw)
    return requests.post(url,
        headers = headers,
        data = dict(data, center=center)
    )

if __name__ == '__main__':

    import unittest

    import sys
    from os.path import basename, splitext

    class AuthTestCase(unittest.TestCase):

        def test_credentials_1(self):
            settings.update({"apikey": "apikey", "apisecret": "apisecret"})
            res = get_credentials()
            self.assertEqual(res, b'apikey:apisecret')

    _testlog = splitext(basename(__file__))[0]+'.log'
    with open(_testlog, "w") as testlog:
        runner = unittest.TextTestRunner(testlog)
        unittest.main(testRunner=runner, exit=False)
    with open(_testlog) as testlog:
        print(testlog.read())
