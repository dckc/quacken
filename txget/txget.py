
from datetime import date, datetime, timedelta
from functools import partial as pf_
from functools import partial as classOf  # TODO: use fp.classOf?
import ConfigParser
import logging

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select

log = logging.getLogger(__name__)


def main(argv, open_arg, make_driver, calendar, clock):
    '''
    :type argv: IndexedSeq[String]
    :type open_arg: String => File
    :type make_driver: () => WebDriver
    :type calendar: { def today(): date }
    :type clock: { def now(): datetime }
    '''
    logging.basicConfig(level=logging.INFO)

    config_fn = argv[1]
    config = ConfigParser.SafeConfigParser()
    config.readfp(open_arg(config_fn), config_fn)

    browser = make_driver()
    for section in argv[2:]:
        site = AcctSite(browser, calendar, clock)
        ofx = site.txget(config, section)
        log.info('OFX from %s: %s', section, ofx)


def _imports_are_not_unused(x):
    ''':type x: Object'''
    date(2000, 1, 1)
    datetime(2000, 1, 1, 12, 30, 30)

    isinstance(x, classOf(WebDriver))
    isinstance(x, classOf(WebElement))


class AcctSite(object):
    def __init__(self, ua, cal, clock):
        '''
        :type ua: WebDriver
        :type cal: { def today(): date }
        :type clock: { def now(): datetime }

        '''
        self.__ua = ua
        self._cal = cal
        self._clock = clock

    def txget(self, conf, section_):
        '''
        :type conf: ConfigParser.ConfigParser
        :type section_: String
        :rtype: String
        '''
        var, section = 0, section_  # noqa
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
        '''
        :param home: home page URL
        :type home: String
        :param logged_in: text that signals log in is complete
        :type logged_in: String

        TODO: infer types from default int, string args
        :type wait_time: Int
        :type poll_period: Int
        '''
        log.info('opening home: %s', home)
        self.__ua.get(home)
        log.debug('opened')
        wt = WebDriverWait(self.__ua, wait_time, poll_period)

        def login_text_found(ua):
            ''':type ua: WebDriver'''
            return ua.find_element_by_xpath(
                "//div[contains(normalize-space(.), '%s')]" % logged_in)

        log.info("Waiting 'till %s for user to log in...",
                 self._clock.now() + timedelta(seconds=wait_time))
        wt.until(login_text_found)
        log.info('Logged in (%s).', logged_in)

    def follow_link(self, which, timeout=10):
        '''
        :type which: String
        :type timeout: Int
        '''
        def by_xpath(ua):
            ''':type ua: WebDriver'''
            return ua.find_element_by_xpath(
                '//a[%s]' % which[1:-1])

        def by_text(ua):
            ''':type ua: WebDriver'''
            return ua.find_element_by_link_text(which)

        wt = WebDriverWait(self.__ua, timeout)
        e = wt.until(by_xpath if which.startswith('"') else by_text)
        e.click()

    def form_fill(self, conf, section):
        '''
        :type conf: ConfigParser.ConfigParser
        :type section: String
        '''
        f = self.__ua.find_element_by_xpath(
            conf.get(section, 'form')[1:-1])

        submit = ""

        var, n, v = 0, "", ""  # noqa

        for n, v in conf.items(section):
            if n.startswith('select_'):
                name, idx = n_v(v)
                select_option(f, name, int(idx))
            if n.startswith('radio_'):
                name, value = n_v(v)
                set_radio(f, name, value)
            elif n.startswith('text_'):
                name, value = n_v(v)
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
    '''
    :type f: WebElement
    :type name: String
    :type idx: Int
    '''
    sel = Select(f.find_element_by_name(name))
    sel.select_by_index(idx)


def set_radio(f, name, value):
    '''
    :type f: WebElement
    :type name: String
    :type value: String
    '''
    val_constraint = (("and @id='%s'" % value[3:])
                      if value.startswith('id=') else
                      ("and @value='%s'" % value))
    radio = f.find_element_by_xpath(
        ".//input[@type='radio' and @name='%s' %s]" % (
            name, val_constraint))
    radio.click()


def set_text(f, name, value):
    '''
    :type f: WebElement
    :type name: String
    :type value: String
    '''
    field = f.find_element_by_name(name)
    field.clear()
    field.send_keys(value)


def make_use_chromium(mk_chrome,
                      path='/usr/lib/chromium-browser/chromium-browser'):
    '''Use Chromium to work around problems with Chrome 29.

    to wit:
    Unknown command 'WaitForAllTabsToStopLoading'
    cf. https://bitbucket.org/DanC/quacken/issue/1/unknown-command

    :type mk_chrome: Options => WebDriver
    :type path: String
    '''
    def use_chromium():
        use_chromium = Options()
        use_chromium.binary_location = path
        return mk_chrome(use_chromium)
    return pf_(use_chromium)


def typed(x, t):
    # TODO: use fp.typed?
    return x


def n_v(s):
    '''
    :type s: String
    '''
    l = s.split(' ', 1)
    return l[0], l[1]


if __name__ == '__main__':
    def _main_with_caps():
        from sys import argv
        import datetime

        from selenium.webdriver import Chrome

        def open_arg(path):
            ''':type path: String'''
            if path not in argv:
                raise IOError('not authorized CLI arg: %s' % path)
            return open(path)

        def mk_chrome(options):
            ''':type options: Options'''
            return Chrome(chrome_options=options)

        return main(argv=argv[:], open_arg=open_arg,
                    calendar=datetime.date, clock=datetime.datetime,
                    make_driver=make_use_chromium(pf_(mk_chrome)))

    _main_with_caps()
