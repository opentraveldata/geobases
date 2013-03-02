#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This is the GeoBase module.
'''

# Extracting from GeoBaseModule
from .GeoBaseModule         import GeoBase
from .SourcesManagerModule import SourcesManager

# We only export the main class
__all__ = ['GeoBase', 'SourcesManager']
