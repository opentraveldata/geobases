#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is an aggregator.

    >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5}
    >>> Aggregator(geo_a, 'country_code').add_from_dict(test).aggregate()
    {'FR': 62, 'US': 55}
    >>> Aggregator(geo_a, 'country_code').add('NCE', 15).add('DFW', 5).aggregate()
    {'FR': 15, 'US': 5}
'''

import numpy as np
from datetime import datetime


class Aggregator(object):
    '''
    The aggregator.

    Simplest example::
    
    >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5}
    >>> Aggregator(geo_a, 'country_code').add_from_dict(test).aggregate()
    {'FR': 62, 'US': 55}
    >>> Aggregator(geo_a, 'country_code').add('NCE', 15).add('DFW', 5).aggregate()
    {'FR': 15, 'US': 5}
    
    More features with tuple for aggregation::
    
    >>> test = { ('ORY', 'CDG', '20061101'): 4,
    ...          ('ORY', 'NCE', '20061108'): 5,
    ...          ('AAA', 'NCE', '20061201'): 5 }
    >>> Aggregator(geo_a, ('*', 'city_code', 'year')).add_from_dict(test).aggregate('mean')
    {('*', 'NCE', '2006'): 5.0, ('*', 'PAR', '2006'): 4.0}
    >>> Aggregator(geo_a, ('*', 'city_code', 'year')).add_from_dict(test).aggregate(('+', 'mean', 'keep'))
    {('*', 'NCE', '2006'): (10, 5.0, [5, 5]), ('*', 'PAR', '2006'): (4, 4.0, [4])}
    >>> Aggregator(geo_a, ('country_code', 'country_code', 'day_of_week')).add_from_dict(test).aggregate(int.__add__)
    {('PF', 'FR', 'Friday'): 5, ('FR', 'FR', 'Wednesday'): 9}

    Way to handle alternative input format::
    
    >>> test = { ('ORY', 'CDG', '2006/11/01'): 4,
    ...          ('ORY', 'NCE', '2006/11/08'): 5,
    ...          ('AAA', 'NCE', '2006/12/01'): 5 }
    >>> Aggregator(geo_a, ('*', 'city_code', 'year')).add_from_dict(test, date_format="%Y/%m/%d").aggregate(('+', 'mean', 'keep'))
    {('*', 'NCE', '2006'): (10, 5.0, [5, 5]), ('*', 'PAR', '2006'): (4, 4.0, [4])}
    >>> Aggregator(geo_a, ('*', 'city_code', 'year'), date_format="%Y/%m/%d").add_from_dict(test).aggregate(('+', 'mean', 'keep'))
    {('*', 'NCE', '2006'): (10, 5.0, [5, 5]), ('*', 'PAR', '2006'): (4, 4.0, [4])}
    
    Partial aggregation::
    
    >>> Aggregator(geo_a, ('*', 'city_code', 'year'), date_format="%Y/%m/%d").add_from_dict(test).aggregate(final=False).add_from_dict(test).aggregate()
    {('*', 'NCE', '2006'): 20, ('*', 'PAR', '2006'): 8}
    
    Way to handle errors::
    
    >>> test = {'NCE':15, 'ORY':20, 'AFW':50, 'CDG':27, 'DFW':5, 'UNKNOWN_AIRPORT': 150}
    >>> Aggregator(geo_a, 'country_code').add_from_dict(test).aggregate()
    Traceback (most recent call last):
    KeyError: 'Thing not found: UNKNOWN_AIRPORT'
    >>> Aggregator(geo_a, 'country_code', safe_mode=True).add_from_dict(test).aggregate()
    /!\ Key not found /!\: UNKNOWN_AIRPORT
    {'FR': 62, 'US': 55}
    >>> Aggregator(geo_a, 'country_code', safe_mode=True).add('UNKNOWN_AIRPORT', 15).aggregate()
    /!\ Key not found /!\: UNKNOWN_AIRPORT
    {}
    >>> Aggregator(geo_a, 'country_code', safe_mode=True, verbose=False).add_from_dict(test).aggregate()
    {'FR': 62, 'US': 55}
    '''
    
    def __init__(self, geob, fields=None, date_format=None, safe_mode=False, verbose=True):
        
        # A geobase object
        self._geob = geob
        
        # A date manager
        self._dconv = DateConverter(date_format)
        
        self._fields    = fields
        self._safe_mode = safe_mode
        self._verbose   = verbose

        # _agg is a dictionary containing groups of airports sharing the
        # same characteristics (given by T_field during aggregation)
        self._agg = {}
        

    def __iter__(self):
        return self._agg.iterkeys()


    def __contains__(self, key):
        return key in self._agg
    
    
    def clear(self):
        self._agg = {}


    def multiGet(self, T_key, T_field, date_format=None):
        '''
        Almost the same as get: method to get an information-tuple
        from an thing-tuple. Not very useful, but its a cool wrapper
        when you perform data aggregation.

        :param T_key:   a tuple of keys, like ('ORY', 'SFO')
        :param T_field: a tuple of fields, like ('name', 'lat')
        :returns:       a tuple of informations
        :raises:        IndexError, if the two input tuples have different size.

        >>> Aggregator(geo_a).multiGet('CDG', 'city_code')
        'PAR'
        >>> Aggregator(geo_t).multiGet('frnic', 'name')
        'Nice-Ville'
        >>> Aggregator(geo_t).multiGet('frnic', '*')
        '*'
        >>> Aggregator(geo_t).multiGet('frnic', None)
        'frnic'
        >>> Aggregator(geo_a).multiGet(('ORY', 'CDG'), ('city_code', 'country_name'))
        ('PAR', 'France')
        >>> Aggregator(geo_t).multiGet(('frnic', 'frxat', 'frpmo'), ('*', None, 'name'))
        ('*', 'frxat', 'Paris-Montparnasse')
        >>> Aggregator(geo_a).multiGet(('ORY', ), ('city_code', ))
        ('PAR',)
        >>> Aggregator(geo_a).multiGet('ORY', None)
        'ORY'

        This get function raise exception when input is not correct.

        >>> Aggregator(geo_t).multiGet('frnic', 'not_a_field')
        Traceback (most recent call last):
        ValueError: Bad field not_a_field not in ['code', 'lines', 'name', 'info', 'lat', 'lng', 'type'] or set(['year', 'day_of_month', 'day_of_week', 'month', 'month_of_year', 'day'])
        >>> Aggregator(geo_t).multiGet('frmoron', 'name')
        Traceback (most recent call last):
        KeyError: 'Thing not found: frmoron'
        '''
            
        # Ok we manage moronic user input :), but really
        # the spirit is to give tuples
        if isinstance(T_field, tuple):
            return tuple(self.multiGet(k, f, date_format) for k, f in zip(T_key, T_field))

        if T_field is None:
            return T_key

        if T_field == '*':
            return '*'

        if T_field in self._geob._headers:
            return self._geob.get(T_key, T_field)

        if self._dconv.hasDateFormat(T_field):
            return self._dconv.convertDate(T_key, T_field, date_format)

        raise ValueError("Bad field %s not in %s or %s" % (T_field, self._geob._headers, self._dconv._date_formats))


    def add(self, key, value, date_format=None):

        try:
            agg_key = self.multiGet(key, self._fields, date_format)

        except KeyError as e:
            if not self._safe_mode:
                raise

            if self._verbose:
                print "/!\ Key not found /!\: %s" % key

        else:
            if agg_key not in self._agg:
                self._agg[agg_key] = []

            self._agg[agg_key].append(value)
            
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
    
    
    def aggregate(self, operator='+', final=True):
        
        if final:
            return dict( (k, self._reduceGroup(g, operator)) for k, g in self._agg.iteritems() )
            
        for k, g in self._agg.iteritems():
            self._agg[k] = [ self._reduceGroup(g, operator) ]
            
        return self


    @staticmethod
    def _reduceGroup(group, op):
        '''
        This method is protected and shouldnt be used.
        It computates a group of airports, after aggregation, to have
        the aggregate value for the group.
    
        >>> Aggregator._reduceGroup([1, 2, 6], '+')
        9
        >>> Aggregator._reduceGroup([1.0, 2, 6], '+')
        9.0
        >>> Aggregator._reduceGroup([1, 2, 6], 'var')
        7.0
        >>> Aggregator._reduceGroup([1, 2, 6], ('var', 'mean'))
        (7.0, 3.0)
    
        :param group: a dictionary of values
        :param op: a function indicating which operation the method will use int.__add__, int.__mul__ should work if values are int
        '''
    
        if not group:
            raise ValueError("Empty group")
    
        if isinstance(op, tuple):
            return tuple(Aggregator._reduceGroup(group, o) for o in op)
    
        # Warning: will work for floats,
        # But for other classes sum(), /, ** have to be defined
        if op == 'mean': return np.mean(group)
        if op == 'var' : return np.var(group, ddof=1)
        if op == 'sd'  : return np.sd(group, ddof=1)
    
        if op == 'keep': return group
    
        if op == '+': op = group[0].__class__.__add__
        if op == '*': op = group[0].__class__.__mul__
    
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
        'geo_a': GeoBase(data='airports', verbose=False),
        'geo_t': GeoBase(data='stations', verbose=False),
        'geo_m': GeoBase(data='mix',      verbose=False)
    }

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE |
            doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()



