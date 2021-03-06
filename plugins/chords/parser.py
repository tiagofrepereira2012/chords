#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

"""A simple parser for Chord Pro files.
"""

import re
import codecs

from . import pdf


def break_line(v, width):
  """Breaks the line trying to respect the given width. Returns a tuple."""
  retval = []
  for k in v.split(u' '):
    if not retval:
      retval.append(k)
      continue

    #when you get here, retval is filled with at least one entry

    #adds the space we splitted before
    if len(retval[-1]) < width: retval[-1] += u' '
    else: retval.append(u' ')

    #adds the next word
    if len(retval[-1]) + len(k) <= width: retval[-1] += k
    else: retval.append(k)

  return [k.strip() for k in retval if k.strip()]


def break_chordline(v, width):
  """Does about the same as break_line() above, but breaks the chord lines in
  respecting chord positions relative to the lyrics lines."""

  def clen(v):
    """Calculates the length of v removing the chord entries."""
    return len(LineParser.chord.sub('', v, re.UNICODE))

  retval = []
  for k in v.split(u' '):
    if not retval:
      retval.append(k)
      continue

    #when you get here, retval is filled with at least one entry

    #adds the space we splitted before
    if clen(retval[-1]) < width: retval[-1] += u' '
    else: retval.append(u' ')

    #adds the next word
    if clen(retval[-1]) + clen(k) <= width: retval[-1] += k
    else: retval.append(k)

  return [k.strip() for k in retval if k.strip()]


class Line:
  """A line that contains information of some sort."""

  def __init__(self, v, lineno):
    self.lineno = lineno
    self.value = v

  def __str__(self):
    return '%03d %s' % (self.lineno, self.value)

  def as_html(self):
    return u'<span class="line">%s</span>' % self.value

  def as_pdf(self, width):
    """A normal line just returns itself as PDF"""
    return break_line(self.value, width)


class ChordLine(Line):
  """A special category of line that contains chords."""


  def __init__(self, v, lineno):
    Line.__init__(self, v, lineno)
    self.bare, self.chords = self.real_init([self.value])
    self.bare = self.bare[0]
    self.chords = self.chords[0]


  def real_init(self, value):
    bare = [LineParser.chord.sub('', k, re.UNICODE) for k in value]
    chords = []
    for k in value:
      subtract = 0
      to_append = []
      for z in LineParser.chord.finditer(k):
        to_append.append((z.start()-subtract, z.groups()[0]))
        subtract = z.end() + (z.end() - z.start()) - 2
      for i, c in enumerate(to_append[1:]):
        # make sure the chords have at least 1 space between them.
        if c[0] <= 0: to_append[i+1] = (1, c[1])
      chords.append(to_append)
    return bare, chords


  def __str__(self):
    cline = '    '
    for c in self.chords: cline += (' '*c[0] + c[1])
    v = [cline, '%03d %s' % (self.lineno, self.bare)]
    return '\n'.join(v)


  def as_html(self):
    cline = ''
    for c in self.chords: cline += (' '*c[0] + c[1])
    v = u'<span class="chords">%s</span>\n' % cline
    v += u'<span class="lyrics">%s</span>\n' % self.bare
    return v


  def as_pdf(self, width):
    """A chorded line will actually return 2 lines one with the chord and
    a second one with the lyrics."""
    value = break_chordline(self.value, width)
    lyrics, chords = self.real_init(value)
    diff = len(chords) - len(lyrics)
    if diff > 0: lyrics += diff * ['']
    elif diff < 0: chord += diff * ['']
    lines = []
    for i, k in enumerate(chords):
      cline = ''
      for c in k: cline += (' '*c[0] + c[1].capitalize())
      c = '<font color=#000088><b>' + cline + '</b></font>'
      lines.extend((c, lyrics[i]))
    return lines


class EmptyLine:
  """A line with nothing."""


  def __init__(self, lineno):
    self.lineno = lineno


  def __str__(self):
    return '%03d ' % (self.lineno,)


  def as_html(self):
    return u'\n'


  def as_pdf(self, width):
    return [u'']


  def as_flowable(self, width):
    return pdf.XPreformatted(u'<br/>', pdf.style['verse'])


class HashComment(EmptyLine):
  """A hash comment is a line that starts with a # mark."""


  def __init__(self, v, lineno):
    EmptyLine.__init__(self, lineno)
    self.comment = v


  def __str__(self):
    return '%03d %s' % (self.lineno, self.comment)


  def as_html(self):
    #v = u'<span class="hashcomment">%s</span>\n' % self.comment
    return u''


  def as_pdf(self, width):
    return break_line(self.comment, width)


  def as_flowable(self, width):
    return None


class Verse:
  """A verse."""


  def __init__(self):
    self.lines = []
    self.ended = False


  def append(self, line):
    """Adds another line into this verse. This includes parsing."""
    if not self.ended: self.lines.append(line)
    else:
      raise SyntaxError('Cannot append to Verse started at line %d, it has been closed on line %d' % (self.lines[0].lineno, self.lines[-1].lineno))


  def end(self, line=0): #we don't accumulate the last line
    """Ends this verse."""
    self.ended = True


  def __str__(self):
    v = ['--- Verse:']
    v += [str(k) for k in self.lines]
    v.append('--- End verse')
    return u'\n'.join(v)


  def as_html(self):
    return u'\n'.join([k.as_html() for k in self.lines])


  def as_flowable(self, width):
    data = []
    for k in self.lines: data += k.as_pdf(width)
    return pdf.XPreformatted('\n'.join(data), pdf.style['verse'])


class Chorus(Verse):
  """A complete chorus entry."""


  def __init__(self, start):
    Verse.__init__(self)
    self.starts = start
    self.ends = None
    self.lines = []


  def append(self, line):
    if not self.ended: self.lines.append(line)
    else:
      raise SyntaxError('Cannot append to Chorus started at line %d, it has been closed on line %d' % (self.starts.lineno, self.ends.lineno))


  def end(self, end):
    self.ends = end


  def __str__(self):
    v = [self.starts]
    v += [str(k) for k in self.lines]
    v.append(self.ends)
    return '\n'.join([str(k) for k in v])


  def as_html(self):
    v = u'<span class="chorus">'
    v += u'\n'.join([k.as_html() for k in self.lines])
    v += u'</span>'
    return u'\n' + v + u'\n'


  def as_flowable(self, width):
    data = []
    for k in self.lines: data += k.as_pdf(width)
    return pdf.XPreformatted('\n'.join(data), pdf.style['chorus'])


class Tablature(Verse):
  """A complete tablature entry."""


  def __init__(self, start):
    Verse.__init__(self)
    self.starts = start
    self.ends = None
    self.lines = []


  def append(self, line):
    if not self.ended: self.lines.append(line)
    else:
      raise SyntaxError('Cannot append to Tablature started at line %d, it has been closed on line %d' % (self.starts.lineno, self.ends.lineno))


  def end(self, end):
    self.ends = end


  def __str__(self):
    v = [self.starts]
    v += [str(k) for k in self.lines]
    v.append(self.ends)
    return '\n'.join([str(k) for k in v])


  def as_html(self):
    v = u'<span class="tablature">'
    v += u'\n'.join([k.as_html() for k in self.lines])
    v += u'</span>'
    return u'\n' + v + u'\n'


  def as_flowable(self, width):
    data = []
    for k in self.lines: data += k.as_pdf(width)
    return pdf.XPreformatted('\n'.join(data), pdf.style['tablature'])


class Command:
  """A generic command from chordpro."""


  def __init__(self, lineno):
    self.lineno = lineno


  def as_pdf(self, width):
    return []


  def as_flowable(self, width):
    return None


class StartOfChorus(Command):
  """A start of chorus marker."""

  def __init__(self, lineno):
    Command.__init__(self, lineno)


  def __str__(self):
    return '%03d {start_of_chorus}' % (self.lineno)


class EndOfChorus(Command):
  """A end of chorus marker."""


  def __init__(self, lineno):
    Command.__init__(self, lineno)


  def __str__(self):
    return '%03d {end_of_chorus}' % (self.lineno)


class StartOfTablature(Command):
  """A start of tablature marker."""


  def __init__(self, lineno):
    Command.__init__(self, lineno)


  def __str__(self):
    return '%03d {start_of_tab}' % (self.lineno)


class EndOfTablature(Command):
  """A end of tablature marker."""


  def __init__(self, lineno):
    Command.__init__(self, lineno)


  def __str__(self):
    return '%03d {end_of_tab}' % (self.lineno)


class Comment(Command):
  """A chordpro {comment:...} entry."""


  def __init__(self, lineno, value):
    Command.__init__(self, lineno)
    self.value = value


  def __str__(self):
    return '%03d {comment: %s}' % (self.lineno, self.value)


  def as_html(self):
    return u'<span class="comment">%s</span>\n' % self.value


  def as_pdf(self, width):
    return [u'<font color=#444444><i>' + k + '</i></font>' for k in break_line(self.value, width)]


  def as_flowable(self, width):
    return pdf.XPreformatted('\n'.join(break_line(self.value, width)), pdf.style['comment'])


class UnsupportedCommand(Command):
  """One of the chordpro commands we don't support."""


  def __init__(self, command, value, lineno):
    Command.__init__(self, lineno)
    self.command = command
    self.value = value


  def __str__(self):
    return '%03d {%s: %s} [UNSUPPORTED]' % \
        (self.lineno, self.command, self.value)


  def as_html(self):
    return u''


class CommandParser:
  """Parses and generates the proper command from the input."""


  comment = re.compile(r'{\s*(comment|c)\s*:\s*(?P<v>.*)}', re.I)
  soc = re.compile(r'{\s*(start_of_chorus|soc)\s*}', re.I)
  eoc = re.compile(r'{\s*(end_of_chorus|eoc)\s*}', re.I)
  sot = re.compile(r'{\s*(start_of_tab|sot)\s*}', re.I)
  eot = re.compile(r'{\s*(end_of_tab|eot)\s*}', re.I)
  define = re.compile(r'{\s*(define)\s+(?P<v>.*)}', re.I)
  title = re.compile(r'{\s*(title|t)\s*:\s*(?P<v>.*)}', re.I)
  subtitle = re.compile(r'{\s*(subtitle|st)\s*:\s*(?P<v>.*)}', re.I)


  def __init__(self):
    pass


  def __call__(self, v, lineno):
    if CommandParser.comment.match(v): return Comment(lineno, CommandParser.comment.match(v).group('v'))
    elif CommandParser.soc.match(v): return StartOfChorus(lineno)
    elif CommandParser.eoc.match(v): return EndOfChorus(lineno)
    elif CommandParser.sot.match(v): return StartOfTablature(lineno)
    elif CommandParser.eot.match(v): return EndOfTablature(lineno)
    elif CommandParser.define.match(v):
      return UnsupportedCommand('define', CommandParser.define.match(v).group('v'), lineno)
    elif CommandParser.title.match(v):
      return UnsupportedCommand('title', CommandParser.title.match(v).group('v'), lineno)
    elif CommandParser.subtitle.match(v):
      return UnsupportedCommand('subtitle', CommandParser.subtitle.match(v).group('v'), lineno)

    #we don't do anything if the command is unsupported
    return HashComment('#' + v + ' [IGNORED]', lineno)


class LineParser:

  chord = re.compile(r'\[(?P<v>[^\]]*)\]')


  def __init__(self):
    pass


  def __call__(self, l, lineno):
    if LineParser.chord.search(l): return ChordLine(l, lineno)
    return Line(l, lineno)


def parse(t):
  """Parses a chord-pro formatted file and turns the input into low-level
  constructs that can be easily analyzed by our high-level syntax parser."""

  input = []
  cmdparser = CommandParser()
  lineparser = LineParser()
  for i, l in enumerate(t.split('\n')):
    sl = l.strip()
    if not sl: input.append(EmptyLine(i+1))
    elif sl[0] == '#': input.append(HashComment(sl, i+1))
    elif sl[0] == '{': input.append(cmdparser(sl, i+1))
    else: input.append(lineparser(l.rstrip(), i+1))

  return input


def consume_chorus(input):
  """This method will consume the whole of a chorus section until an end marker
  is found."""
  if not input: return []

  if isinstance(input[0], StartOfChorus):
    retval = Chorus(input.pop(0))
  else:
    return []

  while True:
    try:
      i = input.pop(0)
      if isinstance(i, EndOfChorus):
        retval.end(i)
        return [retval]
      elif isinstance(i, Comment):
        retval.append(i)
      elif isinstance(i, (Command,)):
        raise SyntaxError('Line %d: Cannot have command inside Chorus.' % \
            i.lineno)
      else:
        retval.append(i)
    except IndexError: #input has ended w/o closing
      return [retval]


def consume_tablature(input):
  """This method will consume the whole of a tablature section until an end
  marker is found."""
  if not input: return []

  if isinstance(input[0], StartOfTablature):
    retval = Tablature(input.pop(0))
  else:
    return []

  while True:
    try:
      i = input.pop(0)
      if isinstance(i, EndOfTablature):
        retval.end(i)
        return [retval]
      elif isinstance(i, Comment):
        retval.append(i)
      elif isinstance(i, (Command,)):
        raise SyntaxError('Line %d: Cannot have command inside Tablature.' % \
            i.lineno)
      else:
        retval.append(i)
    except IndexError: #input has ended w/o closing
      return retval


def consume_extra(input):
  """Consumes all empty lines and comments that follow."""
  retval = []

  try:
    while isinstance(input[0], (EmptyLine, HashComment, Comment, UnsupportedCommand)):
      retval.append(input.pop(0))
  except IndexError: #input has ended
    pass

  return retval


def consume_verse(input):
  """Consumes the whole of a verse."""
  if not input: return []
  if isinstance(input[0], Line):
    retval = Verse()
    retval.append(input.pop(0))
  else:
    return []

  try:
    while not isinstance(input[0], (EmptyLine, HashComment, Command)):
      retval.append(input.pop(0))
  except IndexError: #input has ended
    pass

  retval.end()
  return [retval]


def syntax_analysis(input):
  """Syntax analysis groups low-level constructs to make up Choruses,
  Tablatures and Verses."""

  retval = []

  # Makes sure we don't have any syntactical problems
  while input:
    save_length = len(input)
    retval += consume_extra(input)
    retval += consume_verse(input)
    retval += consume_chorus(input)
    retval += consume_tablature(input)
    if save_length == len(input): #nothing was consumed
      raise SyntaxError('Cannot make sense of "%s"' % (input[0]))

  return retval


if __name__ == '__main__':
  import os
  import sys

  if len(sys.argv) == 1:
    print('usage: %s <file.chord>' % os.path.basename(sys.argv[0]))
    sys.exit(1)

  f = codecs.open(sys.argv[1], 'rt', 'utf-8')
  items = syntax_analysis(parse(f))
  f.close()
  print('File %s contains %d blocks' % (sys.argv[1], len(items)))
  for k in items: print(k)
