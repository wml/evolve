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
  Generic utility functions used by evolve.
  Author: Will Leszczuk
'''

__author__ = 'Will Leszczuk'

import os, logging, commands, pwd

_logs = { }

# TODO: rolling file appender
def get_logger(path, level):
  name = path.replace('/', '-')
  if not name in _logs:
    if not os.path.exists(os.path.dirname(path)):
      os.makedirs(os.path.dirname(path))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    filehandler = logging.FileHandler(path)
    filehandler.setFormatter(
      logging.Formatter(
        '%(asctime)s - %(process)d - %(user)s - %(levelname)s - %(message)s'
      )
    )
    logger.addHandler(filehandler)

    logger = logging.LoggerAdapter(
      logger,
      { 'user': pwd.getpwuid(os.getuid()).pw_name + '/' + str(os.getuid()) }
    )

    _logs[name] = logger

  return _logs[name]

def get_modules(package, files):
  return [
    (modname, __import__(package + modname))
      for modname in [
        os.path.basename(f[:-3]) 
        for f in files
        if f.endswith('.py') and not f.startswith('.')
      ]
  ]

def columnize(prefix, widths, values, newline=True, sep=' ', suffix=''):
  values = [
    tuple([str(v) for v in valtuple])
    for valtuple in values
  ]
  if newline: print
  columns = len(widths)
  formatstring = prefix + sep.join('%%-%ds' % w for w in widths) + suffix

  Huge = 10000000
  def natural_or_huge(v): return v if 0 <= v else Huge
  def chopidx(v, w):
    l = len(v)
    return min(
      l,
      natural_or_huge(v.find('\n')),
      natural_or_huge(v.rfind(' ', 0, w)) if l > w else Huge,
      w
    )

  for valtuple in values:
    valset = [v for v in valtuple] + ['' for i in range(columns-len(valtuple))]
    while any(0 < len(valset[i]) for i in range(columns)):
      print formatstring % \
        tuple(valset[i][:chopidx(valset[i], widths[i])] for i in range(columns))
      valset = tuple(
        valset[i][chopidx(valset[i], widths[i]):].lstrip('\n ') 
        for i in range(columns)
      )
    if newline: print

def columnize_best_fit(
  prefix, maxwidth, values, newline=True, sep=' ', suffix='', header=False
):
  values = [
    tuple([str(v) for v in valtuple])
    for valtuple in values
  ]
  largest = []
  for valtuple in values:
    for i in range(len(valtuple)):
      if 1+i > len(largest):
        largest.append(len(valtuple[i]))
      elif len(valtuple[i]) > largest[i]:
        largest[i] = len(valtuple[i])
    
  adjustedmax = \
    maxwidth - (len(sep) * (len(largest) - 1)) - len(prefix) - len(suffix)

  toadjust = len(largest) - 1
  while sum(largest) > adjustedmax and toadjust != -1:
    # default strategy - trim cols to no less than 8 chars starting with the
    # last and moving backwards
    largest[toadjust] = max(largest[toadjust] - (sum(largest)-adjustedmax), 10)
    toadjust -= 1

  if sum(largest) < adjustedmax:
    largest[len(largest)-1] += adjustedmax - sum(largest)

  if header and 1 < len(values):
    values = \
        values[:1] \
      + [tuple(['-' * largest[i] for i in range(len(largest))])] \
      + values[1:]

  columnize(prefix, largest, values, newline, sep, suffix)

def first(fn, *args):
  for a in args:
    if fn(a):
      return a

def coalesce(*args):
  return first(lambda arg: not None is arg, *args)

def do_or_die(command):
  success, output = commands.getstatusoutput(command)
  if 0 != success:
    raise Exception(
      'failed to execute command [%s]: result code = [%d]' % (command, success)
    )

def interleave_tuples(listofkvs):
  '''
    Takes a map of ordered key-value tuples, and interleaves the 'keys'
    contained in the top-level value into each other value, using empty-string
    as the default. Key ordering is maintained according to the order of its
    first appearance.
    
    For example, interleave_keys({
      'C': [('OO', False), ('Interpreted', False)],
      'C++': [('OO', True), ('Templates', True)]
    })

    would produce: {
      'C': [('OO', False), ('Interpreted', False), ('Templates', '')],
      'C++': [('OO', True), ('Interpreted', ''), ('Templates', True)]
    }

    Note that since dict entries are not ordered, the ultimate layout of the
    values that don't strictly overlap is dependent on the order in which the
    dict entries are emitted during iteration.
  '''
  keys = []

  for kvs in listofkvs.values():
    for k, v in kvs:
      if not k in keys:
        keys += [k] # maintain the ordering, first come first served
  
  result = { }
  for k,v in listofkvs.iteritems():
    out = []
    for t in keys:
      for kk, vv in v:
        if kk == t:
          out += [(kk,vv)]
          break
      else:
        out += [(t, '')]
    result[k] = out
  
  return result
