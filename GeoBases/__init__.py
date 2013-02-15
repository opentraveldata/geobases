#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This is the GeoBase module.
'''

# Extracting from GeoBaseModule
from .GeoBaseModule import GeoBase, SOURCES, SOURCES_CONF_PATH, SOURCES_DIR

# We only export the main class
__all__ = ['GeoBase', 'SOURCES', 'SOURCES_CONF_PATH', 'SOURCES_DIR']
