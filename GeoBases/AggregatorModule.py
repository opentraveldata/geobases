#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is an aggregator.

    >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5}
    >>> dict(Aggregator(geo_a, 'country_code').add_from_dict(test).aggregate().items())
    {'FR': [62], 'US': [55]}
    >>> dict(Aggregator(geo_a, 'country_code').add('NCE', 15).add('DFW', 5).aggregate().items())
    {'FR': [15], 'US': [5]}
'''

from __future__ import with_statement

import numpy as np
from datetime import datetime



class Aggregator(object):
    '''
    The aggregator.

    Simplest example::

    >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5}
    >>> Aggregator(geo_a, 'country_code').add_from_dict(test).aggregate('dict')
    {'FR': 62, 'US': 55}
    >>> Aggregator(geo_a, '*').add_from_dict(test).aggregate('dict')
    {'*': 117}
    >>> Aggregator(geo_a, 'country_code').add('NCE', 15).add('DFW', 5).aggregate('dict')
    {'FR': 15, 'US': 5}

    More features with tuple for aggregation::

    >>> test = { ('ORY', 'CDG', '20061101'): 4,
    ...          ('ORY', 'NCE', '20061108'): 5,
    ...          ('AAA', 'NCE', '20061201'): 5 }
    >>> Aggregator(geo_a, ('*', 'city_code', 'year')).add_from_dict(test).aggregate('dict', 'mean')
    {('NCE', '2006'): 5.0, ('PAR', '2006'): 4.0}
    >>> Aggregator(geo_a, ('*', 'city_code', 'year')).add_from_dict(test).aggregate('dict', ('+', 'mean', 'keep'))
    {('NCE', '2006'): (10, 5.0, [5, 5]), ('PAR', '2006'): (4, 4.0, [4])}
    >>> Aggregator(geo_a, ('country_code', 'country_code', 'day_of_week')).add_from_dict(test).aggregate('dict', int.__add__)
    {('PF', 'FR', 'Friday'): 5, ('FR', 'FR', 'Wednesday'): 9}

    Way to handle alternative input format::

    >>> test = { ('ORY', 'CDG', '2006/11/01'): 4,
    ...          ('ORY', 'NCE', '2006/11/08'): 5,
    ...          ('AAA', 'NCE', '2006/12/01'): 5 }
    >>> Aggregator(geo_a, ('*', 'city_code', 'year')).add_from_dict(test, date_format="%Y/%m/%d").aggregate('dict', ('+', 'mean', 'keep'))
    {('NCE', '2006'): (10, 5.0, [5, 5]), ('PAR', '2006'): (4, 4.0, [4])}
    >>> Aggregator(geo_a, ('*', 'city_code', 'year'), date_format="%Y/%m/%d").add_from_dict(test).aggregate('dict', ('+', 'mean', 'keep'))
    {('NCE', '2006'): (10, 5.0, [5, 5]), ('PAR', '2006'): (4, 4.0, [4])}

    Partial aggregation::

    >>> Aggregator(geo_a, ('*', 'city_code', 'year'), date_format="%Y/%m/%d").add_from_dict(test).aggregate().add_from_dict(test).aggregate('dict')
    {('NCE', '2006'): 20, ('PAR', '2006'): 8}
    >>> Aggregator(geo_a, ('country_code', 'city_code')).add(('ORY', 'CDG'), 4).aggregate().add(('ORY', 'SFO'), 3).aggregate('dict')
    {('FR', 'SFO'): 3, ('FR', 'PAR'): 4}

    Way to handle errors::

    >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5, 'UNKNOWN_AIRPORT': 150}
    >>> Aggregator(geo_a, 'country_code').add_from_dict(test).aggregate()
    Traceback (most recent call last):
    KeyError: 'Thing not found: UNKNOWN_AIRPORT'
    >>> Aggregator(geo_a, 'country_code', safe_mode=True).add_from_dict(test).aggregate('dict')
    /!\ Key conversion error /!\: UNKNOWN_AIRPORT
    {'FR': 62, 'US': 55}
    >>> Aggregator(geo_a, 'country_code', safe_mode=True).add('UNKNOWN_AIRPORT', 15).aggregate('dict')
    /!\ Key conversion error /!\: UNKNOWN_AIRPORT
    {}
    >>> Aggregator(geo_a, 'country_code', safe_mode=True, verbose=False).add_from_dict(test).aggregate('dict')
    {'FR': 62, 'US': 55}
    '''

    def __init__(self, geob=None, fields=None, date_format=None, safe_mode=False, verbose=True):

        # A geobase object
        self._geob = geob

        # Caching headers
        if self._geob is not None:
            self._headers = set(self._geob._headers)
        else:
            self._headers = set()

        # A date manager
        self._dconv = DateConverter(date_format)

        self._fields    = fields
        self._safe_mode = safe_mode
        self._verbose   = verbose

        # _agg is a dictionary containing groups of airports sharing the
        # same characteristics (given by T_field during aggregation)
        self._agg = {}

        # This is a performance hack, to avoid type
        # testing and recursion later
        if isinstance(fields, tuple):
            self._proto = self._buildMProto(fields)
            self._n     = len(self._proto)
            self.get    = self._mget
            self._show  = lambda k : '^'.join([str(e) for e in k]) if k else '*'
        else:
            self._proto = self._buildSProto(fields)
            self._n     = 1
            self.get    = self._proto # or self._sget, this is the same
            self._show  = lambda k :  str(k)




    def __iter__(self):
        return self._agg.iterkeys()


    def __contains__(self, key):
        return key in self._agg



    def _buildSProto(self, field):
        '''
        >>> p = Aggregator()._buildSProto('*')
        >>> p('ORY')
        '*'
        >>> p = Aggregator()._buildSProto(None)
        >>> p('ORY')
        'ORY'
        '''

        if field is None:
            return lambda key, df=None: key

        if field == '*':
            return lambda key, df=None: '*'

        if field in self._headers:
            return lambda key, df=None: self._geob.get(key, field)

        if self._dconv.hasDateFormat(field):
            return lambda key, df=None: self._dconv.convertDate(key, field, df)

        raise ValueError("Bad field %s not in %s or %s" % (field, self._headers, self._dconv._date_formats))



    def _buildMProto(self, T_field):
        '''
        >>> p = Aggregator()._buildMProto((None, '*'))
        >>> (p[0]('ORY'), p[1]('CDG'))
        ('ORY', '*')
        '''
        return tuple(self._buildSProto(f) for f in T_field)


    def _sget(self, key, date_format=None):
        '''
        >>> a = Aggregator(fields='*')
        >>> a._sget('ORY')
        '*'
        '''
        return self._proto(key, date_format)


    def _mget(self, T_key, date_format=None):
        '''
        >>> a = Aggregator(fields=(None, '*'))
        >>> a._mget(('ORY', 'CDG'))
        ('ORY',)
        >>> a = Aggregator(fields=(None, '*', None))
        >>> a._mget(('ORY', 'CDG', 'LYS'))
        ('ORY', 'LYS')
        '''
        return tuple(self._proto[i](T_key[i], date_format) for i in xrange(self._n) if self._fields[i] != '*')


    #@profile
    def add(self, key, value, date_format=None):
        '''
        >>> dict(Aggregator(geo_a, 'country_code').add('NCE', 15).add('DFW', 5).aggregate().items())
        {'FR': [15], 'US': [5]}
        '''
        try:
            agg_key = self.get(key, date_format)

        except KeyError as e:
            if not self._safe_mode:
                raise

            if self._verbose:
                print "/!\ Key conversion error /!\: %s" % str(key)

        else:
            try:
                self._agg[agg_key].append(value)
            except KeyError:
                self._agg[agg_key] = [ value ]

        return self



    def add_from_file(self, source, separator,
                      lambda_key, lambda_value, lambda_skip=None,
                      date_format=None, verbose=True, monitor=1000000):
        '''
        >>> import os
        >>> f = os.path.join(os.path.dirname(__file__), '../test/js_shoot_1204_2.txt.hsv.aggreg.test')
        >>> from datetime import datetime
        >>> bef = datetime.now()
        >>>
        >>> a = Aggregator(fields=('*', '*', 'month'))
        >>> a.add_from_file(f, '^', lambda r: (r[0], r[1], r[2]), lambda r: float(r[4]), date_format='%y%m%d')
        <....Aggregator object at ...>
        >>> list(a.aggregate('iter'))
        [(('201204',), 102096.0)]
        >>> a = Aggregator(fields=(None, None, '*'))
        >>> a.add_from_file(f, '^', lambda r: (r[0], r[3], r[2]), lambda r: float(r[4]), lambda r: r[3] == 'UA')
        <....Aggregator object at ...>
        >>> a.aggregate('csv')
        MLU^CO^63.0
        SFO^AS^24.0
        ROA^US^15.0
        ...
        >>> a.aggregate('dict')
        {('MLU', 'CO'): 63.0, ('BOM', 'TG'): 10.0, ...
        >>> #print datetime.now() - bef
        '''

        with open(source) as f:

            self.add_from_flike(f,
                                separator,
                                lambda_key, lambda_value, lambda_skip,
                                date_format,
                                verbose,
                                monitor)

        return self



    def add_from_flike(self, flike, separator,
                       lambda_key, lambda_value, lambda_skip=None,
                       date_format=None, verbose=True, monitor=1000000):
        '''
        File like input possibility.

        >>> import os
        >>> f = os.path.join(os.path.dirname(__file__), '../test/js_shoot_1204_2.txt.hsv.aggreg.test')
        >>>
        >>> a = Aggregator(fields=('*', '*', 'month'))
        >>> fl = open(f)
        >>> a.add_from_flike(fl, '^', lambda r: (r[0], r[1], r[2]), lambda r: float(r[4]), date_format='%y%m%d')
        <....Aggregator object at ...>
        >>> fl.close()
        >>> list(a.aggregate('iter'))
        [(('201204',), 102096.0)]
        '''

        if lambda_skip is None:
            lambda_skip = lambda row: False

        for i, row in enumerate(flike, start=1):

            if i % monitor == 0 and verbose:
                print '%8s done...' % i

            row = row.strip().split(separator)

            if lambda_skip(row):
                continue

            self.add(lambda_key(row), lambda_value(row), date_format)

        return self



    def add_from_dict(self, dict_data, date_format=None):
        '''
        The aggregation function.


        :param dict_data: is an input dictionary of airports, \
            values should be data implementing __add__ method, like int \
            and keys are tuple as ('NCE', '2006')
        :param T_field: tuple of characteristics used \
            to create groups ('country' will group airports by country)
        :param op: specify the type of operation \
            to calculate the value of aggregated data (sum, mean, ...)
        '''

        for key, value in dict_data.iteritems():
            self.add(key, value, date_format)

        return self



    def aggregate(self, output='internal', operator='+', out=None):
        '''
        Output aggregated data on stdout without actually modifying structure.

        >>> test = { ('ORY', 'CDG', '20061101'): 4,
        ...          ('ORY', 'NCE', '20061108'): 5,
        ...          ('AAA', 'NCE', '20061201'): 5 }
        >>> Aggregator(geo_a, ('*', 'city_code', 'year'), safe_mode=True, verbose=False).add_from_dict(test).aggregate('csv')
        NCE^2006^10
        PAR^2006^4
        >>> Aggregator(geo_a, ('*', '*', '*'), safe_mode=True, verbose=False).add_from_dict(test).aggregate('csv')
        *^14
        >>>
        >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5}
        >>> Aggregator(geo_a, 'country_code', safe_mode=True, verbose=False).add_from_dict(test).aggregate('csv')
        FR^62
        US^55
        >>> list(Aggregator(geo_a, 'country_code', safe_mode=True, verbose=False).add_from_dict(test).aggregate('iter'))
        [('FR', 62), ('US', 55)]
        >>> Aggregator(geo_a, 'country_code', safe_mode=True, verbose=False).add_from_dict(test).aggregate('dict')
        {'FR': 62, 'US': 55}
        >>> list(Aggregator(geo_a, 'country_code', safe_mode=True, verbose=False).add_from_dict(test).aggregate().items())
        [('FR', [62]), ('US', [55])]
        '''

        if output == 'internal':
            for k, g in self._agg.iteritems():
                self._agg[k] = [ _reduceGroup(g, operator) ]
            return self

        if output == 'csv':
            if out is None:
                for k, g in self._agg.iteritems():
                    print '%s^%s' % (self._show(k), _reduceGroup(g, operator))
            else:
                with open(out, 'w') as o:
                    for k, g in self._agg.iteritems():
                        o.write('%s^%s\n' % (self._show(k), _reduceGroup(g, operator)))

            return

        if output == 'iter':
            return ((k, _reduceGroup(g, operator)) for k, g in self._agg.iteritems())

        if output == 'dict':
            return dict((k, _reduceGroup(g, operator)) for k, g in self._agg.iteritems())


    def items(self):
        return self._agg.iteritems()

    def values(self):
        return self._agg.itervalues()

    def keys(self):
        return self._agg.iterkeys()

    def clear(self):
        self._agg = {}


def _reduceGroup(group, op):
    '''
    This method is protected and shouldnt be used.
    It computates a group of airports, after aggregation, to have
    the aggregate value for the group.

    >>> _reduceGroup([1, 2, 6], '+')
    9
    >>> _reduceGroup([1.0, 2, 6], '+')
    9.0
    >>> _reduceGroup([1, 2, 6], 'var')
    7.0
    >>> _reduceGroup([1, 2, 6], ('var', 'mean'))
    (7.0, 3.0)

    :param group: a dictionary of values
    :param op: a function indicating which operation the method will use int.__add__, int.__mul__ should work if values are int
    '''

    if not group:
        raise ValueError("Empty group")

    if op == '+'   : return reduce(group[0].__class__.__add__, group)
    if op == '*'   : return reduce(group[0].__class__.__mul__, group)

    # Warning: will work for floats,
    # But for other classes sum(), /, ** have to be defined
    if op == 'mean': return np.mean(group)
    if op == 'var' : return np.var(group, ddof=1)
    if op == 'sd'  : return np.sd(group, ddof=1)

    if op == 'keep': return group

    if isinstance(op, tuple):
        return tuple(_reduceGroup(group, o) for o in op)

    return reduce(op, group)



class DateConverter(object):

    def __init__(self, date_format=None):

        # For aggregation function
        self._date_formats = {
            'year'          : "%Y",
            'month'         : "%Y%m",
            'day'           : "%Y%m%d",
            'month_of_year' : "%B",
            'day_of_week'   : "%A",
            'day_of_month'  : "%d"
        }

        # This is easier to do like this to set initial value.
        # Indeed, another constructor calls this constructor
        # with None as a default value, so it will always be set to None
        # if not checked here.
        if date_format is None:
            self._date_reading_format = "%Y%m%d"
        else:
            self._date_reading_format = date_format


    def hasDateFormat(self, date_format):

        return date_format in self._date_formats


    def convertDate(self, date, field, date_format=None):
        '''
        Method to convert dates, used for aggregation algorithms.

        >>> dc = DateConverter()
        >>> dc.convertDate("20101026", "month")
        '201010'
        >>> dc.convertDate("20101026", "day_of_week")
        'Tuesday'
        >>> dc.convertDate("2010/10/26", "day_of_week", "%Y/%m/%d")
        'Tuesday'
        '''

        if date_format is None:
            date_format = self._date_reading_format

        if field not in self._date_formats:
            raise ValueError("Bad date format, not in %s" % self._date_formats)

        return datetime.strptime(date, date_format).strftime(self._date_formats[field])



def _test():
    '''
    When called directly, launching doctests.
    '''
    import doctest

    from GeoBaseModule import GeoBase

    extraglobs = {
        'geo_a': GeoBase(data='airports', verbose=False)
    }

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE |
            doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()



