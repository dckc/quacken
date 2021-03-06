'''dbbak -- backup GnuCash DB

We use `mysqldump --tab` to produce version-control-happy tab-delimited files,
and we use the `gnome keyring`__ to get the database credentials the same
way GnuCash does.

__ http://developer.gnome.org/gnome-keyring/stable/

'''

import StringIO
import ConfigParser
from contextlib import contextmanager
import logging

from gckey import findMaker

log = logging.getLogger(__name__)


def main(argv,
         set_application_name,
         find_network_password_sync,
         open_write,
         NamedTemporaryFile,
         check_call,
         level=logging.INFO):
    '''
    @param argv: command-line args a la POSIX
    @param set_application_name: a la GTK, for dialogs;
                                 cf `Magnun 17/03/10`__
    @param find_network_password_sync: gnome keyring API capability
    @param NamedTemporaryFile: a la python tempfile module; see configMaker

    __ http://blogs.codecommunity.org/mindbending/bending-gnome-keyring-with-python-part-2/


    >>> commands = []
    >>> main([__name__, MockGK.my_object, 'out_dir'],
    ...      lambda n: (),
    ...      MockGK().find_network_password_sync,
    ...      StringIO.StringIO,
    ...      MockNTF,
    ...      lambda args, stdout=None: commands.append(args))
    >>> commands
    ... #doctest: +NORMALIZE_WHITESPACE
    [('mysqldump', '--defaults-file=tmp_config', '--tab=out_dir',
      '--skip-dump-date', '--skip-comments', 'object0')]
    '''
    logging.basicConfig(level=level)
    set_application_name(__name__)

    findcreds = findMaker(find_network_password_sync)
    client_config = configMaker(NamedTemporaryFile, findcreds)

    if '--splits' in argv:
        db, destpath = argv[2:4]
        fdb = FinDB(db, check_call, client_config)
        with open_write(destpath) as dest:
            fdb.split_detail(dest)
    else:
        db, destdir = argv[1:3]
        fdb = FinDB(db, check_call, client_config)
        fdb.dump_tab(destdir)


class MySQLRunner(object):
    def __init__(self, db,
                 check_call, client_config):
        self.db = db
        self._run = check_call

        self._config = client_config

    def dump_tab(self, destdir,
                 opts=('--skip-dump-date', '--skip-comments'),
                 mysqldump='mysqldump'):
        # http://dev.mysql.com/doc/refman/5.1/en/password-security-user.html
        # http://dev.mysql.com/doc/refman/5.1/en/option-files.html

        with self._config(self.db) as df:
            cmd = (mysqldump,
                   '--defaults-file=' + df.name,
                   '--tab=' + destdir) + opts + (self.db, )
            log.info('mysqldump command: %s', cmd)
            self._run(cmd)


def write_config(fp, items, section='client'):
    '''
    >>> dest = StringIO.StringIO()
    >>> write_config(dest, dict(user='who'))
    >>> print dest.getvalue()
    [client]
    user = who
    <BLANKLINE>
    <BLANKLINE>
    '''
    cp = ConfigParser.SafeConfigParser()
    cp.add_section(section)
    for k, v in items.items():
        cp.set(section, k, v)
    cp.write(fp)


def configMaker(NamedTemporaryFile, findcreds):
    '''Maker to get db credentials and store in temporary mysql config file.

    @param NamedTemporaryFile: a la python tempfile module
    @param find_network_password_sync: a la gnome keyring API

    The first keyring entry matching `server`, `protocol`, and the
    database name will be used.

    Actually, the config file will get re-opened by name, but...

    >>> cc = configMaker(MockNTF,
    ...                  findMaker(MockGK().find_network_password_sync))
    >>> with cc(MockGK.my_object) as conf:
    ...     print conf.name
    ...     print conf.readline().strip()
    ...     print conf.readline().strip()
    tmp_config
    [client]
    password = sekret
    '''
    @contextmanager
    def client_config(db):
        conf = NamedTemporaryFile(suffix='.ini')
        write_config(conf, findcreds(db))
        conf.seek(0)
        yield conf
        conf.close()

    return client_config


class MockNTF(StringIO.StringIO):
    def __init__(self, **kw):
        StringIO.StringIO.__init__(self)
        self.name = 'tmp_config'


class FinDB(MySQLRunner):
    def split_detail(self, dest,
                     sql=('select * from split_detail'
                          ' order by post_date, tx_guid'),
                     mysql='mysql',
                     opts=('--column-names',)):
        with self._config(self.db) as df:
            cmd = (mysql,
                   '--defaults-file=' + df.name) + opts + ('-e', sql, self.db)

            log.info('mysql command: %s', cmd)
            self._run(cmd, stdout=dest)


if __name__ == '__main__':
    def _initial_capabilities():
        import sys
        import glib
        import gnomekeyring as gk
        from subprocess import check_call
        from tempfile import NamedTemporaryFile

        def open_write(n):
            return open(n, 'w')

        return dict(argv=sys.argv,
                    set_application_name=glib.set_application_name,
                    find_network_password_sync=gk.find_network_password_sync,
                    open_write=open_write,
                    check_call=check_call,
                    NamedTemporaryFile=NamedTemporaryFile)

    main(**_initial_capabilities())
