"""
$Id$
"""
import sqlite3
import os
import shutil

from libs import exported
exported.logger.adddtype('sqlite')
exported.logger.cmd_file(['sqlite'])
exported.logger.cmd_console(['sqlite'])

def fixsql(s, like=False):
  if s:
    if like:
      return "'%" + s.replace("'", "''") + "%'"
    else:
      return "'" + s.replace("'", "''") + "'"
  else:
    return 'NULL'
  

class sqldb:
  def __init__(self, dbname=None, dbdir=None):
    self.dbname = dbname or "\\sqlite.sqlite"
    self.dbdir = dbdir or os.path.join(exported.basepath, 'data', 'db')
    self.dbfile = os.path.join(self.dbdir, self.dbname)
    self.db = sqlite3.connect(self.dbfile)
    self.db.row_factory = sqlite3.Row
    self.db.text_factory = str # only return byte strings so is easier to send to a client or the mud
    self.conns = 0
    self.version = 0
    self.versionfuncs = {}
    self.tableids = {}
    self.tables = {}

  def postinit(self):  
    self.checkversion()
    
    for i in self.tables:
      self.checktable(i)

  def turnonpragmas(self):
    pass

  def addtable(self, tablename, sql, prefunc=None, postfunc=None, keyfield=None):
    self.tables[tablename] = {'createsql':sql, 'precreate':prefunc, 'postcreate':postfunc,'keyfield':keyfield}
    col, colbykeys = self.getcolumnsfromsql(tablename)
    self.tables[tablename]['columns'] = col
    self.tables[tablename]['columnsbykeys'] = colbykeys

  def getcolumnsfromsql(self, tablename):
    columns = []
    columnsbykeys = {}
    if self.tables[tablename]:
      tlist = self.tables[tablename]['createsql'].split('\n')
      for i in tlist:
        i = i.strip()
        if not ('CREATE' in i) and not (')' in i):
          ilist = i.split(' ')
          columns.append(ilist[0])
          columnsbykeys[ilist[0]] = True
          
    return columns, columnsbykeys
  
  def converttoinsert(self, tablename, keynull=False, replace=False):
    execstr = ''
    if self.tables[tablename]:
      cols = self.tables[tablename]['columns']
      tlist = [':%s' % i for i in cols]
      colstring = ', '.join(tlist)
      if replace:
        execstr = "INSERT OR REPLACE INTO %s VALUES (%s)" % (tablename, colstring)
      else:
        execstr = "INSERT INTO %s VALUES (%s)" % (tablename, colstring)
      if keynull and self.tables[tablename]['keyfield']:
        execstr = execstr.replace(":%s" % self.tables[tablename]['keyfield'], 'NULL')
    return execstr

  def converttoupdate(self, tablename, wherekey='', nokey=False):
    execstr = ''
    if self.tables[tablename]:
      cols = self.tables[tablename]['columns']
      sqlstr = []
      for i in cols:
        if i == wherekey or (nokey and nokey[i]):
          pass
        else:
          sqlstr.append(i + ' = :' + i)
      colstring = ','.join(sqlstr)
      execstr = "UPDATE %s SET %s WHERE %s = :%s;" % (tablename, colstring, wherekey, wherekey)
    return execstr
        
  def getversion(self):
    version = 1
    c = self.db.cursor()
    c.execute('PRAGMA user_version;')
    r = c.fetchone()
    version = r['user_version']
    c.close()
    return version
    
  def checktable(self, tablename):
    if self.tables[tablename]:
      if not self.checktableexists(tablename):
        if self.tables[tablename]['precreate']:
          self.tables[tablename]['precreate']()
        c = self.db.cursor()
        c.execute(self.tables[tablename]['createsql'])
        self.db.commit()
        c.close()
        if self.tables[tablename]['postcreate']:
          self.tables[tablename]['postcreate']()
    return True
    
  def checktableexists(self, tablename):
    rv = False
    c = self.db.cursor()
    for row in c.execute('SELECT * FROM sqlite_master WHERE name = "%s" AND type = "table";' % tablename):
      if row['name'] == tablename:
        rv = True
    c.close()
    return rv
  
  def checkversion(self):
    dbversion = self.getversion()
    if self.version > dbversion:
      self.updateversion(dbversion, self.version)
      
  def setversion(self, version):
    c = self.db.cursor()
    c.execute('PRAGMA user_version=%s;' % version)
    self.db.commit()
    c.close()
      
  def updateversion(self, oldversion, newversion):
    exported.msg('updating %s from version %s to %s' % (self.dbfile, oldversion, newversion), 'sqlite')
    #self.backupdb('v%s' % oldversion)
    for i in range(oldversion + 1, newversion + 1):
      try:
        self.versionfuncs[i]()
        exported.msg('updated to version %s' % i, 'sqlite')
      except:
        exported.write_traceback('could not upgrade db: %s' % self.dbloc)
        return
    self.setversion(newversion)
    exported.msg('Done upgrading!', 'sqlite')
    
  def runselect(self, selectstmt):
    result = []
    c = self.db.cursor()
    try:
      for row in c.execute(selectstmt):
        result.append(row)
    except:
        exported.write_traceback('could not run sql statement : %s' % selectstmt)
    c.close()
    return result
  
  def runselectbykeyword(self, selectstmt, keyword):
    result = {}
    c = self.db.cursor()
    try:
      for row in c.execute(selectstmt):
        result[row[keyword]] = row
    except:
      exported.write_traceback('could not run sql statement : %s' % selectstmt)
    c.close()
    return result

  def getlastrowid(self, tablename):
    colid = self.tables[tablename].keyfield
    lastid = 0
    try:
      res = self.runselect("SELECT MAX('%s') AS MAX FROM %s" % (colid, tablename))
      lastid = res[0]['MAX']
    except:
      exported.write_traceback('could not get last row id for : %s' % tablename)      
    return lastid   
  
  def getlast(self, tablename, num, where=''):
    colid = self.tables[tablename].keyfield
    execstr = ''
    if where:
      execstr = "SELECT * FROM %s WHERE %s ORDER by %s desc limit %d;" % (tablename, where, colid, num)
    else:
      execstr = "SELECT * FROM %s ORDER by %s desc limit %d;" % (tablename, colid, num)
    res = self.runselect(execstr)
    items = {}
    for row in res:
      items[row[colid]] = row
    return items
      
  def backupdb(self, name):
    exported.msg('backing up database', 'sqlite')
    c = self.db.cursor()
    integrity = True
    for row in c.execute('PRAGMA integrity_check'):
      if row['integrity_check'] != 'ok':
        integrity = False
        
    if not integrity:
      exported.msg('Integrity check failed, aborting backup', 'sqlite')
      return
    self.db.close()
    backupfile = os.path.join(self.dbdir, 'backup', self.dbname + '.' + name)
    try:
      shutil.copy(self.dbfile, backupfile)
      exported.msg('%s was backed up to %s' % (self.dbfile, backupfile), 'sqlite')
    except IOError:
      exported.msg('backup failed, could not copy file', 'sqlite')      
    self.db = sqlite3.connect(self.dbfile)
    
