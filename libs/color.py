"""
$Id$

This module handles colors

Color Codes:
xterm 256
@x154 - make text color xterm 154
@z154 - make background color xterm 154

regular ansi:
         regular    bold
Red        @r        @R
Green      @g        @G
Yellow     @y        @Y
Blue       @b        @B
Magenta    @m        @M
Cyan       @c        @C
White      @w        @W
Reset      @k        @D

"""
import re

# for finding ANSI color sequences
XTERM_COLOR_REGEX = re.compile('^@[xz](?P<num>[\d]{1,3})$')
ANSI_COLOR_REGEX = re.compile(chr(27) + r'\[(?P<arg_1>\d+)(;(?P<arg_2>\d+)(;(?P<arg_3>\d+))?)?m')

CONVERTANSI = {}

CONVERTCOLORS = {
  'k' : '0;30',
  'r' : '0;31',
  'g' : '0;32',
  'y' : '0;33',
  'b' : '0;34',
  'm' : '0;35',
  'c' : '0;36',
  'w' : '0;37',
  'D' : '1;30',
  'R' : '1;31',
  'G' : '1;32',
  'Y' : '1;33',
  'B' : '1;34',
  'M' : '1;35',
  'C' : '1;36',
  'W' : '1;37',
  'x' : '0',
}


for i in CONVERTCOLORS.keys():
  CONVERTANSI[CONVERTCOLORS[i]] = i

#xterm colors
for i in xrange(0,256):
  CONVERTANSI['38;5;%d' % i] = 'x%d' % i
  CONVERTANSI['39;5;%d' % i] = 'z%d' % i

#backgrounds
for i in xrange(40,48):
  CONVERTANSI['%s' % i] = CONVERTANSI['39;5;%d'% (i - 40)]

#foregrounds
for i in xrange(30,38):
  CONVERTANSI['%s' % i] = CONVERTANSI['0;%d' % i]

def genrepl(match):
  """
  a general replace function
  """
  return match.group(1)

def fixstring(tstr):
  """
  fix a strings invalid colors
  """
  # Thanks to Fiendish from the aardwolf mushclient package, see
  # http://code.google.com/p/aardwolfclientpackage/

  # fix tildes
  tstr = re.sub("@-", "~", tstr)
  # change @@ to \0
  tstr = re.sub("@@", "\0", tstr)
  # strip invalid xterm codes (non-number)
  tstr = re.sub("@[xz]([^\d])", genrepl, tstr)
  # strip invalid xterm codes (300+)
  tstr = re.sub("@[xz][3-9]\d\d", "", tstr)
  # strip invalid xterm codes (260+)
  tstr = re.sub("@[xz]2[6-9]\d", "", tstr)
  # strip invalid xterm codes (256+)
  tstr = re.sub("@[xz]25[6-9]", "", tstr)
  # rip out hidden garbage
  tstr = re.sub("@[^xzcmyrgbwCMYRGBWD]", "", tstr)
  return tstr

def iscolor(color):
  """
  check if a string is a @ color, either xterm or ansi
  """
  if re.match('^@[cmyrgbwCMYRGBWD]$', color):
    return True
  else:
    mat = XTERM_COLOR_REGEX.match( color)
    if mat:
      num = int(mat.groupdict()['num'])
      if num >= 0 and num < 257:
        return True

  return False

def convertcolors(tstr):
  """
  convert @ colors in a string
  """
  test = False
  if '@' in tstr:
    if tstr[-2:] != '@w':
      tstr = tstr + '@w'
    tstr = fixstring(tstr)
    if test:
      print 'After fixstring', tstr
    tstr2 = ''
    tmat = re.search("@(\w)([^@]+)", tstr)
    if tmat and tmat.start() != 0:
      tstr2 = tstr[0:tmat.start()]
    for tmatch in re.finditer("@(\w)([^@]+)", tstr):
      color, text = tmatch.groups()
      if color == 'x':
        tcolor, newtext = re.findall("^(\d\d?\d?)(.*)$", text)[0]
        color = '38;5;%s' % tcolor
        tstr2 = tstr2 + ansicode(color, newtext)
      elif color == 'z':
        tcolor, newtext = re.findall("^(\d\d?\d?)(.*)$", text)[0]
        color = '48;5;%s' % tcolor
        tstr2 = tstr2 + ansicode(color, newtext)
      else:
        tstr2 = tstr2 + ansicode(CONVERTCOLORS[color], text)

    if tstr2:
      tstr = tstr2 + "%c[0m" % chr(27)
    if test:
      print 'After:', tstr
  else:
    pass
  tstr = re.sub("\0", "@", tstr)    # put @ back in
  return tstr

def convertansi(text):
  """
  convert ansi color escape sequences to @colors
  """
  def single_sub(match):
      argsdict = match.groupdict()
      tstr = ''
      tstr = tstr + argsdict['arg_1']
      if argsdict['arg_2']:
        tstr = tstr + ';%d' % int(argsdict['arg_2'])

      if argsdict['arg_3']:
        tstr = tstr + ';%d' % int(argsdict['arg_3'])

      try:
        return '@%s' % CONVERTANSI[tstr]
      except KeyError:
        print 'could not lookup color %s for text %s' % (tstr, repr(text))

  return ANSI_COLOR_REGEX.sub(single_sub, text)

def ansicode(color, data):
  """
  return an ansicoded string
  """
  return "%c[%sm%s" % (chr(27), color, data)

def strip_ansi(text):
  """
  strip all ansi from a string
  """
  return ANSI_COLOR_REGEX.sub('', text)
