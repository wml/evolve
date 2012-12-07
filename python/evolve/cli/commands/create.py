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

from evolve.shared.repo import Repository, ArgumentError
from evolve.cli.commands import CommandError

class Command(object):
  '''
    Creates a new meta folder in the evolve repository.
    usage: evolve create [project|release|rlink] <path>
  '''

  def __call__(self, options, type, path, name=None):
    if not type in ['project', 'release', 'rlink']:
      raise CommandError('bad meta type passed to create')

    args = [path]
    if 'rlink' == type:
      if None is name:
        raise CommandError('rlink name is required')
      args.append(name)
    if 'rlink' != type and not None is name:
      raise CommandError('too many arguments to create')

    repo = Repository(options.repo)
    getattr(repo, 'create_' + type)(*args)
