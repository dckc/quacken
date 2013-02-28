'''gckey -- gnome keyring access for GnuCash mysql database
'''

import logging

log = logging.getLogger(__name__)


def findMaker(find_network_password_sync,
              server='localhost', protocol='mysql'):
    '''Maker to get db credentials.

    @param find_network_password_sync: a la gnome keyring API

    The first keyring entry matching `server`, `protocol`, and the
    database name will be used.

    Actually, the config file will get re-opened by name, but...

    >>> f = findMaker(MockGK().find_network_password_sync)
    >>> f(MockGK.my_object)
    {'password': 'sekret', 'user': 'user0'}
    '''
    def findcreds(db):
        log.info('looking for keys: %s',
                 dict(protocol=protocol, server=server, object=db))
        ans = find_network_password_sync(protocol=protocol, server=server,
                                         object=db)
        log.debug('creds: %s', ans[0].keys())
        return dict([(k, ans[0][k]) for k in ('user', 'password')])

    return findcreds


class MockGK(object):
    my_object = 'object0'
    my_protocol = 'mysql'
    my_server = 'localhost'

    my_user = 'user0'
    my_password = 'sekret'

    def find_network_password_sync(self,
                                   user=None,
                                   domain=None,
                                   server=None,
                                   object=None,
                                   protocol=None,
                                   authtype=None,
                                   port=0):
        if (object == self.my_object
            and protocol == self.my_protocol
            and server == self.my_server):
            return [dict(user=self.my_user, password=self.my_password)]

        raise IOError  # well, really some other error, but...


def _integration_test(db, find_network_password_sync):
    find = findMaker(find_network_password_sync)
    print find(db)


if __name__ == '__main__':
    def _initial_capabilities():
        import sys
        import gnomekeyring as gk

        db = sys.argv[1]
        return dict(db=db,
                    find_network_password_sync=gk.find_network_password_sync)

    _integration_test(**_initial_capabilities())
