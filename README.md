# pg_simple

An ultra simple wrapper over Python psycopg2 with support for basic SQL functionality.

## Installation

With `pip` or `easy_install`:

```pip install simplemysql```

or:

```easy_install simplemysql```

Or from the source:

```python setup.py install```

# Basic Usage

### Connecting to the posgtresql server:

```
import sys
from pg_simple import PgSimple

db = pg_simple.PgSimple(host='127.0.0.1',
                        database='pg_simple',
                        user='postgres',
                        password='secret',
                        log=sys.stdout,
                        log_fmt=lambda x: '>> %s' % (x if isinstance(x, str) else x.query),
                        nt_cursor=True)
```

### Raw SQL execution:

```
>>> db.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s and tablename=%s', ['public', 'books'])
<cursor object at 0x102352a50; closed: 0>

>>> db.execute('DROP TABLE IF EXISTS "books"')

>>> db.execute('''CREATE TABLE "books" (
	"id" SERIAL NOT NULL,
	"genre" VARCHAR(20) NOT NULL,
	"name" VARCHAR(40) NOT NULL,
	"price" MONEY NOT NULL,
	"published" DATE NOT NULL,
	"modified" TIMESTAMP(6) NOT NULL DEFAULT now()
)''')

>>> db.execute('''ALTER TABLE "books" ADD CONSTRAINT "books_pkey" PRIMARY KEY ("id")''')
```

### Inserting a row:

```
for i in range(1, 10):
    db.insert("books",
              {"genre": "fiction",
               "name": "Book Name vol. %d" % i,
               "price": 1.23 * i,
               "published": "%d-%d-1" % (2000 + i, i)})

db.commit()
```

### Updating rows:

```
with pg_simple.PgSimple(dsn='dbname=pg_simple user=postgres') as db1:
    db1.update('books',
               data={'name': 'An expensive book',
                     'price': 998.997,
                     'type': 'hardback',
                     'modified': 'NOW()'},
               where=('published = %s', [datetime.date(2001, 1, 1)]))
               
    db1.commit()
```


### Fetching a single record:

```
book = db.fetchone('books', 
                   fields=['name', 'published'], 
                   where=('published = %s', [datetime.date(2002, 2, 1)]))
                   
print(book.name + 'was published on ' + book[1])
```

### Fetching multiple records:

```
books = db.fetchall('books',
                    fields=['name AS n', 'genre AS g'],
                    where=('published BETWEEN %s AND %s', [datetime.date(2005, 2, 1), datetime.date(2009, 2, 1)]),
                    order=['published', 'DESC'], 
                    limit=5, 
                    offset=2)

for book in books:
    print(book.n + 'belongs to ' + book[1])
```