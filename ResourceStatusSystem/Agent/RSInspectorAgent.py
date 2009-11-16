import threading
from DIRAC import gLogger, S_OK, S_ERROR
from DIRAC.Core.Base.AgentModule import AgentModule
from DIRAC.Core.Utilities.ThreadPool import ThreadPool,ThreadedJob
from DIRAC.ResourceStatusSystem.Utilities.Exceptions import *
from DIRAC.ResourceStatusSystem.Utilities.Utils import *
from DIRAC.ResourceStatusSystem.PolicySystem.PEP import PEP
from DIRAC.ResourceStatusSystem.DB.ResourceStatusDB import *
from DIRAC.ResourceStatusSystem.Policy import Configurations

AGENT_NAME = 'ResourceStatus/RSInspectorAgent'

class RSInspectorAgent(AgentModule):
  """ Class RSInspectorAgent is in charge of going through Resources
      table, and pass Resource and Status to the PEP
  """

#############################################################################

  def initialize(self):
    """ Standard constructor
    """
    
    try:
      try:
        self.rsDB = ResourceStatusDB()
      except RSSDBException, x:
        gLogger.error(whoRaised(x))
      except RSSException, x:
        gLogger.error(whoRaised(x))
      
      self.am_setOption( "PollingTime", 60 )
      self.ResToBeChecked = []
      self.ResNamesInCheck = []
      #self.maxNumberOfThreads = gConfig.getValue(self.section+'/NumberOfThreads',1)
      #self.threadPoolDepth = gConfig.getValue(self.section+'/ThreadPoolDepth',1)
      
      self.maxNumberOfThreads = self.am_getOption( 'maxThreadsInPool', 1 )
      #self.threadPool = ThreadPool(1,self.maxNumberOfThreads)
  
      #vedi taskQueueDirector
      self.threadPool = ThreadPool( self.am_getOption('minThreadsInPool'),
                         self.am_getOption('maxThreadsInPool'),
                         self.am_getOption('totalThreadsInPool') )
      if not self.threadPool:
        self.log.error('Can not create Thread Pool:', directorPool)
        return
      
      self.lockObj = threading.RLock()
      
      return S_OK()
    
    except Exception, x:
      errorStr = where(self, self.execute)
      gLogger.exception(errorStr,lException=x)
      return S_ERROR(errorStr)

#############################################################################

  def execute(self):
    """ The main RSInspectorAgent execution method
    """
    
    try:
      resourcesGetter = ThreadedJob(self._getResourcesToCheck)
      self.threadPool.queueJob(resourcesGetter)
      
      #for i in range(self.threadPoolDepth - 2):
      for i in range(self.maxNumberOfThreads - 1):
        checkExecutor = ThreadedJob(self._executeCheck)
        self.threadPool.queueJob(checkExecutor)
    
      self.threadPool.processResults()
      return S_OK()

    except Exception, x:
      errorStr = where(self, self.execute)
      gLogger.exception(errorStr,lException=x)
      return S_ERROR(errorStr)
      
#############################################################################

  def _getResourcesToCheck(self):
    """ call rsDB.ResourcesToCheck() and put result in list
    """

    try:
      res = self.rsDB.getResourcesToCheck(Configurations.ACTIVE_CHECK_FREQUENCY, Configurations.PROBING_CHECK_FREQUENCY, Configurations.BANNED_CHECK_FREQUENCY)
    except RSSDBException, x:
      gLogger.error(whoRaised(x))
    except RSSException, x:
      gLogger.error(whoRaised(x))
 
    for resourceTuple in res:
      if resourceTuple[0] in self.ResNamesInCheck:
        break
      resourceL = ['Resource']
      for x in resourceTuple:
        resourceL.append(x)
      self.lockObj.acquire()
      try:
        self.ResNamesInCheck.insert(0, resourceL[1])
        self.ResToBeChecked.insert(0, resourceL)
      finally:
        self.lockObj.release()

#############################################################################

  def _executeCheck(self):
    """ create istance of a PEP, 
        instantiated popping a resource or site from list
    """
    
    if len(self.ResToBeChecked) > 0:
        
      self.lockObj.acquire()
      try:
        toBeChecked = self.ResToBeChecked.pop()
        self.ResNamesInCheck.remove(toBeChecked[1])
      finally:
        self.lockObj.release()
      
      granularity = toBeChecked[0]
      resourceName = toBeChecked[1]
      status = toBeChecked[2]
      formerStatus = toBeChecked[3]
      reason = toBeChecked[4]
      
      newPEP = PEP(granularity = granularity, name = resourceName, status = status, formerStatus = formerStatus, reason = reason)
      #newPEP = PEP({'PolicyType':'Resource_PolType', 'Granularity':granularity}, name = resourceName, status = status, formerStatus = formerStatus, reason = reason)
      newPEP.enforce()