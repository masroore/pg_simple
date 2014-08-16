# -*- coding: utf-8 -*-
__author__ = 'Masroor Ehsan'

import time
from collections import namedtuple
import logging
import os

from psycopg2.extras import DictCursor, NamedTupleCursor

import pool


class PgSimple(object):
    _connection = None
    _cursor = None
    _log = None
    _log_fmt = None
    _cursor_factory = None
    _pool = None

    def __init__(self, log=None, log_fmt=None, nt_cursor=True):
        self._log = log
        self._log_fmt = log_fmt
        self._cursor_factory = NamedTupleCursor if nt_cursor else DictCursor

        self._connect()

    def _connect(self):
        """Connect to the postgres server"""
        self._pool = pool.get_pool()
        try:
            self._connection = self._pool.get_conn()
            self._cursor = self._connection.cursor(cursor_factory=self._cursor_factory)
        except Exception, e:
            self._log_error('postgresql connection failed: ' + e.message)
            raise

    def _debug_write(self, msg):
        if msg and self._log:
            if isinstance(self._log, logging.Logger):
                self._log.debug(msg)
            else:
                self._log.write(msg + os.linesep)

    def _log_cursor(self, cursor):
        if not self._log:
            return

        if self._log_fmt:
            msg = self._log_fmt(cursor)
        else:
            msg = str(cursor.query)

        self._debug_write(msg)

    def _log_error(self, data):
        if not self._log:
            return

        if self._log_fmt:
            msg = self._log_fmt(data)
        else:
            msg = str(data)

        self._debug_write(msg)

    def fetchone(self, table, fields='*', where=None, order=None, offset=None):
        """Get a single result

            table = (str) table_name
            fields = (field1, field2 ...) list of fields to select
            where = ("parameterized_statement", [parameters])
                    eg: ("id=%s and name=%s", [1, "test"])
            order = [field, ASC|DESC]
        """
        cur = self._select(table, fields, where, order, 1, offset)
        return cur.fetchone()

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
        return cur.fetchall()

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
            Row = namedtuple('Row', [f[0] for f in cur.description])
            rows = [Row(*r) for r in result]

        return rows

    def insert(self, table, data, returning=None):
        """Insert a record"""
        cols, vals = self._format_insert(data)
        sql = 'INSERT INTO %s (%s) VALUES(%s)' % (table, cols, vals)
        sql += self._returning(returning)
        cur = self.execute(sql, data.values())
        return cur.fetchone() if returning else cur.rowcount

    def update(self, table, data, where=None, returning=None):
        """Insert a record"""
        query = self._format_update(data)

        sql = 'UPDATE %s SET %s' % (table, query)
        sql += self._where(where) + self._returning(returning)
        cur = self.execute(sql, data.values() + where[1] if where and len(where) > 1 else data.values())
        return cur.fetchall() if returning else cur.rowcount

    def delete(self, table, where=None, returning=None):
        """Delete rows based on a where condition"""
        sql = 'DELETE FROM %s' % table
        sql += self._where(where) + self._returning(returning)
        cur = self.execute(sql, where[1] if where and len(where) > 1 else None)
        return cur.fetchall() if returning else cur.rowcount

    def execute(self, sql, params=None):
        """Executes a raw query"""
        try:
            if self._log and self._log_fmt:
                self._cursor.timestamp = time.time()
            self._cursor.execute(sql, params)
            if self._log and self._log_fmt:
                self._log_cursor(self._cursor)
        except Exception, e:
            if self._log and self._log_fmt:
                self._log_error('execute() failed: ' + e.message)
            raise

        return self._cursor

    def truncate(self, table, restart_identity=False, cascade=False):
        """Truncate a table or set of tables

        db.truncate('tbl1')
        db.truncate('tbl1, tbl2')
        """
        sql = 'TRUNCATE %s'
        if restart_identity:
            sql += ' RESTART IDENTITY'
        if cascade:
            sql += ' CASCADE'
        self.execute(sql % table)

    def drop(self, table):
        """Drop a table"""
        self.execute('DROP TABLE IF EXISTS %s CASCADE' % table)

    def create(self, table, schema):
        """Create a table with the schema provided

        pg_db.create('my_table','id SERIAL PRIMARY KEY, name TEXT')"""
        self.execute('CREATE TABLE %s (%s)' % (table, schema))

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

    def _format_insert(self, data):
        """Format insert dict values into strings"""
        cols = ",".join(data.keys())
        vals = ",".join(["%s" for k in data])

        return cols, vals

    def _format_update(self, data):
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

    def _returning(self, returning):
        if returning:
            return ' RETURNING %s' % returning
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

    def __exit__(self, exc_type, exc_value, traceback):
        if not isinstance(exc_value, Exception):
            self._debug_write('Committing transaction')
            self.commit()
        else:
            self._debug_write('Rolling back transaction')
            self.rollback()

        self._cursor.close()

    def __del__(self):
        if self._connection:
            self._pool.put_conn(self._connection, fail_silently=True)