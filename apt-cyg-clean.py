#!/usr/bin/python

import os
import os.path as path
from collections import namedtuple
import re
from itertools import groupby
import argparse


def main():
  parser = argparse.ArgumentParser(description="Cleanup package cache for Cygwin setup")
  parser.add_argument("root", help="root directory of packages")
  parser.add_argument("-v", "--verbose", help="verbosely list packages processed",
                      action="store_true")
  args = parser.parse_args()
  forp(prune, ispackdir, args.root, args)

def forp(f, pred, top, args):
  '''Walk the tree topdown, call f(root, files) on subdirectories
  iff pred returns True.
  '''
  for root, dirs, files in os.walk(top, followlinks=True):
    if pred(root, dirs, files):
      f(root, files, args)

def prune(root, files, args):
  '''Remove old versions of this package.'''
  pfiles = [f for f in files if ispackfile(f)]
  if len(pfiles) == 1: return

  # group by package name
  packages = [cygpackage(f) for f in pfiles]
  packages.sort(key=lambda p:p.package)
  pks = [list(v) for k, v in groupby(packages, key=lambda p:p.package)]
  trash = clean(root, pks)
  rmtrash(trash, args)


CygPackage = namedtuple("CygPackage", ['package', 'version', 'release'])
INVALID_PACKAGE = CygPackage(None, None, None)
SUFFIX = ".tar.bz2"

def cygpackage(s):
  '''Construct a CygPackage from string.
  Refer http://cygwin.com/setup.html#naming for cygwin package naming.

  >>> cygpackage("libstdc++6-4.5.3-3.tar.bz2")
  CygPackage(package='libstdc++6', version='4.5.3', release='3')
  >>> cygpackage("gcc4-core-4.5.3-3.tar.bz2")
  CygPackage(package='gcc4-core', version='4.5.3', release='3')
  >>> cygpackage("foobar.tar.bz2")
  CygPackage(package=None, version=None, release=None)
  >>> cygpackage("foo-3.2-4.tar.gz")
  CygPackage(package=None, version=None, release=None)
  '''
  if not s.endswith(SUFFIX): return INVALID_PACKAGE
  p = s[:len(s)-len(SUFFIX)]
  pack = p.rsplit("-",2)
  return CygPackage(*pack) if chkpackage(pack) else INVALID_PACKAGE

def chkversion(ver):
  '''Package version is vender specific, different formats exists.

  >>> chkversion("4.5.3")
  True
  >>> chkversion("20121212")
  True
  >>> chkversion("1.3")
  True
  >>> chkversion(".3.2")
  False
  >>> chkversion("3.4.foo")
  False
  '''
  return re.match(r'^\d[0-9\.]*$', ver)

def chkrelease(rel):
  '''Package release is a number, starting from 1.

  >>> chkrelease("0")
  False
  >>> chkrelease("1")
  True
  >>> chkrelease("7")
  True
  >>> chkrelease("100")
  True
  >>> chkrelease("quux")
  False
  '''
  return re.match(r'^[1-9]\d*$', rel)

def chkpackage(parts):
  '''Return True if all parts are valid.
  '''
  return len(parts) == 3 and \
         chkversion(parts[1]) and chkrelease(parts[2])

def ispackfile(s):
  return cygpackage(s) is not INVALID_PACKAGE

def packname(p):
  '''Reconstruct package file name from CygPackage.
  >>> packname(cygpackage("libstdc++6-4.5.3-3.tar.bz2")) == "libstdc++6-4.5.3-3.tar.bz2"
  True
  >>> packname(INVALID_PACKAGE) == ""
  True
  >>> packname(cygpackage("gcc4-core-4.5.3-3.tar.bz2")) == "gcc4-core-4.5.3-3.tar.bz2"
  True
  '''
  if p is INVALID_PACKAGE: return ""
  t = "{0}-{1}-{2}{3}"
  return t.format(p.package, p.version, p.release, SUFFIX)

def clean(root, pks):
  trash = {}
  for vs in pks:
    vs.sort(key=lambda p:p.version+"-"+p.release)
    p = vs.pop()
    if vs:
      trash[p] = [path.join(root, packname(v)) for v in vs]
  return trash

def rmtrash(trash, args):
  if args.verbose:
    rmtrash_v(trash)
  for _, vs in trash.items():
    for f in vs:
      os.remove(f)

def rmtrash_v(trash):
  for p, vs in trash.items():
    print "Latest version of %s is %s-%s" % (p.package, p.version, p.release)
    print "%s\n" % "\n".join(vs)

def ispackdir(root, dirs, files):
  return any(ispackfile(s) for s in files)


if __name__ == '__main__':
  main()