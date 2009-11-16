""" The PilotsEfficiency_Simple_Policy class is a policy class 
    that checks the efficiency of the pilots
"""

from DIRAC.ResourceStatusSystem.Policy.PolicyBase import PolicyBase
from DIRAC.ResourceStatusSystem.Client.Command.ClientsInvoker import ClientsInvoker
from DIRAC.ResourceStatusSystem.Utilities.Exceptions import *
from DIRAC.ResourceStatusSystem.Utilities.Utils import *
from DIRAC.ResourceStatusSystem.Policy import Configurations

class PilotsEfficiency_Simple_Policy(PolicyBase):
  
  def evaluate(self, args, knownInfo=None, commandIn=None):
    """ evaluate policy on pilots stats, using args (tuple). 
        - args[0] should be a ValidRes
        - args[1] should be the name of the ValidRes
        - args[2] should be the present status
        
        returns:
            { 
              'SAT':True|False, 
              'Status':Active|Probing|Banned, 
              'Reason':'PilotsEff:low|PilotsEff:med|PilotsEff:good',
            }
    """ 

    if not isinstance(args, tuple):
      raise TypeError, where(self, self.evaluate)
    
    if args[0] not in ValidRes:
      raise InvalidRes, where(self, self.evaluate)
    
    if args[2] not in ValidStatus:
      raise InvalidStatus, where(self, self.evaluate)

    if args[2] == 'Banned':
      return {'SAT':None}

    if knownInfo is not None:
      if 'PilotsEff' in knownInfo.keys():
        status = knownInfo['PilotsEff']
    else:
      if commandIn is not None:
        command = commandIn
      else:
        # use standard command
        from DIRAC.ResourceStatusSystem.Client.Command.Pilots_Command import PilotsEffSimple_Command
        command = PilotsEffSimple_Command()
        
      clientsInvoker = ClientsInvoker()
      clientsInvoker.setCommand(command)
      status = clientsInvoker.doCommand(args)['PilotsEff']
    
    result = {}
    
    if args[2] == 'Active':
      if status == 'Good':
        result['SAT'] = False
        result['Status'] = 'Active'
        result['Reason'] = 'PilotsEff:Good'
      elif status == 'Fair':
        result['SAT'] = True
        result['Status'] = 'Probing'
        result['Reason'] = 'PilotsEff:Fair'
      elif status == 'Poor':
        result['SAT'] = True
        result['Status'] = 'Probing'
        result['Reason'] = 'PilotsEff:Poor'
      elif status == 'Idle':
        result['SAT'] = None
      elif status == 'Bad':
        result['SAT'] = True
        result['Status'] = 'Banned'
        result['Reason'] = 'PilotsEff:Bad'
    elif args[2] == 'Probing':
      if status == 'Good':
        result['SAT'] = True
        result['Status'] = 'Active'
        result['Reason'] = 'PilotsEff:Good'
      elif status == 'Fair':
        result['SAT'] = False
        result['Status'] = 'Probing'
        result['Reason'] = 'PilotsEff:Fair'
      elif status == 'Poor':
        result['SAT'] = False
        result['Status'] = 'Probing'
        result['Reason'] = 'PilotsEff:Poor'
      elif status == 'Idle':
        result['SAT'] = None
      elif status == 'Bad':
        result['SAT'] = True
        result['Status'] = 'Banned'
        result['Reason'] = 'PilotsEff:Bad'

    return result