# $HeadURL:  $
''' SeSInspectorAgent

  This agent inspect Services, and evaluates policies that apply.

'''

import Queue
import time

from DIRAC                                                  import S_OK, S_ERROR
from DIRAC.Core.Base.AgentModule                            import AgentModule
from DIRAC.Core.Utilities.ThreadPool                        import ThreadPool
from DIRAC.ResourceStatusSystem.Utilities                   import CS
from DIRAC.ResourceStatusSystem.Client.ResourceStatusClient import ResourceStatusClient
from DIRAC.ResourceStatusSystem.Command                     import knownAPIs
from DIRAC.ResourceStatusSystem.PolicySystem.PEP            import PEP
from DIRAC.ResourceStatusSystem.Utilities.Utils             import where

__RCSID__  = '$Id: $'
AGENT_NAME = 'ResourceStatus/SeSInspectorAgent'

class SeSInspectorAgent( AgentModule ):
  '''
    The SeSInspector agent ( ServiceInspectorAgent ) is one of the four
    InspectorAgents of the RSS.

    This Agent takes care of the Service. In order to do so, it gathers
    the eligible ones and then evaluates their statuses with the PEP.

    If you want to know more about the SeSInspectorAgent, scroll down to the
    end of the file.
  '''

  # Too many public methods
  # pylint: disable-msg=R0904

  def initialize( self ):

    # Attribute defined outside __init__ 
    # pylint: disable-msg=W0201

    try:
      self.rsClient      = ResourceStatusClient()
      self.servicesFreqs = CS.getTypedDictRootedAtOperations( 'CheckingFreqs/ServicesFreqs' )
      self.queue         = Queue.Queue()

      self.maxNumberOfThreads = self.am_getOption( 'maxThreadsInPool', 1 )
      self.threadPool         = ThreadPool( self.maxNumberOfThreads,
                                            self.maxNumberOfThreads )
      if not self.threadPool:
        self.log.error( 'Can not create Thread Pool' )
        return S_ERROR( 'Can not create Thread Pool' )

      for _i in xrange( self.maxNumberOfThreads ):
        self.threadPool.generateJobAndQueueIt( self._executeCheck )

      return S_OK()

    except Exception:
      errorStr = "SeSInspectorAgent initialization"
      self.log.exception( errorStr )
      return S_ERROR( errorStr )

  def execute( self ):

    try:
      
      kwargs = { 'meta' : {} }
      kwargs['meta']['columns'] = [ 'ServiceName', 'StatusType', 'Status',
                                    'FormerStatus', 'SiteType',
                                    'ServiceType', 'TokenOwner' ]
      kwargs[ 'tokenOwner' ]    = 'RS_SVC'

      resQuery = self.rsClient.getStuffToCheck( 'Service', self.servicesFreqs, **kwargs )
      if not resQuery[ 'OK' ]:
        self.log.error( resQuery[ 'Message' ] )
        return resQuery

      resQuery = resQuery[ 'Value' ]
      self.log.info( 'Found %d candidates to be checked.' % len( resQuery ) )

      for service in resQuery:
        resourceL = [ 'Service' ] + service
        # Here we peek INSIDE the Queue to know if the item is already
        # here. It's ok _here_ since (i.e. I know what I'm doing):
        # - It is a read only operation.
        # - We do not need exact accuracy, it's ok to have 2 times the same item in the queue sometimes.
        if resourceL not in self.queue.queue:
          self.queue.put( resourceL )

      return S_OK()

    except Exception, x:
      errorStr = where( self, self.execute )
      self.log.exception( errorStr, lException = x )
      return S_ERROR( errorStr )

  def finalize( self ):
    '''
      Method executed at the end of the last cycle. It waits until the queue
      is empty.
    '''
    if not self.queue.empty():
      self.log.info( "Wait for queue to get empty before terminating the agent"  )
      while not self.queue.empty():
        time.sleep( 2 )
      self.log.info( "Queue is empty, terminating the agent..." )
    return S_OK()

################################################################################

  def _executeCheck(self):
    '''
      Method executed by the threads in the pool. Picks one element from the
      common queue, and enforces policies on that element.
    '''
    # Init the APIs beforehand, and reuse them.
    __APIs__ = [ 'ResourceStatusClient', 'ResourceManagementClient' ]
    clients = knownAPIs.initAPIs( __APIs__, {} )

    pep = PEP( clients = clients )

    while True:
      toBeChecked = self.queue.get()

      pepDict = { 'granularity'  : toBeChecked[ 0 ],
                  'name'         : toBeChecked[ 1 ],
                  'statusType'   : toBeChecked[ 2 ],
                  'status'       : toBeChecked[ 3 ],
                  'formerStatus' : toBeChecked[ 4 ],
                  'siteType'     : toBeChecked[ 5 ],
                  'serviceType'  : toBeChecked[ 6 ],
                  'tokenOwner'   : toBeChecked[ 7 ]}

      try:
        self.log.info( "Checking Service %s, with type/status: %s/%s" %
                      ( pepDict['name'], pepDict['statusType'], pepDict['status'] ) )

        pepRes = pep.enforce( **pepDict )
        if pepRes.has_key( 'PolicyCombinedResult' ) and pepRes[ 'PolicyCombinedResult' ].has_key( 'Status' ):
          pepStatus = pepRes[ 'PolicyCombinedResult' ][ 'Status' ]
          if pepStatus != pepDict[ 'status' ]:
            self.log.info( 'Updated %s %s from %s/%s to %s/%s' %
                          ( pepDict["granularity"],
                            pepDict['name'],
                            pepDict['statusType'], pepDict['status'],
                            pepDict['statusType'], pepStatus ))

      except Exception:
        self.log.exception( "SeSInspector._executeCheck Checking Service %s, with type/status: %s/%s" %
                           ( pepDict['name'], pepDict['statusType'], pepDict['status'] ) )

################################################################################
#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF
