'''mcc -- mint cloud client
'''

import logging
import urllib
import json

import mechanize

log = logging.getLogger(__name__)

def main(argv):
    import sys

    u, p = argv[1:3]
    c = MintCloudClient()
    c.login(u, p)

    #pprint.pprint(c.getCategories())
    json.dumps(c.allTransactions(), sys.stdout, ensure_ascii=False, indent=2)


class MintCloudClient(mechanize.Browser):
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
                                    filterType='cash',
                                    comparableType=0,
                                    task='transactions',
                                    rnd=rnd)
            txns = data['set'][0].get('data', [])
            if not txns:
                break
            alltx.extend(txns)
            offset += len(txns)

        return alltx

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

