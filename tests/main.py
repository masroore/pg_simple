# -*- coding: utf-8 -*-

__author__ = 'Masroor Ehsan'

import unittest
import threading
import time

import pg_simple


TEST_DB_DSN = 'dbname=pg_simple user=masroor'


class AbstractPgSimpleTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(AbstractPgSimpleTestCase, self).__init__(*args, **kwargs)

        # Kludge alert: We want this class to carry test cases without being run
        # by the unit test framework, so the `run' method is overridden to do
        # nothing.  But in order for sub-classes to be able to do something when
        # run is invoked, the constructor will rebind `run' from TestCase.
        if self.__class__ != AbstractPgSimpleTestCase:
            # Rebind `run' from the parent class.
            self.run = unittest.TestCase.run.__get__(self, self.__class__)
        else:
            self.run = lambda self, *args, **kwargs: None

    def setUp(self):
        super(AbstractPgSimpleTestCase, self).setUp()
        pg_simple.config_pool(max_conn=25,
                              expiration=5,
                              pool_manager=self._get_pool_manager(),
                              dsn=TEST_DB_DSN)

        self.tables = (('pg_t1', '''id SERIAL PRIMARY KEY,
                                   name TEXT NOT NULL,
                                   count INTEGER NOT NULL DEFAULT 0,
                                   active BOOLEAN NOT NULL DEFAULT true'''),
                       ('pg_t2', '''id SERIAL PRIMARY KEY,
                                   value TEXT NOT NULL,
                                   pg_t1_id INTEGER NOT NULL REFERENCES pg_t1(id)'''))

    def _get_pool_manager(self):
        raise NotImplementedError()

    def _drop_tables(self, db):
        db.drop('pg_t1', True)
        db.drop('pg_t2')

    def _truncate_tables(self, db):
        db.truncate('pg_t2', restart_identity=True)
        db.truncate('pg_t1', restart_identity=True, cascade=True)

    def _populate_tables(self, db):
        for i in range(26):
            id_ = db.insert('pg_t1', {'name': chr(97 + i) * 5}, returning='id')
            _ = db.insert('pg_t2', {'value': chr(97 + i) * 4, 'pg_t1_id': id_})

    def _create_tables(self, db, fill=False):
        for (name, schema) in self.tables:
            db.create(name, schema)

        if fill:
            self._populate_tables(db)

    def test_basic_functions(self):
        import code
        import doctest
        import sys

        db = pg_simple.PgSimple()
        if sys.argv.count('--interact'):
            db.log = sys.stdout
            code.interact(local=locals())
        else:
            try:
                # Setup tables
                self._drop_tables(db)
                self._create_tables(db, fill=True)
                # Run tests
                doctest.testmod(optionflags=doctest.ELLIPSIS)
            finally:
                # Drop tables
                self._drop_tables(db)
        self.assertEqual(True, True)

    def _check_table(self, db, table_name):
        record = db.fetchone('pg_tables', fields=['tablename', ],
                             where=('schemaname=%s AND tablename=%s', ['public', table_name]))
        self.assertEqual(record is not None and record.tablename == table_name, True,
                         'Table must exist, but was not found. Auto-commit fail.')

    def test_connection_auto_commit(self):
        import code
        import sys

        with pg_simple.PgSimple() as db:
            if sys.argv.count('--interact'):
                db.log = sys.stdout
                code.interact(local=locals())
            else:
                self._drop_tables(db)
                self._create_tables(db, fill=True)

        with pg_simple.PgSimple() as db:
            try:
                self._check_table(db, 'pg_t1')
            finally:
                self._drop_tables(db)


class PgSimpleTestCase(AbstractPgSimpleTestCase):
    def _get_pool_manager(self):
        return pg_simple.SimpleConnectionPool


class PgSimpleThread(threading.Thread):
    def __init__(self, thread_id, name, counter, test_cls):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.counter = counter
        self.test_cls = test_cls

    def run(self):
        print('Starting %s' % self.name)
        self.database_operations()
        print('Exiting %s' % self.name)

    def database_operations(self):
        with pg_simple.PgSimple() as db:
            self.test_cls._check_table(db, 'pg_t1')
            self.test_cls._truncate_tables(db)
            self.test_cls._populate_tables(db)

        time.sleep(1)


class PgSimpleThreadedTestCase(AbstractPgSimpleTestCase):
    def _get_pool_manager(self):
        return pg_simple.ThreadedConnectionPool

    def test_threaded_connections(self):
        with pg_simple.PgSimple() as db:
            self._drop_tables(db)
            self._create_tables(db, fill=True)

        threads = []

        # Create new threads
        for i in range(20):
            t = PgSimpleThread(i, 'thread-' + str(i), i, self)
            threads.append(t)

        # Start new Threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Drop tables
        with pg_simple.PgSimple() as db:
            self._drop_tables(db)

        print "Exiting Main Thread \n"


if __name__ == '__main__':
    unittest.main()