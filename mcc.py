'''mcc -- mint cloud client
'''

import logging
import urllib
import json
import getpass

import mechanize

log = logging.getLogger(__name__)

def main(argv):
    u, outf = argv[1:3]
    out = open(outf, 'w')  # fail early
    c = MintCloudClient()
    c.login(u, getpass.getpass('Mint password for %s:' % u))

    #pprint.pprint(c.getCategories())
    flatten(c.allTransactions(), out)


def flatten(arr, o):
    o.write('[')
    first = True
    for item in arr:
        if not first:
            o.write(',\n')
        else:
            first = False
        # TODO: make sure newlines in strings are escaped
        o.write(json.dumps(item))
    o.write(']')


class MintCloudClient(mechanize.Browser):
    '''
    .. todo:: figure out how rnd works, i.e. whether it's required etc.
    '''
    base = 'https://wwws.mint.com/'

    def login(self, username, password, pg='login.event'):
        log.debug('login: open(%s)', self.base + pg)
        self.open(self.base + pg)

        def has_validation(f):
            return len([c for c in f.controls
                        if c.name == 'validation' and c.value]) > 0

        self.select_form(predicate=has_validation)
        self['username'] = username
        self['password'] = password
        log.debug('login: submit creds.')
        return self.submit()

    def getJsonData(self, path='getJsonData.xevent',
                    **urlparams):
        log.debug('get JSON data: %s %s', path, urlparams)
        ans = self.open('%s%s?%s' % (
            self.base, path, urllib.urlencode(urlparams)))
        return json.load(ans)

    def getCategories(self):
        return self.getJsonData(task='categories', rnd='1325289755805')

    def allTransactions(self, rnd='1325292983069'):
        alltx = []
        offset = 0
        while 1:
            data = self.getJsonData(queryNew='',
                                    offset=offset,
                                    filterType='cash',  # monkey see...
                                    comparableType=0,
                                    task='transactions',
                                    rnd=rnd)
            txns = data['set'][0].get('data', [])
            if not txns:
                break
            alltx.extend(txns)
            log.debug('txn #%d: %s', offset,
                      [txns[-1][f] for f in ('date', 'merchant', 'amount')])
            offset += len(txns)

            for tx in txns:
                if tx['isChild']:
                    p = self.parent(tx['id'])
                    tx['parent'] = p['id']
                    # Oops... this may fetch the same parent more than once.
                    # alltx should be a dict.
                    alltx.append(p)


        return alltx

    def parent(self, id, rnd='1325341961533',
               path='listSplitTransactions.xevent'):
        data = self.getJsonData(path=path, txnId='%s:0' % id, rnd=rnd)
        return data['parent'][0]

    def listTransaction(self, queryNew='', offset=0, filterType='cash',
                        comparableType=3, rnd='1325292983068',
                        path='listTransaction.xevent'):
        return self.getJsonData(path='listTransaction.xevent',
                                queryNew=queryNew,
                                offset=offset,
                                filterType=filterType,
                                comparableType=comparableType,
                                rnd=rnd)

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv)

