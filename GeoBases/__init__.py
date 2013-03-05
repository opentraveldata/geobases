#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This is the GeoBase module.
'''

# Extracting from GeoBaseModule
from .GeoBaseModule        import GeoBase, DEFAULTS
from .SourcesManagerModule import SourcesManager, is_remote, is_archive

# We only export the main class
__all__ = ['GeoBase', 'DEFAULTS', 'SourcesManager', 'is_remote', 'is_archive']
