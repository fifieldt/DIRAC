#!/usr/bin/env python
# $HeadURL$
"""
 Perform initial sanity checks on WN, installs and configures DIRAC and runs
 Job Agent to execute pending workload on WMS.
 It requires dirac-install script to be sitting in the same directory.
"""
__RCSID__ = "$Id$"

import os
import sys
import getopt
import urllib2
import stat
import socket
import imp
import re

#Check PYTHONPATH and LD_LIBARY_PATH
try:
  os.umask( 022 )

  pythonpath = os.getenv( 'PYTHONPATH', '' ).split( ':' )
  newpythonpath = []
  for p in pythonpath:
    if p == '': continue
    try:
      if os.path.normpath( p ) in sys.path:
        # In case a given directory is twice in PYTHONPATH it has to removed only once
        sys.path.remove( os.path.normpath( p ) )
    except Exception, x:
      print 'Directories in PYTHONPATH:', pythonpath
      print 'Failing path:', p, os.path.normpath( p )
      print 'sys.path:', sys.path
      raise x
except Exception, x:
  print sys.executable
  print sys.version
  print os.uname()
  print x
  raise x

class CliParams:

  MAX_CYCLES = 5

  def __init__( self ):
    self.debug = False
    self.local = False
    self.dryRun = False
    self.testVOMSOK = False
    self.site = ""
    self.ceName = ""
    self.platform = ""
    self.minDiskSpace = 2560 #MB
    self.jobCPUReq = 900
    self.pythonVersion = '25'
    self.userGroup = ""
    self.userDN = ""
    self.maxCycles = CliParams.MAX_CYCLES
    self.flavour = 'DIRAC'
    self.gridVersion = '2009-08-13'
    
###
# Helper functions
###

def logDEBUG( msg ):
  if cliParams.debug:
    for line in msg.split( "\n" ):
      print "[DEBUG] %s" % line

def logERROR( msg ):
  for line in msg.split( "\n" ):
    print "[ERROR] %s" % line

def logINFO( msg ):
  for line in msg.split( "\n" ):
    print "[INFO]  %s" % line
    
def executeAndGetOutput( cmd ):
  try:
    import subprocess
    p = subprocess.Popen( "%s" % cmd, shell = True, stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, close_fds = True )
    outData = p.stdout.read().strip()
    p.wait()
  except ImportError:
    import popen2
    p3 = popen2.Popen3( "%s" % cmd )
    outData = p3.fromchild.read().strip()
    p3.wait()
  return outData

# Version print

logINFO( "Running %s" % " ".join( sys.argv ) )
logINFO( "Version %s" % __RCSID__ )

###
# Checking scripts are ok
###
try:
  pilotScript = os.path.realpath( __file__ )
  # in old python versions __file__ is not defined
except:
  pilotScript = os.path.realpath( sys.argv[0] )

pilotScriptName = os.path.basename( pilotScript )
pilotRootPath = os.path.dirname( pilotScript )

rootPath = os.getcwd()

installScriptName = 'dirac-install.py'

for dir in ( pilotRootPath, rootPath ):
  installScript = os.path.join( dir, installScriptName )
  if os.path.isfile( installScript ):
    break

if not os.path.isfile( installScript ):
  logERROR( "%s requires %s to exist in one of: %s, %s" % ( pilotScriptName, installScriptName,
                                                            pilotRootPath, rootPath ) )
  logINFO( "Trying to download it to %s..." % rootPath )
  try:
    remoteLocation = "http://svnweb.cern.ch/guest/dirac/DIRAC/trunk/DIRAC/Core/scripts/dirac-install.py"
    remoteLocation = "http://svnweb.cern.ch/guest/dirac/DIRAC/trunk/DIRAC/Core/scripts/dirac-install.py"
    remoteFD = urllib2.urlopen( remoteLocation )
    installScript = os.path.join( rootPath, installScriptName )
    localFD = open( installScript, "w" )
    localFD.write( remoteFD.read() )
    localFD.close()
    remoteFD.close()
  except Exception, e:
    logERROR( "Could not download %s..: %s" % ( remoteLocation, str( e ) ) )
    sys.exit( 1 )

os.chmod( installScript, stat.S_IRWXU )


###
# Option parsing
###

"""
 Flags not migrated from old dirac-pilot
   -r --repository=<rep>       Use <rep> as cvs repository              <--Not done
   -C --cvs                    Retrieve from CVS (implies -b) <--Not done
"""

cmdOpts = ( ( 'b', 'build', 'Force local compilation' ),
            ( 'd', 'debug', 'Set debug flag' ),
            ( 'e:', 'extraPackages=', 'Extra packages to install (comma separated)' ),
            ( 'g:', 'grid=', 'lcg tools package version' ),
            ( 'h', 'help', 'Show this help' ),
            ( 'i:', 'python=', 'Use python<24|25> interpreter' ),
            ( 'p:', 'platform=', 'Use <platform> instead of local one' ),
            ( 't', 'test', 'Make a dry run. Do not run JobAgent' ),
            ( 'u:', 'url=', 'Use <url> to download tarballs' ),
            ( 'r:', 'release=', 'DIRAC release to install' ),
            ( 'n:', 'name=', 'Set <Site> as Site Name' ),
            ( 'D:', 'disk=', 'Require at least <space> MB available' ),
            ( 'M:', 'MaxCycles=', 'Maximum Number of JobAgent cycles to run' ),
            ( 'N:', 'Name=', 'Use <CEName> to determine Site Name' ),
            ( 'P:', 'path=', 'Install under <path>' ),
            ( 'E', 'server', 'Make a full server installation' ),
            ( 'S:', 'setup=', 'DIRAC Setup to use' ),
            ( 'C:', 'configurationServer=', 'Configuration servers to use' ),
            ( 'T:', 'CPUTime', 'Requested CPU Time' ),
            ( 'G:', 'Group=', 'DIRAC Group to use' ),
            ( 'O:', 'OwnerDN', 'Pilot OwnerDN (for private pilots)' ),
            ( 'U', 'Upload', 'Upload compiled distribution (if built)' ),
            ( 'V:', 'VO=', 'Virtual Organization' ),
            ( 'W:', 'gateway=', 'Configure <gateway> as DIRAC Gateway during installation' ),
            ( 's:', 'section=', 'Set base section for relative parsed options' ),
            ( 'o:', 'option=', 'Option=value to add' ),
            ( 'c', 'cert', 'Use server certificate instead of proxy' ),
          )

cliParams = CliParams()

installOpts = []
configureOpts = []

optList, args = getopt.getopt( sys.argv[1:],
                               "".join( [ opt[0] for opt in cmdOpts ] ),
                               [ opt[1] for opt in cmdOpts ] )
for o, v in optList:
  if o in ( '-h', '--help' ):
    print "Usage %s <opts>" % sys.argv[0]
    for cmdOpt in cmdOpts:
      print "%s %s : %s" % ( cmdOpt[0].ljust( 4 ), cmdOpt[1].ljust( 20 ), cmdOpt[2] )
    sys.exit( 1 )
  elif o in ( '-b', '--build' ):
    installOpts.append( '-b' )
  elif o == '-d' or o == '--debug':
    cliParams.debug = True
    installOpts.append( '-d' )
  elif o == '-e' or o == '--extraPackages':
    installOpts.append( '-e "%s"' % v )
  elif o == '-g' or o == '--grid':
    cliParams.gridVersion = v
  elif o == '-i' or o == '--python':
    cliParams.pythonVersion = v
  elif o == '-n' or o == '--name':
    configureOpts.append( '-n "%s"' % v )
    cliParams.site = v
  elif o == '-p' or o == '--platform':
    installOpts.append( '-p "%s"' % v )
    cliParams.platform = v
  elif o == '-r' or o == '--release':
    installOpts.append( '-r "%s"' % v )
  elif o == '-t' or o == '--test':
    cliParams.dryRun = True
  elif o == '-u' or o == '--url':
    #TODO
    pass
  elif o == '-N' or o == '--Name':
    configureOpts.append( '-N "%s"' % v )
    cliParams.ceName = v
  elif o == '-D' or o == '--disk':
    try:
      cliParams.minDiskSpace = int( v )
    except:
      pass
  elif o == '-M' or o == '--MaxCycles':
    try:
      cliParams.maxCycles = min( CliParams.MAX_CYCLES, int( v ) )
    except:
      pass
  elif o in ( '-S', '--setup' ):
    configureOpts.append( '-S "%s"' % v )
  elif o in ( '-C', '--configurationServer' ):
    configureOpts.append( '-C "%s"' % v )
  elif o in ( '-P', '--path' ):
    installOpts.append( '-P "%s"' % v )
    rootPath = v
  elif o in ( '-T', '--CPUTime' ):
    cliParams.jobCPUReq = v
  elif o in ( '-G', '--Group' ):
    cliParams.userGroup = v
  elif o in ( '-O', '--OwnerDN' ):
    cliParams.userDN = v
  elif o in ( '-U', '--Upload' ):
    #TODO
    pass
  elif o in ( '-V', '--VO' ):
    configureOpts.append( '-V "%s"' % v )
  elif o in ( '-W', '--gateway' ):
    configureOpts.append( '-W "%s"' % v )
  elif o == '-E' or o == '--server':
    installOpts.append( '-t "server"' )
  elif o == '-o' or o == '--option':
    configureOpts.append( '-o "%s"' % v )
  elif o == '-s' or o == '--section':
    configureOpts.append( '-s "%s"' % v )
  elif o == '-c' or o == '--cert':
    configureOpts.append( '--UseServerCertificate' )

if cliParams.gridVersion:
  installOpts.append( "-g '%s'" % cliParams.gridVersion )
  
if cliParams.pythonVersion:
  installOpts.append( '-i "%s"' % cliParams.pythonVersion )
##
# Attempt to determine the flavour
##

pilotRef = 'Unknown'
if os.environ.has_key( 'EDG_WL_JOBID' ):
  cliParams.flavour = 'LCG'
  pilotRef = os.environ['EDG_WL_JOBID']

if os.environ.has_key( 'GLITE_WMS_JOBID' ):
  cliParams.flavour = 'gLite'
  pilotRef = os.environ['GLITE_WMS_JOBID']

configureOpts.append( '-o /LocalSite/GridMiddleware=%s' % cliParams.flavour )

###
# Try to get the CE name
###
if pilotRef != 'Unknown':
  CE = executeAndGetOutput( 'edg-brokerinfo getCE || glite-brokerinfo getCE' )
  cliParams.ceName = CE.split( ':' )[0]
  configureOpts.append( '-o /LocalSite/PilotReference=%s' % pilotRef )
  configureOpts.append( '-N "%s"' % cliParams.ceName )
else:
  cliParams.ceName = 'Local'

###
# Set the platform if defined
###

if cliParams.platform:
  installOpts.append( '-p "%s"' % cliParams.platform )

###
# Set the group and the DN
###

if cliParams.userGroup:
  configureOpts.append( '-o /AgentJobRequirements/OwnerGroup="%s"' % cliParams.userGroup )

if cliParams.userDN:
  configureOpts.append( '-o /AgentJobRequirements/OwnerDN="%s"' % cliParams.userDN )

###
# Do the installation
###

installCmd = "%s %s" % ( installScript, " ".join( installOpts ) )

logDEBUG( "Installing with: %s" % installCmd )

if os.system( installCmd ):
  logERROR( "Could not make a proper DIRAC installation" )
  sys.exit( 1 )

###
# Set the env to use the recently installed DIRAC
###

diracScriptsPath = os.path.join( rootPath, 'scripts' )
sys.path.insert( 0, diracScriptsPath )

###
# Configure DIRAC
###

configureCmd = "%s %s" % ( os.path.join( diracScriptsPath, "dirac-configure" ), " ".join( configureOpts ) )

logDEBUG( "Configuring DIRAC with: %s" % configureCmd )

if os.system( configureCmd ):
  logERROR( "Could not configure DIRAC" )
  sys.exit( 1 )

###
# Dump the CS to cache in file
###

cfgFile = os.path.join( rootPath, "etc", "dirac.cfg" )
cacheScript = os.path.join( diracScriptsPath, "dirac-configuration-dump-local-cache" )
if os.system( "%s -f %s" % ( cacheScript, cfgFile ) ):
  logERROR( "Could not dump the CS to %s" % cfgFile )

###
# Set the LD_LIBRARY_PATH and PATH
###
if not cliParams.platform:
  platformPath = os.path.join( rootPath, "DIRAC", "Core", "Utilities", "Platform.py" )
  platFD = open( platformPath, "r" )
  PlatformModule = imp.load_module( "Platform", platFD, platformPath, ( "", "r", imp.PY_SOURCE ) )
  platFD.close()
  cliParams.platform = PlatformModule.getPlatformString()

if cliParams.testVOMSOK:
  # Check voms-proxy-info before touching the original PATH and LD_LIBRARY_PATH
  os.system( 'which voms-proxy-info && voms-proxy-info -all' )

diracLibPath = os.path.join( rootPath, cliParams.platform, 'lib' )
diracBinPath = os.path.join( rootPath, cliParams.platform, 'bin' )
if 'LD_LIBRARY_PATH' in os.environ:
  os.environ['LD_LIBRARY_PATH_SAVE'] = os.environ['LD_LIBRARY_PATH']
else:
  os.environ['LD_LIBRARY_PATH_SAVE'] = ""
os.environ['LD_LIBRARY_PATH'] = "%s" % ( diracLibPath )
os.environ['PATH'] = '%s:%s:%s' % ( diracBinPath, diracScriptsPath, os.getenv( 'PATH' ) )

###
# End of initialisation
###

#
# Check proxy
#

ret = os.system( 'dirac-proxy-info' )
if cliParams.testVOMSOK:
  ret = os.system( 'dirac-proxy-info | grep -q fqan' )
  if ret != 0:
    os.system( 'dirac-proxy-info 2>&1 | mail -s "dirac-pilot: missing voms certs at %s" dirac.alarms@gmail.com' % cliParams.site )
    sys.exit( -1 )

#
# Set the lhcb platform
#

architectureScriptName = "dirac-architecture"
architectureScript = ""
for entry in os.listdir( rootPath ):
  if entry.find( "DIRAC" ) == -1:
    continue
  candidate = os.path.join( entry, "scripts", architectureScriptName )
  if os.path.isfile( candidate ):
    architectureScript = candidate

if architectureScript:
  lhcbArchitecture = executeAndGetOutput( architectureScript ).strip()
  os.environ['CMTCONFIG'] = lhcbArchitecture
  dirac.logINFO( 'Setting CMTCONFIG=%s' % lhcbArchitecture )
  os.system( "%s -f %s -o '/LocalSite/Architecture=%s'" % ( cacheScript, lhcbArchitecture ) )
#
# Get host and local user info
#

localUid = os.getuid()
try:
  import pwd
  localUser = pwd.getpwuid( localUid )[0]
except:
  localUser = 'Unknown'

logINFO( 'Uname      = %s' % " ".join( os.uname() ) )
logINFO( 'Host Name  = %s' % socket.gethostname() )
logINFO( 'Host FQDN  = %s' % socket.getfqdn() )
logINFO( 'User Name  = %s' % localUser )
logINFO( 'User Id    = %s' % localUid )
logINFO( 'CurrentDir = %s' % rootPath )

fileName = '/etc/redhat-release'
if os.path.exists( fileName ):
  f = open( fileName, 'r' )
  logINFO( 'RedHat Release = %s' % f.read().strip() )
  f.close()

fileName = '/etc/lsb-release'
if os.path.isfile( fileName ):
  f = open( fileName, 'r' )
  logINFO( 'Linux release:\n%s' % f.read().strip() )
  f.close()

fileName = '/proc/cpuinfo'
if os.path.exists( fileName ):
  f = open( fileName, 'r' )
  cpu = f.readlines()
  f.close()
  nCPU = 0
  for line in cpu:
    if line.find( 'cpu MHz' ) == 0:
      nCPU += 1
      freq = line.split()[3]
    elif line.find( 'model name' ) == 0:
      CPUmodel = line.split( ': ' )[1].strip()
  logINFO( 'CPU (model)    = %s' % CPUmodel )
  logINFO( 'CPU (MHz)      = %s x %s' % ( nCPU, freq ) )

fileName = '/proc/meminfo'
if os.path.exists( fileName ):
  f = open( fileName, 'r' )
  mem = f.readlines()
  f.close()
  freeMem = 0
  for line in mem:
    if line.find( 'MemTotal:' ) == 0:
      totalMem = int( line.split()[1] )
    if line.find( 'MemFree:' ) == 0:
      freeMem += int( line.split()[1] )
    if line.find( 'Cached:' ) == 0:
      freeMem += int( line.split()[1] )
  logINFO( 'Memory (kB)    = %s' % totalMem )
  logINFO( 'FreeMem. (kB)  = %s' % freeMem )

#
# Disk space check
#

fs = os.statvfs( rootPath )
# bsize;    /* file system block size */
# frsize;   /* fragment size */
# blocks;   /* size of fs in f_frsize units */
# bfree;    /* # free blocks */
# bavail;   /* # free blocks for non-root */
# files;    /* # inodes */
# ffree;    /* # free inodes */
# favail;   /* # free inodes for non-root */
# flag;     /* mount flags */
# namemax;  /* maximum filename length */
diskSpace = fs[4] * fs[0] / 1024 / 1024
logINFO( 'DiskSpace (MB) = %s' % diskSpace )

if diskSpace < cliParams.minDiskSpace:
  logERROR( '%s MB < %s MB, not enough local disk space available, exiting'
                  % ( diskSpace, cliParams.minDiskSpace ) )
  sys.exit( 1 )

#
# Get job CPU requirement and queue normalization
#

if pilotRef != 'Unknown':
  logINFO( 'CE = %s' % cliParams.ceName )
  logINFO( 'LCG_SITE_CE = %s' % cliParams.site )

  queueNormList = executeAndGetOutput( 'dirac-wms-get-queue-normalization %s' % cliParams.ceName )
  queueNormList = queueNormList.strip().split( ' ' )
  if len( queueNormList ) == 2:
    queueNorm = float( queueNormList[1] )
    logINFO( 'Queue Normalization = %s SI00' % queueNorm )
    if queueNorm:
      # Update the local normalization factor: We are using seconds @ 500 SI00
      # This is the ratio SpecInt published by the site over 500 (the reference used for Matching)
      os.system( "%s -f %s -o /LocalSite/CPUScalingFactor=%s" % ( cacheScript, cfgFile, queueNorm / 500. ) )
  else:
    logERROR( 'Fail to get Normalization of the Queue' )

  queueLength = executeAndGetOutput( 'dirac-wms-get-normalized-queue-length %s' % cliParams.ceName )
  queueNormList = queueLength.strip().split( ' ' )
  if len( queueLength ) == 2:
    cliParams.jobCPUReq = float( queueLength[1] )
    logINFO( 'Normalized Queue Length = %s' % cliParams.jobCPUReq )
  else:
    logERROR( 'Failed to get Normalized length of the Queue' )

#
# further local configuration
#

inProcessOpts = ['-s /Resources/Computing/CEDefaults' ]
inProcessOpts .append( '-o WorkingDirectory=%s' % rootPath )
inProcessOpts .append( '-o GridCE=%s' % cliParams.ceName )
inProcessOpts .append( '-o LocalAccountString=%s' % localUser )
inProcessOpts .append( '-o TotalCPUs=%s' % 1 )
inProcessOpts .append( '-o MaxCPUTime=%s' % ( int( cliParams.jobCPUReq ) ) )
inProcessOpts .append( '-o CPUTime=%s' % ( int( cliParams.jobCPUReq ) ) )
inProcessOpts .append( '-o MaxRunningJobs=%s' % 1 )
# To prevent a wayward agent picking up and failing many jobs.
inProcessOpts .append( '-o MaxTotalJobs=%s' % 10 )


jobAgentOpts = [ '-o MaxCycles=%s' % cliParams.maxCycles ]
# jobAgentOpts.append( '-o CEUniqueID=%s' % JOB_AGENT_CE )
# jobAgentOpts.append( '-o ControlDirectory=%s' % jobAgentControl )
if cliParams.debug:
  jobAgentOpts.append( '-o LogLevel=DEBUG' )

if cliParams.userGroup:
  logINFO( 'Setting DIRAC Group to "%s"' % cliParams.userGroup )
  inProcessOpts .append( '-o OwnerGroup="%s"' % cliParams.userGroup )

if cliParams.userDN:
  logINFO( 'Setting Owner DN to "%s"' % cliParams.userDN )
  inProcessOpts .append( '-o OwnerDN="%s"' % cliParams.userDN )

# Find any .cfg file uploaded with the sandbox
extraCFG = []
for i in os.listdir( rootPath ):
  cfg = os.path.join( rootPath, i )
  if os.path.isfile( cfg ) and re.search( '.cfg&', cfg ):
    extraCFG.append( cfg )

#
# Start the job agent
#

logINFO( 'Starting JobAgent' )

os.environ['PYTHONUNBUFFERED'] = 'yes'

diracAgentScript = os.path.join( rootPath, "scripts", "dirac-agent" )
jobAgent = '%s WorkloadManagement/JobAgent %s %s %s' % ( diracAgentScript,
                                                         " ".join( jobAgentOpts ),
                                                         " ".join( inProcessOpts ),
                                                         " ".join( extraCFG ) ) 

logINFO( "JobAgent execution command:\n%s" % jobAgent )

if not cliParams.dryRun:
  os.system( jobAgent )

fs = os.statvfs( rootPath )
# bsize;    /* file system block size */
# frsize;   /* fragment size */
# blocks;   /* size of fs in f_frsize units */
# bfree;    /* # free blocks */
# bavail;   /* # free blocks for non-root */
# files;    /* # inodes */
# ffree;    /* # free inodes */
# favail;   /* # free inodes for non-root */
# flag;     /* mount flags */
# namemax;  /* maximum filename length */
diskSpace = fs[4] * fs[0] / 1024 / 1024
logINFO( 'DiskSpace (MB) = %s' % diskSpace )
ret = os.system( 'dirac-proxy-info' )


sys.exit( 0 )