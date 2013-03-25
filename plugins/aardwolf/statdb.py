"""
$Id$
"""
import copy, time
from plugins import BasePlugin
from libs.sqldb import Sqldb
from libs import exported

NAME = 'StatDB'
SNAME = 'statdb'
PURPOSE = 'Add events to the stat database'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Statdb(Sqldb):
  """
  a class to manage sqlite3 databases
  """
  def __init__(self, dbname=None, dbdir=None):
    """
    initialize the class
    """
    Sqldb.__init__(self, 'chardb.sqlite')

    self.version = 12

    self.addtable('stats', """CREATE TABLE stats(
          stat_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          name TEXT NOT NULL,
          level INT default 1,
          totallevels INT default 1,
          remorts INT default 1,
          tiers INT default 0,
          race TEXT default "",
          sex TEXT default "",
          subclass TEXT default "",
          qpearned INT default 0,
          questscomplete INT default 0 ,
          questsfailed INT default 0,
          campaignsdone INT default 0,
          campaignsfld INT default 0,
          gquestswon INT default 0,
          duelswon INT default 0,
          duelslost INT default 0,
          timeskilled INT default 0,
          monsterskilled INT default 0,
          combatmazewins INT default 0,
          combatmazedeaths INT default 0,
          powerupsall INT default 0,
          totaltrivia INT default 0,
          time INT default 0,
          milestone TEXT,
          redos INT default 0
        );""", {'keyfield':'stat_id'})
          
    self.addtable('quests', """CREATE TABLE quests(
          quest_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          starttime INT default 0,
          finishtime INT default 0,
          mobname TEXT default "Unknown",
          mobarea TEXT default "Unknown",
          mobroom TEXT default "Unknown",
          qp INT default 0,
          double INT default 0,
          daily INT default 0,
          totqp INT default 0,
          gold INT default 0,
          tier INT default 0,
          mccp INT default 0,
          lucky INT default 0,
          tp INT default 0,
          trains INT default 0,
          pracs INT default 0,
          level INT default -1,
          failed INT default 0
        );""", {'keyfield':'quest_id'})    
        
    self.addtable('classes', """CREATE TABLE classes(
            class TEXT NOT NULL PRIMARY KEY,
            remort INTEGER
          );""", {'keyfield':'class', 'postcreate':self.initclasses})        
        
    self.addtable('levels', """CREATE TABLE levels(
          level_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          type TEXT default "level",
          level INT default -1,
          str INT default 0,
          int INT default 0,
          wis INT default 0,
          dex INT default 0,
          con INT default 0,
          luc INT default 0,
          starttime INT default -1,
          finishtime INT default -1,
          hp INT default 0,
          mp INT default 0,
          mv INT default 0,
          pracs INT default 0,
          trains INT default 0,
          bonustrains INT default 0,
          blessingtrains INT default 0
        )""", {'keyfield':'level_id'})        
        
    self.addtable('campaigns', """CREATE TABLE campaigns(
          cp_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          starttime INT default 0,
          finishtime INT default 0,
          qp INT default 0,
          bonusqp INT default 0,
          gold INT default 0,
          tp INT default 0,
          trains INT default 0,
          pracs INT default 0,
          level INT default -1,
          failed INT default 0
        );""", {'keyfield':'cp_id'})

    self.addtable('cpmobs', """CREATE TABLE cpmobs(
          cpmob_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          cp_id INT NOT NULL,
          name TEXT default "Unknown",
          location TEXT default "Unknown"
        )""", {'keyfield':'cpmob_id'})

    self.addtable('mobkills', """CREATE TABLE mobkills(
          mk_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          name TEXT default "Unknown",
          xp INT default 0,
          bonusxp INT default 0,
          blessingxp INT default 0,
          totalxp INT default 0,
          gold INT default 0,
          tp INT default 0,
          time INT default -1,
          vorpal INT default 0,
          banishment INT default 0,
          assassinate INT default 0,
          slit INT default 0,
          disintegrate INT default 0,
          deathblow INT default 0,
          wielded_weapon TEXT default '',
          second_weapon TEXT default '',
          room_id INT default 0,
          level INT default -1
        )""", {'keyfield':'mk_id'})

    self.addtable('gquests', """CREATE TABLE gquests(
          gq_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          starttime INT default 0,
          finishtime INT default 0,
          qp INT default 0,
          qpmobs INT default 0,
          gold INT default 0,
          tp INT default 0,
          trains INT default 0,
          pracs INT default 0,
          level INT default -1,
          won INT default 0,
          completed INT default 0
        )""", {'keyfield':'gq_id'})


    self.addtable('gqmobs', """CREATE TABLE gqmobs(
          gqmob_id INTEGER NOT NULL PRIMARY KEY autoincrement,
          gq_id INT NOT NULL,
          num INT,
          name TEXT default "Unknown",
          location TEXT default "Unknown"
        )""", {'keyfield':'gqmod_id'})
        
    # Need to do this after adding tables
    self.postinit()

  def turnonpragmas(self):
    #-- PRAGMA foreign_keys = ON;
    self.dbconn.execute("PRAGMA foreign_keys=On;")
    #-- PRAGMA journal_mode=WAL
    self.dbconn.execute("PRAGMA journal_mode=WAL;")

  def savequest(self, questinfo):
    """
    save a quest in the db
    """
    if questinfo['failed'] == 1:
      self.addtostat('questsfailed', 1)
    else:
      self.addtostat('questscomplete', 1)
      self.addtostat('questpoints', questinfo['totqp'])
      self.addtostat('qpearned', questinfo['totqp'])
      self.addtostat('triviapoints', questinfo['tp'])
      self.addtostat('totaltrivia', questinfo['tp'])

    cur = self.dbconn.cursor()    
    stmt = self.converttoinsert('quests', keynull=True)
    cur.execute(stmt, questinfo)
    rowid = cur.lastrowid
    self.dbconn.commit()
    cur.close()
    exported.msg('added quest: %s' % rowid, 'statdb') 
    return rowid

  def setstat(self, stat, value):
    """
    set a stat
    """
    cur = self.dbconn.cursor()
    stmt = 'update stats set %s=%s where milestone = "current"' % (
                                                      stat, value)
    cur.execute(stmt)
    self.dbconn.commit()
    cur.close()
    exported.msg('set %s to %s' % (stat, value), 'statdb')
    
  def getstat(self, stat):
    """
    get a stat from the stats table
    """
    tstat = None
    cur = self.dbconn.cursor()
    cur.execute('SELECT * FROM stats WHERE milestone = "current"')
    row = cur.fetchone()
    if row and stat in row:
      tstat = row[stat]
    cur.close()
    return tstat
    
  def addtostat(self, stat, add):
    """
    add to  a stat in the stats table
    """
    if add <= 0:
      return True
      
    if self.checkcolumnexists('stats', stat):
      cur = self.dbconn.cursor()
      cur.execute(
          "UPDATE stats SET %s = %s + %s WHERE milestone = 'current'" \
          % (stat, stat, add))
      self.dbconn.commit()
      cur.close()
      
  def savewhois(self, whoisinfo):
    """
    save info into the stats table
    """
    cur = self.dbconn.cursor()
    if self.getstat('totallevels'):
      nokey = {}
      nokey['stat_id'] = True
      nokey['totaltrivia'] = True
      whoisinfo['milestone'] = 'current'
      whoisinfo['time'] = 0
      stmt = self.converttoupdate('stats', 'milestone', nokey)
      cur.execute(stmt, whoisinfo)
    else:
      whoisinfo['milestone'] = 'current'
      whoisinfo['totaltrivia'] = 0
      whoisinfo['time'] = 0
      stmt = self.converttoinsert('stats', True)
      cur.execute(stmt, whoisinfo)
      #add a milestone here
      self.addmilestone('start')
      
    self.dbconn.commit()
    cur.close()
    exported.msg('updated stats', 'statdb')
    # add classes here
    self.addclasses(whoisinfo['classes'])
    
  def addmilestone(self, milestone):
    """
    add a milestone
    """
    if not milestone:
      return

    trows = self.runselect('SELECT * FROM stats WHERE milestone = "%s"' \
                                                          % milestone)
    if len(trows) > 0:
      exported.sendtoclient('@RMilestone %s already exists' % milestone)
      return -1

    stats = self.runselect('SELECT * FROM stats WHERE milestone = "current"')
    tstats = stats[0]
    
    if tstats:
      tstats['milestone'] = milestone
      tstats['time'] = time.time()
      stmt = self.converttoinsert('stats', True)
      cur = self.dbconn.cursor()
      cur.execute(stmt, tstats)
      trow = cur.lastrowid
      self.dbconn.commit()
      cur.close()
      
      exported.msg('inserted milestone %s with rowid: %s' % (milestone, trow))
      return trow
    
    return -1

  def addclasses(self, classes):
    """
    add classes from whois
    """
    stmt = 'UPDATE CLASSES SET REMORT = :remort WHERE class = :class'
    cur = self.dbconn.cursor()    
    cur.executemany(stmt, classes)
    self.dbconn.commit()
    cur.close()
    
  def getclasses(self):
    """
    get all classes
    """
    classes = []
    tclasses = self.runselect('SELECT * FROM classes ORDER by remort ASC')
    for i in tclasses:
      if i['remort'] != -1:
        classes.append(i['class'])
      
    return classes
   
  def initclasses(self):
    """
    initialize the class table
    """
    classabb = exported.aardu.classabb()
    classes = []
    for i in classabb:
      classes.append({'class':i})
    stmt = "INSERT INTO classes VALUES (:class, -1)"
    cur = self.dbconn.cursor()
    cur.executemany(stmt, classes)
    self.dbconn.commit()
    cur.close()
   
  def resetclasses(self):
    """
    reset the class table
    """
    classabb = exported.aardu.classabb()
    classes = []
    for i in classabb:
      classes.append({'class':i})
    stmt = """UPDATE classes SET remort = -1
                    WHERE class = :class"""
    cur = self.dbconn.cursor()
    cur.executemany(stmt, classes)
    self.dbconn.commit()
    cur.close()

  def savecp(self, cpinfo):
    """
    save cp information
    """  
    if cpinfo['failed'] == 1:
      self.addtostat('campaignsfld', 1)
    else:
      self.addtostat('campaignsdone', 1)
      self.addtostat('questpoints', cpinfo['qp'])
      self.addtostat('qpearned', cpinfo['qp'])
      self.addtostat('triviapoints', cpinfo['tp'])
      self.addtostat('totaltrivia', cpinfo['tp'])

    stmt = self.converttoinsert('campaigns', keynull=True)
    cur = self.dbconn.cursor()
    cur.execute(stmt, cpinfo)
    rowid = self.getlastrowid('campaigns')
    self.dbconn.commit()
    cur.close()
    exported.msg('added cp: %s' % rowid, 'statdb') 

    for i in cpinfo['mobs']:
      i['cp_id'] = rowid
    stmt2 = self.converttoinsert('cpmobs', keynull=True)
    cur = self.dbconn.cursor()    
    cur.executemany(stmt2, cpinfo['mobs'])
    self.dbconn.commit()
    cur.close()
  
  def savegq(self, gqinfo):
    """
    save gq information
    """
    exported.sendtoclient(gqinfo)
    self.addtostat('questpoints', int(gqinfo['qp']) + int(gqinfo['qpmobs']))
    self.addtostat('qpearned', int(gqinfo['qp']) + int(gqinfo['qpmobs']))
    self.addtostat('triviapoints', gqinfo['tp'])
    self.addtostat('totaltrivia', gqinfo['tp'])
    if gqinfo['won'] == 1:
      self.addtostat('gquestswon', 1)

    stmt = self.converttoinsert('gquests', keynull=True)
    cur = self.dbconn.cursor()
    cur.execute(stmt, gqinfo)
    rowid = self.getlastrowid('gquests')
    self.dbconn.commit()
    cur.close()
    exported.msg('added gq: %s' % rowid, 'statdb') 

    for i in gqinfo['mobs']:
      i['gq_id'] = rowid
    stmt2 = self.converttoinsert('gqmobs', keynull=True)
    cur = self.dbconn.cursor()    
    cur.executemany(stmt2, gqinfo['mobs'])
    self.dbconn.commit()
    cur.close()  
  
  def savelevel(self, levelinfo, first=False):
    """
    save a level
    """
    rowid = -1
    if not first:
      if levelinfo['type'] == 'level':
        if levelinfo['totallevels'] and levelinfo['totallevels'] > 0:
          self.setstat('totallevels', levelinfo['totallevels'])
          self.setstat('level', levelinfo['level'])
        else:
          self.addtostat('totallevels', 1)
          self.addtostat('level', 1)
      elif levelinfo['type'] == 'pup':
        self.addtostat('powerupsall', 1)
      if levelinfo['totallevels'] and levelinfo['totallevels'] > 0:
        levelinfo['level'] = levelinfo['totallevels']
      else:
        levelinfo['level'] = self.getstat('totallevels')
      
    levelinfo['finishtime'] = -1
    cur = self.dbconn.cursor()
    stmt = self.converttoinsert('levels', keynull=True)
    cur.execute(stmt, levelinfo)
    rowid = self.getlastrowid('levels')
    exported.msg('inserted level %s' % rowid, 'statdb')
    if rowid > 1:
      stmt2 = "UPDATE levels SET finishtime = %s WHERE level_id = %d" % (
                    levelinfo['starttime'], int(rowid) - 1)
      cur.execute(stmt2)
    self.dbconn.commit()
    cur.close()
    
    if levelinfo['type'] == 'level':
      self.addmilestone(str(levelinfo['totallevels']))
      
    return rowid
   
   
  def savemobkill(self, killinfo):
    """
    save a mob kill
    """
    self.addtostat('totaltrivia', killinfo['tp'])
    self.addtostat('monsterskilled', 1)
    if not killinfo['name']:
      killinfo['name'] = 'Unknown'
    cur = self.dbconn.cursor()
    stmt = self.converttoinsert('mobkills', keynull=True)
    cur.execute(stmt, killinfo)
    self.dbconn.commit()
    rowid = self.getlastrowid('mobkills')
    cur.close()
    exported.msg('inserted mobkill: %s' % rowid)
      

class Plugin(BasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.dependencies.append('aardu')    
    self.events['aard_quest_comp'] = {'func':self.questevent}
    self.events['aard_quest_failed'] = {'func':self.questevent}
    self.events['aard_cp_comp'] = {'func':self.cpevent}
    self.events['aard_cp_failed'] = {'func':self.cpevent}
    self.events['aard_whois'] = {'func':self.whoisevent}
    self.events['aard_level_gain'] = {'func':self.levelevent}
    self.events['aard_mobkill'] = {'func':self.mobkillevent}
    self.events['aard_gq_completed'] = {'func':self.gqevent}
    self.events['aard_gq_done'] = {'func':self.gqevent}
    self.events['aard_gq_won'] = {'func':self.gqevent}
    self.exported['runselect'] = {'func':self.runselect}
    self.statdb = None
    
  def questevent(self, args):
    """
    handle a quest completion
    """
    self.statdb.savequest(args)
    
  def whoisevent(self, args):
    """
    handle whois data
    """
    self.statdb.savewhois(args)
    
  def cpevent(self, args):
    """
    handle a cp
    """
    self.statdb.savecp(args)
    
  def gqevent(self, args):
    """
    handle a gq
    """
    self.statdb.savegq(args)    
    
  def levelevent(self, args):
    """
    handle a level
    """
    levelinfo = copy.deepcopy(args)    
    self.statdb.savelevel(levelinfo)
    
  def mobkillevent(self, args):
    """
    handle a mobkill
    """
    self.statdb.savemobkill(args)
    
  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)
    self.statdb = Statdb()
    
  def unload(self):
    """
    handle unloading
    """
    BasePlugin.unload(self)
    self.statdb.dbconn.close()
    self.statdb = None
    
  def runselect(self, select):
    """
    run a select stmt against the char db
    """
    if self.statdb:
      return self.statdb.runselect(select)
    
    return None
      