
import ConfigParser
import logging
from datetime import timedelta

from selenium.webdriver.support import wait
from selenium.webdriver.support.ui import Select

log = logging.getLogger(__name__)


def main(argv, open_arg, make_driver, calendar, clock):
    logging.basicConfig(level=logging.INFO)

    config_fn = argv[1]
    config = ConfigParser.SafeConfigParser()
    config.readfp(open_arg(config_fn), config_fn)

    browser = make_driver()
    for section in argv[2:]:
        site = AcctSite(browser, calendar, clock)
        ofx = site.txget(config, section)
        log.info('OFX from %s: %s', section, ofx)


class AcctSite(object):
    def __init__(self, ua, cal, clock):
        self.__ua = ua
        self._cal = cal
        self._clock = clock

    def txget(self, conf, section):
        self.login(conf.get(section, 'home'),
                   conf.get(section, 'logged_in'))

        while conf.has_option(section, 'next'):
            section = conf.get(section, 'next')
            log.info('on to section: %s', section)
            if conf.has_option(section, 'link'):
                self.follow_link(conf.get(section, 'link'))
            if conf.has_option(section, 'form'):
                self.form_fill(conf, section)
            if conf.has_option(section, 'ofx'):
                return conf.get(section, 'ofx')

        raise ValueError('no ofx option in any section')

    def login(self, home, logged_in,
              wait_time=60, poll_period=3):
        log.info('opening home: %s', home)
        self.__ua.get(home)
        log.debug('opened')
        wt = wait.WebDriverWait(self.__ua, wait_time, poll_period)

        def login_text_found(ua):
            return ua.find_element_by_xpath(
                "//div[contains(normalize-space(.), '%s')]" % logged_in)

        log.info("Waiting 'till %s for user to log in...",
                 self._clock.now() + timedelta(seconds=wait_time))
        wt.until(login_text_found)
        log.info('Logged in (%s).', logged_in)

    def follow_link(self, which, timeout=10):
        def by_xpath(ua):
            return ua.find_element_by_xpath(
                '//a[%s]' % which[1:-1])

        def by_text(ua):
            return ua.find_element_by_link_text(which)

        wt = wait.WebDriverWait(self.__ua, timeout)
        e = wt.until(by_xpath if which.startswith('"') else by_text)
        e.click()

    def form_fill(self, conf, section):
        f = self.__ua.find_element_by_xpath(
            conf.get(section, 'form')[1:-1])

        submit = None

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

        if submit:
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


def make_use_chromium(Chrome,
                      path='/usr/lib/chromium-browser/chromium-browser'):
    '''Use Chromium to work around problems with Chrom 29.

    to wit:
    Unknown command 'WaitForAllTabsToStopLoading'
    cf. https://bitbucket.org/DanC/quacken/issue/1/unknown-command
    '''
    def use_chromium():
        from selenium.webdriver.chrome.options import Options
        use_chromium = Options()
        use_chromium.binary_location = path
        return Chrome(chrome_options=use_chromium)
    return use_chromium


if __name__ == '__main__':
    def _initial_caps():
        from sys import argv
        import datetime

        from selenium import webdriver

        def open_arg(path):
            if path not in argv:
                raise IOError('not authorized CLI arg: %s' % path)
            return open(path)

        return dict(argv=argv[:], open_arg=open_arg,
                    calendar=datetime, clock=datetime.datetime,
                    make_driver=make_use_chromium(webdriver.Chrome))

    main(**_initial_caps())
