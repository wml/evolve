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

'''

__author__ = 'Will Leszczuk'

import traceback
from evolve.cli.evolvecli import execute_command, UsageError, CommandError

class Command(object):
  '''
    Invokes the interactive evolve shell.
    usage: evolve shell
  '''

  def __call__(self, options):
    tb = traceback.extract_stack()
    if 1 < reduce(lambda a,b: a + 1 if b[0].endswith('shell.py') else a, tb, 0):
      raise CommandError('nested shells not supported')

    while True:
      try: inp = raw_input('evolve$ ')
      except KeyboardInterrupt: 
        print
        break
      args = inp.split(' ')
      if 0 == len(args) or '' == args[0].strip():
        output = 'a command is required (type `commands\' for a list)'
      else:
        try: output = execute_command(args[0], options, *args[1:])
        except UsageError, ex: output = str(ex)
        except CommandError, ex: output = str(ex)
      if not None is output and '' != output: print '=> ' + output
