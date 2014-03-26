"""
$Id$

This plugin reads and parses invmon data from Aardwolf
"""
import copy
import time
import argparse
import shlex
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Eq cmds, parser'
SNAME = 'eq'
PURPOSE = 'Eq Manipulation'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

flags = ['K', 'G', 'H', 'I', 'M']

flagaardcolours = {
 'K':'R',
 'M':'B',
 'G':'W',
 'H':'C',
 'I':'w',
}

optionallocs = [8, 9, 10, 11, 25, 28, 29, 30, 31, 32]

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle equipment related actions
  invmon, eqdata, inv
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.itemcache = {}
    self.eqdata = {}
    self.invdata = {}

    self.currentcontainer = None

    self.wearall = False
    self.removeall = False
    self.putall = False
    self.getall = False
    self.sellall = False
    self.buyall = False
    self.dropall = False

    self.waiting = {}
    self.waitingforid = {}

    self.layout = {}
    self.layout['invheader'] = ["serial", "level", "type", "worth",
                                "weight", "wearable", "flags", "owner",
                                "fromclan", "timer", "u1", "u2", "u3",
                                "score"]
    self.layout['container'] = ["capacity", "heaviestitem", "holding",
                                "itemsinside", "totalweight", "itemburden",
                                "itemweightpercent"]
    self.layout['statmod'] = ['stat', 'value']
    self.layout['resistmod'] = ['resist', 'value']
    self.layout['weapon'] = ["wtype", "avedam", "inflicts", "damtype",
                             "special"]
    self.layout['skillmod'] = ['skillnum', 'value']
    self.layout['spells'] = ["uses", "level", "sn1", "sn2", "sn3", "sn4",
                             "u1"]
    self.layout['food'] = ['percent']
    self.layout['drink'] = ["servings", "liquid", "liquidmax", "liquidleft",
                            "thirstpercent", "hungerpercent", "u1"]
    self.layout['furniture'] = ["hpregen", "manaregen", "u1"]
    self.layout['eqdata'] = ["serial", "shortflags", "cname", "level",
                             "type", "unique", "wearslot", "timer"]
    self.layout['light'] = ['duration']
    self.layout['portal'] = ['uses']

    self.api.get('dependency.add')('itemu')

  def load(self):
    """
    load the plugin
    """
    AardwolfBasePlugin.load(self)

    self.resetworneq()

    parser = argparse.ArgumentParser(add_help=False,
                 description='show equipment worn')
    parser.add_argument('-n', "--noflags", help="don't show flags, default False",
              action="store_true")
    parser.add_argument('-c', "--score", help="show score, default False",
              action="store_true")
    parser.add_argument('-s', "--serial", help="show serial, default False",
              action="store_true")
    self.api.get('commands.add')('eq', self.cmd_eq,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show inventory or a container')
    parser.add_argument('container', help='the container to see', default='Inventory', nargs='?')
    parser.add_argument('-n', "--noflags", help="don't show flags, default False",
              action="store_true")
    parser.add_argument('-c', "--score", help="show score, default False",
              action="store_true")
    parser.add_argument('-s', "--serial", help="show serial, default False",
              action="store_true")
    parser.add_argument('-g', "--nogroup", help="don't group items, default False",
              action="store_true")
    self.api.get('commands.add')('inv', self.cmd_inv,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show some internal variables')
    self.api.get('commands.add')('sv', self.cmd_showinternal,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    parser.add_argument('otherargs', help='the rest of the args', default=[], nargs='*')
    self.api.get('commands.add')('get', self.cmd_get,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    parser.add_argument('otherargs', help='the rest of the args', default=[], nargs='*')
    self.api.get('commands.add')('put', self.cmd_put,
                                parser=parser, format=False, preamble=False)

    self.api.get('triggers.add')('dead',
      "^You die.$",
      enabled=True, group='dead')

    self.api.get('triggers.add')('badinvdata1',
      "^Syntax: invdata                - view all inv data.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata2',
      "^      : invdata <container id> - view all inv data in a container.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata3',
      "^      : invdata ansi           - remove color codes from output.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata4',
      "^      : invdata <container> ansi - remove color codes from output.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('invmon',
      "^\{invmon\}(?P<action>.*),(?P<serial>.*),(?P<container>.*),(?P<location>.*)$",
      enabled=True, group='invmon')

    self.api.get('triggers.add')('invitem',
      "^\{invitem\}(?P<data>.*)$",
      enabled=True, matchcolor=True)

    self.api.get('triggers.add')('eqdatastart',
      "^\{eqdata\}$",
      enabled=True)

    self.api.get('triggers.add')('eqdataend',
      "^\{/eqdata\}$",
      enabled=False, group='eqdata')

    self.api.get('triggers.add')('invdatastart',
      "^\{invdata\s*(?P<container>.*)?\}$",
      enabled=True)

    self.api.get('triggers.add')('invdataend',
      "^\{/invdata\}$",
      enabled=True, group='invdata')

    self.api.get('triggers.add')('invdetailsstart',
      "^\{invdetails\}$",
      enabled=True)

    self.api.get('triggers.add')('invdetailsend',
      "^\{/invdetails\}$",
      enabled=True, group='invdetails')

    self.api.get('triggers.add')('identityon',
      "\+-----------------------------------------------------------------\+",
      enabled=False, group='identify')

    self.api.get('events.register')('trigger_dead', self.dead)
    self.api.get('events.register')('trigger_invitem', self.trigger_invitem)
    self.api.get('events.register')('trigger_eqdatastart', self.eqdatastart)
    self.api.get('events.register')('trigger_eqdataend', self.eqdataend)
    self.api.get('events.register')('trigger_invdatastart', self.invdatastart)
    self.api.get('events.register')('trigger_invdataend', self.invdataend)
    self.api.get('events.register')('trigger_invmon', self.invmon)

  def api_putininventory(self, serial):
    """
    put an item in inventory
    """
    serial = int(serial)
    if serial in self.itemcache:
      container = self.itemcache[serial]['container']
      if container == 'Worn':
        self.sendcmd('remove %s' % serial)
      elif container != 'Inventory':
        self.sendcmd('get %s %s' % (serial, container))
      else:
        container = ''
      return True, container
    else:
      return False, ''

  def api_putincontainer(self, serial, container):
    """
    put an item in a container
    """
    serial = int(serial)
    container = int(container)

    self.api_putininventory(serial)

    if serial in self.itemcache and container in self.itemcache:
      self.sendcmd('put %s %s' % (serial, container))
      return True, container

    return False, ''

  def api_wearitem(self, serial):
    """
    wear an item
    """
    pass

  def api_removeitem(self, serial):
    """
    remove an item
    """
    pass

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)
    self.getdata('Worn')
    self.getdata('Inventory')

  def dead(self, _):
    """
    reset stuff on death
    """
    self.invdata = {}
    self.waiting = {}
    self.resetworneq()

  def cmd_showinternal(self, args):
    """
    show internal stuff
    """
    msg = []
    msg.append('Waiting   : %s' % self.waiting)
    msg.append('invdata   : %s' % self.invdata)
    msg.append('eqdata    : %s' % self.eqdata)
    msg.append('itemcache : %s' % self.itemcache)

    return True, msg

  def find_item(self, item):
    """
    find and item by serial or identifier
    """
    if type(item) == int:
      item = int(item)
      if item in self.itemcache:
        return item
    else:
      #check for identifiers here
      if item == 'tokenbag':
        return 417249394
      else:
        return "'%s'" % item if ' ' in item else item

  def cmd_get(self, args):
    """
    get an item
    """
    try:
      item = self.find_item(args['item'])
      if item in self.itemcache:
        retval, container = self.api_putininventory(item)
        return True, []

    except ValueError:
      pass

    tlist = ['%s' % self.find_item(x) for x in args['otherargs']]
    tlist.insert(0, '%s' % self.find_item(args['item']))
    cmd = ' '.join(tlist)

    # need to parse all items for identifiers
    self.api.get('send.msg')('serial is not a number, sending \'get %s\'' % cmd)
    self.sendcmd('get %s' % cmd)

    return True, []

  def cmd_put(self, args):
    """
    put an item in something
    """
    item = self.find_item(args['item'])
    if item in self.itemcache and self.itemcache[item] != 'Inventory':
      self.api_putininventory(item)

    tlist = ['%s' % self.find_item(x) for x in args['otherargs']]
    tlist.insert(0, '%s' % item)
    cmd = ' '.join(tlist)

    # need to parse all items for identifiers
    self.api.get('send.msg')('sending \'put %s\'' % cmd)
    self.sendcmd('put %s' % cmd)

  def sendcmd(self, cmd):
    self.api.get('send.msg')('sending cmd: %s' % cmd)
    self.api.get('send.execute')(cmd)

  def checkvaliditem(self, item):
    if item['serial'] == "" or \
      item['level'] == "" or \
      item['type'] == "" or \
      item['name'] == "" or \
      item['cname'] == "":
        return False

    return True

  def getdata(self, etype):
    """
    get container or worn data
    """
    if etype in self.waiting and self.waiting[etype]:
      return

    if etype == 'Inventory':
      self.sendcmd('invdata')
      self.waiting[etype] = True
    elif etype == 'Worn':
      self.sendcmd('eqdata')
      self.waiting[etype] = True
    else:
      self.sendcmd('invdata ' + str(etype))
      self.waiting[etype] = True

  def addmod(self, ltype, mod):
    if not (ltype in self.invdetails):
      self.invdetails[ltype] = []

    self.invdetails[ltype][mod[0]] = int(mod[1])

  def cmd_sell(self, args):
    self.api.get('send.msg')('got sell with args: %s' % args)
    pline = shlex.split(args['data'])
    self.api.get('send.msg')('shlex returned %s' % pline)
    if pline[1] == 'all':
      self.api.get('send.msg')('setting sellall')
      self.sellall = True
    elif 'all.' in pline[1]:
      self.api.get('send.msg')('setting sellall')
      self.sellall = True

  def cmd_buy(self, args):
    self.api.get('send.msg')('got buy with args: %s' % args)
    pline = shlex.split(args['data'])
    self.api.get('send.msg')('shlex returned %s' % pline)
    try:
      num = int(pline[1])
      if num > 20:
        self.api.get('send.msg')('setting buyall')
        self.buyall = True

    except ValueError:
      pass

  def resetworneq(self):
    """
    reset worn eq
    """
    wearlocs = self.api.get('itemu.wearlocs')()
    self.eqdata = []
    for i in xrange(0, len(wearlocs)):
      self.eqdata.append(-1)

  def wearitem(self, serial, wearloc):
    """
    wear an item
    """
    del self.eqdata[wearloc]
    self.itemcache[serial]['container'] = 'Worn'
    self.eqdata.insert(wearloc, serial)

  def takeoffitem(self, serial):
    self.itemcache[serial]['container'] = None
    try:
      location = self.eqdata.index(serial)
      del self.eqdata[location]
      self.eqdata.insert(location, -1)
    except IndexError:
      self.getdata('Worn')

  def eqdatastart(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.msg')('found {eqdata}')
    self.api.get('triggers.togglegroup')('eqdata', True)
    self.api.get('events.register')('trigger_all', self.eqdataline)
    self.resetworneq()

  def eqdataline(self, args):
    """
    parse a line of eqdata
    """
    line = args['line'].strip()
    if line != '{eqdata}':
      self.api.get('send.msg')('eqdata args: %s' % args)
      titem = self.api.get('itemu.dataparse')(line, 'eqdata')
      self.itemcache[titem['serial']] = titem
      self.api.get('send.msg')('eqdata parsed item: %s' % titem)
      self.wearitem(titem['serial'], titem['wearslot'])

  def eqdataend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.waiting['eqdata'] = False
    self.api.get('send.msg')('found {/eqdata}')
    self.api.get('events.unregister')('trigger_all', self.eqdataline)
    self.api.get('triggers.togglegroup')('eqdata', False)

  def invdatastart(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.msg')('found {invdata}: %s' % args)
    if not args['container']:
      container = 'Inventory'
    else:
      container = int(args['container'])
    self.currentcontainer = container
    self.api.get('triggers.togglegroup')('invdata', True)
    self.api.get('events.register')('trigger_all', self.invdataline)
    self.invdata[self.currentcontainer] = []

  def putitemincontainer(self, container, serial, place=-1):
    """
    add item to a container
    """
    self.itemcache[serial]['container'] = container
    if place >= 0:
      self.invdata[container].insert(place, serial)
    else:
      self.invdata[container].append(serial)

  def removeitemfromcontainer(self, container, serial):
    """
    remove an item from inventory
    """
    self.itemcache[serial]['container'] = ''
    itemindex = self.invdata[container].index(serial)
    del self.invdata[container][itemindex]

  def invdataline(self, args):
    """
    parse a line of eqdata
    """
    line = args['line'].strip()
    if line != '{invdata}':
      self.api.get('send.msg')('invdata args: %s' % args)
      try:
        titem = self.api.get('itemu.dataparse')(line, 'eqdata')
        self.itemcache[titem['serial']] = titem
        self.api.get('send.msg')('invdata parsed item: %s' % titem)
        self.putitemincontainer(self.currentcontainer, titem['serial'])
        if titem['type'] == 11 and not (titem['serial'] in self.invdata):
          self.getdata(titem['serial'])
      except (IndexError, ValueError):
        self.api.get('send.msg')('incorrect invdata line: %s' % line)


  def invdataend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.waiting[self.currentcontainer] = False
    self.currentcontainer = None
    self.api.get('send.msg')('found {/invdata}')
    self.api.get('events.unregister')('trigger_all', self.invdataline)
    self.api.get('triggers.togglegroup')('invdata', False)

  def trigger_invitem(self, args):
    self.api.get('send.msg')('invitem args: %s' % args)
    titem = self.api.get('itemu.dataparse')(args['data'], 'eqdata')
    self.itemcache[titem['serial']] = titem
    self.api.get('send.msg')('invitem parsed item: %s' % titem)
    self.itemcache[titem['serial']] = titem

  def cmd_eq(self, args):
    """
    show eq
    """
    self.api.get('send.msg')('cmd_eq args: %s' % args)

    return True, self.build_worn(args)

  def cmd_inv(self, args):
    """
    show inventory
    """
    self.api.get('send.msg')('cmd_inv args: %s' % args)

    return True, self.build_container(args)

  def build_containerheader(self, args):
    """
    build the container header
    """
    header = []

    if not args['nogroup']:
      header.append(' %3s  '% '#')

    if not args['noflags']:
      header.append('(')
      count = 0
      for flag in flags:
        colour = flagaardcolours[flag]
        count = count + 1
        if count == 1:
          header.append(' @' + colour + flag + '@x ')
        else:
          header.append('@' + colour + flag + '@x ')

      header.append('@w) ')

    header.append('(')
    header.append("@G%3s@w" % 'Lvl')
    header.append(') ')

    if args['serial']:
      header.append('(@x136')
      header.append("%-12s" % "Serial")
      header.append('@w) ')

    if args['score']:
      header.append('(@C')
      header.append("%-5s" % 'Score')
      header.append('@w) ')

    header.append("%s" % 'Item Name')

    return ''.join(header)

  def build_container(self, args):
    """
    build a container
    """
    self.api.get('send.msg')('build_container args: %s' % args)

    try:
      container = int(args['container'])
    except ValueError:
      container = args['container']

    msg = ['Items in %s:' % container]

    msg.append(self.build_containerheader(args))

    msg.append('@B' + '-' * 80)

    if not (container in self.invdata) or not self.invdata[container]:
      msg.append('You have nothing in %s' % container)
    else:
      items = []
      numstyles = {}
      foundgroup = {}

      for serial in self.invdata[container]:
        item = self.itemcache[serial]
        #item = i
        stylekey = item['name'] + item['shortflags'] + str(item['level'])
        doit = True
        sitem = []
        if not args['nogroup'] and stylekey in numstyles:
          if not (stylekey) in foundgroup:
            foundgroup[stylekey] = 1
          foundgroup[stylekey] = foundgroup[stylekey] + 1
          doit = False
          numstyles[stylekey]['item'].pop(numstyles[stylekey]['countcol'])
          numstyles[stylekey]['item'].insert(numstyles[stylekey]['countcol'],
                                    "(%3d) " % foundgroup[stylekey])
          if args['serial'] and foundgroup[stylekey] == 2:
            numstyles[stylekey]['item'].pop(numstyles[stylekey]['serialcol'])
            numstyles[stylekey]['item'].insert(numstyles[stylekey]['serialcol'],
                                      "%-12s" % "Many")

        if doit:
          if not args['nogroup']:
            sitem.append(" %3s  " % " ")
            if not (stylekey in numstyles):
              numstyles[stylekey] = {'item':sitem, 'countcol':len(sitem) - 1,
                                     'serial':item['serial']}

          if not args['noflags']:
            sitem.append('(')

            count = 0
            for flag in flags:
              aardcolour = flagaardcolours[flag]
              count = count + 1
              if flag in item['shortflags']:
                if count == 1:
                  sitem.append(' @' + aardcolour + flag + ' ')
                else:
                  sitem.append('@' + aardcolour + flag + ' ')
              else:
                if count == 1:
                  sitem.append('   ')
                else:
                  sitem.append('  ')
            sitem.append('@w)')

            sitem.append(' ')

          sitem.append('(')
          sitem.append("@G%3s@w" % (item['level'] or ""))
          sitem.append(') ')

          if args['serial']:
            sitem.append('(@x136')
            sitem.append("%-12s" % (item['serial'] if 'serial' in item else ""))
            if not args['nogroup']:
              if stylekey in numstyles:
                numstyles[stylekey]['serialcol'] = len(sitem) - 1
            sitem.append('@w) ')

          if args['score']:
            sitem.append('(@C')
            sitem.append("%5s" % (item['score'] if 'score' in item else 'Unkn'))
            sitem.append('@w) ')

          sitem.append(item['cname'])
          items.append(sitem)

      for item in items:
        msg.append(''.join(item))

      msg.append('')

    return msg


  def build_wornitem(self, item, wearloc, args):
    """
    build the output of a worn item
    """
    sitem = []

    wearlocs = self.api.get('itemu.wearlocs')()

    sitem.append('@G[@w')

    colour = '@c'
    if wearlocs[wearloc] == 'wielded' or wearlocs[wearloc] == 'second':
      colour = '@R'
    elif wearlocs[wearloc] == 'above' or wearlocs[wearloc] == 'light':
      colour = '@W'
    elif wearlocs[wearloc] == 'portal' or wearlocs[wearloc] == 'sleeping':
      colour = '@C'

    sitem.append(' %s%-8s@x ' % (colour, wearlocs[wearloc]))
    sitem.append('@G]@w ')

    if not args['noflags']:
      sitem.append('(')

      count = 0
      for flag in flags:
        aardcolour = flagaardcolours[flag]
        count = count + 1
        if flag in item['shortflags']:
          if count == 1:
            sitem.append(' @' + aardcolour + flag + ' ')
          else:
            sitem.append('@' + aardcolour + flag + ' ')
        else:
          if count == 1:
            sitem.append('   ')
          else:
            sitem.append('  ')
      sitem.append('@w)')

      sitem.append(' ')

    sitem.append('(')
    sitem.append("@G%3s@w" % (item['level'] or ""))
    sitem.append(') ')

    if args['serial']:
      sitem.append('(@x136')
      sitem.append("%-12s" % (item['serial'] if 'serial' in item else ""))
      sitem.append('@w) ')

    if args['score']:
      sitem.append('(@C')
      sitem.append("%5s" % (item['score'] if 'score' in item else 'Unkn'))
      sitem.append('@w) ')

    sitem.append(item['cname'])

    return ''.join(sitem)

  def build_worn(self, args):
    """
    build the output of a container
    """
    wearlocs = self.api.get('itemu.wearlocs')()
    self.api.get('send.msg')('build_worn args: %s' % args)
    msg = ['You are using:']
    header = []

    header.append('@G[@w')
    header.append(' %-8s ' % 'Location')
    header.append('@G]@w ')

    if not args['noflags']:
      header.append('(')
      count = 0
      for flag in flags:
        colour = flagaardcolours[flag]
        count = count + 1
        if count == 1:
          header.append(' @' + colour + flag + '@x ')
        else:
          header.append('@' + colour + flag + '@x ')

      header.append('@w) ')

    header.append('(')
    header.append("@G%3s@w" % 'Lvl')
    header.append(') ')

    if args['serial']:
      header.append('(@x136')
      header.append("%-12s" % "Serial")
      header.append('@w) ')

    if args['score']:
      header.append('(@C')
      header.append("%-5s" % 'Score')
      header.append('@w) ')

    header.append("%s" % 'Item Name')

    header.append('  ')

    msg.append(''.join(header))

    msg.append('@B' + '-' * 80)

    for i in xrange(0, len(wearlocs)):
      if self.eqdata[i] != -1:
        serial = self.eqdata[i]
        item = self.itemcache[serial]
        msg.append(self.build_wornitem(item, i, args))
      else:
        doit = True
        if i in optionallocs:
          doit = False
        if (i == 23 or i == 26) and self.eqdata[25] != -1:
          doit = False
        if doit:
          item = {'cname':"@r< empty >@w", 'shortflags':"", 'level':'',
                  'serial':''}
          msg.append(self.build_wornitem(item, i, args))

    msg.append('')
    return msg

  def invmon(self, args):
    """
    do the appropriate action when seeing an invmon message
    """
    action = int(args['action'])
    serial = int(args['serial'])
    container = int(args['container'])
    location = int(args['location'])
    self.api.get('send.msg')('action: %s, item: %s' % (action, serial))
    if action == 1:
    # Remove an item
      if serial in self.eqdata:
        self.putitemincontainer('Inventory', serial, place=0)
        self.takeoffitem(serial)
      else:
        self.getdata('Inventory')
        self.getdata('Worn')
    elif action == 2:
    # Wear an item
      if 'Inventory' in self.invdata and serial in self.invdata['Inventory']:
        self.removeitemfromcontainer('Inventory', serial)
        self.wearitem(serial, location)
      else:
        self.getdata('Inventory')
        self.getdata('Worn')
    elif action == 3 or action == 7:
      # 3 = Removed from inventory, 7 = consumed
      if 'Inventory' in self.invdata and serial in self.invdata['Inventory']:
        titem = self.itemcache[serial]
        if titem['type'] == 11:
          for item in self.invdata[serial]:
            del self.itemcache[item]
        self.removeitemfromcontainer('Inventory', serial)
        del self.itemcache[serial]
      else:
        self.getdata('Inventory')
    elif action == 4:
    # Added to inventory
      try:
        self.putitemincontainer('Inventory', serial, place=0)
        titem = self.itemcache[serial]
        if titem['type'] == 11:
          self.getdata(serial)
      except KeyError:
        self.getdata('Inventory')
    elif action == 5:
    # Taken out of container
      try:
        self.removeitemfromcontainer(container, serial)
        self.putitemincontainer('Inventory', serial, place=0)
      except KeyError:
        self.getdata('Inventory')
        self.getdata(container)
    elif action == 6:
    # Put into container
      try:
        self.removeitemfromcontainer('Inventory', serial)
        self.putitemincontainer(container, serial, place=0)
      except KeyError:
        self.getdata('Inventory')
        self.getdata(container)
