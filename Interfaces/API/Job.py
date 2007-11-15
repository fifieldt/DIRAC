########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/Interfaces/API/Job.py,v 1.1 2007/11/15 21:36:39 paterson Exp $
# File :   Job.py
# Author : Stuart Paterson
########################################################################

"""
   Job Base Class

   This class provides generic job submission functionality suitable for any VO.

   Helper functions are documented with example usage for the DIRAC API.

"""

__RCSID__ = "$Id: Job.py,v 1.1 2007/11/15 21:36:39 paterson Exp $"

import string, re, os, time, shutil, types, copy

from DIRAC.Core.Workflow.Parameter                  import *
from DIRAC.Core.Workflow.Module                     import *
from DIRAC.Core.Workflow.Step                       import *
from DIRAC.Core.Workflow.Workflow                   import *
from DIRAC.Core.Workflow.WorkflowReader             import *
from DIRAC.Core.Utilities.ClassAd.ClassAdLight      import ClassAd
from DIRAC.ConfigurationSystem.Client.Config        import gConfig
from DIRAC                                          import gLogger

COMPONENT_NAME='/Interfaces/API/Job'

class Job:

  #############################################################################

  def __init__(self,script=None):
    """Instantiates the Workflow object and some default parameters.
    """
    self.log = gLogger
    self.section    = COMPONENT_NAME
    self.dbg = False
    if gConfig.getValue(self.section+'/LogLevel','DEBUG') == 'DEBUG':
      self.dbg = True

    self.defaultOutputSE = 'CERN-tape' # to discuss
    #gConfig.getValue('Tier0SE-tape','SEName')
    self.stepCount = 1
    self.owner = 'NotSpecified'
    self.name = 'Name'
    self.type = 'user'
    self.priority = 0
    self.group = 'lhcb'
    self.site = 'ANY'
    self.setup = 'Development'
    self.origin = 'DIRAC'
    self.stdout = 'std.out'
    self.stderr = 'std.err'
    self.executable = '$DIRACROOT/DIRAC/scripts/jobexec' # to be clarified
    self.addToInputSandbox = []
    self.addToOutputSandbox = []

    self.reqParams = {'MaxCPUTime':   'other.NAME>=VALUE',
                      'MinCPUTime':   'other.NAME<=VALUE',
                      'Site':         'other.NAME=="VALUE"',
                      'Platform':     'other.NAME=="VALUE"',
                      'SystemConfig': 'Member("VALUE",other.CompatiblePlatforms)'}

    self.script = script
    if not script:
      self.workflow = Workflow()
      self.__setJobDefaults()

  #############################################################################
  def setExecutable(self,executable,logFile=''):
    """Helper function.

       Specify executable for DIRAC jobs.

       These can be either:

        - Submission of a python or shell script to DIRAC
           - Can be inline scripts e.g. C{'/bin/ls'}
           - Scripts as executables e.g. python or shell script file

       Example usage:

       >>> job = Job()
       >>> job.setExecutable('myScript.py')

       @param executable: Executable, can include path to file
       @type executable: string
    """
    stepNumber = self.stepCount
    self.stepCount +=1
    moduleName = 'Script'
    module = ModuleDefinition(moduleName)
    body = 'from DIRAC.WorkflowLib.Module.Script import Script\n'
    if os.path.exists(executable):
      self.log.debug('Found script executable file %s' % (executable))
      self._addParameter(module,'Name','Parameter',os.path.basename(executable),'Executable Script')

      self._addParameter(module,'Name','Parameter',os.path.basename(executable),'Executable ')
      self.addToInputSandbox.append(executable)
      logName = os.path.basename(executable)+'.log'
    else:
      self.log.debug('Found executable code')
      self._addParameter(module,'ExecutableCode','PARAMETER',executable,'Lines of executable code')
      body = executable
      logName = 'ScriptOutput.log'

    if logFile:
      if type(logFile) == type(' '):
        logName = logFile+'.log'

    self._addParameter(module,'LogFile','Parameter',logName,'Log file name',io='output')
    self.addToOutputSandbox.append(logName)

    module.setBody(body)
    stepName = 'ScriptStep%s' %(stepNumber)

    step = StepDefinition(stepName)
    step.addModule(module)

    moduleInstance = step.createModuleInstance('Script', moduleName)

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepName, 'Step')

  #############################################################################
  def setName(self,jobname):
    """Helper function.

       A name for the job can be specified if desired. This will appear
       in the JobName field of the monitoring webpage. If nothing is
       specified a default value will appear.

       Example usage:

       >>> job=Job()
       >>> job.setName("myJobName")

       @param jobname: Name of job
       @param type: string
    """
    if type(jobname)==type(" "):
      self.workflow.setName(jobname)
      self._addParameter(self.workflow,'JobName','JDL',jobname,'User specified name')
    else:
      raise TypeError,'Expected string for Job name'

  #############################################################################
  def setInputSandbox(self,files):
    """Helper function.

       Specify input sandbox files less than 10MB in size.  If over 10MB, files
       or a directory may be uploaded to Grid storage, see C{dirac.uploadSandbox()}.

       Paths to the options file and (if required) 'lib/' directory of the DLLs
       are specified here. Default is local directory.  CMT requirements files or
       executables may be placed in the lib/ directory if desired. The lib/ directory
       is transferred to the Grid Worker Node before the job executes.

       Files / directories can be specified using the '*' character e.g. *.txt  these
       are resolved correctly before job execution on the WN.

       Example usage:

       >>> job = Job()
       >>> job.setInputSandbox(['DaVinci.opts'])

       @param files: Input sandbox files, can specify full path
       @type files: Single string or list of strings ['','']
    """
    if type(files) == list and len(files):
      resolvedFiles = self._resolveInputSandbox(files)
      fileList = string.join(resolvedFiles,";")
      description = 'Input sandbox file list'
      self._addParameter(self.workflow,'InputSandbox','JDL',fileList,description)
    elif type(files) == type(" "):
      description = 'Input sandbox file'
      self._addParameter(self.workflow,'InputSandbox','JDL',files,description)
    else:
      raise TypeError,'Expected string or list for InputSandbox'

  #############################################################################
  def setOutputSandbox(self,files):
    """Helper function.

       Specify output sandbox files.  If specified files are over 10MB, these
       may be uploaded to Grid storage with a notification returned in the
       output sandbox.

       Example usage:

       >>> job = Job()
       >>> job.setOutputSandbox(['DaVinci_v17r6.log','DVNTuples.root'])

       @param files: Output sandbox files
       @type files: Single string or list of strings ['','']

    """
    if type(files) == list and len(files):
      fileList = string.join(files,";")
      description = 'Output sandbox file list'
      self._addParameter(self.workflow,'OutputSandbox','JDL',fileList,description,io='output')
    elif type(files) == type(" "):
      description = 'Output sandbox file'
      self._addParameter(self.workflow,'OutputSandbox','JDL',files,description,io='output')
    else:
      raise TypeError,'Expected string or list for OutputSandbox'

  #############################################################################
  def setInputData(self,lfns):
    """Helper function.

       Specify input data by Logical File Name (LFN).

       Example usage:

       >>> job = Job()
       >>> job.setInputData(['/lhcb/production/DC04/v2/DST/00000742_00003493_10.dst'])

       @param lfns: Logical File Names
       @type lfns: Single LFN string or list of LFNs
    """
    if type(lfns)==list and len(lfns):
      for i in xrange(len(lfns)):
        lfns[i] = lfns[i].replace('LFN:','')

      inputData = map( lambda x: 'LFN:'+x, lfns)
      inputDataStr = string.join(inputData,';')
      description = 'List of input data specified by LFNs'
      self._addParameter(self.workflow,'InputData','JDL',inputDataStr,description)
    elif type(lfns)==type(' '):  #single LFN
      description = 'Input data specified by LFN'
      self._addParameter(self.workflow,'InputData','JDL',lfns,description)
    else:
      raise TypeError,'Expected String or List'

  #############################################################################
  def setOutputData(self,lfns,OutputSE=None):
    """Helper function.

       For specifying output data to be registered in Grid storage
       (Tier-1 storage by default).

       Example usage:

       >>> job = Job()
       >>> job.setOutputData(['DVNtuple.root'])

       @param files: Output data file or files
       @type files: Single string or list of strings ['','']
       @param OutputSE: Optional parameter to specify the Storage
       Element to store data or files, e.g. CERN-tape
       @type OutputSE: string
    """
    if type(lfns)==list and len(lfns):
      outputDataStr = string.join(lfns,';')
      description = 'List of output data files'
      self._addParameter(self.workflow,'OutputData','JDL',outputDataStr,description,io='output')
    elif type(lfns)==type(" "):
      description = 'Output data file'
      self._addParameter(self.workflow,'OutputData','JDL',lfns,description,io='output')
    else:
      raise TypeError,'Expected string or list of output data files'

    if OutputSE:
      description = 'User specified Output SE'
      self._addParameter(self.workflow,'OutputSE','JDL',OutputSE,description)
    else:
      description = 'Default Output SE'
      self._addParameter(self.workflow,'OutputSE','JDL',self.defaultOutputSE,description)

  #############################################################################
  def setPlatform(self, backend):
    """Developer function.

       Choose platform (system) on which job is executed e.g. DIRAC, LCG.
       Default of LCG in place for users.
    """
    if type(backend) == type(" "):
      description = 'Platform type'
      self._addParameter(self.workflow,'Platform','JDLReqt',backend,description)
    else:
      raise TypeError,'Expected string for platform'

  #############################################################################
  def setSystemConfig(self, config):
    """Helper function.

       Choose system configuration (e.g. where user DLLs have been compiled). Default ANY in place
       for user jobs.  Available system configurations can be browsed
       via dirac.checkSupportedPlatforms() method.

       Example usage:

       >>> job=Job()
       >>> job.setSystemConfig("slc4_ia32_gcc34")

       @param config: architecture, CMTCONFIG value
       @param type: string
    """
    if type(config) == type(" "):
      description = 'User specified system configuration for job'
      self._addParameter(self.workflow,'SystemConfig','JDLReqt',config,description)
    else:
      raise TypeError,'Expected string for platform'

  #############################################################################
  def setCPUTime(self,timeInSecs):
    """Helper function.

       Under Development. Specify CPU time requirement in DIRAC units.

       Example usage:

       >>> job = Job()
       >>> job.setCPUTime(5000)

       @param timeInSecs: CPU time
       @param timeInSecs: Int
    """
    if type(timeInSecs) == int:
      if timeInSecs:
        description = 'CPU time in secs'
        self._addParameter(self.workflow,'MaxCPUTime','JDLReqt',timeInSecs,description)
    else:
      raise TypeError,'Expected Integer for CPU time'

  #############################################################################
  def setDestination(self,destination):
    """Helper function.

       Can specify a desired destination site for job.  This can be useful
       for debugging purposes but often limits the possible candidate sites
       and overall system response time.

       Example usage:

       >>> job = Job()
       >>> job.setDestination('LCG.CERN.ch')

       @param optsLine: site string
       @param optsLine: string
    """

    if type(destination) == type("  "):
      description = 'User specified destination site'
      self._addParameter(self.workflow,'Site','JDLReqt',destination,description)
    else:
      raise TypeError,'Expected string for destination site'

  #############################################################################
  def setBannedSites(self,sites):
    """Helper function.

       Can specify a desired destination site for job.  This can be useful
       for debugging purposes but often limits the possible candidate sites
       and overall system response time.

       Example usage:

       >>> job = Job()
       >>> job.setBannedSites(['LCG.GRIDKA.de','LCG.CNAF.it'])

       @param optsLine: site string
       @param optsLine: string
    """
    if type(sites)==list and len(sites):
      bannedSites = string.join(lfns,';')
      description = 'List of sites excluded by user'
      self._addParameter(self.workflow,'BannedSites','JDL',bannedSites,description)
    elif type(lfns)==type(" "):
      description = 'Site excluded by user'
      self._addParameter(self.workflow,'BannedSites','JDL',sites,description)
    else:
      raise TypeError,'Expected string or list of output data files'

  #############################################################################
  def setOwner(self, ownerProvided):
    """Currently a developer function but could eventually extract the VOMS GA
       nickname and be an internal function to the Job object.
    """
    if type(ownerProvided)==type("  "):
     # self._removeParameter(self.workflow,'Owner')
      self._addParameter(self.workflow,'Owner','JDL',ownerProvided,'User specified ID')
    else:
      raise TypeError,'Expected string for Job owner'

  #############################################################################
  def setType(self, jobType):
    """Developer function.

       Specify job type for testing purposes.
    """
    if type(jobType)==type("  "):
      #self._removeParameter(self.workflow,'JobType')
      self._addParameter(self.workflow,'JobType','JDL',jobType,'User specified type')
    else:
      raise TypeError,'Expected string for Job type'

    if type(jobType) == type(" "):
      self.type = jobType

  #############################################################################
  def setSoftwareTags(self, tags):
    """Helper function.

       Choose any software tags if desired.  These are not compulsary but will ensure jobs only
       arrive at an LCG site where the software is preinstalled.  Without the tags, missing software is
       installed automatically by the Job Agent.

       Example usage:

       >>> job=Job()
       >>> job.setSoftwareTags(['VO-lhcb-Brunel-v30r17','VO-lhcb-Boole-v12r10','VO-lhcb-Gauss-v25r12'])

       @param tags: software tags
       @param type: string or list
    """
    if type(tags) == type(" "):
      self._addParameter(self.workflow,'SoftwareTag','JDL',tags,'VO software tag')
    elif type(tags) == list:
      swTags = string.join(tags,';')
      self._addParameter(self.workflow,'SoftwareTag','JDL',swTags,'List of VO software tags')
    else:
      raise TypeError,'Expected String or List of software tags'

  #############################################################################
  def createCode(self):
    """Developer function.
       Wrapper method to create the code.
    """
    print self.workflow.createCode()

  #############################################################################

  def _dumpParameters(self,showType=None):
    """Developer function.
       Method to print the workflow parameters.
    """
    paramsDict = {}
    paramList = self.workflow.parameters
    for param in paramList:
      paramsDict[param.getName()]= {'type':param.getType(),'value':param.getValue()}
    self.log.info('--------------------------------------')
    self.log.info('Workflow parameter summary:           ')
    self.log.info('--------------------------------------')
    #print self.workflow.parameters
    #print params.getParametersNames()
    for name,props in paramsDict.items():
      ptype = paramsDict[name]['type']
      value = paramsDict[name]['value']
      if showType:
        if ptype==showType:
          self.log.info('NAME: %s\nTYPE: %s\nVALUE: %s ' %(name,ptype,value))
          self.log.info('--------------------------------------')
      else:
        self.log.info('NAME: %s\nTYPE: %s\nVALUE: %s ' %(name,ptype,value))
        self.log.info('--------------------------------------')

  #############################################################################

  def __setJobDefaults(self):
    """Set job default values.  For initial version still using local account string
    for a nickname.
    """
    try:
      self.owner = os.getlogin()
    except Exception, x :
      if os.environ.has_key('USER'):
        self.owner = os.environ['USER']
      else:
        self.owner = "Unknown"

    self._addParameter(self.workflow,'Owner','JDL',self.owner,'Job Owner')
    self._addParameter(self.workflow,'JobType','JDL',self.type,'Job Type')
    self._addParameter(self.workflow,'Priority','JDL',self.priority,'User Job Priority')
    self._addParameter(self.workflow,'JobGroup','JDL',self.group,'Corresponding VOMS role')
    self._addParameter(self.workflow,'JobName','JDL',self.name,'Name of Job')
    self._addParameter(self.workflow,'DIRACSetup','JDL',self.setup,'DIRAC Setup')
    self._addParameter(self.workflow,'Site','JDL',self.site,'Site Requirement')
    self._addParameter(self.workflow,'Origin','JDL',self.origin,'Origin of client')
    self._addParameter(self.workflow,'StdOutput','JDL',self.stdout,'Standard output file')
    self._addParameter(self.workflow,'StdError','JDL',self.stderr,'Standard error file')

  #############################################################################
 # def _addStep(self,step):
 #   """Add step to workflow.
 #   """
    #to do

 #   self.workflow.addStep(step)
  #############################################################################
#  def _addModule(self,module,step = 0):
    #to do
 #   self.workflow.addModule(module)

  #############################################################################

  def _addParameter(self,object,name,ptype,value,description,io='input'):
    """ Internal Function

        Adds a parameter to the object.
    """
    if io=='input':
      inBool = True
      outBool = False
    elif io=='output':
      inBool = False
      outBool = True
    else:
      raise TypeError,'I/O flag is either input or output'

    p = Parameter(name,value,ptype,"","",inBool,outBool,description)
    object.appendParameter(Parameter(parameter=p))

  ############################################################################
  def _resolveInputSandbox(self, inputSandbox):
    """ Internal function.

        Resolves wildcards for input sandbox files.  This is currently linux
        specific and should be modified.
    """
    resolvedIS = []

    for i in inputSandbox:
      if not re.search('\*',i):
        if not os.path.isdir(i):
          resolvedIS.append(i)

    for f in inputSandbox:
      if re.search('\*',f): #escape the star character...
        cmd = 'ls -d '+f
        status, output, error, pythonError = exeCommand(cmd,iTimeout = 10)
        if output:
          files = string.split(output)
          for check in files:
            if os.path.isfile(check):
              self.log.debug('Found file '+check+' appending to Input Sandbox')
              resolvedIS.append(check)
            if os.path.isdir(check):
              if re.search('/$',check): #users can specify e.g. /my/dir/lib/
                 check = check[:-1]
              tarname = os.path.basename(check)
              directory = os.path.dirname(check) #if just the directory this is null
              if directory:
                cmd = 'tar cfz '+tarname+'.tar.gz '+' -C '+directory+' '+tarname
              else:
                cmd = 'tar cfz '+tarname+'.tar.gz '+tarname

              status, output, error, pythonError = exeCommand(cmd,iTimeout = 10)
              resolvedIS.append(tarname+'.tar.gz')
              self.log.debug('Found directory '+check+', appending '+check+'.tar.gz to Input Sandbox')

      if os.path.isdir(f):
        self.log.debug('Found specified directory '+f+', appending '+f+'.tar.gz to Input Sandbox')
        if re.search('/$',f): #users can specify e.g. /my/dir/lib/
           f = f[:-1]
        tarname = os.path.basename(f)
        directory = os.path.dirname(f) #if just the directory this is null
        if directory:
          cmd = 'tar cfz '+tarname+'.tar.gz '+' -C '+directory+' '+tarname
        else:
          cmd = 'tar cfz '+tarname+'.tar.gz '+tarname
        status, output, error, pythonError = exeCommand(cmd,iTimeout = 10)
        resolvedIS.append(tarname+'.tar.gz')

    return resolvedIS

  #############################################################################
  def _toXML(self):
    """Internal Function.

       Creates an XML representation of itself as a Job,
       wraps around workflow toXML().
    """
    return self.workflow.toXML()

  #############################################################################
  def _toJDL(self,xmlFile=''): #messy but need to account for xml file being in /tmp/guid dir
    """Creates a JDL representation of itself as a Job
    """
    #Check if we have to do old bootstrap...
    classadJob = ClassAd('[]')

    paramsDict = {}
    params = self.workflow.parameters # ParameterCollection object

    paramList =  params
    for param in paramList:
      paramsDict[param.getName()]= {'type':param.getType(),'value':param.getValue()}

    scriptname = 'jobDescription.xml'
    if self.script:
      if os.path.exists(self.script):
        scriptname = os.path.abspath(self.script)
    else:
      if xmlFile:
        scriptname = xmlFile

    classadJob.insertAttributeString('Arguments',scriptname)
    classadJob.insertAttributeString('Executable',self.executable)

    #Extract i/o sandbox parameters from steps and any input data parameters
    #to do when introducing step-level api...

    #To add any additional files to input and output sandboxes
    if self.addToInputSandbox:
      if paramsDict.has_key('InputSandbox'):
        extraFiles = string.join(self.addToInputSandbox,';')
        currentFiles = paramsDict['InputSandbox']['value']
        paramsDict['InputSandbox']['value'] = currentFiles+';'+extraFiles
        self.log.debug('Final Input Sandbox %s' %(currentFiles+';'+extraFiles))

    if self.addToOutputSandbox:
      if paramsDict.has_key('OutputSandbox'):
        extraFiles = string.join(self.addToOutputSandbox,';')
        currentFiles = paramsDict['OutputSandbox']['value']
        paramsDict['OutputSandbox']['value'] = currentFiles+';'+extraFiles
        self.log.debug('Final Output Sandbox %s' %(currentFiles+';'+extraFiles))

    #Add any JDL parameters to classad obeying lists with ';' rule
    requirements = False
    for name,props in paramsDict.items():
      ptype = paramsDict[name]['type']
      value = paramsDict[name]['value']
      if name.lower()=='requirements' and ptype=='JDL':
        self.log.debug('Found existing requirements: %s' %(value))
        requirements = True

      if re.search('^JDL',ptype):
        if not re.search(';',value):
          classadJob.insertAttributeString(name,value)
        else:
          classadJob.insertAttributeVectorString(name,string.split(value,';'))

    if not requirements:
      reqtsDict = self.reqParams
      exprn = ''
      for name,props in paramsDict.items():
        ptype = paramsDict[name]['type']
        value = paramsDict[name]['value']
        if ptype=='JDLReqt':
          plus = ' && '
          exprn += reqtsDict[name].replace('NAME',name).replace('VALUE',str(value))+plus

      exprn = exprn[:-len(plus)]
      self.log.debug('Requirements: %s' %(exprn))
      classadJob.set_expression('Requirements', exprn)

    jdl = classadJob.asJDL()
    start = string.find(jdl,'[')
    end   = string.rfind(jdl,']')
    return jdl[(start+1):(end-1)]

  #EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#