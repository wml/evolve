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
  Invokes one of the `evolve' platform commands.
  Author: Will Leszczuk
'''

__author__ = 'Will Leszczuk'

# TODO: log command before execute, dont print return val (never any)

import sys, logging, os, time, pwd
from optparse import OptionParser
from evolve.shared.util import get_logger
from evolve.shared.repo import RepoError, ArgumentError
from evolve.cli.commands import CommandError

class UsageError(Exception): pass

EvolveUser = 'evolve'
_modmap = { }
_LogPath = '/var/log/evolve/'
_CommandLog = _LogPath + 'commands.log'
_SessionLog = _LogPath + 'sessions.log'

def get_command(name):
  if not name in _modmap: 
    try: _modmap[name] = __import__('evolve.cli.commands.' + name)
    except ImportError, ex: 
      raise UsageError('invalid command [%s]: [%s]' % (name, str(ex)))
  return getattr(_modmap[name].cli.commands, name).Command()

def execute_command(name, options, *args):
  '''
    Executes an evolve command by name with the supplied options and arguments.
    Returns the result code of the command, or 1 in case of an invocation error.
  '''
  command = get_command(name)
  logger = get_logger(
    _CommandLog,
    logging.DEBUG if options.debug else logging.INFO
  )

  try: result = command(options, *args)
  except TypeError, ex:
    # TODO: kind of crappy but it works
    if -1 != str(ex).find('__call__() takes '):
      raise UsageError('argument mismatch (type `help\' <command> for usage)')
    raise
  except ArgumentError, ex:
    raise UsageError(ex)
  except RepoError, ex:
    _log_command(logger.error, name, args, str(ex), options)
    raise

  _log_command(logger.info, name, args, result, options)
  return result

def _log_command(meth, name, args, result, options):
  meth(
      '%s(%s) => %s (options = %s)'
    % (
      name,
      ', '.join(args),
      result,
      str(
        dict([
          (key, val) for (key, val) in eval(str(options)).iteritems()
          if not None is val and '' != val and False != val
        ])
      )
    )
  )

def _get_options():
  parser = OptionParser(
    description=__doc__, usage='Usage: evolve [OPTIONS] <command> [<arg> ...]'
  )
  parser.add_option(
    '-d', '--debug', action='store_true', dest='debug', 
    default=False, help='turns on debug logging'
  )
  parser.add_option(
    '-r', '--repo', action='store', dest='repo', 
    default=os.getenv('EVOLVE_REPO'),
    help='the evolve repository upon which to operate'
  )
  parser.add_option(
    '-R', '--recursive', action='store_true', dest='recursive',
    default=False, help='perform action recursively'
  )
  parser.add_option(
    '-f', '--force', action='store_true', dest='force',
    default=False, help='force action, suppress confirmations'
  )
  return parser.parse_args()

def _validate_args(options, args):
  if 1 > len(args):
    raise UsageError('a command is required (use `commands\' for a list)')
  elif None is options.repo:
    raise UsageError('an evolve repository is required')

def _log_session(start):
  logger = logging.getLogger('sessions')
  logger.setLevel(logging.INFO)
  filehandler = logging.FileHandler(_SessionLog)
  filehandler.setFormatter(logging.Formatter('%(message)s'))
  logger.addHandler(filehandler)
  logger.info('\t'.join([
    str(start),
    str(time.time()),
    pwd.getpwuid(os.geteuid()).pw_name + '/' + str(os.geteuid()),
    pwd.getpwuid(os.getuid()).pw_name + '/' + str(os.getuid()),
    sys.executable,
    '"%s"' % (' '.join([a.replace(' ', '\\ ') for a in sys.argv]))
  ]))

if '__main__' == __name__:
  success = 1
  logsession = False
  start = time.time()
  options, args = _get_options()

  from evolve.cli.evolvecli import UsageError

  try:
    _validate_args(options, args)
    logsession = True
    output = execute_command(args[0], options, *args[1:])
  except (UsageError, CommandError), ex:
    output = str(ex)
  else:
    success = 0
  finally: 
    if logsession: _log_session(start)

  if not None is output and not '' == output: print output
  sys.exit(success)
