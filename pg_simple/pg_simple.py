# -*- coding: utf-8 -*-
import time

__author__ = 'Masroor Ehsan'

from collections import namedtuple
import logging
import os
import psycopg2
from psycopg2.extras import DictCursor, NamedTupleCursor


class PgSimple(object):
    _connection = None
    _cursor = None
    _config = None
    _dsn = None
    _log = None
    _log_fmt = None
    _cursor_factory = None

    def __init__(self, **kwargs):
        self._dsn = kwargs.get('dsn', None)
        if not self._dsn:
            self._config = kwargs
            self._config['host'] = kwargs.get('host', 'localhost')

        self._log = kwargs.get('log', None)
        self._log_fmt = kwargs.get('log_fmt', None)
        self._cursor_factory = NamedTupleCursor if kwargs.get('nt_cursor', True) else DictCursor

        self.connect()

    def _log_debug(self, cursor):
        if self._log_fmt:
            msg = self._log_fmt(cursor)
        else:
            msg = str(cursor.query)

        if msg:
            if isinstance(self._log, logging.Logger):
                self._log.debug(msg)
            else:
                self._log.write(msg + os.linesep)

    def _log_error(self, data):
        if self._log_fmt:
            msg = self._log_fmt(data)
        else:
            msg = str(data)

        if isinstance(self._log, logging.Logger):
            self._log.error(msg)
        else:
            self._log.write(msg + os.linesep)

    def connect(self):
        """Connect to the postgres server"""

        try:
            if self._dsn:
                self._connection = psycopg2.connect(self._dsn)
            else:
                self._connection = psycopg2.connect(database=self._config['database'],
                                              host=self._config.get('host'),
                                              port=self._config.get('port'),
                                              user=self._config.get('user'),
                                              password=self._config.get('password'))
            self._cursor = self._connection.cursor(cursor_factory=self._cursor_factory)
        except Exception, e:
            self._log_error('postgresql connection failed: ' + e.message)
            raise

    def fetchone(self, table, fields='*', where=None, order=None, offset=None):
        """Get a single result

            table = (str) table_name
            fields = (field1, field2 ...) list of fields to select
            where = ("parameterized_statement", [parameters])
                    eg: ("id=%s and name=%s", [1, "test"])
            order = [field, ASC|DESC]
        """

        cur = self._select(table, fields, where, order, 1, offset)
        result = cur.fetchone()
        return result

    def fetchall(self, table, fields='*', where=None, order=None, limit=None, offset=None):
        """Get all results

            table = (str) table_name
            fields = (field1, field2 ...) list of fields to select
            where = ("parameterized_statement", [parameters])
                    eg: ("id=%s and name=%s", [1, "test"])
            order = [field, ASC|DESC]
            limit = [limit, offset]
        """

        cur = self._select(table, fields, where, order, limit, offset)
        result = cur.fetchall()
        return result

    def join(self, tables=(), fields=(), join_fields=(), where=None, order=None, limit=None, offset=None):
        """Run an inner left join query

            tables = (table1, table2)
            fields = ([fields from table1], [fields from table 2])  # fields to select
            join_fields = (field1, field2)  # fields to join. field1 belongs to table1 and field2 belongs to table 2
            where = ("parameterized_statement", [parameters])
                    eg: ("id=%s and name=%s", [1, "test"])
            order = [field, ASC|DESC]
            limit = [limit1, limit2]
        """

        cur = self._join(tables, fields, join_fields, where, order, limit, offset)
        result = cur.fetchall()

        rows = None
        if result:
            Row = namedtuple("Row", [f[0] for f in cur.description])
            rows = [Row(*r) for r in result]

        return rows

    def insert(self, table, data):
        """Insert a record"""

        query = self._serialize_insert(data)

        sql = "INSERT INTO %s (%s) VALUES(%s)" % (table, query[0], query[1])

        return self.execute(sql, data.values()).rowcount

    def update(self, table, data, where=None):
        """Insert a record"""

        query = self._serialize_update(data)

        sql = "UPDATE %s SET %s" % (table, query)

        if where and len(where) > 0:
            sql += " WHERE %s" % where[0]

        return self.execute(sql, data.values() + where[1] if where and len(where) > 1 else data.values()).rowcount

    def delete(self, table, where=None, returning=None):
        """Delete rows based on a where condition"""

        sql = 'DELETE FROM %s' % table

        if where and len(where) > 0:
            sql += ' WHERE %s' % where[0]

        if returning:
            sql += ' RETURNING %s' % returning
            return self.execute(sql, where)

        return self.execute(sql, where[1] if where and len(where) > 1 else None).rowcount

    def execute(self, sql, params=None):
        """Executes a raw query"""

        try:
            if self._log and self._log_fmt:
                self._cursor.timestamp = time.time()
            self._cursor.execute(sql, params)
            if self._log and self._log_fmt:
                self._log_debug(self._cursor)
        except Exception, e:
            if self._log and self._log_fmt:
                self._log_error('execute() failed: ' + e.message)
            raise

        return self._cursor

    def drop(self, table):
        """Drop a table"""
        self.execute('DROP TABLE IF EXISTS %s CASCADE' % table)

    def commit(self):
        """Commit a transaction"""
        return self._connection.commit()

    def rollback(self):
        """Roll-back a transaction"""
        return self._connection.rollback()

    @property
    def is_open(self):
        """Check if the connection is open"""
        return self._connection.open

    def close(self):
        """Kill the connection"""
        self._cursor.close()
        self._cursor = None
        self._connection.close()
        self._connection = None

    def _serialize_insert(self, data):
        """Format insert dict values into strings"""
        keys = ",".join(data.keys())
        vals = ",".join(["%s" for k in data])

        return [keys, vals]

    def _serialize_update(self, data):
        """Format update dict values into string"""
        return "=%s,".join(data.keys()) + "=%s"

    def _where(self, where=None):
        if where and len(where) > 0:
            return ' WHERE %s' % where[0]
        return ''

    def _order(self, order=None):
        sql = ''
        if order:
            sql += ' ORDER BY %s' % order[0]

            if len(order) > 1:
                sql += ' %s' % order[1]
        return sql

    def _limit(self, limit):
        if limit:
            return ' LIMIT %d' % limit
        return ''

    def _offset(self, offset):
        if offset:
            return ' OFFSET %d' % offset
        return ''

    def _select(self, table=None, fields=(), where=None, order=None, limit=None, offset=None):
        """Run a select query"""
        sql = 'SELECT %s FROM %s' % (",".join(fields), table) \
              + self._where(where) \
              + self._order(order) \
              + self._limit(limit) \
              + self._offset(offset)
        return self.execute(sql, where[1] if where and len(where) == 2 else None)

    def _join(self, tables=(), fields=(), join_fields=(), where=None, order=None, limit=None, offset=None):
        """Run an inner left join query"""

        fields = [tables[0] + "." + f for f in fields[0]] + [tables[1] + "." + f for f in fields[1]]

        sql = 'SELECT {0:s} FROM {1:s} LEFT JOIN {2:s} ON ({3:s} = {4:s})'.format(
            ','.join(fields),
            tables[0],
            tables[1],
            '{0}.{1}'.format(tables[0], join_fields[0]),
            '{0}.{1}'.format(tables[1], join_fields[1]))

        sql += self._where(where) + self._order(order) + self._limit(limit) + self._offset(offset)

        return self.execute(sql, where[1] if where and len(where) > 1 else None)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()