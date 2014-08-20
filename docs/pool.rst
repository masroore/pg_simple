Connection pool management
--------------------------

Initialize the connection pool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    import pg_simple

    pg_simple.config_pool(max_conn=250,
                          expiration=60, # idle timeout = 60 seconds
                          host='localhost',
                          port=5432,
                          database='pg_simple',
                          user='postgres',
                          password='secret')

or, using ``dsn``:

.. code:: python

    pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          dsn='dbname=database_name user=postgres password=secret')

or, using ``db_url``:

.. code:: python

    pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          db_url= 'postgres://username:password@hostname:numeric_port/database')

The above snippets will create a connection pool capable of
accommodating a maximum of 250 concurrent database connections. Once
that limit is reached and the pool does not contain any idle
connections, all subsequent new connection request will result in a
``PoolError`` exception (until the pool gets refilled with idle
connections).

Take caution to properly clean up all ``pg_simple.PgSimple`` objects
after use (wrap the object inside python try-finally block or ``with``
statement). Once the object is released, it will quietly return the
internal database connction to the idle pool. Failure to dispose
``PgSimple`` properly may result in pool exhaustion error.

Configure connection pool for thread-safe access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default ``SimpleConnectionPool`` pool manager is not thread-safe. To
utilize the connection pool in multi-threaded apps, use the
``ThreadedConnectionPool``:

.. code:: python

    pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          pool_manager=ThreadedConnectionPool,
                          dsn='...')

Disable connection pooling
~~~~~~~~~~~~~~~~~~~~~~~~~~

To disable connection pooling completely, set the ``disable_pooling``
parameter to True:

.. code:: python

    pg_simple.config_pool(disable_pooling=True, dsn='...')

All database requests on this pool will create new connections on the
fly, and all connections returned to the pool (upon disposal of
``PgSimple`` object or by explicitly invoking ``pool.put_conn()``) will
be discarded immediately.

Obtaining the current connection pool manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Call the ``pg_simple.get_pool()`` method to get the current pool:

.. code:: python

    pool = pg_simple.get_pool()

Garbage collect stale connections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To explicitly purge the pool of stale database connections (whose
duration of stay in the pool exceeds the ``expiration`` timeout), invoke
the ``pool.purge_expired_connections()`` method:

.. code:: python

    pool = pg_simple.get_pool()
    pool.purge_expired_connections()

Note that the pool is automatically scavenged for stale connections when
an idle connection is returned to the pool (using the
``pool.put_conn()`` method).