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

from time import ctime
from evolve.shared.repo import Repository
from evolve.shared.util import columnize_best_fit

class Command(object):
  '''
    Displays the history of an rlink.
    usage: evolve history <path>
  '''
  
  def __call__(self, options, path=''):
    history = Repository(options.repo).get_history(path)
    print
    print '  +' + '-' * 76 + '+'
    columnize_best_fit(
      '  | ',
      80,
        [('Target', 'Modified By', 'Last Modified')]
      + [(h[0], h[1], ctime(h[2])) for h in history],
      newline=False,
      sep = ' | ',
      suffix = ' |',
      header = True
    )
    print '  +' + '-' * 76 + '+'
    print
