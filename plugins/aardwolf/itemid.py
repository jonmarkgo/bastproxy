"""
This plugin reads and parses id and invdetails from Aardwolf
"""
import argparse
import re
import textwrap
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Item Identification'
SNAME = 'itemid'
PURPOSE = 'Parse invdetails and id'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

DETAILS_RE = '^\{(?P<header>.*)\}(?P<data>.*)$'
DETAILS_REC = re.compile(DETAILS_RE)

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle equipment identification, id and invdetails
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.waitingforid = {}
    self.showid = {}
    self.pastkeywords = False
    self.dividercount = 0
    self.affectmods = False
    self.nonotes = False

    self.currentitem = {}

    self.api.get('dependency.add')('aardwolf.itemu')

    self.api.get('api.add')('identify', self.api_identify)
    self.api.get('api.add')('format', self.api_formatitem)
    self.api.get('api.add')('show', self.api_showitem)

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('idcmd', True, str,
                      'identify')

    parser = argparse.ArgumentParser(add_help=False,
                 description='id an item')
    parser.add_argument('serial', help='the item to id', default='', nargs='?')
    self.api.get('commands.add')('id', self.cmd_id,
                                parser=parser, format=False, preamble=False)

    self.api.get('triggers.add')('invdetailsstart',
      "^\{invdetails\}$", group='invdetails',
      enabled=False, omit=True)

    self.api.get('triggers.add')('invdetailsline',
      "^\{(?!/*invdetails)(?P<header>.*)\}(?P<data>.*)$", group='invdetails',
      enabled=False, omit=True)

    self.api.get('triggers.add')('invdetailsend',
      "^\{/invdetails\}$",
      enabled=False, group='invdetails', omit=True)

    self.api.get('triggers.add')('identifyon',
      "\+-*\+",
      enabled=False, group='identify', omit=True)

    self.api.get('triggers.add')('identify1',
      '^\|\s*(?P<data>.*)\s*\|$', group='identify',
      enabled=False, omit=True)

    self.api.get('events.register')('trigger_invdetailsstart',
                                      self.invdetailsstart)
    self.api.get('events.register')('trigger_invdetailsend',
                                      self.invdetailsend)
    self.api.get('events.register')('trigger_invdetailsline',
                                      self.invdetailsline)
    self.api.get('events.register')('trigger_identifyon', self.identifyon)
    self.api.get('events.register')('trigger_identify1', self.identifyline)

  def sendcmd(self, cmd):
    """
    send a command
    """
    self.api.get('send.msg')('sending cmd: %s' % cmd)
    if 'invdetails' in cmd:
      self.api.get('triggers.togglegroup')('invdetails', True)
    elif 'identify' in cmd:
      self.api.get('triggers.togglegroup')('identify', True)
    self.api.get('send.execute')(cmd)

  def addmod(self, ltype, mod):
    """
    add a mod to an item (stat, skills, resist, etc)
    """
    if not (ltype in self.currentitem):
      self.currentitem[ltype] = {}

    if ltype == 'tempmod':
      if not (mod['type'] in self.currentitem[ltype]):
        self.currentitem[ltype][mod['type']] = []
      self.currentitem[ltype][mod['type']].append(mod)
    else:
      self.currentitem[ltype][mod['name']] = int(mod['value'])

  def invdetailsstart(self, args):
    """
    start gathering the invdetails data
    """
    self.currentitem = {}
    self.api.get('send.msg')('found {invdetails}')

  def invdetailsline(self, args):
    """
    parse a line of invdetails
    """
    self.api.get('send.msg')('invdetailsline args: %s' % args)
    header = args['header']
    data = args['data']
    self.api.get('send.msg')('match: %s - %s' % (header,
                                                  data))
    titem = self.api.get('itemu.dataparse')(data,
                                            header)
    if header == 'invheader':
      self.currentitem = titem
    elif header in ['statmod', 'resistmod', 'skillmod']:
      self.addmod(header, titem)
    else:
      self.currentitem[header] = titem
    self.api.get('send.msg')('invdetails parsed item: %s' % titem)

  def invdetailsend(self, args):
    """
    reset current when seeing an {/invdetails}
    """
    self.api.get('send.msg')('found {/invdetails}')
    self.api.get('triggers.togglegroup')('invdetails', False)

  def identifyon(self, args):
    """
    start gathering the identify data, this is also triggered by an
    identify divider, the line with multiple ---- in it
    """
    self.dividercount = self.dividercount + 1
    if self.dividercount == 1:
      self.api.get('send.msg')('found identify')
      self.api.get('triggers.togglegroup')('identifydata', True)
      self.api.get('events.register')('trigger_emptyline', self.identifyend)
    elif self.dividercount == 2:
      self.pastkeywords = True
    if self.affectmods:
      self.affectmods = False
    self.nonotes = False

  def identifyline(self, args):
    """
    parse an identify line, we only want a couple of things that don't
    appear in invdetails: Keywords, Found, Material, Leads, Affect Mods and
    any item notes
    """
    data = args['data']
    if 'Keywords' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['keywords'] = item.strip()
    elif 'Found at' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['foundat'] = item.strip()
    elif 'Material' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['material'] = item.strip()
    elif 'Leads to' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['leadsto'] = item.strip()
    elif 'Affect Mods' in data:
      self.affectmods = True
      item = data.split(':')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      item = item.strip()
      tlist = item.split(',')
      self.currentitem['affectmod'] = []
      for i in tlist:
        if i:
          self.currentitem['affectmod'].append(i.strip())
    elif self.affectmods:
      item = data.split(':')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      item = item.strip()
      tlist = item.split(',')
      for i in tlist:
        if i:
          self.currentitem['affectmod'].append(i.strip())
    elif 'Mods' in data or 'Portal' in data or 'Capacity' in data or \
         'Weapon Type' in data or 'Spells' in data or \
           'Food' in data or 'Drink' in data or 'Heal Rate' in data or \
             'Temporary Effects' in data:
      self.nonotes = True
    elif self.pastkeywords and not self.nonotes:
      if args['line'][2] != ' ':
        if not ('notes' in self.currentitem):
          self.currentitem['notes'] = []
        tdat = args['colorline'][1:-1]
        self.currentitem['notes'].append(tdat.strip())

  def identifyend(self, args):
    """
    stop gathering identify data

    this raise an itemid_<serial> event
    """
    self.api.get('events.unregister')('trigger_emptyline', self.identifyend)
    self.api.get('triggers.togglegroup')('identify', False)
    self.pastkeywords = False
    self.dividercount = 0
    if self.currentitem['serial'] in self.waitingforid:
      del self.waitingforid[self.currentitem['serial']]
    titem = self.api.get('eq.addidentify')(self.currentitem['serial'],
                                          self.currentitem)
    self.api.get('events.eraise')('itemid_%s' % self.currentitem['serial'],
                            {'item':self.api.get('eq.getitem')(
				      self.currentitem['serial'])})
    self.api.get('events.eraise')('itemid_all' % self.currentitem['serial'],
                            {'item':self.api.get('eq.getitem')(
                                      self.currentitem['serial'])})
    ### Get the item from eq and update it

  # identify an item
  def api_identify(self, serial):
    """  identify an item
    @Yserial@w    = the serial # if the item to identify

    this function returns None if the identify data has to gathered,
    or the item if is in the cache"""
    titem = self.api.get('eq.getitem')(serial)
    if titem.hasbeenided:
      return titem
    else:
      self.waitingforid[serial] = True
      if titem.curcontainer and titem.curcontainer.cid != 'Inventory':
        self.api.get('eq.get')(serial)
      self.sendcmd('invdetails %s' % serial)
      self.sendcmd('identify %s' % serial)
      self.api('events.register')('itemid_%s' % titem.serial, self.putincontainer,
				  prio=40)
      return None

  def putincontainer(self, args):
    """
    after identification, put an item into its original container
    """
    self.api('events.unregister')(args['eventname'], self.putincontainer)

    titem = args['item']

    if titem.origcontainer and titem.origcontainer.cid != 'Inventory':
      self.api.get('eq.put')(titem.serial)

  def event_showitem(self, args):
    """
    this function is for showing an item when using the id command,
    it registers with itemid_<serial>
    """
    self.api.get('events.unregister')(args['eventname'], self.event_showitem)
    self.api.get('itemid.show')(args['item'].serial)

  def cmd_id(self, args):
    """
    do an id
    """
    msg = []
    if args['serial']:
      #try:
      serial = int(args['serial'])
      titem = self.api.get('eq.getitem')(serial)
      if not titem:
        msg.append('Could not find %s' % serial)
      else:
        if titem.hasbeenided:
          self.api.get('itemid.show')(serial)
        else:
          self.api.get('events.register')('itemid_%s' % serial,
                                          self.event_showitem)
          self.api.get('itemid.identify')(serial)
      #except ValueError:
        #msg.append('%s is not a serial number' % args['serial'])
    else:
      msg.append('Please supply a serial #')

    return True, msg

  def formatsingleline(self, linename, linecolour, data, datacolor=None):
    """
    format a single data line
     | Keywords   : aylorian dagger thin blade dirk                    |
    """
    if not datacolor:
      datacolor = '@W'

    data = str(data)

    printstring = '| %s%-11s@w: %s%s'
    ttext = printstring % (linecolour, linename, datacolor, data)
    newnum = 66 - len(self.api.get('colors.stripcolor')(ttext))
    tstring = "%" + str(newnum) + "s@w|"
    ttext = ttext + tstring % ""

    return ttext

  def formatdoubleline(self, linename, linecolour, data, linename2, data2):
    """
    format a double data line
     | Worth      : 20                       Weight : 4                |
    """
    if not linecolour:
      linecolour = '@W'

    data = str(data)
    data2 = str(data2)

    adddata = 24 + self.api.get('colors.lengthdiff')(data)
    adddata2 = 17 + self.api.get('colors.lengthdiff')(data2)

    printstring = '| %s%-11s@w: @W%-' + str(adddata) + 's %s%-7s@w: @W%-' + \
            str(adddata2) + 's@w|'

    return printstring % (linecolour, linename, data,
                          linecolour, linename2, data2)

  def formatspecialline(self, linename, linecolour, data,
                                linename2='', data2=''):
    """
    format a special text line
     | Skill Mods : Modifies Dagger by +2                              |
    """
    if not linecolour:
      linecolour = '@W'

    data = str(data)
    data2 = str(data2)

    adddata = 20 + self.api.get('colors.lengthdiff')(data)

    printstring = '| %s%-11s@w: @W%-' + str(adddata) + 's'

    ttext = printstring % (linecolour, linename, data)

    if linename2:
      adddata2 = 14 + self.api.get('colors.lengthdiff')(data2)
      printstring2 = ' %s%-13s:  @W%-' + str(adddata2) + 's@w|'
      ttext = ttext + printstring2 % (linecolour, linename2, data2)
    else:
      newnum = 66 - len(self.api.get('colors.stripcolor')(ttext))
      tstring = "%" + str(newnum) + "s@w|"
      ttext = ttext + tstring % ""

    return ttext

  def formatstatsheader(self):
    """
    format the stats header
     |     DR   HR    Str Int Wis Dex Con Luc   Sav   HP   MN   MV     |
    """
    return '|     @w%-4s %-4s  %-3s %-3s %-3s ' \
                  '%-3s %-3s %-3s   %-3s   %-4s %-4s %-4s   |' % (
                            'DR', 'HR', 'Str', 'Int', 'Wis',
                            'Dex', 'Con', 'Luc', 'Sav', 'HP', 'MN', 'MV')

  def formatstats(self, stats):
    """
    format all stats
     |     -    2     -   -   -   -   -   -     -     -    -    -      |
    """
    colors = {}
    for i in stats:
      if int(stats[i]) > 0:
        colors[i] = '@G'
      else:
        colors[i] = '@R'

    allstats = ['Damage roll', 'Hit roll', 'Strength', 'Intelligence',
              'Wisdom', 'Dexterity', 'Constitution', 'Luck', 'Saves',
              'Hit points', 'Mana', 'Moves']

    for i in allstats:
      if i in stats:
        if int(stats[i]) > 0:
          colors[i] = '@G'
        elif int(stats[i]) < 0:
          colors[i] = '@R'
        else:
          colors[i] = '@w'

      else:
        stats[i] = 0
        colors[i] = '@w'

    return '|     %s%-4s@w %s%-4s@w  %s%-3s@w %s%-3s@w ' \
            '%s%-3s@w %s%-3s@w %s%-3s@w %s%-3s@w   ' \
            '%s%-3s@w   %s%-4s@w %s%-4s@w %s%-4s@w   |' % (
                colors['Damage roll'], stats['Damage roll'] or '-',
                colors['Hit roll'], stats['Hit roll'] or '-',
                colors['Strength'], stats['Strength'] or '-',
                colors['Intelligence'], stats['Intelligence'] or '-',
                colors['Wisdom'], stats['Wisdom'] or '-',
                colors['Dexterity'], stats['Dexterity'] or '-',
                colors['Constitution'], stats['Constitution'] or '-',
                colors['Luck'], stats['Luck'] or '-',
                colors['Saves'], stats['Saves'] or '-',
                colors['Hit points'], stats['Hit points'] or '-',
                colors['Mana'], stats['Mana'] or '-',
                colors['Moves'], stats['Moves'] or '-')

  def formatresist(self, resists, divider):
    """
    format resists

      |     Bash  Pierce  Slash    All Phys  All Mag   Diss  Poisn      |
      |      -      -       -         13       -        -     -         |
      +-----------------------------------------------------------------+
      |     Acid   Air   Cold  Earth   Eltrc   Enrgy   Fire    Holy     |
      |     100    100   100   100     100     100     100     100      |
      |     Light  Magic Mntl  Ngtv    Shdw    Sonic   Water            |
      |     100    100   100   100     100     100     100              |
    """
    colors = {}
    ttext = []
    foundfirst = False
    foundsecond = False

    firstline = ['Bash', 'Pierce', 'Slash', 'All physical',
                 'All magic', 'Disease', 'Poison']

    secondline = ['Acid', 'Air', 'Cold', 'Earth', 'Electric', 'Energy',
              'Fire', 'Holy', 'Light', 'Magic', 'Mental', 'Negative', 'Shadow',
              'Sonic', 'Water']

    allresists = firstline + secondline

    for i in allresists:
      if i in resists:
        if not foundfirst and i in firstline:
          foundfirst = True
        if not foundsecond and i in secondline:
          foundsecond = True

        if int(resists[i]) > 0:
          colors[i] = '@G'
        elif int(resists[i]) < 0:
          colors[i] = '@R'
        else:
          colors[i] = '@w'
      else:
        resists[i] = 0
        colors[i] = '@w'

    if foundfirst:
      ttext.append('|%5s@w%-5s %-7s %-7s  %-8s  %-8s  %-5s %-5s %5s|' % (
                              '', 'Bash', 'Pierce', 'Slash', 'All Phys',
                              'All Mag', 'Diss', 'Poisn', ''))
      ttext.append(
        '|%6s%s%-5s  %s%-7s %s%-7s   %s%-8s %s%-8s %s%-5s %s%-5s @w%4s|' % (
                        '',
                        colors['Bash'], resists['Bash'] or '-',
                        colors['Pierce'], resists['Pierce'] or '-',
                        colors['Slash'], resists['Slash'] or '-',
                        colors['All physical'], resists['All physical'] or '-',
                        colors['All magic'], resists['All magic'] or '-',
                        colors['Disease'], resists['Disease'] or '-',
                        colors['Poison'], resists['Poison'] or '-',
                        ''))

    if foundsecond:
      ttext.append(divider)
      ttext.append('|%5s%-5s  %-5s %-5s %-5s   %-5s   ' \
                    '%-5s   %-5s   %-5s@w %3s|' % (
                            '', 'Acid', 'Air', 'Cold', 'Earth',
                            'Eltrc', 'Enrgy', 'Fire', 'Holy', ''))

      ttext.append('|%5s%s%-5s  %s%-5s %s%-5s %s%-5s   ' \
                        '%s%-5s   %s%-5s   %s%-5s   %s%-5s@w %3s|' % (
                            '',
                            colors['Acid'], resists['Acid'] or '-',
                            colors['Air'], resists['Air'] or '-',
                            colors['Cold'], resists['Cold'] or '-',
                            colors['Earth'], resists['Earth'] or '-',
                            colors['Electric'], resists['Electric'] or '-',
                            colors['Energy'], resists['Energy'] or '-',
                            colors['Fire'], resists['Fire'] or '-',
                            colors['Holy'], resists['Holy'] or '-',
                            ''))

      ttext.append(
                '|%4s %-5s  %-5s %-5s %-5s   %-5s   %-5s   %-5s @w %10s|' % (
                            '', 'Light', 'Magic', 'Mntl', 'Ngtv',
                            'Shdw', 'Sonic', 'Water', ''))

      ttext.append('|%4s %s%-5s  %s%-5s %s%-5s %s%-5s   %s%-5s   ' \
                            '%s%-5s   %s%-5s@w %11s|' % (
                            '',
                            colors['Light'], resists['Light'] or '-',
                            colors['Magic'], resists['Magic'] or '-',
                            colors['Mental'], resists['Mental'] or '-',
                            colors['Negative'], resists['Negative'] or '-',
                            colors['Shadow'], resists['Shadow'] or '-',
                            colors['Sonic'], resists['Sonic'] or '-',
                            colors['Water'], resists['Water'] or '-',
                            ''))

    return ttext

  def checkattr(self, item, attr):
    if hasattr(item, attr) and item.__dict__[attr]:
      return True

    return False

  # format an item
  def api_formatitem(self, serial):
    """  format an item
    @Yserial@w    = the serial # if the item to identify

    this function returns a list of strings that are the formatted item"""
    divider = '+' + '-' * 65 + '+'
    linelen = 50

    serial = int(serial)
    item = self.api.get('eq.getitem')(serial)

    iteml = [divider]

    if item.checkattr('keywords'):
      tstuff = textwrap.wrap(item.keywords, linelen)
      header = 'Keywords'
      for i in tstuff:
        iteml.append(self.formatsingleline(header, '@R', i))
        header = ''

    # do identifiers here

    if item.checkattr('cname'):
      iteml.append(self.formatsingleline('Name', '@R', '@w' + item.cname))

    iteml.append(self.formatsingleline('Id', '@R', item.serial))

    if item.checkattr('curcontainer'):
      if item.curcontainer.cid == 'Worn':
        wearlocs = self.api.get('itemu.wearlocs')()
        iteml.append(self.formatsingleline('Location', '@R',
                                         'Worn - %s' % wearlocs[item.wearslot]))
      else:
        iteml.append(self.formatsingleline('Location', '@R',
                                         item.curcontainer.cid))

    if item.checkattr('itype') and item.checkattr('level'):
      objtypes = self.api.get('itemu.objecttypes')()
      ntype = item.itype.capitalize()
      iteml.append(self.formatdoubleline('Type', '@c', ntype,
                                         'Level', item.level))
    elif item.checkattr(level):
      iteml.append(self.formatsingleline('Level', '@c', item.level))

    if item.checkattr('worth') and item.checkattr('weight'):
      iteml.append(self.formatdoubleline('Worth', '@c', item.worth,
                                         'Weight', item.weight))

    if item.checkattr('wearable'):
      iteml.append(self.formatsingleline('Wearable', '@c',
                                         item.wearable))

    if item.checkattr('score'):
      iteml.append(self.formatsingleline('Score', '@c', item.score,
                                         datacolor='@Y'))

    if item.checkattr('material'):
      iteml.append(self.formatsingleline('Material', '@c', item.material))

    if item.checkattr('flags'):
      tlist = textwrap.wrap(item.flags, linelen)
      header = 'Flags'
      for i in tlist:
        i = i.replace('precious', '@Yprecious@w')
        iteml.append(self.formatsingleline(header, '@c', i.rstrip()))
        header = ''

    if item.checkattr('owner'):
      iteml.append(self.formatsingleline('Owned by', '@c', item.owner))

    if item.checkattr('fromclan'):
      iteml.append(self.formatsingleline('Clan Item', '@G', item.fromclan,
                                         datacolor='@M'))

    if item.checkattr('foundat'):
      iteml.append(self.formatsingleline('Found at', '@G', item.foundat,
                                         datacolor='@M'))

    if item.checkattr('leadsto'):
      iteml.append(self.formatsingleline('Leads to', '@G', item.leadsto,
                                         datacolor='@M'))

    if item.checkattr('notes'):
      iteml.append(divider)
      tlist = textwrap.wrap(' '.join(item.notes), linelen)
      header = 'Notes'
      for i in tlist:
        iteml.append(self.formatsingleline(header, '@W', i, '@w'))
        header = ''

    if item.checkattr('affectmod'):
      iteml.append(divider)
      tlist = textwrap.wrap(', '.join(item.affectmod), linelen)
      header = 'Affects'
      for i in tlist:
        iteml.append(self.formatsingleline(header, '@g', i, '@w'))
        header = ''

    if item.checkattr('container'):
      iteml.append(divider)
      iteml.append(self.formatspecialline('Capacity', '@c',
                          item.container['capacity'], 'Heaviest Item',
                          item.container['heaviestitem']))
      iteml.append(self.formatspecialline('Holding', '@c',
                            item.container['holding'], 'Items Inside',
                            item.container['itemsinside']))
      iteml.append(self.formatspecialline('Tot Weight', '@c',
                            item.container['totalweight'], 'Item Burden',
                            item.container['itemburden']))
      iteml.append(self.formatspecialline('', '@c',
                  '@wItems inside weigh @Y%d@w%%@w of their usual weight' % \
                          item.container['itemweightpercent']))

    if item.checkattr('weapon'):
      iteml.append(divider)
      iteml.append(self.formatspecialline('Weapon Type', '@c',
                                  item.weapon['wtype'], 'Average Dam',
                                  item.weapon['avedam']))
      iteml.append(self.formatspecialline('Inflicts', '@c',
                                  item.weapon['inflicts'], 'Damage Type',
                                  item.weapon['damtype']))
      if 'special' in item.weapon and item.weapon['special']:
        iteml.append(self.formatspecialline('Specials', '@c',
                                            item.weapon['special']))

    if item.itype == 20:
      if item.checkattr('portal'):
        iteml.append(divider)
        iteml.append(self.formatsingleline('Portal', '@R',
                  '@Y%s@w uses remaining.' % item.portal['uses']))

    if item.checkattr('statmod'):
      iteml.append(divider)
      iteml.append(self.formatstatsheader())
      iteml.append(self.formatstats(item.statmod))

    if item.checkattr('resistmod'):
      iteml.append(divider)
      for i in self.formatresist(item.resistmod, divider):
        iteml.append(i)

    if item.checkattr('skillmod'):
      iteml.append(divider)
      header = 'Skill Mods'
      for i in item.skillmod:
        spell = self.api.get('skills.gets')(i)
        color = '@R'
        if int(item.skillmod[i]) > 0:
          color = '@G'
        iteml.append(self.formatspecialline(header, '@c',
               'Modifies @g%s@w by %s%+d@w' % (str(spell['name']).capitalize(),
               color, int(item.skillmod[i]))))
        header = ''

    if item.checkattr('spells'):
      iteml.append(divider)

      header = 'Spells'
      for i in xrange(1, 5):
        key = 'sn%s' % i
        if item.spells[key] and item.spells[key] != 0:
          spell = self.api.get('skills.gets')(item.spells[key])
          plural = ''
          if int(item.spells['uses']) > 1:
            plural = 's'
          iteml.append(self.formatspecialline(header, '@c',
                    "%d use%s of level %d '@g%s@w'" % (
                            item.spells['uses'], plural,
                            item.spells['level'],
                            spell['name'].lower())))
          header = ''

    if item.checkattr('food'):
      iteml.append(divider)
      header = 'Food'
      iteml.append(self.formatspecialline(header, '@c',
          "Will replenish hunger by %d%%" % (item.food['percent'])))

    if item.checkattr('drink'):
      iteml.append(divider)
      iteml.append(self.formatspecialline('Drink', '@c',
                  "%d servings of %s. Max: %d" % (item.drink['servings'],
                                    item.drink['liquid'],
                                    item.drink['liquidmax']/20 or 1)))
      iteml.append(self.formatspecialline('', '@c',
                  "Each serving replenishes thirst by %d%%" % \
                    item.drink['thirstpercent']))
      iteml.append(self.formatspecialline('', '@c',
                  "Each serving replenishes hunger by %d%%" % \
                    item.drink['hungerpercent']))

    if item.checkattr('furniture'):
      iteml.append(divider)
      iteml.append(self.formatspecialline('Heal Rate', '@c',
              "Health [@Y%d@w]    Magic [@Y%d@w]" % (
                    item.furniture['hpregen'],
                    item.furniture['manaregen'])))

    iteml.append(divider)

    return iteml

  # show an item to the client
  def api_showitem(self, serial):
    """  show an item to the client
    @Yserial@w    = the serial # of the item to show

    if the serial isn't in the cache, then it is identified through the id
    command

    this function returns nothing"""
    item = self.api.get('eq.getitem')(serial)
    if item:
      if item.hasbeenided:
        tstuff = self.api.get('itemid.format')(serial)

        self.api.get('send.client')('\n'.join(tstuff), preamble=False)
      else:
        self.api.get('send.execute')('#bp.itemid.id %s' % serial)
