
import ConfigParser
import logging

from selenium import webdriver
from selenium.webdriver.support import wait
from selenium.webdriver.support.ui import Select

log = logging.getLogger(__name__)


def main(argv):
    import datetime

    logging.basicConfig(level=logging.INFO)

    config_fn = argv[1]
    config = ConfigParser.SafeConfigParser()
    config.read(config_fn)

    browser = webdriver.Chrome()
    for section in argv[2:]:
        site = AcctSite(browser, datetime.date)
        ofx = site.txget(config, section)
        log.info('OFX from %s: %s', section, ofx)


class AcctSite(object):
    def __init__(self, ua, cal):
        self.__ua = ua
        self._cal = cal

    def txget(self, conf, section):
        self.login(conf.get(section, 'home'),
                   conf.get(section, 'logged_in'))

        while conf.has_option(section, 'next'):
            section = conf.get(section, 'next')
            if conf.has_option(section, 'link'):
                self.follow_link(conf.get(section, 'link'))
            if conf.has_option(section, 'submit'):
                self.form_fill(conf, section, conf.get(section, 'submit'))
            if conf.has_option(section, 'ofx'):
                return conf.get(section, 'ofx')

        raise ValueError('no ofx option in any section')

    def login(self, home, logged_in):
        log.info('opening home: %s', home)
        self.__ua.get(home)
        log.debug('opened')
        wt = wait.WebDriverWait(self.__ua, 60, 3)

        def login_text_found(ua):
            return ua.find_element_by_xpath(
                "//div[contains(normalize-space(.), '%s')]" % logged_in)

        log.info('Waiting for user to log in...')
        wt.until(login_text_found)

    def follow_link(self, which):
        if which.startswith('"'):
            e = self.__ua.find_element_by_xpath(
                '//a[%s]' % which[1:-1])
        else:
            e = self.__ua.find_element_by_link_text(which)
        e.click()

    def form_fill(self, conf, section, submit):
        f = self.__ua.find_element_by_xpath(
            conf.get(section, 'form')[1:-1])

        for n, v in conf.items(section):
            if n.startswith('select_'):
                name, idx = v.split(' ', 1)
                select_option(f, name, int(idx))
            if n.startswith('radio_'):
                name, value = v.split(' ', 1)
                set_radio(f, name, value)
            elif n.startswith('text_'):
                name, value = v.split(' ', 1)
                set_text(f, name, value)
            elif n == 'today':
                mdy = self._cal.today().strftime("%02m/%02d/%Y")
                set_text(f, v, mdy)
            elif n == 'submit':
                submit = v

        btn = (f.find_element_by_xpath(submit[1:-1])
               if submit.startswith('"')
               else f.find_element_by_name(submit))
        btn.click()


def select_option(f, name, idx):
    sel = Select(f.find_element_by_name(name))
    sel.select_by_index(idx)


def set_radio(f, name, value):
    val_constraint = (("and @id='%s'" % value[3:])
                      if value.startswith('id=') else
                      ("and @value='%s'" % value))
    radio = f.find_element_by_xpath(
        ".//input[@type='radio' and @name='%s' %s]" % (
            name, val_constraint))
    radio.click()


def set_text(f, name, value):
    field = f.find_element_by_name(name)
    field.clear()
    field.send_keys(value)


if __name__ == '__main__':
    import sys
    main(sys.argv)
