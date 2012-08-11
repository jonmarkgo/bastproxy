r"""TELNET client class.

Based on RFC 854: TELNET Protocol Specification, by J. Postel and
J. Reynolds

Example:

>>> from telnetlib import Telnet
>>> tn = Telnet('www.python.org', 79)   # connect to finger port
>>> tn.write('guido\r\n')
>>> print tn.read_all()
Login       Name               TTY         Idle    When    Where
guido    Guido van Rossum      pts/2        <Dec  2 11:10> snag.cnri.reston..

>>>

Note that read_all() won't read until eof -- it just reads some data
-- but it guarantees to read at least one byte unless EOF is hit.

It is possible to pass a Telnet object to select.select() in order to
wait until more data is available.  Note that in this case,
read_eager() may return '' even if there was data on the socket,
because the protocol negotiation may have eaten the data.  This is why
EOFError is needed in some cases to distinguish between "no data" and
"connection closed" (since the socket also appears ready for reading
when it is closed).

To do:
- option negotiation
- timeout should be intrinsic to the connection object instead of an
  option on one of the read calls only

"""

from __future__ import print_function
# Imported modules
import asyncore
import ConfigParser
import os
import socket
import struct
import sys
import traceback
import zlib

__all__ = ["Telnet"]

# Tunable parameters
DEBUGLEVEL = 1

if sys.platform == "linux2":
  try:
    socket.SO_ORIGINAL_DST
  except AttributeError:
    # There is a missing const in the socket module... So we will add it now
    socket.SO_ORIGINAL_DST = 80

  def get_original_dest(sock):
    '''Gets the original destination address for connection that has been
    redirected by netfilter.'''
    # struct sockaddr_in {
    #     short            sin_family;   // e.g. AF_INET
    #     unsigned short   sin_port;     // e.g. htons(3490)
    #     struct in_addr   sin_addr;     // see struct in_addr, below
    #     char             sin_zero[8];  // zero this if you want to
    # };
    # struct in_addr {
    #     unsigned long s_addr;  // load with inet_aton()
    # };
    # getsockopt(fd, SOL_IP, SO_ORIGINAL_DST, (struct sockaddr_in *)&dstaddr, &dstlen);

    data = sock.getsockopt(socket.SOL_IP, socket.SO_ORIGINAL_DST, 16)
    _, port, a1, a2, a3, a4 = struct.unpack("!HHBBBBxxxxxxxx", data)
    address = "%d.%d.%d.%d" % (a1, a2, a3, a4)
    return address, port


elif sys.platform == "darwin":
  def get_original_dest(sock):
    '''Gets the original destination address for connection that has been
    redirected by ipfw.'''
    return sock.getsockname()

# Telnet protocol defaults
TELNET_PORT = 23

# Telnet protocol characters (don't change)
IAC  = chr(255) # "Interpret As Command"
DONT = chr(254)
DO   = chr(253)
WONT = chr(252)
WILL = chr(251)
theNULL = chr(0)

SE  = chr(240)  # Subnegotiation End
NOP = chr(241)  # No Operation
DM  = chr(242)  # Data Mark
BRK = chr(243)  # Break
IP  = chr(244)  # Interrupt process
AO  = chr(245)  # Abort output
AYT = chr(246)  # Are You There
EC  = chr(247)  # Erase Character
EL  = chr(248)  # Erase Line
GA  = chr(249)  # Go Ahead
SB =  chr(250)  # Subnegotiation Begin


# Telnet protocol options code (don't change)
# These ones all come from arpa/telnet.h
BINARY = chr(0) # 8-bit data path
ECHO = chr(1) # echo
RCP = chr(2) # prepare to reconnect
SGA = chr(3) # suppress go ahead
NAMS = chr(4) # approximate message size
STATUS = chr(5) # give status
TM = chr(6) # timing mark
RCTE = chr(7) # remote controlled transmission and echo
NAOL = chr(8) # negotiate about output line width
NAOP = chr(9) # negotiate about output page size
NAOCRD = chr(10) # negotiate about CR disposition
NAOHTS = chr(11) # negotiate about horizontal tabstops
NAOHTD = chr(12) # negotiate about horizontal tab disposition
NAOFFD = chr(13) # negotiate about formfeed disposition
NAOVTS = chr(14) # negotiate about vertical tab stops
NAOVTD = chr(15) # negotiate about vertical tab disposition
NAOLFD = chr(16) # negotiate about output LF disposition
XASCII = chr(17) # extended ascii character set
LOGOUT = chr(18) # force logout
BM = chr(19) # byte macro
DET = chr(20) # data entry terminal
SUPDUP = chr(21) # supdup protocol
SUPDUPOUTPUT = chr(22) # supdup output
SNDLOC = chr(23) # send location
TTYPE = chr(24) # terminal type
EOR = chr(25) # end or record
TUID = chr(26) # TACACS user identification
OUTMRK = chr(27) # output marking
TTYLOC = chr(28) # terminal location number
VT3270REGIME = chr(29) # 3270 regime
X3PAD = chr(30) # X.3 PAD
NAWS = chr(31) # window size
TSPEED = chr(32) # terminal speed
LFLOW = chr(33) # remote flow control
LINEMODE = chr(34) # Linemode option
XDISPLOC = chr(35) # X Display Location
OLD_ENVIRON = chr(36) # Old - Environment variables
AUTHENTICATION = chr(37) # Authenticate
ENCRYPT = chr(38) # Encryption option
NEW_ENVIRON = chr(39) # New - Environment variables
# the following ones come from
# http://www.iana.org/assignments/telnet-options
# Unfortunately, that document does not assign identifiers
# to all of them, so we are making them up
TN3270E = chr(40) # TN3270E
XAUTH = chr(41) # XAUTH
CHARSET = chr(42) # CHARSET
RSP = chr(43) # Telnet Remote Serial Port
COM_PORT_OPTION = chr(44) # Com Port Control Option
SUPPRESS_LOCAL_ECHO = chr(45) # Telnet Suppress Local Echo
TLS = chr(46) # Telnet Start TLS
KERMIT = chr(47) # KERMIT
SEND_URL = chr(48) # SEND-URL
FORWARD_X = chr(49) # FORWARD_X
PRAGMA_LOGON = chr(138) # TELOPT PRAGMA LOGON
SSPI_LOGON = chr(139) # TELOPT SSPI LOGON
PRAGMA_HEARTBEAT = chr(140) # TELOPT PRAGMA HEARTBEAT
EXOPL = chr(255) # Extended-Options-List
NOOPT = chr(0)
MCCP2 = chr(86)  # Mud Compression Protocol, v2
MCCP1 = chr(85)  # Mud Compression Protocol, v1 (broken and not supported here)
MSP = chr(90) # Mud Sound Protocol
MXP = chr(91) # Mud eXtension Protocol
GMCP = chr(201)

# reverse lookup allowing us to see what's going on more easily
# when we're debugging.
# for a list of telnet options: http://www.freesoft.org/CIE/RFC/1700/10.htm
CODES = {255: "IAC",
         254: "DON'T",
         253: "DO",
         252: "WON'T",
         251: "WILL",
         250: "SB",
         249: "GA",
         240: "SE",
         239: "TELOPT_EOR",
         0:   "<IS>",
         1:   "[<ECHO> or <SEND/MODE>]",
         3:   "<SGA>",
         5:   "STATUS",
         24:  "<TERMTYPE>",
         25:  "<EOR>",
         31:  "<NegoWindoSize>",
         32:  "<TERMSPEED>",
         34:  "<Linemode>",
         35:  "<XDISPLAY>",
         36:  "<ENV>",
         39:  "<NewENV>",
         85:  "MCCP1",
         86:  "MCCP2",
         90:  "MSP",
         91:  "MXP",
         201: "GMCP"}

will_v2 = "%s%s%s"     % (IAC, WILL, MCCP2)

class Telnet(asyncore.dispatcher):

    """Telnet interface class.

    read_sb_data()
        Reads available data between SB ... SE sequence. Don't block.

    set_option_negotiation_callback(callback)
        Each time a telnet option is read on the input flow, this callback
        (if set) is called with the following parameters :
        callback(command, option)
            option will be chr(0) when there is no option.
        No other action is done afterwards by telnetlib.

    """

    def __init__(self, host=None, port=0, sock=None):
        """Constructor.

        When called without arguments, create an unconnected instance.
        With a hostname argument, it connects the instance; port number
        and timeout are optional.
        """
        if sock:
          asyncore.dispatcher.__init__(self, sock)
        else:
          asyncore.dispatcher.__init__(self)
        self.debuglevel = DEBUGLEVEL
        self.host = host
        self.port = port
        self.rawq = ''
        self.irawq = 0
        self.cookedq = ''
        self.eof = 0
        self.iacseq = '' # Buffer for IAC sequence.
        self.sb = 0 # flag for SB and SE sequence.
        self.sbdataq = ''
        self.outbuffer = ''
        self.options = {}
        self.connected = False
        self.zlib_comp = None
        self.zlib_decomp = None
        self.option_callback = self.handleopt

    def readdatafromsocket(self):
      return self.recv(1024)

    def handleopt(self, command, option):
      origoption = option
      origcommand = command
      if ord(command) in CODES:
        command = CODES[ord(command)]
      if ord(option) in CODES:
        option = CODES[ord(option)]
      self.msg('Command:', command, '(', origcommand, ':', ord(origcommand), ') with option', option, '(', origoption, ':', ord(origoption), ')')

      if command == 'DO' and option == 'MCCP2':
        if self.ttype == 'Client':
          self.msg("starting mccp")
          cmd = '%s%s%s%s%s' % (IAC, SB, MCCP2, IAC, SE,)
          self.send(IAC + SB + MCCP2 + IAC + SE)

          self.options['MCCP2'] = True
          self.zlib_comp = zlib.compressobj(15)
          self.outbuffer = self.zlib_comp.compress(self.outbuffer)
          self.process_rawq()

      elif command == 'WILL' and option == 'MCCP2':
        if self.ttype == 'Server':
          self.msg('sending IAC DO MCCP2')
          self.send(IAC + DO + MCCP2)

          #self.options['MCCP2'] = True
          #self.zlib_comp = zlib.compressobj(9)
          #self.zlib_decomp = zlib.decompressobj(9)
          #self.process_rawq()

      elif command == 'WILL' and option == 'GMCP':
        if self.ttype == 'Server':
          self.msg('sending IAC DO GMCP')
          self.send(IAC + DO + GMCP)


      elif command == 'WILL':
          self.msg('Sending IAC WONT %s' % ord(option))
          self.send(IAC + WONT + origoption)
      elif command == 'DO':
          self.msg('Sending IAC DONT %s' % ord(option))
          self.send(IAC + DONT + origoption)
      elif command == 'DON\'T' or command == 'WON\'T':
          pass
      else:
          self.msg('Fallthrough:', command, '(', origcommand, ':', ord(origcommand), ') with option', option, '(', origoption, ':', ord(origoption), ')')
          self.msg(type(command), type(origcommand))
          if command == 'SE' or origcommand == SE:
            subcommand = self.sbdataq[0]
            if subcommand == MCCP2 and self.ttype == 'Server':
              self.msg('got an SE mccp in handleopt')
              self.msg('starting compression with server')
              self.options['MCCP2'] = True
              self.zlib_decomp = zlib.decompressobj(15)
              if self.rawq:
                self.msg('converting rawq in handleopt')
                self.rawq = self.zlib_decomp.decompress(self.rawq)
                self.process_rawq()
            else:
              self.msg('sbdataq: %r' % self.sbdataq)
              if subcommand == GMCP and self.ttype == 'Server':
                data = self.sbdataq[1:]
                package, data = data.split(" ", 1)
                import json
                newdata = json.loads(data)
                self.msg(package, data)
                self.msg(type(newdata), newdata)

          self.msg('length of sbdataq', len(self.sbdataq))
          if len(self.sbdataq) == 1:
            self.msg('should look at the sbdataq', self.sbdataq, '(', ord(self.sbdata), ')')
          else:
            self.msg('should look at the sbdataq', self.sbdataq)


    def __del__(self):
        """Destructor -- close the connection."""
        self.close()

    def msg(self, *args, **kwargs):
        """Print a debug message, when the debug level is > 0.

        If extra arguments are present, they are substituted in the
        message using the standard string formatting operator.

        """
        if not('level' in kwargs):
          kwargs['level'] = 1
        if kwargs['level'] >= self.debuglevel:
            print('Telnet(%-15s - %-5s %-7s): ' % (self.host, self.port, self.ttype), *args)

    def set_debuglevel(self, debuglevel):
        """Set the debug level.

        The higher it is, the more debug output you get (on sys.stdout).

        """
        self.debuglevel = debuglevel

    def doconnect(self):
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.connect((self.host, self.port))
      if self.ttype == 'Server':
        self.send("%s%s%s" % (IAC, WILL, MCCP2))
      self.connected = True

    def handle_close(self):
        """Close the connection."""
        self.msg('closing connection')
        self.close()
        self.options = {}
        self.eof = 1
        self.iacseq = ''
        self.sb = 0

    def handle_write(self):
      self.msg('Handle_write', self.ttype, self.outbuffer)
      sent = self.send(self.outbuffer)
      self.outbuffer = self.outbuffer[sent:]

    def addtooutbuffer(self, outbuffer):
        """Write a string to the socket, doubling any IAC characters.

        Can block if the connection is blocked.  May raise
        socket.error if the connection is closed.

        """
        self.msg( 'adding to buffer')
        if IAC in outbuffer:
            outbuffer = outbuffer.replace(IAC, IAC+IAC)

        if 'MCCP2' in self.options and self.ttype == 'Client':
          self.msg( 'compressing data for')
          outbuffer = self.zlib_comp.compress(outbuffer) + self.zlib_comp.flush(zlib.Z_SYNC_FLUSH)
        self.outbuffer = self.outbuffer + outbuffer

    def writable(self):
      #self.msg( 'writable', self.ttype, len(self.outbuffer) > 0)
      return len(self.outbuffer) > 0

    def handle_error(self):
      pass

    def handle_read(self):
        """Read readily available data.

        Raise EOFError if connection closed and no cooked data
        available.  Return '' if no cooked data available otherwise.
        Don't block unless in the midst of an IAC sequence.

        """
        self.process_rawq()
        self.fill_rawq()
        self.process_rawq()

    def getdata(self):
        """Return any data available in the cooked queue.

        Raise EOFError if connection closed and no data available.
        Return '' if no cooked data available otherwise.  Don't block.

        """
        buf = self.cookedq
        self.cookedq = ''
        if not buf and self.eof and not self.rawq:
            raise EOFError, 'telnet connection closed'
        return buf

    def read_sb_data(self):
        """Return any data available in the SB ... SE queue.

        Return '' if no SB ... SE available. Should only be called
        after seeing a SB or SE command. When a new SB command is
        found, old unread SB data will be discarded. Don't block.

        """
        buf = self.sbdataq
        self.sbdataq = ''
        return buf

    def set_option_negotiation_callback(self, callback):
        """Provide a callback function called after each receipt of a telnet option."""
        self.option_callback = callback

    def process_rawq(self):
        """Transfer from raw queue to cooked queue.

        Set self.eof when connection is closed.  Don't block unless in
        the midst of an IAC sequence.

        """
        buf = ['', '']
        try:
            while self.rawq:
                c = self.rawq_getchar()
                if not self.iacseq:
                    if c == theNULL:
                        continue
                    if c == "\021":
                        continue
                    if c != IAC:
                        buf[self.sb] = buf[self.sb] + c
                        continue
                    else:
                        self.iacseq += c
                elif len(self.iacseq) == 1:
                    # 'IAC: IAC CMD [OPTION only for WILL/WONT/DO/DONT]'
                    if c in (DO, DONT, WILL, WONT):
                        self.iacseq += c
                        continue

                    self.iacseq = ''
                    if c == IAC:
                        buf[self.sb] = buf[self.sb] + c
                    else:
                        if c == SB: # SB ... SE start.
                            self.sb = 1
                            self.sbdataq = ''
                        elif c == SE:
                            self.sb = 0
                            self.sbdataq = self.sbdataq + buf[1]
                            buf[1] = ''
                            if len(self.sbdataq) == 1:
                              self.msg('proccess_rawq: got an SE', ord(self.sbdataq))
                            else:
                              self.msg('proccess_rawq: got an SE (2)', self.sbdataq)
                        if self.option_callback:
                            # Callback is supposed to look into
                            # the sbdataq
                            self.option_callback(c, NOOPT)
                        else:
                            # We can't offer automatic processing of
                            # suboptions. Alas, we should not get any
                            # unless we did a WILL/DO before.
                            self.msg('IAC %d not recognized' % ord(c))
                elif len(self.iacseq) == 2:
                    cmd = self.iacseq[1]
                    self.iacseq = ''
                    opt = c
                    if cmd in (DO, DONT):
                        self.msg('IAC %s %d' %
                            (cmd == DO and 'DO' or 'DONT', ord(opt)))
                        if self.option_callback:
                            self.option_callback(cmd, opt)
                        else:
                            self.msg('Sending IAC WONT %s' % ord(opt))
                            self.send(IAC + WONT + opt)
                    elif cmd in (WILL, WONT):
                        self.msg('IAC %s %d' %
                            (cmd == WILL and 'WILL' or 'WONT', ord(opt)))
                        if self.option_callback:
                            self.option_callback(cmd, opt)
                        else:
                            self.msg('Sending IAC DONT %s' % ord(opt))
                            self.send(IAC + DONT + opt)
        except EOFError: # raised by self.rawq_getchar()
            self.iacseq = '' # Reset on EOF
            self.sb = 0
            pass
        self.cookedq = self.cookedq + buf[0]
        self.sbdataq = self.sbdataq + buf[1]

    def rawq_getchar(self):
        """Get next char from raw queue.

        Block if no data is immediately available.  Raise EOFError
        when connection is closed.

        """
        if not self.rawq:
            self.fill_rawq()
            if self.eof:
                raise EOFError
        c = self.rawq[self.irawq]
        self.irawq = self.irawq + 1
        if self.irawq >= len(self.rawq):
            self.rawq = ''
            self.irawq = 0
        return c

    def fill_rawq(self):
        """Fill raw queue from exactly one recv() system call.

        Block if no data is immediately available.  Set self.eof when
        connection is closed.

        """
        if self.irawq >= len(self.rawq):
            self.rawq = ''
            self.irawq = 0
        # The buffer size should be fairly small so as to avoid quadratic
        # behavior in process_rawq() above
        buf = self.readdatafromsocket()
        #print 'fill_rawq', self.ttype, self.host, self.port, 'received', buf
        self.msg("recv %r" % buf)
        if 'MCCP2' in self.options and self.ttype == 'Server':
          self.msg('decompressing')
          tbuf = self.zlib_decomp.decompress(buf)
          self.msg('unused_data', self.zlib_decomp.unused_data)
          self.msg('unconsumed_tail', self.zlib_decomp.unconsumed_tail)
          self.msg('Uncompressed: %s %r' % (type(tbuf), tbuf))
          self.rawq = self.rawq + tbuf
        else:
          self.eof = (not buf)
          self.rawq = self.rawq + buf
        self.msg('rawq', self.rawq)

if __name__ == '__main__':
    test()
