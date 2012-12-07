#!/usr/bin/python

# Copyright (c) 2010 William Leszczuk
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

'''
  Logic for manipulating an `evolve' repository.
'''

__author__ = 'Will Leszczuk'

import logging, os, re, fcntl, time, pwd
from cPickle import dump, load
from evolve.shared.util import get_logger, do_or_die

class RepoError(Exception): pass
class ArgumentError(RepoError): pass

# TODO: chmod on src directory needs to be -R
# TODO: should bin just be a symlink to the build artifact directory instead?
# TODO: way to resolve jars/etc for various startups based on dependencies
# TODO: consolidate validations
# TODO: vefify locking in new commands
# TODO: logging!
# TODO: ability to push to another repository (dev/prod)
# TODO: to deploy, all dependencies must be deployed
# TODO: can only set rlink to deployed releases
# TODO: can only push rlinks (and pull the target) (--deploy-all-dependencies flag?)
# TODO: dep graph
# TODO: clone dependencies from another release
# TODO: unlock command? (leaning against)

class _RepoMetaFile(object):
  RepoMetaFileName = '.evolverepo'

  @staticmethod
  def load(path):
    with open(_RepoMetaFile._get_metapath(path), 'r') as repofile:
      result = load(repofile)
    if not hasattr(result, 'lastmoduser'): result.lastmoduser = 'unavailable'
    if not hasattr(result, 'lastmodtime'): result.lastmodtime = 0
    return result

  @staticmethod
  def exists(path):
    return os.path.exists(_RepoMetaFile._get_metapath(path))

  def save(self, path):
    self.lastmoduser = pwd.getpwuid(os.getuid()).pw_name
    self.lastmodtime = time.time()
    with open(_RepoMetaFile._get_metapath(path), 'w') as repofile:
      dump(self, repofile)

  @staticmethod
  def _get_metapath(path):
    return os.path.join(path, _RepoMetaFile.RepoMetaFileName)

  def get_descriptor(self):
    return [
      ('Type',             self.get_type()),
      ('Last Mod By', self.lastmoduser),
      ('Last Modified',
       'unavailable' if 0 == self.lastmodtime else time.ctime(self.lastmodtime)
      ),
    ]

class _RepoRoot(_RepoMetaFile):
  Type = 'repository root'

  def __init__(self):
    self.projects = []

  def is_root(self): return True
  def is_leaf(self): return False
  def get_type(self): return _RepoRoot.Type
  def accepts_project(self): return True
  def accepts_release(self): return False
  def accepts_rlink(self): return False
  def get_children(self): return self.projects

class _RepoProject(_RepoMetaFile):
  Type = 'project'

  def __init__(self):
    self.projects = []
    self.releases = []

  def is_root(self): return False
  def is_leaf(self): return False
  def get_type(self): return _RepoProject.Type
  def accepts_project(self): return 0 == len(self.releases)
  def accepts_release(self): return 0 == len(self.projects)
  def accepts_rlink(self):
    return 0 == len(self.projects) and 0 < len(self.releases)
  def get_children(self):
    return self.releases if 0 < len(self.releases) else self.projects

class _RepoRelease(_RepoMetaFile):
  Type = 'release'

  def __init__(self):
    self.deployed = False
    self.dependencies = []

  def is_root(self): return False
  def is_leaf(self): return True
  def get_type(self): return _RepoRelease.Type
  def accepts_project(self): return False
  def accepts_release(self): return False
  def accepts_rlink(self): return False
  def get_children(self): return []
  def get_descriptor(self):
    return _RepoMetaFile.get_descriptor(self) + [
      ('Dpl', 'Yes' if self.deployed else '')
    ]

class _RepoRlink(_RepoMetaFile):
  Type = 'rlink'

  def __init__(self, target):
    self.target = target
    self.dependencies = []
    self.history = []

  def is_root(self): return False
  def is_leaf(self): return True
  def get_type(self): return _RepoRlink.Type
  def accepts_project(self): return False
  def accepts_release(self): return False
  def accepts_rlink(self): return False
  def get_children(self): return []
  def get_descriptor(self):
    return _RepoMetaFile.get_descriptor(self) + [
      ('Target', self.target.split('/')[-1])
    ]

  def update(self, target):
    if not hasattr(self, 'history'): self.history = []
    self.history = [(self.target, self.lastmoduser, self.lastmodtime)] \
      + self.history
    self.target = target

  def get_history(self):
    return self.history or []

class _RepoLock(object):
  class LockError(Exception): pass

  RepoLockFileName = '.evolvelock'

  def __init__(self, path, steal=False):
    self.path = path
    self.steal = steal

  def __enter__(self):
    lockpath = self._get_lockpath()
    if not self.steal and os.path.exists(lockpath): self._throw_busy()
    self.lockfile = open(lockpath, 'w')

    try: fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError, ex:
      self.lockfile.close()
      self._throw_busy()
    # no return - don't want anybody messing with the lock object

  def __exit__(self, type, value, traceback):
    self.lockfile.close()
    os.remove(self._get_lockpath())

  def _get_lockpath(self):
    return os.path.join(self.path, _RepoLock.RepoLockFileName)

  def _throw_busy(self):
    raise _RepoLock.LockError()

class Repository(object):

  @staticmethod
  def init_repo(path):
    Repository._validate_empty_directory(path)
    Repository._claim_repo(path)
    Repository._init_repo(path)
    repo = Repository(path)
    repo.logger.info('repository initialized')

  @staticmethod
  def _validate_empty_directory(path):
    if not os.path.exists(path): 
      raise ArgumentError('directory does not exist')
    directory = os.path.normpath(path) + '/'
    if not os.path.isdir(directory): 
      raise ArgumentError('path does not correspond to a directory')
    contents = os.listdir(directory)
    if Repository.RepoMetaFileName in contents:
      raise ArgumentError('path corresponds to an existing repository')
    if 0 != len(contents):
      raise ArgumentError('path does not correspond to an empty directory')

  @staticmethod
  def _claim_repo(path):
    # TODO: move evolve user and group to a constant somewhere
    #  (or get name from os.geteuid())
    do_or_die('sudo chown evolve:evolve ' + path)

  @staticmethod
  def _init_repo(path):
    _RepoRoot().save(path)

  def __init__(self, path):
    self.path = path.strip().rstrip('/')
    self._validate_repo()
    self.logger = get_logger(path + '/.logs/repo.log', logging.INFO)

  def _validate_repo(self):
    valid = True
    try:
      metafile = _RepoMetaFile.load(self.path)
    except IOError, ex:
      valid = False
    else:
      if not metafile.is_root():
        valid = False

    if not valid:
      raise ArgumentError(
        'path [%s] does not correspond to a repository root' % self.path
      )
      
  def create_project(self, path):
    path = path.strip().strip('/')
    parent, metafile = self._get_valid_project_parent_path(path)
    fullpath = os.path.join(self.path, path)
    projects = fullpath.replace(parent + '/', '').split('/')
    
    try:
      with _RepoLock(parent):
        self._create_project(parent, projects)
        metafile.projects.append(projects[0])
        metafile.save(parent)
    except _RepoLock.LockError, ex:
      raise RepoError('parent at [%s] is locked' % parent)
    except BaseException, ex:
      firstproject = os.path.join(parent, projects[0])
      if os.path.exists(firstproject):
        do_or_die('rm -rf ' + firstproject)
      raise

    self.logger.info('created project [%s]' % path)

  def create_release(self, path):
    path = path.strip().strip('/')
    project, metafile, release = self._get_valid_project_and_release(path)

    try:
      with _RepoLock(project):
        self._create_release(project, release)
        metafile.releases.append(release)
        metafile.save(project)
    except _RepoLock.LockError, ex:
      raise RepoError('project at [%s] is locked' % project)
    except BaseException, ex:
      fullpath = os.path.join(project, release)
      if os.path.exists(fullpath):
        do_or_die('rm -rf ' + fullpath)
      raise

    self.logger.info('created release [%s]' % path)

  def create_rlink(self, path, name):
    path, name = path.strip().strip('/'), name.strip().strip('/')
    project, metafile = self._get_valid_project_for_rlink(path, name)

    try:
      with _RepoLock(project):
        self._create_rlink(project, path, name)
        metafile.releases.append(name)
        metafile.save(project)
    except _RepoLock.LockError, ex:
      raise RepoError('project at [%s] is locked' % project)
    except BaseException, ex:
      fullpath = os.path.join(project, name)
      if os.path.exists(fullpath):
        do_or_die('rm -rf ' + fullpath)
      raise

    self.logger.info(
      'created rlink [%s]' % os.path.join(path.split('/')[-1], name)
    )

  def update_rlink(self, path, name):
    path = path.strip().strip('/')
    rlinkpath, rlinkmetafile = self._get_valid_rlink_for_update(path, name)
    with _RepoLock(rlinkpath): # should not fail at this point
      if rlinkmetafile.target == path:
        raise ArgumentError('existing and specified targets are the same')

      releasepath = os.path.join(self.path, path)
      rlinkbin = os.path.join(rlinkpath,'bin')

      do_or_die(
        'rm %s && ln -s %s %s'
          % (rlinkbin, os.path.join(releasepath,'bin'), rlinkbin)
      )
      # TODO: this should be an option at the command line
      do_or_die('find %s/ | egrep -v \'^%s/$\' | xargs touch' % (rlinkbin, rlinkbin))

      rlinkmetafile.update(path)
      rlinkmetafile.save(rlinkpath)

  def get_directory_contents(self, path):
    path = path.strip().strip('/')
    fullpath = os.path.join(self.path, path)

    if not os.path.exists(fullpath):
      raise ArgumentError('repository location not found: [%s]' % path)

    if not _RepoMetaFile.exists(fullpath):
      raise ArgumentError(
          'location does not correspond to repository element: [%s]' % path
      )
    
    targetmeta = _RepoMetaFile.load(fullpath)
    childdescriptors = { }

    for child in targetmeta.get_children():
      childmeta = _RepoMetaFile.load(os.path.join(fullpath, child))
      childdescriptors[child] = childmeta.get_descriptor()

    return (targetmeta.get_descriptor(), childdescriptors)

  def walk(self, path, callback):
    def _walk(self, path, callback, more):
      fullpath = os.path.join(self.path, path)
      metafile = _RepoMetaFile.load(fullpath)
      callback(path, more, metafile.get_type())
      
      if not metafile.is_leaf():
        sortedmeta = sorted(
          [d for d in os.listdir(fullpath) if not d.startswith('.')]
        )
        for i in range(len(sortedmeta)-1):
          _walk(self, os.path.join(path, sortedmeta[i]), callback, more+[True])
        else:
          if 0 < len(sortedmeta):
            _walk(self,os.path.join(path, sortedmeta[-1]),callback,more+[False])

    path = path.strip().strip('/')
    if not os.path.exists(os.path.join(self.path, path)):
      raise ArgumentError('repository location not found: [%s]' % path)

    _walk(self, path, callback, [False])

  def get_history(self, path):
    path = path.strip().strip('/')

    fullpath = os.path.join(self.path, path)
    if not os.path.exists(fullpath):
      raise ArgumentError('rlink path not found: [%s]' % path)

    metafile = _RepoMetaFile.load(fullpath)
    if not _RepoRlink.Type == metafile.get_type():
      raise ArgumentError('path does not correspond to an rlink: [%s]' % path)

    return metafile.get_history()

  def install(self, path, artifactpath):
    path = path.strip().strip('/')
    artifactpath = artifactpath.strip().strip('/')
    target, src = self._get_valid_paths_for_install(path, artifactpath)
    do_or_die('rsync -r --delete --force %s/ %s' % (src, target))

  def deploy(self, path):
    path = path.strip().strip('/')
    releasepath, releasemeta, src = \
      self._get_valid_release_and_src_for_deploy(path)

    try:
      with _RepoLock(releasepath):
        releasemeta.deployed = True
        releasemeta.save(releasepath)
        os.chmod(src, 0755)
    except _RepoLock.LockError, ex:
      raise RepoError('release at [%s] is locked' % path)

  def clean(self, path):
    path = path.strip().strip('/')
    fullpath = os.path.join(self.path, path)
    if not os.path.exists(fullpath):
      raise ArgumentError('repository location not found: [%s]' % path)
    with _RepoLock(fullpath, True): pass

  def _get_valid_project_parent_path(self, path):
    if '' == path:
      raise ArgumentError('empty path specified for project')

    for sub in path.split('/'):
      if not re.match(r'[a-zA-z][\w\-_\.]*', sub):
        raise ArgumentError('illegal project name: [%s]' % sub)
      
    path = os.path.join(self.path, path)
    if os.path.exists(path):
      metafile = _RepoMetaFile.load(path)
      raise ArgumentError(
        'project path corresponds to existing ' + metafile.get_type()
      )

    sepidx = path.rfind('/')
    while -1 != sepidx:
      parent = path[:sepidx]
      if os.path.exists(parent):
        metafile = _RepoMetaFile.load(parent)
        if not metafile.accepts_project():
          raise ArgumentError('invalid project location')
        result = (parent, metafile)
        break
      sepidx = parent.rfind('/')

    return result

  def _create_project(self, parent, projects):
    projpath = os.path.join(parent, projects[0])
    os.makedirs(projpath)
    with _RepoLock(projpath): # should not fail at this point
      metafile = _RepoProject()
      try:
        if 1 < len(projects): 
          self._create_project(projpath, projects[1:])
          metafile.projects.append(projects[1])
      finally:
        metafile.save(projpath)

  def _get_valid_project_and_release(self, path):
    if '' == path or -1 == path.find('/'):
      raise ArgumentError('cannot create release at repository root')

    fullpath = os.path.join(self.path, path)
    sepidx = fullpath.rfind('/')
    project = fullpath[:sepidx]
    release = fullpath[1 + sepidx:]

    if not os.path.exists(project):
      raise ArgumentError('project path not found: [%s]' % project)

    if not re.match(r'\w[\w\-_\.]*', release):
      raise ArgumentError('illegal release name: [%s]' % release)
 
    metafile = _RepoMetaFile.load(project)
    if not metafile.accepts_release():
      raise ArgumentError('invalid release location')

    if os.path.exists(fullpath):
      raise ArgumentError('release [%s] already exists' % path)

    return project, metafile, release

  def _create_release(self, projectpath, release):
    releasepath = os.path.join(projectpath, release)
    os.makedirs(releasepath)
    src, bin = self._get_srcbin(
      os.path.join(projectpath.replace(self.path, ''), release).strip('/')
    )
    with _RepoLock(releasepath): # should not fail at this point
      os.makedirs(src)
      os.chmod(src, 0775)
      os.makedirs(bin)
      _RepoRelease().save(releasepath)

  def _get_srcbin(self, path):
    releasepath = os.path.join(self.path, path)
    return (os.path.join(releasepath, 'src'), os.path.join(releasepath, 'bin'))

  def _get_valid_project_for_rlink(self, path, name):
    # TODO: deployment check
    if '' == path or -1 == path.find('/'):
      raise ArgumentError('cannot create rlink at repository root')
    if -1 != name.find('/'):
      raise ArgumentError('hierarchical rlinks not supported')

    release = os.path.join(self.path, path)
    sepidx = release.rfind('/')
    project = release[:sepidx]

    if not os.path.exists(project):
      raise ArgumentError('project path not found: [%s]' % project)

    if not os.path.exists(project):
      raise ArgumentError('release path not found: [%s]' % release)

    if not re.match(r'\w[\w\-_\.]*', name):
      raise ArgumentError('illegal rlink name: [%s]' % name)

    namepath = os.path.join(project, name)
    if os.path.exists(namepath):
      metafile = _RepoMetaFile.load(namepath)
      raise ArgumentError(
        'name corresponds to existing %s %s' % (
          metafile.get_type(),
          '' if _RepoRlink.Type != metafile.get_type()
            else '(did you mean `update\'?)' 
        )
      )
 
    metafile = _RepoMetaFile.load(project)
    if not metafile.accepts_rlink():
      raise ArgumentError('invalid rlink location')

    return project, metafile

  def _get_valid_rlink_for_update(self, path, name):
    # TODO: deployment check
    release = os.path.join(self.path, path)
    sepidx = release.rfind('/')
    rlink = os.path.join(os.path.join(release[:sepidx], name))

    if not os.path.exists(release):
      raise ArgumentError('release not found: [%s]' % path)

    if not os.path.exists(rlink):
      raise ArgumentError('rlink not found: [%s]' % name)

    releasemetafile = _RepoMetaFile.load(release)
    if not _RepoRelease.Type == releasemetafile.get_type():
      raise ArgumentError('path [%s] does not correspond to a release' % path)

    rlinkmetafile = _RepoMetaFile.load(rlink)
    if not _RepoRlink.Type == rlinkmetafile.get_type():
      raise ArgumentError('path [%s] does not correspond to an rlink' % path)

    return rlink, rlinkmetafile

  def _create_rlink(self, projectpath, release, rlink):
    releasepath = os.path.join(projectpath, release.split('/')[-1])
    rlinkpath = os.path.join(projectpath, rlink)
    os.makedirs(rlinkpath)
    with _RepoLock(rlinkpath): # should not fail at this point
      os.symlink(os.path.join(releasepath,'bin'), os.path.join(rlinkpath,'bin'))
      _RepoRlink(release).save(rlinkpath)

  def _get_valid_paths_for_install(self, path, artifactpath):
    releasepath = os.path.join(self.path, path)

    if not os.path.exists(releasepath):
      raise ArgumentError('release not found: [%s]' % path)

    releasemetafile = _RepoMetaFile.load(releasepath)
    if not _RepoRelease.Type == releasemetafile.get_type():
      raise ArgumentError('path [%s] does not correspond to a release' % path)

    if releasemetafile.deployed:
      raise ArgumentError('release [%s] is locked and deployed' % path)

    src, bin = self._get_srcbin(path)
    fullartpath = os.path.join(src, artifactpath)

    if not os.path.exists(fullartpath):
      raise ArgumentError(
        'build artifact path not found: [%s/src/%s]' % (path, artifactpath)
      )
    
    return bin, fullartpath

  def _get_valid_release_and_src_for_deploy(self, path):
    fullpath = os.path.join(self.path, path)
    if not os.path.exists(fullpath):
      raise ArgumentError('release not found: [%s]' % path)

    releasemetafile = _RepoMetaFile.load(fullpath)
    if not _RepoRelease.Type == releasemetafile.get_type():
      raise ArgumentError('path [%s] does not correspond to a release' % path)

    if releasemetafile.deployed:
      raise ArgumentError('release [%s] already deployed' % path)

    src, bin = self._get_srcbin(path)
    if 0 == len(os.listdir(bin)):
      raise ArgumentError('no build artifacts installed for release [%s]'%path)

    return fullpath, releasemetafile, src
