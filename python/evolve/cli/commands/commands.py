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

import os
from evolve.shared.util import columnize, get_modules, coalesce

class Command(object):
  '''
    Lists the available evolve commands in this installation.
    usage: evolve commands
  '''

  _modprefix = 'evolve.cli.commands.'

  def _get_files():
    return [
      c for c in os.listdir(os.path.dirname(__file__)) 
        if c.endswith('.py') and -1 == c.find('__init__')
    ]
  _get_files = staticmethod(_get_files)

  def __call__(self, options):
    files = Command._get_files()
    files.sort()
    modules = get_modules(Command._modprefix, files)
    commandWidth = 2 + max(*[len(n) for (n, m) in modules])
    striplen = len(Command._modprefix)
    columnize(
      '  ',
      (commandWidth, 77 - commandWidth), 
      [(s.__name__[striplen:], coalesce(s.Command.__doc__, '').strip()) 
        for s in [getattr(m.cli.commands, n) for (n, m) in modules]
      ]
    )
