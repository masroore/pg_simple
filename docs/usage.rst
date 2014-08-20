Basic Usage
-----------

Connecting to the posgtresql server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following snippet will connect to the posgtresql server and allocate
a cursor:

.. code:: python

    import sys
    import pg_simple

    db = pg_simple.PgSimple(log=sys.stdout,
                            log_fmt=lambda x: '>> %s' % (x if isinstance(x, str) else x.query),
                            nt_cursor=True)

By default ``PgSimple`` generates result sets as
``collections.namedtuple`` objects (using
``psycopg2.extras.NamedTupleCursor``). If you want to access the
retrieved records using an interface similar to the Python dictionaries
(using ``psycopg2.extras.DictCursor``), set the ``nt_cursor`` parameter
to ``False``:

.. code:: python

    db = pg_simple.PgSimple(nt_cursor=False)

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

    with pg_simple.PgSimple() as db1:
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

    with pg_simple.PgSimple() as _db:
        try:
            _db.execute('Some SQL statement')
            _db.commit()
        except:
            _db.rollback()

Implicit database transaction management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    with pg_simple.PgSimple() as _db:
        _db.execute('Some SQL statement')
        _db.commit()

The above transaction will automatically be rolled back should something
go awry.
