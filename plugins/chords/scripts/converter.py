#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

"""Converts a song in simple chord format (chords on the top) into a chordpro
format.
"""

import os
import sys
import re
import codecs

CHORD_REGEXP = re.compile(r'\s*[A-H]\S*', re.UNICODE)


class Empty(object):

  def __init__(self, lineno):
    self.lineno = lineno


class Line(object):

  def __init__(self, value, lineno):
    self.value = value
    self.lineno = lineno


class Chord(object):

  def __init__(self, value, lineno):
    self.value = value
    self.lineno = lineno


def combine(chord, line):
  """Combines chords and lines in a single chordpro-style line."""
  retval = line.value
  extra = 0
  for c in CHORD_REGEXP.finditer(chord.value):
    crd = c.group(0).lstrip()
    leading = len(c.group(0)) - len(crd) #leading white-spaces
    pos = c.start() + leading + extra
    retval = retval[:pos] + '[' + crd + ']' + retval[pos:]
    extra += len(crd) + 2
  #print '**', chord.value
  #print '**', line.value
  #print '**', retval
  return retval


def convert(lines):
  parsed = []
  for i, l in enumerate(lines):
    #print i, l.strip()
    if not l.strip():
      parsed.append(Empty(i+1))

    elif False in [bool(CHORD_REGEXP.match(k)) for k in l.split()]:
      #cannot be a chord line
      parsed.append(Line(l.rstrip(), i+1))

    else:
      #has to be a chord line
      parsed.append(Chord(l.rstrip(), i+1))

    #print parsed[-1]

  retval = []
  waiting = None
  while parsed: #consume doublets.
    k = parsed.pop(0)
    if isinstance(k, Empty): retval.append('')
    elif isinstance(k, Line):
      if waiting:
        retval.append(combine(waiting, k))
        waiting = None
      else:
        retval.append(k.value)
    else: #has to be a chord line
      if waiting: retval.append(waiting.value)
      waiting = k

  return '\n'.join(retval)


def main():
  if len(sys.argv) != 2:
    print 'usage: %s <filename.top>' % os.path.basename(sys.argv[0])
    return 1

  f = codecs.open(sys.argv[1], 'rt', encoding='utf-8')
  lines = f.readlines()
  f.close()
  print convert(lines)


if __name__ == '__main__':
  main()
