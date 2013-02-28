#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module provides tools to administrate sources.
"""

from __future__ import with_statement

import os
import os.path as op
from textwrap import dedent

# Not in standard library
import yaml


# Cache directory
CACHE_DIR = op.join(os.getenv('HOME', '.'), '.GeoBases.d')
if not op.isdir(CACHE_DIR):
    os.mkdir(CACHE_DIR)


class SourcesAdmin(object):
    """
    This class is used to administrate sources.
    """
    def __init__(self, sources_conf_path, sources_dir):

        # Path to the configuration file
        self.sources_conf_path = sources_conf_path

        with open(sources_conf_path) as fl:
            self.sources = yaml.load(fl)

        # Root folder where we find data
        self.sources_dir = sources_dir


    def __contains__(self, source):
        """For *in* test.
        """
        return source in self.sources


    def __iter__(self):
        """For iteration.
        """
        return iter(self.sources)


    def get(self, source):
        """Get source information.
        """
        return self.sources[source]


    def add(self, source, config):
        """Add new source.
        """
        if source in self.sources:
            print 'Source %s already exists.' % source
        else:
            self.sources[source] = config


    def drop(self, source):
        """Drop source.
        """
        del self.sources[source]


    def update(self, source, option, option_config):
        """Update source.
        """
        if source not in self.sources:
            print 'Source %s not in sources.' % source
            return

        self.sources[source][option] = option_config



    def build_help(self):
        """Display informations on available sources.
        """
        missing = '<none>'

        def fmt_keys(l):
            """Nice key_fields formatting."""
            if l is None:
                return missing
            if isinstance(l, (list, tuple, set)):
                return '+'.join(l)
            return str(l)

        def fmt_path(p):
            """Nice path formatting."""
            if isinstance(p, str):
                return str(p)
            if 'extract' not in p:
                return p['file']
            return '%s -> %s' % (p['file'], p['extract'])

        tip = [dedent('''
        * Data sources from %s [%s]
        ''' % (self.sources_dir, op.basename(self.sources_conf_path)))]

        tip.append('-' * 80)
        tip.append('%-20s | %-25s | %s' % ('NAME', 'KEY', 'PATHS (DEFAULT + FAILOVERS)'))
        tip.append('-' * 80)

        for source in sorted(self.sources.keys()):
            config = self.sources[source]

            if config is not None:
                keys  = config.get('key_fields', missing)
                paths = config.get('paths', missing)
            else:
                keys, paths = missing, missing

            if isinstance(paths, (str, dict)):
                paths = [paths]
            tip.append('%-20s | %-25s | %s' % \
                       (source, fmt_keys(keys), '.) %s' % fmt_path(paths[0])))

            for n, path in enumerate(paths[1:], start=1):
                tip.append('%-20s | %-25s | %s' % \
                           ('-', '-', '%s) %s' % (n, fmt_path(path))))

        tip.append('-' * 80)

        return '\n'.join(tip)


    def help_permanent_add(self, options):
        """Display help on how to make a data source permanent.
        """
        conf = {
            'paths' : '<INSERT_ABSOLUTE_FILE_PATH>',
            'local' : False
        }

        for option, value in options.iteritems():
            # Source is not allowed in configuration, replaced by paths/local
            if option not in ('source', 'verbose'):
                conf[option] = value

        print
        print '* You can make this data source permanent!'
        print '* Edit %s with:' % self.sources_conf_path
        print
        print '$ cat >> %s << EOF' % self.sources_conf_path
        print '# ================ BEGIN ==============='
        print
        print yaml.dump({
            '<INSERT_ANY_NAME>' : conf
        }, indent=4, default_flow_style=None)

        print '# ================  END  ==============='
        print 'EOF'
        print
        print '* Replace the placeholders <INSERT_...> with:'
        print '$ vim %s' % self.sources_conf_path
        print







def _test():
    """When called directly, launching doctests.
    """
    import doctest

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE)
            #doctest.REPORT_ONLY_FIRST_FAILURE)
            #doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(optionflags=opt)



if __name__ == '__main__':
    _test()

