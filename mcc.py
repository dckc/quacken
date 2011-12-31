'''mcc -- mint cloud client
'''

import logging
import urllib
import json

import mechanize

log = logging.getLogger(__name__)

def main(argv):
    u, p = argv[1:3]
    c = MintCloudClient()
    c.login(u, p)
    print c.getJsonData()


class MintCloudClient(mechanize.Browser):
    base = 'https://wwws.mint.com/'

    def login(self, username, password, pg='login.event'):
        log.debug('login: open(%s)', self.base + pg)
        self.open(self.base + pg)

        def has_validation(f):
            log.debug('checking form: %s', f)
            return len([c for c in f.controls
                        if c.name == 'validation' and c.value]) > 0

        self.select_form(predicate=has_validation)
        self['username'] = username
        self['password'] = password
        log.debug('login: submit creds.')
        return self.submit()

    def getJsonData(self, task='categories', rnd='1325289755805',
                    path='getJsonData.xevent'):
        ans = self.open('%s%s?%s' % (
            self.base, path,
            urllib.urlencode(dict(task=task, rnd=rnd))))
        return json.load(ans)


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv)

