#!/usr/bin/python
# -*- coding: utf-8 -*-

from SysUtils import localToFile, addTopLevel

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
    
    
def load_mano_file(source):
    
    # GEM utils
    CODE = 0
    NAME = 1
    LAT  = 2
    LNG  = 3
    SEPARATOR = '^'
    
    gen_id = generate_manual_line_id()
    
    cache = OrderedDict()
    
    with open(source) as f:

        for row in f:
            
            # Skip comments and empty lines
            if not row or row.startswith('#'):
                #print row
                continue
                            
            row = row.strip().split(SEPARATOR)
            
            cache[row[CODE]] = (row[CODE], gen_id(), row[NAME], 'Desserte Voyageur-Manual addition', row[LAT], row[LNG])

    
    print "Import successful from %s" % source
                        
    return cache



class generate_manual_line_id(object):
    '''
    Class to generate line ids for additional stations.
    
    >>> gl = generate_manual_line_id()
    >>> gl()
    '1000001'
    >>> gl()
    '1000002'
    '''
    def __init__(self):
        self.r = 0
        
    def __call__(self):
        
        self.r += 1        
        return str(1000000 + self.r)
    
    
def add_mano_entries(cache, source, output):

    SEPARATOR = '^'
    
    with open(output, 'w') as out:
        with open(source) as f:
            
            for row in f:
                out.write(row)
            
            for fields in cache.itervalues():
                out.write(SEPARATOR.join(fields) + '\n')
                    
        print "Import successful from %s" % source                      
    print "Export successful of %s" % output


def add_LaMano_RFF(mano_source, rff_source, rff_output):
    
    add_mano_entries(load_mano_file(mano_source), rff_source, rff_output)



def _test():
    '''
    When called directly, launching doctests.
    '''
    import doctest

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE )
            #doctest.IGNORE_EXCEPTION_DETAIL)

    globs = {}
    
    doctest.testmod(optionflags=opt,
                    extraglobs=globs,
                    verbose=False)

    
    
if __name__ == '__main__':

    _test()
    
    add_LaMano_RFF(localToFile(__file__, "../LaMano/additional_stations.csv"),
                   localToFile(__file__, "RFF/RFF_gares.ids.gm.csv"), 
                   localToFile(__file__, "RFF/RFF_gares.ids.gm.man.csv"))



