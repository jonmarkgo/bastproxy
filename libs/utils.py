import fnmatch
import os
import datetime

def find_files(directory, filematch):
  matches = []
  for root, dirnames, filenames in os.walk(directory):
    for filename in fnmatch.filter(filenames, filematch):
        matches.append(os.path.join(root, filename))
        
  return matches
  
def timedeltatostring(stime, etime):
    delay = datetime.timedelta(seconds=abs(etime - stime))
    if (delay.days > 0):
        tstr = str(delay)
        tstr = tstr.replace(" day, ", ":")
        out  = tstr.replace(" days, ", ":")
    else:
        out = "0:" + str(delay)
    outAr = out.split(':')
    outAr = [(int(float(x))) for x in outAr]
    tmsg = []
    days, hours, minutes = False, False, False
    if outAr[0] != 0:
      days = True
      tmsg.append('%dy' % outAr[0])
    if outAr[1] != 0 or days:
      hours = True
      tmsg.append('%dh' % outAr[1])
    if outAr[2] != 0 or days or hours:
      tmsg.append('%dm' % outAr[2])
    tmsg.append('%ds' % outAr[3])
      
    out   = ":".join(tmsg)
    return out
  