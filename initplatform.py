#!/usr/bin/python

# Copyright (c) 2010 William Leszczuk
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

'''
  Initializes or reinitializes the `evolve' platform:
   - creates /var/log/evolve and /var/lib/evolve.uid, if they don't exist
   - logs to /var/log/evolve/platform.log
   - creates the `evolve' user account
   - changes the owner of the `evolve' bootstrapper to that user and adds the
       setuid permission
'''

__author__ = 'Will Leszczuk'

import os, pwd, random, logging
from optparse import OptionParser
from evolve.shared.util import do_or_die
from evolve.cli import evolvecli

_LogPath = '/var/log/evolve'
_LogFilePath = _LogPath + '/platform.log'
_Bootstrapper = '/usr/bin/evolve'
_logger = None

def _gen_phrase(length=20):
  phrasechars = \
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' \
    '1234567890-=!@#$%^&*()_+'
  return ''.join(
    [phrasechars[random.randint(0,len(phrasechars) - 1)] for i in range(length)]
  )

class _AccountManager:
  __UidPath = '/var/lib/evolve.uid'

  def __init__(self, username):
    self.username = username
    self.initialized = self._is_initialized()

  def _is_initialized(self):
    result = True
    try: self.uid = pwd.getpwnam(self.username).pw_uid
    except KeyError: result = False
    return result

  def create(self):
    assert(not self.initialized)
    self._add_user()
    self._set_cli_permissions()

  def _add_user(self):
    olduid = self._read_old_uid()
    do_or_die(
      "useradd %s -d '/home/%s' -mp '%s' -K PASS_MAX_DAYS=-1 -K UMASK=0133 %s"
      % (
        '' if None is olduid else ('-u %d' % olduid), 
        self.username, 
        _gen_phrase(), 
        self.username
      )
    )
    self.uid = pwd.getpwnam(self.username).pw_uid
    self._write_old_uid(self.uid)
    _logger.info('created user [%s] ([%d])' % (self.username, self.uid))

  def _read_old_uid(self):
    if os.path.exists(_AccountManager._AccountManager__UidPath):
      with open(_AccountManager._AccountManager__UidPath, 'r') as uidfile:
        olduid = int(uidfile.readline())
      _logger.info(
          'recovered uid [%d] from [%s]' 
        % (olduid, _AccountManager._AccountManager__UidPath)
      )
      return olduid

  def _write_old_uid(self, uid):
    with open(_AccountManager._AccountManager__UidPath, 'w') as uidfile:
      uidfile.write(str(uid))

  def _set_cli_permissions(self):
    assert(hasattr(self, 'uid'))
    cli = _Bootstrapper
    os.chown(cli, self.uid, self.uid)
    _logger.info(
        'changed owner of [%s] to %s:%s ([%d])' 
      % (cli, self.username, self.username, self.uid)
    )
    os.chmod(cli, 04755)
    _logger.info('set mod to [4755] on [%s]' % cli)

  def delete(self, transferuser):
    self._revert_cli_permissions(transferuser)
    self._delete_user()

  def _delete_user(self):
    do_or_die('userdel %s' % self.username)
    _logger.info('deleted user [%s] ([%d])' % (self.username, self.uid))
    del self.uid
    self.initialized = False

  def _revert_cli_permissions(self, transferuser):
    transferuid = pwd.getpwnam(transferuser).pw_uid
    cli = _Bootstrapper
    os.chmod(cli, 0755)
    _logger.info('set mod to [0755] on [%s]' % cli)
    os.chown(cli, transferuid, transferuid)
    _logger.info(
        'changed owner of [%s] to %s:%s ([%d])'
      % (cli, transferuser, transferuser, transferuid)
    )

def _init_logging():
  global _logger 
  _logger = logging.getLogger()
  _logger.setLevel(logging.INFO)
  consolehandler = logging.StreamHandler()
  _logger.addHandler(consolehandler)
  filehandler = logging.FileHandler(_LogFilePath)
  filehandler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
  )
  _logger.addHandler(filehandler)

def _init_directory_structure():
  if not os.path.exists(_LogPath): os.mkdir(_LogPath, 0744)

def _set_directory_permissions(username):
  do_or_die('chown -R %s:%s \'%s\'' % (username, username, _LogPath))
  _logger.info(
      'recursively changed owner of [%s] to %s:%s'
    % (_LogPath, username, username)
  )
  do_or_die('chmod -R 744 \'%s\'' % _LogPath)
  _logger.info('recursively set mod to 744 on [%s]' % _LogPath)

def _get_options():
  parser = OptionParser(description=__doc__, usage='usage: %prog [OPTIONS]')
  parser.add_option(
    '-f', '--force', action='store_true', dest='force', default=False,
    help='force account reinitialization if the evolve user exists'
  )
  return parser.parse_args()[0]

if '__main__' == __name__:
  sudouser = os.getenv('SUDO_USER')
  if 0 != os.geteuid() or None is sudouser: 
    print 'this script must be run as root via sudo'
  else:
    options = _get_options()
    _init_directory_structure()
    _init_logging()
     
    acctmgr = _AccountManager(evolvecli.EvolveUser)
    if acctmgr.initialized:
      if not options.force:
        print 'account already initialized (use --force to reinit)'
      else:
        confstring = '!' + _gen_phrase(7)
        if confstring == raw_input(
          'type [%s] to reinitialize the `evolve\' user account: ' % confstring
        ):
          acctmgr.delete(sudouser)

    if not acctmgr.initialized:
      acctmgr.create()
      _set_directory_permissions(evolvecli.EvolveUser)
