#!/usr/bin/python
# -*- coding: utf-8 -*-

from functools import wraps
from flask import current_app, request


def support_jsonp(f):
    '''
    Wraps JSONified output for JSONP
    '''

    @wraps(f)
    def decorated_function(*args, **kwargs):

        callback = request.args.get('callback', False)

        if callback:
            # If you are decorating a function which
            # returns raw text, you may use the first line
            # Otherwise, you should return Response object
            #content = '%s(%s)' % (callback, f(*args, **kwargs))
            content = '%s(%s)' % (callback, f(*args, **kwargs).data)

            return current_app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)

    return decorated_function

