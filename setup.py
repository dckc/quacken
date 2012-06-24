'''
For now, we assume some familiarity with virtualenv,
`The Hitchhiker's Guide to Packaging`__.

__ http://guide.python-distribute.org/

Getting Started
---------------

- cd <directory containing this file>

- `$venv/bin/python setup.py develop` to install dependencies
  in your development environment.


http://pypi.python.org/pypi/keyring/0.9.2

tested with:

http://code.google.com/p/chromedriver/downloads/list
chromedriver_linux64_21.0.1180.4.zip   6.7 MB
SHA1 Checksum:	 4f8f043f3893ca0969176c8cf4868117b47e3781

'''
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = __doc__ # TODO: open(os.path.join(here, 'README.rst')).read()
CHANGES = ''  # TODO: open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'selenium',
    ]

setup(name='txget',
      version='0.1',
      description='txget',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved",
        "License :: OSI Approved :: Apache Software License",
        ],
      author='Dan Connolly',
      author_email='dckc@madmode.com',
      url='http://www.madmode.com/',
      keywords='ofx web',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='txget',
      install_requires=requires,
      )



