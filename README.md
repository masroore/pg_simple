# pg_simple

The `pg_simple` module provides a simple yet efficient layer over `psycopg2` providing Python API for common SQL functions, explicit and implicit transactions management and database connection pooling for single and multi-threaded applications.

`pg_simple` is not intended to provide ORM-like functionality, rather to make it easier to interact with the PostgreSQL database from python code for direct SQL access using convenient wrapper methods. The module wraps the excellent `psycopg2` library and most of the functionality is provided by this behind the scenes.

The `pg_simple` module provides:

* Simplified handling of database connections/cursor
* Connection pool for single or multithreaded access
* Python API to wrap basic SQL functionality: select, update, delete, join et al
* Query results as python namedtuple and dict objects (using `psycopg2.extras.NamedTupleCursor` and `psycopg2.extras.DictCursor` respectively)
* Debug logging support


## Installation

With `pip` or `easy_install`:

```pip install pg_simple```

or:

```easy_install pg_simple```

or from the source:

```python setup.py install```


##30 Seconds Quick-start Guide

* Step 1: Configure a connection pool using `pg_simple.config_pool()`
* Step 2: Create a database connection and cursor by instantiating a `pg_simple.PgSimple` object

Here's a pseudo-example to illustrate the basic concepts:

```python
import pg_simple

pg_simple.config_pool(dsn='dbname=my_db user=my_username ...')

with pg_simple.PgSimple() as db:
    row = db.insert('table_name',
                    data={'column': 123,
                          'another_column': 'data'})
    db.commit()

with pg_simple.PgSimple() as db1:
    rows = db1.fetchall('table_name')
```


## Basic Usage

### Initializing the connection pool

```python
import pg_simple

pg_simple.config_pool(max_conn=250,
                      expiration=60, # idle timeout = 60 seconds
                      host='localhost',
                      port=5432,
                      database='pg_simple',
                      user='postgres',
                      password='secret')
```

or, using `dsn`:

```python
pg_simple.config_pool(max_conn=250,
                      expiration=60,
                      dsn='dbname=database_name user=postgres password=secret')

```

or, using `db_url`:

```python
pg_simple.config_pool(max_conn=250,
                      expiration=60,
                      db_url= 'postgres://username:password@hostname:port/database')

```

The above snippets will create a connection pool capable of accommodating a maximum of 250 concurrent database connections. Once that limit is reached and the pool does not contain any idle connections, all subsequent new connection request will result in a `PoolError` exception (until the pool gets refilled with idle connections).

Take caution to properly clean up all `pg_simple.PgSimple` objects after use (wrap the object inside python try-finally block or `with` statement). Once the object is released, it will quietly return the internal database connction to the idle pool. Failure to dispose `PgSimple` properly may result in pool exhaustion error.

To configure the connection pool for use in multi-threaded apps, use the `ThreadedConnectionPool`:

```python
pg_simple.config_pool(max_conn=250,
                      expiration=60,
                      pool_manager=ThreadedConnectionPool,
                      dsn='...')
```

Note: The default pool manager `SimpleConnectionPool` is not thread-safe.

To disable connection pooling completely, set the `disable_pooling` parameter to True:

```python
pg_simple.config_pool(disable_pooling=True, dsn='...')
```

All database requests on this pool will create new connections on the fly, and all connections returned to the pool (upon `PgSimple` disposal or by explicitly invoking `pool.put_conn()`) will be discarded immediately.


### Connecting to the posgtresql server

The following snippet will connect to the posgtresql server and allocate a cursor:

```python
import sys
import pg_simple

db = pg_simple.PgSimple(log=sys.stdout,
                        log_fmt=lambda x: '>> %s' % (x if isinstance(x, str) else x.query),
                        nt_cursor=True)
```

By default `PgSimple` generates result sets as `collections.namedtuple` objects (using `psycopg2.extras.NamedTupleCursor`). If you want to access the retrieved records using an interface similar to the Python dictionaries (using `psycopg2.extras.DictCursor`), set the `nt_cursor` parameter to `False`:

```python
db = pg_simple.PgSimple(nt_cursor=False)
```

### Raw SQL execution

```python
>>> db.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s and tablename=%s', ['public', 'books'])
<cursor object at 0x102352a50; closed: 0>
```

### Dropping and creating tables

```python
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

```

### Emptying a table or set of tables

```python
db.truncate('tbl1')
db.truncate('tbl2, tbl3', restart_identity=True, cascade=True)
db.commit()
```

### Inserting rows

```python
for i in range(1, 10):
    db.insert("books",
              {"genre": "fiction",
               "name": "Book Name vol. %d" % i,
               "price": 1.23 * i,
               "published": "%d-%d-1" % (2000 + i, i)})

db.commit()
```

### Updating rows

```python
with pg_simple.PgSimple() as db1:
    db1.update('books',
               data={'name': 'An expensive book',
                     'price': 998.997,
                     'genre': 'non-fiction',
                     'modified': 'NOW()'},
               where=('published = %s', [datetime.date(2001, 1, 1)]))
               
    db1.commit()
```

### Deleting rows

```python
db.delete('books', where=('published >= %s', [datetime.date(2005, 1, 31)]))
db.commit()
```

### Inserting/updating/deleting rows with return value

```python
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
```

### Fetching a single record

```python
book = db.fetchone('books', 
                   fields=['name', 'published'], 
                   where=('published = %s', [datetime.date(2002, 2, 1)]))
                   
print(book.name + 'was published on ' + book[1])
```

### Fetching multiple records

```python
books = db.fetchall('books',
                    fields=['name AS n', 'genre AS g'],
                    where=('published BETWEEN %s AND %s', [datetime.date(2005, 2, 1), datetime.date(2009, 2, 1)]),
                    order=['published', 'DESC'], 
                    limit=5, 
                    offset=2)

for book in books:
    print(book.n + 'belongs to ' + book[1])
```

### Explicit database transaction management

```python
with pg_simple.PgSimple() as _db:
    try:
        _db.execute('Some SQL statement')
        _db.commit()
    except:
        _db.rollback()
```

### Implicit database transaction management

```python
with pg_simple.PgSimple() as _db:
    _db.execute('Some SQL statement')
    _db.commit()
```

The above transaction will automatically be rolled back should something go awry.