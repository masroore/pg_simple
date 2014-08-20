30 Seconds Quick-start Guide
----------------------------

-  Step 1: Initialize a connection pool manager using
   ``pg_simple.config_pool()``
-  Step 2: Create a database connection and cursor by instantiating a
   ``pg_simple.PgSimple`` object

Here's a pseudo-example to illustrate the basic concepts:

.. code:: python

    import pg_simple

    pg_simple.config_pool(dsn='dbname=my_db user=my_username ...')

    with pg_simple.PgSimple() as db:
        db.insert('table_name',
                  data={'column': 123,
                        'another_column': 'blah blah'})
        db.commit()

    with pg_simple.PgSimple() as db1:
        rows = db1.fetchall('table_name')