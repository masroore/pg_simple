`pg\_simple <https://github.com/masroore/pg_simple>`__
======================================================

The `pg\_simple <https://github.com/masroore/pg_simple>`__ module
provides a simple yet efficient layer over ``psycopg2`` providing Python
API for common SQL functions, explicit and implicit transactions
management and database connection pooling for single and multi-threaded
applications.

``pg_simple`` is not intended to provide ORM-like functionality, rather
to make it easier to interact with the PostgreSQL database from python
code for direct SQL access using convenient wrapper methods. The module
wraps the excellent ``psycopg2`` library and most of the functionality
is provided by this behind the scenes.

The ``pg_simple`` module provides:

-  Simplified handling of database connections/cursor
-  Connection pool for single or multithreaded access
-  Python API to wrap basic SQL functionality: select, update, delete,
   join et al
-  Query results as python namedtuple and dict objects (using
   ``psycopg2.extras.NamedTupleCursor`` and
   ``psycopg2.extras.DictCursor`` respectively)
-  Debug logging support

Installation
------------

With ``pip`` or ``easy_install``:

``pip install pg_simple``

or:

``easy_install pg_simple``

or from the source:

``python setup.py install``

30 Seconds Quick-start Guide
----------------------------

-  Step 1: Initialize a connection pool manager using
   ``pg_simple.config_pool()``
-  Step 2: Create a database connection and cursor by instantiating a
   ``pg_simple.PgSimple`` object

Here's a pseudo-example to illustrate the basic concepts:

.. code:: python

    import pg_simple

    connection_pool = pg_simple.config_pool(dsn='dbname=my_db user=my_username ...')

    with pg_simple.PgSimple(connection_pool) as db:
        db.insert('table_name',
                  data={'column': 123,
                        'another_column': 'blah blah'})
        db.commit()

    with pg_simple.PgSimple(connection_pool) as db1:
        rows = db1.fetchall('table_name')

Connection pool management
--------------------------

Initialize the connection pool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    import pg_simple

    connection_pool = pg_simple.config_pool(max_conn=250,
                          expiration=60, # idle timeout = 60 seconds
                          host='localhost',
                          port=5432,
                          database='pg_simple',
                          user='postgres',
                          password='secret')

or, using ``dsn``:

.. code:: python

    connection_pool = pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          dsn='dbname=database_name user=postgres password=secret')

or, using ``db_url``:

.. code:: python

    connection_pool = pg_simple.config_pool(max_conn=250,
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

Configure multiple connection pools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To generate different connection pools simply define each connection:

.. code:: python

    connection_pool_1 = pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          dsn='dbname=database_name_1 user=postgres1 password=secret1')

    connection_pool_2 = pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          dsn='dbname=database_name_2 user=postgres2 password=secret2')

After that you can use each connection pool object to generate connections to the databases as you would with only one connection.
You can define as many of connection pool objects as your systems can handle and also both types (``SimpleConnectionPool`` and ``ThreadedConnectionPool``) at the same time.

Configure connection pool for thread-safe access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default ``SimpleConnectionPool`` pool manager is not thread-safe. To
utilize the connection pool in multi-threaded apps, use the
``ThreadedConnectionPool``:

.. code:: python

    connection_pool = pg_simple.config_pool(max_conn=250,
                          expiration=60,
                          pool_manager=ThreadedConnectionPool,
                          dsn='...')

Disable connection pooling
~~~~~~~~~~~~~~~~~~~~~~~~~~

To disable connection pooling completely, set the ``disable_pooling``
parameter to True:

.. code:: python

    connection_pool = pg_simple.config_pool(disable_pooling=True, dsn='...')

All database requests on this pool will create new connections on the
fly, and all connections returned to the pool (upon disposal of
``PgSimple`` object or by explicitly invoking ``pool.put_conn()``) will
be discarded immediately.

Garbage collect stale connections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To explicitly purge the pool of stale database connections (whose
duration of stay in the pool exceeds the ``expiration`` timeout), invoke
the ``pool.purge_expired_connections()`` method:

.. code:: python


    connection_pool.purge_expired_connections()

Note that the pool is automatically scavenged for stale connections when
an idle connection is returned to the pool (using the
``pool.put_conn()`` method).

Basic Usage
-----------

Connecting to the posgtresql server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following snippet will connect to the posgtresql server and allocate
a cursor:

.. code:: python

    import sys
    import pg_simple

    db = pg_simple.PgSimple(connection_pool, log=sys.stdout,
                            log_fmt=lambda x: '>> %s' % (x if isinstance(x, str) else x.query),
                            nt_cursor=True)

By default ``PgSimple`` generates result sets as
``collections.namedtuple`` objects (using
``psycopg2.extras.NamedTupleCursor``). If you want to access the
retrieved records using an interface similar to the Python dictionaries
(using ``psycopg2.extras.DictCursor``), set the ``nt_cursor`` parameter
to ``False``:

.. code:: python

    db = pg_simple.PgSimple(connection_pool, nt_cursor=False)

Raw SQL execution
~~~~~~~~~~~~~~~~~

.. code:: python

    >>> db.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s and tablename=%s', ['public', 'books'])
    <cursor object at 0x102352a50; closed: 0>

Dropping and creating tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    db.drop('books')

    db.create('books',
              '''
    "id" SERIAL NOT NULL,
    "type" VARCHAR(20) NOT NULL,
    "name" VARCHAR(40) NOT NULL,
    "price" MONEY NOT NULL,
    "published" DATE NOT NULL,
    "modified" TIMESTAMP(6) NOT NULL DEFAULT now()
    '''
    )

    db.execute('''ALTER TABLE "books" ADD CONSTRAINT "books_pkey" PRIMARY KEY ("id")''')
    db.commit()

Emptying a table or set of tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    db.truncate('tbl1')
    db.truncate('tbl2, tbl3', restart_identity=True, cascade=True)
    db.commit()

Inserting rows
~~~~~~~~~~~~~~

.. code:: python

    for i in range(1, 10):
        db.insert("books",
                  {"genre": "fiction",
                   "name": "Book Name vol. %d" % i,
                   "price": 1.23 * i,
                   "published": "%d-%d-1" % (2000 + i, i)})

    db.commit()

Updating rows
~~~~~~~~~~~~~

.. code:: python

    with pg_simple.PgSimple(connection_pool) as db1:
        db1.update('books',
                   data={'name': 'An expensive book',
                         'price': 998.997,
                         'genre': 'non-fiction',
                         'modified': 'NOW()'},
                   where=('published = %s', [datetime.date(2001, 1, 1)]))
                   
        db1.commit()

Deleting rows
~~~~~~~~~~~~~

.. code:: python

    db.delete('books', where=('published >= %s', [datetime.date(2005, 1, 31)]))
    db.commit()

Inserting/updating/deleting rows with return value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    row = db.insert("books",
                    {"type": "fiction",
                     "name": "Book with ID",
                     "price": 123.45,
                     "published": "1997-01-31"},
                    returning='id')
    print(row.id)

    rows = db.update('books',
                     data={'name': 'Another expensive book',
                           'price': 500.50,
                           'modified': 'NOW()'},
                     where=('published = %s', [datetime.date(2006, 6, 1)]),
                     returning='modified')
    print(rows[0].modified)

    rows = db.delete('books', 
                     where=('published >= %s', [datetime.date(2005, 1, 31)]), 
                     returning='name')
    for r in rows:
        print(r.name)

Fetching a single record
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    book = db.fetchone('books', 
                       fields=['name', 'published'], 
                       where=('published = %s', [datetime.date(2002, 2, 1)]))
                       
    print(book.name + 'was published on ' + book[1])

Fetching multiple records
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    books = db.fetchall('books',
                        fields=['name AS n', 'genre AS g'],
                        where=('published BETWEEN %s AND %s', [datetime.date(2005, 2, 1), datetime.date(2009, 2, 1)]),
                        order=['published', 'DESC'], 
                        limit=5, 
                        offset=2)

    for book in books:
        print(book.n + 'belongs to ' + book[1])

Explicit database transaction management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    with pg_simple.PgSimple(connection_pool) as _db:
        try:
            _db.execute('Some SQL statement')
            _db.commit()
        except:
            _db.rollback()

Implicit database transaction management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    with pg_simple.PgSimple(connection_pool) as _db:
        _db.execute('Some SQL statement')
        _db.commit()

The above transaction will be rolled back automatically should something
goes awry.
