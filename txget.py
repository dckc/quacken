
import ConfigParser
import logging

from selenium import webdriver
from selenium.webdriver.support import wait

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
        self.login(conf.get(section, 'home'),
                   conf.get(section, 'logged_in'))

    def login(self, home, logged_in):
        log.info('opening home: %s', home)
        self.__ua.get(home)
        log.debug('opened')
        wt = wait.WebDriverWait(self.__ua, 60, 3)

        def login_text_found(ua):
            return ua.find_element_by_xpath("//div[contains(normalize-space(.), '%s')]" % logged_in)

        wt.until(login_text_found)


if __name__ == '__main__':
    import sys
    main(sys.argv)
