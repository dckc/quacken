
import ConfigParser
import logging

from selenium import webdriver


log = logging.getLogger(__name__)


def main(argv):
    logging.basicConfig(level=logging.DEBUG)

    config_fn, section = argv[1:3]
    config = ConfigParser.SafeConfigParser()
    config.read(config_fn)

    browser = webdriver.Chrome()
    site = AcctSite(browser)
    site.txget(config, section)


class AcctSite(object):
    def __init__(self, ua):
        self.__ua = ua

    def txget(self, conf, section):
        home = conf.get(section, 'home')
        log.info('opening home: %s', home)
        ua = self.__ua
        ua.get(home)
        log.debug('opened')


if __name__ == '__main__':
    import sys
    main(sys.argv)
