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

from evolve.shared.repo import Repository
from evolve.shared.util import columnize_best_fit, interleave_tuples

class Command(object):
  '''
    Lists the contents of the specified meta folder.
    usage: evolve ls [-R] <path>='/'
  '''
  
  TypeMap = {
    'repository root': '*',
    'project':         'P',
    'release':         'R',
    'rlink':           'L',
  }

  def __call__(self, options, path=''):
    repo = Repository(options.repo)
    getattr(self, 'ls' if not options.recursive else 'graph')(repo, path)

  def ls(self, repo, path):
    (target, children) = repo.get_directory_contents(path)
    children = interleave_tuples(children)

    path = path.strip().strip('/')
    if '' == path: path = '/'

    print
    print '  Path:                ' + path
    for attr in target:
      print '  %-20.20s %s' % (attr[0] + ':', attr[1])

    if 0 < len(children):
      print '  Child Count:         ' + str(len(children))
      print
      print '  Children'
      print '  +' + '-' * 76 + '+'
      columnize_best_fit(
        '  | ',
        80,
          [tuple(['Name'] + [k for k,v in children[children.keys()[0]]])]
        + [
          tuple([c[0]] + [v for k,v in c[1]])
          for c in sorted(children.iteritems())
        ],
        newline=False,
        sep = ' | ',
        suffix = ' |',
        header = True
      )
      print '  +' + '-' * 76 + '+'
    
    # TODO: print dependencies

    print

  def graph(self, repo, path):
    print
    def _graph(path, more, type):
      path = '/' if '' == path else path.split('/')[-1]
      print '  %s+ [%s] %s' % (
        ''.join(['|  ' if m else ' ' * 3 for m in more[:-1]]),
        Command.TypeMap[type],
        path
      )
    repo.walk(path, _graph)
    print
