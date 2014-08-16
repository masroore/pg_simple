# -*- coding: utf-8 -*-

__author__ = 'Erick Almeida and Masroor Ehsan'

import datetime
import urlparse
import os
import gc
import threading

import psycopg2
import psycopg2.extensions as _ext
from psycopg2.pool import PoolError


class AbstractConnectionPool(object):
    """Generic key-based pooling code."""

    def __init__(self, expiration, max_conn, **kwargs):
        """Initialize the connection pool."""
        self._pool = []
        self._used = {}
        self._rused = {}  # id(conn) -> key map
        self._tused = {}  # last used timestamp
        self._keys = 0
        self._disposed = False
        self.expiration = expiration
        self.max_conn = max_conn
        self._debug = kwargs.get('debug', False)
        if self._debug:
            self._debug_fn = self._debug.debug if hasattr(self._debug, 'debug') else self._debug.write
        if kwargs.has_key('debug'):
            del kwargs['debug']
        self._db_config = kwargs
        self._dsn = kwargs.get('dsn', None)

    def _log_internal(self, msg):
        """
        Debugging information logging.
        """
        if self._debug:
            curr_thr = threading.currentThread()
            self._debug_fn('[%d:%s] %s' % (os.getpid(), curr_thr.name, msg))

    def _connect(self, key=None):
        """Create a new connection and assign it to 'key' if not None."""
        if self._dsn:
            conn = psycopg2.connect(self._dsn)
        else:
            conn = psycopg2.connect(**self._db_config)

        if key is not None:
            self._used[key] = conn
            self._rused[id(conn)] = key
            self._tused[id(conn)] = datetime.datetime.now()
        else:
            self._pool.append(conn)

        self._log('Connection created %s' % conn)
        return conn

    def _release(self, conn, remove_from_pool=False):
        if remove_from_pool and conn in self._pool:
            self._pool.remove(conn)
        conn.close()
        del self._tused[id(conn)]
        self._log('Connection closed: %s' % conn)
        self._log('Pool=%d' % len(self._pool))

    def _get_key(self):
        """Return a new unique key."""
        self._keys += 1
        return self._keys

    def _get_conn(self, key=None):
        """Get a free connection and assign it to 'key' if not None."""
        if self._disposed:
            raise PoolError('Connection pool is disposed')
        if key is None:
            key = self._get_key()
        if key in self._used:
            return self._used[key]

        if self._pool:
            self._used[key] = conn = self._pool.pop()
            self._rused[id(conn)] = key
            self._tused[id(conn)] = datetime.datetime.now()
            return conn
        else:
            if len(self._used) == self.max_conn:
                raise PoolError('Connection pool exhausted')
            return self._connect(key)

    def purge_expired_connections(self):
        now = datetime.datetime.now()
        expiry_list = []
        for item in self._pool:
            conn_time = self._tused[id(item)]
            minutes, seconds = divmod((now - conn_time).seconds, 60)
            if minutes >= self.expiration:
                expiry_list.append(item)

        self._log('Purging. Pool=%d, Expired=%d' % (len(self._pool), len(expiry_list)))
        for item in expiry_list:
            self._release(item, True)

    def _put_conn(self, conn, key=None, close=False, fail_silently=False):
        """Stow away a connection."""
        self._log('Putting away %s%s' % (conn, ' key=' + key if key else ''))
        if self._disposed:
            if fail_silently:
                return
            raise PoolError('Connection pool is disposed')

        if key is None:
            key = self._rused.get(id(conn))
        if not key:
            raise PoolError('Trying to put un-keyed [{key}] connection'.format(key=key))

        if len(self._pool) < self.max_conn and not close:
            # Return the connection into a consistent state before putting
            # it back into the pool
            if not conn.closed:
                status = conn.get_transaction_status()
                if status == _ext.TRANSACTION_STATUS_UNKNOWN:
                    # server connection lost
                    self._log('Connection lost. Closing %s' % conn)
                    self._release(conn.close)
                elif status != _ext.TRANSACTION_STATUS_IDLE:
                    # connection in error or in transaction
                    self._log('Connection is in transaction. Rolling back %s' % conn)
                    conn.rollback()
                    self._pool.append(conn)
                else:
                    # regular idle connection
                    self._pool.append(conn)
                    # If the connection is closed, we just discard it.
        else:
            self._log('Closing (pool exhausted or explicit close requested) %s' % conn)
            self._release(conn)

        self.purge_expired_connections()

        # here we check for the presence of key because it can happen that a
        # thread tries to put back a connection after a call to close
        if not self._disposed or key in self._used:
            del self._used[key]
            del self._rused[id(conn)]

    def _release_all(self):
        """Release all connections.

        Note that this can lead to some code fail badly when trying to use
        an already closed connection. If you call .release_all() make sure
        your code can deal with it.
        """
        # Make sure that all connections lying about are collected before we go on.
        try:
            gc.collect()
        except (TypeError, AttributeError):
            # We've detected that we're being called in an incomplete
            # finalization state, we just bail out, leaving the connections
            # to take care of themselves.
            return

        if self._disposed:
            raise PoolError('Connection pool is disposed')

        close_list = self._pool + list(self._used.values())
        self._log('Closing %d connection(s)' % len(close_list))

        for conn in close_list:
            try:
                conn.close()
            except:
                pass

        self._disposed = True
        self._pool = []
        self._used = {}

    @property
    def disposed(self):
        return self._disposed

    def __del__(self):
        self._release_all()


class SimpleConnectionPool(AbstractConnectionPool):
    """A connection pool that can't be shared across different threads."""

    get_conn = AbstractConnectionPool._get_conn
    put_conn = AbstractConnectionPool._put_conn
    release_all = AbstractConnectionPool._release_all
    _log = AbstractConnectionPool._log_internal


class ThreadedConnectionPool(AbstractConnectionPool):
    """A connection pool that works with the threading module."""

    def __init__(self):
        """Initialize the threading lock."""
        AbstractConnectionPool.__init__(self)
        self._lock = threading.Lock()
        if self._debug:
            # lock used to serialize debug output between threads
            self._log_lock = threading.Lock()

    def _log(self, msg):
        if self._debug:
            try:
                self._log_lock.acquire()
                self._log_internal(msg)
            finally:
                self._log_lock.release()

    def get_conn(self, key=None):
        """Get a free connection and assign it to 'key' if not None."""
        self._lock.acquire()
        try:
            return self._get_conn(key)
        finally:
            self._lock.release()

    def put_conn(self, conn=None, key=None, close=False):
        """Put away an unused connection."""
        self._lock.acquire()
        try:
            self._put_conn(conn, key, close)
        finally:
            self._lock.release()

    def release_all(self):
        """Release all connections (even the one currently in use.)"""
        self._lock.acquire()
        try:
            self._release_all()
        finally:
            self._lock.release()


__pool__ = None


def config_pool(max_conn=5, expiration=5, pool_manager=SimpleConnectionPool, **kwargs):
    global __pool__

    config = None
    dsn = kwargs.get('dsn', os.environ.get('DATABASE_DSN'))
    db_url = kwargs.get('db_url', os.environ.get('DATABASE_URL'))
    debug = kwargs.get('debug', False)

    if not dsn:
        if db_url:
            params = urlparse.urlparse(db_url)
            config = {'database': params.path[1:],
                      'user': params.username,
                      'password': params.password,
                      'host': params.hostname,
                      'port': params.port}
        else:
            config = kwargs
            config['host'] = kwargs.get('host', 'localhost')

    if not dsn and not config:
        raise Exception('No database configuration provided')

    if dsn:
        __pool__ = pool_manager(expiration=expiration,
                                max_conn=max_conn,
                                dsn=dsn,
                                debug=debug)
    else:
        __pool__ = pool_manager(expiration=expiration,
                                max_conn=max_conn,
                                database=config['database'],
                                host=config.get('host'),
                                port=config.get('port'),
                                user=config.get('user'),
                                password=config.get('password'),
                                debug=debug)


def get_pool():
    return __pool__