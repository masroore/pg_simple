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

.. include install.rst
.. include quick.rst
.. include pool.rst
.. include usage.rst

.. toctree::
   :maxdepth: 2

   install
   quick
   pool
   usage