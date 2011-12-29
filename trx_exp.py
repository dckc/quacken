'''trx_exp -- is (date, original description, amount) unique?
'''

import csv
import logging
import datetime

import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Integer, String, Date, DECIMAL, Enum

Base = declarative_base()
Session = sqlalchemy.orm.sessionmaker()

Money = DECIMAL(precision=8, scale=2)
FreeText = String(250)
TagList = String(250)
Name = String(80)

log = logging.getLogger(__name__)


def main(argv):
    if '--project' in argv:
        trx_in, trx_out = argv[2:5]
        project(open(trx_in), open(trx_out, 'w'))
        return

    export_file, engine_url = argv[1:3]
    import_csv(open(export_file), sqlalchemy.create_engine(engine_url))


class Trx(Base):
    __tablename__ = 'mintexport'
    id = Column(Integer, primary_key=True)
    num = Column(Name)
    date = Column(Date, nullable=False)
    description = Column(FreeText)
    original_description = Column(FreeText)
    amount = Column(Money, nullable=False)
    transaction_type = Column(Enum('debit', 'credit'))
    category = Column(Name)
    account_name = Column(Name)
    labels = Column(TagList)
    notes = Column(FreeText)


def import_csv(lines, engine,
               excluded_categories=('Exclude From Mint')):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    rows = csv.reader(lines)
    rows.next()  # skip schema
    cols = [c.name for c in Trx.__table__.columns][2:]  # id, num not imported
    cat_col = cols.index('category')
    log.debug('cols: %s', cols)
    engine.execute(Trx.__table__.insert(),
                   [dict(zip(cols, [mkdate(row[0])] + row[1:]))
                    for row in rows
                    if row[cat_col] not in excluded_categories])


def mkdate(mm_dd_yyyy):
    '''
    >>> mkdate("12/22/2011")
    datetime.date(2011, 12, 22)
    '''
    m, d, y = map(int, mm_dd_yyyy.split('/'))
    return datetime.date(y, m, d)


def project(lines, outfp,
            exclude_cols=('labels', 'notes'),
            select_accts=('PERFORMANCE CHECKING',),
            exclude_cats=('Exclude From Mint',)):
    inrows = csv.reader(lines)
    cols = [c.name for c in Trx.__table__.columns][2:]  # id, num not imported
    ax = cols.index('account_name')
    cx = cols.index('category')
    colx = [cols.index(c) for c in cols
            if c not in exclude_cols]
    log.debug('cols, colx: %s, %s', cols, colx)
    outrows = csv.writer(outfp, quoting=csv.QUOTE_ALL,
                         lineterminator='\n')
    outrows.writerows([
        [row[ix] for ix in colx] for row in inrows
        if row[ax] in select_accts and row[cx] not in exclude_cats])


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv)
