# Purpose: handle tables section
# Created: 21.07.2012, taken from my ezdxf project
# Copyright (C) 2012, Manfred Moitzi
# License: MIT License
from __future__ import absolute_import
from __future__ import unicode_literals
__author__ = "mozman <mozman@gmx.at>"

from .defaultchunk import iterchunks, DefaultChunk
from .layers import LayerTable
from .styles import StyleTable
from .linetypes import LinetypeTable

TABLENAMES = {
    'layer': 'layers',
    'ltype': 'linetypes',
    'appid': 'appids',
    'dimstyle': 'dimstyles',
    'style': 'styles',
    'ucs': 'ucs',
    'view': 'views',
    'vport': 'viewports',
    'block_record': 'block_records',
    }


def tablename(dxfname):
    """ Translate DXF-table-name to attribute-name. ('LAYER' -> 'layers') """
    name = dxfname.lower()
    return TABLENAMES.get(name, name+'s')


class GenericTable(DefaultChunk):
    @property
    def name(self):
        return tablename(self.tags[1].value)


class DefaultDrawing(object):
    dxfversion = 'AC1009'
    encoding = 'cp1252'


class TablesSection(object):
    name = 'tables'

    def __init__(self, drawing=DefaultDrawing()):
        self._tables = dict()
        self._drawing = drawing
        self._create_default_tables()

    def _create_default_tables(self):
        for cls in TABLESMAP.values():
            table = cls()
            self._tables[table.name] = table

    @staticmethod
    def from_tags(tags, drawing):
        tables_section = TablesSection(drawing)
        tables_section._setup_tables(tags)
        return tables_section

    def _setup_tables(self, tags):
        def name(table):
            return table[1].value

        def skiptags(tags, count):
            for i in xrange(count):
                tags.next()
            return tags

        itertags = skiptags(iter(tags), 2)  # (0, 'SECTION'), (2, 'TABLES')
        for table in iterchunks(itertags, stoptag='ENDSEC', endofchunk='ENDTAB'):
            table_class = table_factory(name(table))
            new_table = table_class.from_tags(table, self._drawing)
            self._tables[new_table.name] = new_table

    def __getattr__(self, key):
        try:
            return self._tables[key]
        except KeyError:
            raise AttributeError(key)

# support for further tables types are possible
TABLESMAP = {
    'LAYER': LayerTable,
    'STYLE': StyleTable,
    'LTYPE': LinetypeTable,
}


def table_factory(name):
    return TABLESMAP.get(name, GenericTable)
