#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module defines a class *VisualMixin* which will be used by the *GeoBase*
as a mixin.
"""

from __future__ import with_statement

import os
import os.path as op
from operator import itemgetter
from itertools import product
import json
from shutil import copy
from collections import defaultdict
from datetime import datetime
import math

# Not in standard library
from dateutil.relativedelta import relativedelta

# Relative paths handling
DIRNAME = op.dirname(__file__)

def relative(rel_path, root=DIRNAME):
    """Handle relative paths.
    """
    return op.join(op.realpath(root), rel_path)

# Default temporary files directory and base names
DEFAULT_TMP_NAME = 'example'
DEFAULT_TMP_DIR  = None # translated to working dir


# We only export the main class
__all__ = ['VisualMixin']


class VisualMixin(object):
    """
    Main class used as mixin for the *GeoBase* class.
    """
    def buildGraphData(self, graph_fields, graph_weight=None, with_types=False, directed=False, from_keys=None):
        """Build graph data.

        :param graph_fields: iterable of fields used to define the nodes. \
                Nodes are the values of these fields. Edges represent the \
                data.
        :param graph_weight: field used to define the weight of nodes and \
                edges. If ``None``, the weight is ``1`` for each key.
        :param with_types:  boolean to consider values from different fields \
                of the same "type" or not, meaning we will create only one \
                node if the same value is found accross different fields, if \
                there are no types. Otherwise we create different nodes. \
                Default is ``False``, meaning untyped graphs.
        :param directed:    boolean, if the graph is directed or not, \
                default is ``False``.
        :param from_keys:   only use this iterable of keys if not ``None``
        :returns:           the nodes data

        >>> nodes = g.buildGraphData(
        ...     graph_fields=['continent_name', 'country_code'],
        ...     graph_weight='page_rank'
        ... )
        >>> edges = nodes['Antarctica']['edges'].values()
        >>> sorted(edges[0].items())
        [('from', 'Antarctica'), ('to', 'AQ'), ('weight', 0)]
        """
        if from_keys is None:
            from_keys = iter(self)

        for field in graph_fields:
            if field not in self.fields:
                raise ValueError('graph_fields "%s" not in fields %s.' % \
                                 (field, self.fields))

        if graph_weight is not None and graph_weight not in self.fields:
            raise ValueError('graph_weight "%s" not in fields %s.' % \
                             (graph_weight, self.fields))

        if graph_weight is None:
            get_weight = lambda key: 1
        else:
            def get_weight(key):
                """Custom weight computation."""
                try:
                    w = float(self.get(key, graph_weight))
                except (ValueError, TypeError):
                    w = 0
                return w

        def _empty_node(type_, name):
            """Make an empty node.
            """
            return {
                'types'  : set([type_]),
                'name'   : name,
                'edges'  : {},
                'weight' : 0
            }

        def _empty_edge(ori_id, des_id):
            """Make an empty edge.
            """
            return {
                'from'   : ori_id,
                'to'     : des_id,
                'weight' : 0
            }

        nodes = {}
        nb_edges = len(graph_fields) - 1

        for key in from_keys:
            # We stringify values here because json requires string as keys
            values = tuple(str(self.get(key, f)) for f in graph_fields)
            weight = get_weight(key)

            for i in xrange(nb_edges):
                ori_type = graph_fields[i]
                des_type = graph_fields[i + 1]
                ori_val  = values[i]
                des_val  = values[i + 1]

                if with_types:
                    # We include the type in the key
                    ## We do not use tuples because json requires string as keys
                    ## This workaround may produce bugs if values look like types
                    #TODO: find a way to use tuples
                    ori_id = '%s/%s' % (ori_type, ori_val)
                    des_id = '%s/%s' % (des_type, des_val)
                else:
                    # Here the key is just the value, no type
                    ori_id = ori_val
                    des_id = des_val

                # Adding nodes if do not exist already
                if ori_id not in nodes:
                    nodes[ori_id] = _empty_node(ori_type, ori_val)

                if des_id not in nodes:
                    nodes[des_id] = _empty_node(des_type, des_val)

                # Updating types and weight
                ori_node = nodes[ori_id]
                des_node = nodes[des_id]
                ori_node['types'].add(ori_type)
                des_node['types'].add(des_type)
                ori_node['weight'] += weight
                des_node['weight'] += weight

                # Updating edges
                edge_id = '%s-%s' % (ori_id, des_id)

                if edge_id not in ori_node['edges']:
                    ori_node['edges'][edge_id] = _empty_edge(ori_id, des_id)

                edge = ori_node['edges'][edge_id]
                edge['weight'] += weight

                if not directed:
                    # If not directed we create the "mirror" edge
                    edge_id = '%s-%s' % (des_id, ori_id)

                    if edge_id not in des_node['edges']:
                        des_node['edges'][edge_id] = _empty_edge(des_id, ori_id)

                    edge = des_node['edges'][edge_id]
                    edge['weight'] += weight


            # In this case we did not iterate through the previous loop
            # Note that if graph_fields is [], nb_edges is -1 so
            # we do not go here either
            if nb_edges == 0:
                _type = graph_fields[0]
                _val  = values[0]

                if with_types:
                    _id = '%s/%s' % (_type, _val)
                else:
                    _id = _val

                if _id not in nodes:
                    nodes[_id] = _empty_node(_type, _val)

                _node = nodes[_id]
                _node['types'].add(_type)
                _node['weight'] += weight

        # Getting rid of sets because not JSON serializable
        # And fixing order with sorted to make sure
        # we do not get different colors in frontend
        for node in nodes.itervalues():
            node['types'] = sorted(node['types'])

        return nodes



    def graphVisualize(self,
                       graph_fields,
                       graph_weight=None,
                       with_types=False,
                       from_keys=None,
                       output=DEFAULT_TMP_NAME,
                       output_dir=DEFAULT_TMP_DIR,
                       verbose=True):
        """Graph display (like force directed graph).

        :param graph_fields: iterable of fields used to define the nodes. \
                Nodes are the values of these fields. Edges represent the \
                data.
        :param graph_weight: field used to define the weight of nodes and \
                edges. If ``None``, the weight is ``1`` for each key.
        :param with_types:  boolean to consider values from different fields \
                of the same "type" or not, meaning we will create only one \
                node if the same value is found accross different fields, if \
                there are no types. Otherwise we create different nodes. \
                Default is ``False``, meaning untyped graphs.
        :param from_keys:   only display this iterable of keys if not ``None``
        :param output:      set the name of the rendered files
        :param output_dir:  set the directory of the rendered files, will \
                be created if it does not exist
        :param verbose:     toggle verbosity
        :returns:           this is the tuple of (names of templates \
                rendered, (list of html templates, list of static files))
        """
        graph_fields = tuplify(graph_fields)

        nodes = self.buildGraphData(graph_fields=graph_fields,
                                    graph_weight=graph_weight,
                                    with_types=with_types,
                                    directed=False,
                                    from_keys=from_keys)

        # Handle output directory
        if not output_dir:
            output_dir = '.'
        elif not op.isdir(output_dir):
            os.makedirs(output_dir)

        # Dump the json geocodes
        json_name = '%s_graph.json' % op.join(output_dir, output)

        with open(json_name, 'w') as out:
            out.write(json.dumps({
                'nodes' : nodes,
                'meta'  : {
                    'graph_fields' : graph_fields,
                    'graph_weight' : graph_weight,
                    'with_types'   : with_types,
                },
            }))

        return ['graph'], render_templates(['graph'], output, output_dir, json_name, verbose=verbose)



    def _buildDashboardCounters(self, keep, get_weight, keys):
        """Dashboard counters.
        """
        # Main structure, dict: field -> data
        counters = {}

        # We are going to count everything for normal fields
        # So we exclude splitted and special fields
        for field in self.fields:
            if not self._isFieldNormal(field):
                continue

            counters[field] = defaultdict(int)

            for key in keys:
                counters[field][self.get(key, field)] += get_weight(key)

        # Computing general information
        sum_info = {}

        for field in counters:
            sum_info[field] = sum(counters[field].itervalues())

        # Now we sort and keep the most important
        for field in counters:
            counters[field] = sorted(counters[field].iteritems(),
                                     key=itemgetter(1),
                                     reverse=True)

            # Tail information
            if len(counters[field]) > keep:
                head = counters[field][:keep]
                tail = counters[field][keep:]

                counters[field] = head + [('others', sum(v for k, v in tail))]

        return counters, sum_info



    def _detectFieldsTypes(self, threshold=0.99, from_keys=None):
        """Detect numeric fields.
        """
        if from_keys is None:
            from_keys = iter(self)

        # This might be iterated over several times
        from_keys = list(from_keys)

        numeric_fields = []
        datetime_fields = []

        for field in self.fields:
            if not self._isFieldNormal(field):
                continue

            counter = {
                'numeric' : 0,
                'datetime': 0,
                'total'   : 0,
            }

            for key in from_keys:
                if not self.get(key, field):
                    # Empty values are not counted
                    continue

                counter['total'] += 1

                try:
                    float(self.get(key, field))
                except (ValueError, TypeError):
                    # TypeError when input type was not string or float/int
                    # ValueError for failing to convert
                    pass
                else:
                    counter['numeric'] += 1

                d = _parse_date(self.get(key, field))
                if d is not None:
                    counter['datetime'] += 1

            # We make sure we have actual data
            if counter['total'] > 0:
                if counter['numeric'] >= threshold * counter['total']:
                    numeric_fields.append(field)

                if counter['datetime'] >= threshold * counter['total']:
                    datetime_fields.append(field)

        # We do not want to plot densities for datetime fields
        numeric_fields = [f for f in numeric_fields if f not in datetime_fields]

        return numeric_fields, datetime_fields


    def _buildDashboardDensity(self, field, get_weight, keys):
        """Build dashboard density for a numeric field.
        """
        values = []

        for key in keys:
            try:
                v = float(self.get(key, field))
            except (ValueError, TypeError):
                # TypeError when input type was not even string of float/int
                # ValueError for failing to convert
                continue
            else:
                values.append((v, get_weight(key)))

        return _build_density(values)


    def _buildDashboardTimeSeries(self, field, get_weight, keys):
        """Build dashboard density for a numeric field.
        """
        values = []

        for key in keys:
            d = _parse_date(self.get(key, field))
            if d is not None:
                values.append((d, get_weight(key)))

        return _aggregate_datetimes(values)


    def buildDashboardData(self, keep=10, dashboard_weight=None, from_keys=None):
        """Build dashboard data.

        :param keep:   the number of values kept after counting for \
                each field
        :param dashboard_weight: the field used as weight for the graph. Leave \
                ``None`` if you just want to count the number of keys
        :param from_keys: only use this iterable of keys if not ``None``
        :returns: a dictionary of fields counters information
        """
        # Arguments testing
        if dashboard_weight is not None and dashboard_weight not in self.fields:
            raise ValueError('weight "%s" not in fields %s.' % (dashboard_weight, self.fields))

        # Defining get_weight lambda function
        if dashboard_weight is None:
            get_weight = lambda key: 1
        else:
            def get_weight(key):
                """Custom weight computation."""
                try:
                    w = float(self.get(key, dashboard_weight))
                except (ValueError, TypeError):
                    w = 0
                return w

        if from_keys is None:
            from_keys = iter(self)

        # Since we are going to loop several times over it, we list()
        from_keys = list(from_keys)

        # Computing counters and sum_info for bar charts
        counters, sum_info = self._buildDashboardCounters(keep, get_weight, from_keys)

        # Sniffing fields
        numeric_fields, datetime_fields = self._detectFieldsTypes(from_keys=from_keys)

        # Computing densities
        densities = {}
        for field in numeric_fields:
            densities[field] = self._buildDashboardDensity(field, get_weight, from_keys)

        time_series = {}
        for field in datetime_fields:
            time_series[field] = self._buildDashboardTimeSeries(field, get_weight, from_keys)

        return counters, sum_info, densities, time_series



    def dashboardVisualize(self,
                           output=DEFAULT_TMP_NAME,
                           output_dir=DEFAULT_TMP_DIR,
                           keep=10,
                           dashboard_weight=None,
                           from_keys=None,
                           verbose=True):
        """Dashboard display (aggregated view).

        :param output:      set the name of the rendered files
        :param output_dir:  set the directory of the rendered files, will \
                be created if it does not exist
        :param keep:        the number of values kept after counting for \
                each field
        :param dashboard_weight: the field used as weight for the graph. Leave \
                ``None`` if you just want to count the number of keys
        :param from_keys:   only display this iterable of keys if not ``None``
        :param verbose:     toggle verbosity
        :returns:           this is the tuple of (names of templates \
                rendered, (list of html templates, list of static files))
        """
        # Handle output directory
        if not output_dir:
            output_dir = '.'
        elif not op.isdir(output_dir):
            os.makedirs(output_dir)

        dashboard_data = self.buildDashboardData(keep=keep,
                                                 dashboard_weight=dashboard_weight,
                                                 from_keys=from_keys)

        counters, sum_info, densities, time_series = dashboard_data

        # Dump the json geocodes
        json_name = '%s_dashboard.json' % op.join(output_dir, output)

        with open(json_name, 'w') as out:
            out.write(json.dumps({
                'counters'   : counters,
                'sum_info'   : sum_info,
                'densities'  : densities,
                'time_series': time_series,
                'weight'     : dashboard_weight,
                'keep'       : keep,
            }))

        return ['dashboard'], render_templates(['dashboard'],
                                               output,
                                               output_dir,
                                               json_name,
                                               verbose=verbose)


    def visualize(self,
                  output=DEFAULT_TMP_NAME,
                  output_dir=DEFAULT_TMP_DIR,
                  icon_label=None,
                  icon_weight=None,
                  icon_color=None,
                  icon_type='auto',
                  from_keys=None,
                  add_lines=None,
                  add_anonymous_icons=None,
                  add_anonymous_lines=None,
                  link_duplicates=True,
                  draw_join_fields=True,
                  catalog=None,
                  line_colors=None,
                  use_3D=False,
                  verbose=True,
                  warnings=False):
        """Map and table display.

        :param output:      set the name of the rendered files
        :param output_dir:  set the directory of the rendered files, will \
                be created if it does not exist
        :param icon_label:  set the field which will appear as map icons title
        :param icon_weight: set the field defining the map icons circle \
                surface
        :param icon_color:  set the field defining the map icons colors
        :param icon_type:   set the icon size, either ``'B'``, ``'S'``, \
                ``'auto'`` or ``None`` for no-icons mode
        :param from_keys:   only display this iterable of keys if not ``None``
        :param add_lines:   list of ``(key1, key2, ..., keyN)`` to draw \
                additional lines
        :param add_anonymous_icons: list of geocodes, like \
                ``[(lat1, lng1), (lat2, lng2), ..., (latN, lngN)]``, \
                to draw additional icons from geocodes not in the data
        :param add_anonymous_icons: list of list of geocodes, like \
                ``[[(lat1, lng1), (lat2, lng2), ..., (latN, lngN)], ...]``,  \
                to draw additional lines from geocodes not in the data
        :param link_duplicates: boolean toggling lines between duplicated \
                keys, default ``True``
        :param draw_join_fields: boolean toggling drawing of join fields \
                containing geocode information, default ``True``
        :param catalog:     dictionary of ``{'value': 'color'}`` to have \
                specific colors for some categories, which is computed with \
                the ``icon_color`` field
        :param line_colors: tuple of 4 colors to change the default lines \
                color, the three values are for the three line types: those \
                computed with ``link_duplicates``, those given with \
                ``add_lines``, those given with ``add_anonymous_lines``, \
                those computed with ``draw_join_fields``
        :param use_3D:      toggle 3D visualizations
        :param verbose:     toggle verbosity
        :param warnings:    toggle warnings, even more verbose
        :returns:           this is the tuple of (names of templates \
                rendered, (list of html templates, list of static files))
        """
        if not self.hasGeoSupport():
            if verbose:
                print
                print '/!\ Could not find geographical fields in headers %s.' % self.fields
                print '/!\ Setting draw_join_fields to True.'

            draw_join_fields = True

        if icon_label is not None and icon_label not in self.fields:
            raise ValueError('icon_label "%s" not in fields %s.' % (icon_label, self.fields))

        if icon_weight is not None and icon_weight not in self.fields:
            raise ValueError('icon_weight "%s" not in fields %s.' % (icon_weight, self.fields))

        if icon_color is not None and icon_color not in self.fields:
            raise ValueError('icon_color "%s" not in fields %s.' % (icon_color, self.fields))

        # Optional function which gives points weight
        if icon_label is None:
            get_label = lambda key: key
        else:
            get_label = lambda key: str(self.get(key, icon_label))

        # Optional function which gives points weight
        if icon_weight is None:
            get_weight = lambda key: 1
        else:
            def get_weight(key):
                """Custom weight computation."""
                try:
                    w = float(self.get(key, icon_weight))
                except (ValueError, TypeError):
                    w = 0
                return w


        # Optional function which gives points category
        if icon_color is None:
            get_category = lambda key: None
        else:
            get_category = lambda key: self.get(key, icon_color)

        # from_keys lets you have a set of keys to visualize
        if from_keys is None:
            from_keys = iter(self)

        # Additional stuff
        if add_lines is None:
            add_lines = []

        if add_anonymous_icons is None:
            add_anonymous_icons = []

        if add_anonymous_lines is None:
            add_anonymous_lines = []

        # catalog is a user defined color scheme
        if catalog is None:
            # Default diff-friendly catalog
            catalog = {
                ' ' : 'blue',
                '+' : 'green',
                'Y' : 'green',
                '-' : 'red',
                'N' : 'red',
                '@' : 'yellow',
            }

        # line colors
        def_line_colors = 'blue', 'orange', 'yellow', 'purple'

        if line_colors is None:
            line_colors = def_line_colors

        if len(line_colors) != len(def_line_colors):
            raise ValueError('line_colors must a tuple of %s colors, was %s.' % \
                             (len(def_line_colors), str(line_colors)))

        # Storing json data
        data = [
            self._buildIconData(key, get_label, get_weight, get_category)
            for key in from_keys if key in self
        ] + [
            self._buildAnonymousIconData(lat_lng)
            for lat_lng in add_anonymous_icons
        ]


        # Duplicates data
        dup_lines = []
        if link_duplicates:
            dup_lines = self._buildLinksForDuplicates(data)
            if verbose:
                print '* Added lines for duplicates linking, total %s' % len(dup_lines)


        # Join data
        join_icons, join_lines = [], []

        if draw_join_fields:
            # Finding out which external base has geocode support
            # We start goin over the self.fields to preserve fields order
            # then we look for potential join on multiple fields
            # in self._join.keys()
            geo_join_fields_list = []

            for fields in self.fields + self._join.keys():
                fields = tuplify(fields)

                if fields in geo_join_fields_list:
                    continue

                if self.hasJoin(fields):
                    if self.getJoinBase(fields).hasGeoSupport():
                        geo_join_fields_list.append(fields)

                        if verbose:
                            print '* Detected geocode support in join fields %s [%s].' % \
                                    (str(fields), str(self._join[fields]))


            if not geo_join_fields_list:
                if verbose:
                    print '* Could not detect geocode support in join fields.'

            else:
                join_icons, join_lines = self._buildJoinLinesData(geo_join_fields_list,
                                                                  data,
                                                                  'Joined',
                                                                  line_colors[3],
                                                                  get_label,
                                                                  verbose=warnings)
                if verbose:
                    print '* Added icons for join fields, total %s' % len(join_icons)
                    print '* Added lines for join fields, total %s' % len(join_lines)

        # Adding join icons on already computed data
        data = data + join_icons

        # Gathering data for lines
        data_lines = [
            self._buildLineData(l, get_label, 'Duplicates', line_colors[0])
            for l in dup_lines
        ] + [
            self._buildLineData(l, get_label, 'Line', line_colors[1])
            for l in add_lines
        ] + [
            self._buildAnonymousLineData(l, 'Anonymous line', line_colors[2])
            for l in add_anonymous_lines
        ] + \
            join_lines

        # Icon type
        has_many  = len(data) >= 100
        base_icon = compute_base_icon(icon_type, has_many)

        # Building categories
        with_icons   = icon_type is not None
        with_circles = icon_weight is not None
        categories   = build_categories(data, with_icons, with_circles, catalog, verbose=verbose)

        # Finally, we write the colors as an element attribute
        for elem in data:
            elem['__col__'] = categories[elem['__cat__']]['color']

        # Handle output directory
        if not output_dir:
            output_dir = '.'
        elif not op.isdir(output_dir):
            os.makedirs(output_dir)

        # Dump the json geocodes
        json_name = '%s_map.json' % op.join(output_dir, output)

        with open(json_name, 'w') as out:
            out.write(json.dumps({
                'meta' : {
                    'icon_label'      : icon_label,
                    'icon_weight'     : icon_weight,
                    'icon_color'      : icon_color,
                    'icon_type'       : icon_type,
                    'base_icon'       : base_icon,
                    'link_duplicates' : link_duplicates,
                    'toggle_lines'    : True if (add_lines or \
                                                 add_anonymous_lines or \
                                                 not self.hasGeoSupport()) else False,
                },
                'points'     : data,
                'lines'      : data_lines,
                'categories' : sorted(categories.items(),
                                      key=lambda x: x[1]['volume'],
                                      reverse=True)
            }))

        # We do not render the map template if nothing to see
        nb_geocoded_points = 0
        for elem in data:
            if (elem['lat'], elem['lng']) != ('?', '?'):
                nb_geocoded_points += 1

        if nb_geocoded_points > 0 or data_lines:
            if use_3D:
                rendered = ['map', 'globe', 'table']
            else:
                rendered = ['map', 'table']
        else:
            rendered = ['table']

        return rendered, render_templates(rendered, output, output_dir, json_name, verbose=verbose)



    def _buildIconData(self, key, get_label, get_weight, get_category):
        """Build data for key display.
        """
        lat_lng = self.getLocation(key)

        if lat_lng is None:
            lat_lng = '?', '?'

        elem = {
            '__key__' : key,
            '__lab__' : get_label(key),
            '__wei__' : get_weight(key),
            '__cat__' : get_category(key),
            '__hid__' : False,
            'lat'     : lat_lng[0],
            'lng'     : lat_lng[1]
        }

        for field in self.fields:
            # Keeping only important fields
            if self._isFieldNormal(field) and field not in elem:
                elem[field] = str(self.get(key, field))

        return elem


    @staticmethod
    def _buildAnonymousIconData(lat_lng):
        """Build data for anonymous point display.
        """
        if lat_lng is None:
            lat_lng = '?', '?'

        return {
            '__key__' : '(%s, %s)' % lat_lng,
            '__lab__' : 'Anonymous',
            '__wei__' : 0,
            '__cat__' : '@',
            '__hid__' : False,
            'lat'     : lat_lng[0],
            'lng'     : lat_lng[1]
        }


    def _buildLineData(self, line, get_label, title, color):
        """Build data for line display.
        """
        data_line = []

        for l_key in line:

            if l_key not in self:
                continue

            lat_lng = self.getLocation(l_key)

            if lat_lng is None:
                lat_lng = '?', '?'

            data_line.append({
                '__key__' : l_key,
                '__lab__' : get_label(l_key),
                'lat'     : lat_lng[0],
                'lng'     : lat_lng[1],
            })

        return {
            '__lab__' : title,
            '__col__' : color,
            'path'    : data_line,
        }


    @staticmethod
    def _buildAnonymousLineData(line, title, color):
        """Build data for anonymous line display.
        """
        data_line = []

        for lat_lng in line:
            if lat_lng is None:
                lat_lng = '?', '?'

            data_line.append({
                '__key__' : '(%s, %s)' % lat_lng,
                '__lab__' : 'Anonymous',
                'lat'     : lat_lng[0],
                'lng'     : lat_lng[1],
            })

        return {
            '__lab__' : title,
            '__col__' : color,
            'path'    : data_line,
        }


    def _buildLinksForDuplicates(self, data):
        """Build lines data between duplicated keys.
        """
        dup_lines = []
        # We add to dup_lines all list of duplicates
        # We keep a set of already processed "master" keys to avoid
        # putting several identical lists in the json
        done_keys = set()

        for elem in data:
            key = elem['__key__']

            if key not in self:
                # Possible for anonymous keys added for display
                continue

            if not self.hasParents(key):
                mkey = set([key])
            else:
                mkey = set(self.get(key, '__par__'))

            if self.hasDuplicates(key) and not mkey.issubset(done_keys):
                # mkey have some keys which are not in done_keys
                dup_lines.append(self.getFromAllDuplicates(key, '__key__'))
                done_keys = done_keys | mkey

        return dup_lines


    def _buildJoinLinesData(self, geo_join_fields_list, data, title, line_color, get_label, verbose=True):
        """Build lines data for join fields
        """
        # Precaution on fields type
        geo_join_fields_list = [
            tuplify(fields) for fields in geo_join_fields_list
        ]

        join_lines = []
        join_icons = {}

        for elem in data:
            key = elem['__key__']
            key_lat_lng = self.getLocation(key)

            if key not in self:
                # Possible for anonymous keys added for display
                continue

            joined_values = [
                self.get(key, fields, ext_field='__key__')
                for fields in geo_join_fields_list
            ]

            # Cartesian product is made on non-empty join results
            if verbose:
                for v, fields in zip(joined_values, geo_join_fields_list):
                    if not v:
                        values = [str(self.get(key, f)) for f in fields]
                        print 'Could not retrieve data from join on "%s" for "%s", key "%s".' % \
                                ('/'.join(fields), '/'.join(values), key)

            comb = product(*[v for v in joined_values if v])

            for c in comb:
                #print c
                if not c:
                    # Case where there is no fields in self._join
                    continue

                data_line = []

                if key_lat_lng is not None:
                    # We add the geocode at the beginning of the line
                    data_line.append({
                        '__key__' : key,
                        '__lab__' : get_label(key),
                        'lat'     : key_lat_lng[0],
                        'lng'     : key_lat_lng[1],
                    })

                for jkeys, fields in zip(c, geo_join_fields_list):

                    # Is a tuple if we had some subdelimiters
                    jkeys = tuplify(jkeys)

                    for jkey in jkeys:

                        lat_lng = self.getJoinBase(fields).getLocation(jkey)

                        if lat_lng is None:
                            lat_lng = '?', '?'

                        values = [str(self.get(key, f)) for f in fields]

                        if jkey not in join_icons:
                            # joined icons do not inherit color and size
                            join_icons[jkey] = {
                                '__key__' : jkey,
                                '__lab__' : '%-6s [line %s, join on field(s) %s for value(s) %s]' % \
                                        (jkey, key, '/'.join(fields), '/'.join(values)),
                                '__wei__' : 0,
                                '__cat__' : None,
                                '__hid__' : True,
                                'lat'     : lat_lng[0],
                                'lng'     : lat_lng[1]
                            }

                            for ext_f in self.getJoinBase(fields).fields:
                                # Keeping only important fields
                                if self._isFieldNormal(ext_f) and ext_f not in join_icons[jkey]:
                                    join_icons[jkey][ext_f] = str(self.getJoinBase(fields).get(jkey, ext_f))


                        data_line.append({
                            '__key__' : jkey,
                            '__lab__' : '%-6s [line %s, join on field(s) %s for value(s) %s]' % \
                                    (jkey, key, '/'.join(fields), '/'.join(values)),
                            'lat'     : lat_lng[0],
                            'lng'     : lat_lng[1],
                        })

                join_lines.append({
                    '__lab__' : title,
                    '__col__' : line_color,
                    'path'    : data_line,
                })

        return join_icons.values(), join_lines




def compute_base_icon(icon_type, has_many):
    """Compute icon.
    """
    if icon_type is None:
        return ''

    if icon_type == 'auto':
        return 'point.png' if has_many else 'marker.png'

    if icon_type == 'S':
        return 'point.png'

    if icon_type == 'B':
        return 'marker.png'

    raise ValueError('icon_type "%s" not in %s.' % \
                     (icon_type, ('auto', 'S', 'B', None)))


def build_categories(data, with_icons, with_circles, catalog, verbose=True):
    """Build categories from data and catalog
    """
    # Count the categories for coloring
    categories = {}

    for elem in data:
        if not with_icons:
            # Here we are in no-icon mode, categories
            # will be based on the entries who will have a circle
            try:
                c = float(elem['__wei__'])
            except ValueError:
                c = 0
        else:
            c = 1

        cat = elem['__cat__']
        if cat not in categories:
            categories[cat] = 0
        if c > 0:
            categories[cat] += c

    # Color repartition given biggest categories
    colors  = ('red', 'orange', 'yellow', 'green', 'cyan', 'purple')
    col_num = 0

    if not categories:
        step = 1
    else:
        # c > 0 makes sure we do not create a category
        # for stuff that will not be displayed
        nb_non_empty_cat = len([c for c in categories.values() if c > 0])

        if nb_non_empty_cat > 0:
            step = max(1, len(colors) / nb_non_empty_cat)
        else:
            # All categories may be empty if not icons + not circles
            step = 1

    for cat, vol in sorted(categories.items(), key=itemgetter(1), reverse=True):
        categories[cat] = {
            'volume' : vol
        }
        if cat is None:
            # None is also the default category, when icon_color is None
            categories[cat]['color'] = 'blue'

        elif col_num < len(colors):
            # We affect the next color available
            categories[cat]['color'] = colors[col_num]
            col_num += step
        else:
            # After all colors are used, remaining categories are black
            categories[cat]['color'] = 'black'

        if verbose:
            if with_icons:
                field_vol = 'volume'
            elif with_circles:
                field_vol = 'weight'
            else:
                field_vol = '(not used)'

            print '> Affecting category %-8s to color %-7s | %s %s' % \
                    (cat, categories[cat]['color'], field_vol, vol)


    for cat in catalog:
        if cat in categories:

            old_color = categories[cat]['color']
            new_color = catalog[cat]
            categories[cat]['color'] = new_color

            if verbose:
                print '> Overrides category %-8s to color %-7s (from %-7s)' % \
                        (cat, new_color, old_color)

            # We test other categories to avoid duplicates in coloring
            for ocat in categories:
                if ocat == cat:
                    continue
                ocat_color = categories[ocat]['color']

                if ocat_color == new_color:
                    categories[ocat]['color'] = old_color

                    if verbose:
                        print '> Switching category %-8s to color %-7s (from %-7s)' % \
                                (ocat, old_color, ocat_color)

    return categories


# Assets for map and table
ASSETS = {
    'map' : {
        'template' : {
            # source : v_target
            relative('MapAssets/template.html') : '%s_map.html',
        },
        'static' : {
            # source : target
            relative('MapAssets/map.js')            : 'map.js',
            relative('MapAssets/point.png')         : 'point.png',
            relative('MapAssets/marker.png')        : 'marker.png',
            relative('MapAssets/red_point.png')     : 'red_point.png',
            relative('MapAssets/red_marker.png')    : 'red_marker.png',
            relative('MapAssets/orange_point.png')  : 'orange_point.png',
            relative('MapAssets/orange_marker.png') : 'orange_marker.png',
            relative('MapAssets/yellow_point.png')  : 'yellow_point.png',
            relative('MapAssets/yellow_marker.png') : 'yellow_marker.png',
            relative('MapAssets/green_point.png')   : 'green_point.png',
            relative('MapAssets/green_marker.png')  : 'green_marker.png',
            relative('MapAssets/cyan_point.png')    : 'cyan_point.png',
            relative('MapAssets/cyan_marker.png')   : 'cyan_marker.png',
            relative('MapAssets/blue_point.png')    : 'blue_point.png',
            relative('MapAssets/blue_marker.png')   : 'blue_marker.png',
            relative('MapAssets/purple_point.png')  : 'purple_point.png',
            relative('MapAssets/purple_marker.png') : 'purple_marker.png',
            relative('MapAssets/black_point.png')   : 'black_point.png',
            relative('MapAssets/black_marker.png')  : 'black_marker.png',
        }
    },
    'globe' : {
        'template' : {
            # source : v_target
            relative('GlobeAssets/template.html') : '%s_globe.html',
        },
        'static' : {
            # source : target
            relative('GlobeAssets/globe.js')       : 'globe.js',
            relative('GlobeAssets/Detector.js')    : 'Detector.js',
            relative('GlobeAssets/RequestAF.js')   : 'RequestAF.js',
            relative('GlobeAssets/ThreeExtras.js') : 'ThreeExtras.js',
            relative('GlobeAssets/ThreeWebGL.js')  : 'ThreeWebGL.js',
            relative('GlobeAssets/Tween.js')       : 'Tween.js',
            relative('GlobeAssets/loading.gif')    : 'loading.gif',
            relative('GlobeAssets/world.jpg')      : 'world.jpg',
        }
    },
    'table' : {
        'template' : {
            # source : v_target
            relative('TableAssets/template.html') : '%s_table.html',
        },
        'static' : {
            # source : target
            relative('TableAssets/table.js') : 'table.js',
        }
    },
    'graph' : {
        'template' : {
            # source : v_target
            relative('GraphAssets/template.html') : '%s_graph.html',
        },
        'static' : {
            # source : target
            relative('GraphAssets/graph.js')  : 'graph.js',
            relative('GraphAssets/jit-yc.js') : 'jit-yc.js',
        }
    },
    'dashboard' : {
        'template' : {
            # source : v_target
            relative('DashboardAssets/template.html') : '%s_dashboard.html',
        },
        'static' : {
            # source : target
            relative('DashboardAssets/dashboard.js') : 'dashboard.js',
            relative('DashboardAssets/nv.d3.min.js') : 'nv.d3.min.js',
            relative('DashboardAssets/nv.d3.css') : 'nv.d3.css',
        }
    }
}



def render_templates(names, output, output_dir, json_name, verbose):
    """Render HTML templates.
    """
    tmp_template = []
    tmp_static   = [json_name]

    for name in names:
        if name not in ASSETS:
            raise ValueError('Unknown asset name "%s".' % name)

        assets = ASSETS[name]

        for template, v_target in assets['template'].iteritems():
            target = op.join(output_dir, v_target % output)

            with open(template) as temp:
                with open(target, 'w') as out:
                    for row in temp:
                        row = row.replace('{{file_name}}', output)
                        row = row.replace('{{json_file}}', op.basename(json_name))
                        out.write(row)

            tmp_template.append(target)

        for source, target in assets['static'].iteritems():
            target = op.join(output_dir, target)
            copy(source, target)
            tmp_static.append(target)

    if verbose:
        print
        print '* Now you may use your browser to visualize:'
        print ' '.join(tmp_template)
        print
        print '* If you want to clean the temporary files:'
        print 'rm %s' % ' '.join(tmp_static + tmp_template)
        print

    return tmp_template, tmp_static



def tuplify(s):
    """
    Convert iterable into tuple,
    if string just put in in a tuple.

    >>> tuplify('test')
    ('test',)
    >>> tuplify(['test', 'titi'])
    ('test', 'titi')
    """
    if isinstance(s, str):
        return (s,)
    else:
        return tuple(s)



def _build_density(values, bins=None):
    """Build density from a list of (values, weight).
    """
    if bins is None:
        # Excel heuristic :)
        bins = int(math.sqrt(len(values)))

    if not values:
        return {
            'density'   : [],
            'nb_values' : 0,
            'step'      : None
        }

    values  = sorted(values)
    min_val = min(values)[0]
    max_val = max(values)[0]

    if bins > 0:
        step = float(max_val - min_val) / bins
    else:
        # In this case step will never be used
        step = 1

    counter = defaultdict(int)
    upper = min_val
    i = 0

    while i < len(values):
        v, w = values[i]
        if v <= upper:
            counter[upper] += w
            i += 1
        else:
            upper += step
            counter[upper] = 0

    return {
        'density'   : sorted(counter.iteritems(), key=itemgetter(0)),
        'nb_values' : sum(w for _, w in values),
        'step'      : step
    }



def _parse_date(value):
    """Fast date parsing.

    >>> _parse_date('2012')
    datetime.datetime(2012, 1, 1, 0, 0)
    >>> _parse_date('2012/01/01')
    datetime.datetime(2012, 1, 1, 0, 0)
    >>> _parse_date('2012/01/01 08:40:10')
    datetime.datetime(2012, 1, 1, 8, 40, 10)
    >>> _parse_date('not_a_date') # None
    >>> _parse_date([]) # None
    """
    def _clean(s, excluded):
        """Remove characters from a string.
        """
        return ''.join(l for l in list(s) if l not in excluded)

    def _scan_int(s, **kwargs):
        """Scan integer, with default value if empty string.
        """
        if not s and 'default' in kwargs:
            return kwargs['default']
        return int(s)

    s = _clean(str(value).strip(), set([' ', '/', '-', ':']))
    try:
        hours   = _scan_int(s[8:10],  default=0)
        minutes = _scan_int(s[10:12], default=0)
        seconds = _scan_int(s[12:14], default=0)

        days   = _scan_int(s[6:8], default=1)
        months = _scan_int(s[4:6], default=1)
        years  = _scan_int(s[0:4])

        # This test prevents failure when using strftime later
        # This also avoid detecting numeric columns as time series
        if years < 1900:
            raise ValueError()
        if years > 2099:
            raise ValueError()

        d = datetime(years, months, days, hours, minutes, seconds)
    except (ValueError, TypeError):
        # This may be raised by int() or datetime()
        d = None
    return d



def _guess_time_aggregation(gap_seconds):
    """Compute time aggregation function.
    """
    # Typical durations in seconds
    durations = [
        ('year',   31556926),
        ('month',  60 * 60 * 24 * 31),
        ('day',    60 * 60 * 24),
        ('hour',   60 * 60),
        ('minute', 60),
        ('second', 1),
    ]

    aggregators = {
        'year'   : lambda d: datetime(d.year, 1, 1, 0, 0, 0),
        'month'  : lambda d: datetime(d.year, d.month, 1, 0, 0, 0),
        'day'    : lambda d: datetime(d.year, d.month, d.day, 0, 0, 0),
        'hour'   : lambda d: datetime(d.year, d.month, d.day, d.hour, 0, 0),
        'minute' : lambda d: datetime(d.year, d.month, d.day, d.hour, d.minute, 0),
        'second' : lambda d: d,
    }

    # Magic number
    r = 2.5

    # The aggregation is made by year, month, day, ...
    for name, duration in durations:
        if gap_seconds >= r * duration:
            return name, aggregators[name]
    return None, lambda d: d



def _gen_inter_datetimes(d_min, d_max, agg_level):
    """Generate all datetimes between two datetimes and an aggregation level.

    >>> d_min = datetime(2012, 12, 31)
    >>> d_max = datetime(2013,  1,  1)
    >>> list(_gen_inter_datetimes(d_min, d_max, 'day'))
    [datetime.datetime(2012, 12, 31, 0, 0), datetime.datetime(2013, 1, 1, 0, 0)]

    >>> d_min = datetime(2012, 6, 1)
    >>> d_max = datetime(2013, 1, 1)
    >>> list(_gen_inter_datetimes(d_min, d_max, 'year'))
    [datetime.datetime(2012, 6, 1, 0, 0), datetime.datetime(2013, 1, 1, 0, 0)]
    """
    if agg_level is None:
        # not aggregated
        raise StopIteration

    agg_level = '%ss' % agg_level # adding "s" for relativedelta

    # This is blowing your mind
    delta = relativedelta(**{ agg_level : 1 })
    start = d_min

    while start < d_max:
        yield start
        start += delta
    yield d_max



def _aggregate_datetimes(values):
    """Aggregate datetime objects.
    """
    if not values:
        return {
            'time_series' : [],
            'nb_values'   : 0,
            'agg_level'   : None
        }

    def _total_seconds(td):
        """Timedelta total_seconds() implementation.
        """
        return (td.microseconds + \
               (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)

    values = sorted(values)
    d_min  = min(values)[0]
    d_max  = max(values)[0]

    # (d_max - d_min) is a timedelta object
    # with Python >= 2.7, use .total_seconds()
    gap_seconds = _total_seconds(d_max - d_min)
    agg_level, aggregate = _guess_time_aggregation(gap_seconds)

    # Computing counter with 0 value for each period
    counter = defaultdict(int)
    for d in _gen_inter_datetimes(aggregate(d_min), aggregate(d_max), agg_level):
        counter[aggregate(d)] = 0

    for d, w in values:
        counter[aggregate(d)] += w

    # Convert dict to list, then stringify datetimes
    counter = sorted(counter.iteritems(), key=itemgetter(0))

    # Output datetime format
    dt_format = '%Y-%m-%d %H:%M:%S'
    for i, (d, w) in enumerate(counter):
        counter[i] = d.strftime(dt_format), w

    return {
        'time_series' : counter,
        'nb_values'   : sum(w for _, w in values),
        'agg_level'   : agg_level
    }



def _test():
    """When called directly, launching doctests.
    """
    import doctest
    from .GeoBaseModule import GeoBase

    extraglobs = {
        'g' : GeoBase(data='ori_por',  verbose=False),
    }

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE)
            #doctest.REPORT_ONLY_FIRST_FAILURE)
            #doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()

