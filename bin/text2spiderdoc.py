#!/usr/bin/env python

import os
import sys
import time
###import six
import inspect
import re

MODIFIED="Modified 2024 Mar 07"

#def printvars(variables, quitTF=False, typeTF=False):
  #"""Print the local variables in the caller's frame.
  
  #Adapted from https://stackoverflow.com/questions/6618795/get-locals-from-calling-namespace-in-python
  #"""
  
  #if type(variables) is list:
    ## Weird things happen if
    #assert isinstance(variables[0], six.string_types), "UH OH!! Passed non-string %s instead of variable name" % variables[0]
    
    #variable_list= variables
  #elif isinstance(variables, six.string_types):  # six works with both Pythons 2 & 3
    #variable_list= [variables]
  #else:
    #print("ERROR!! Don't know how to deal with type %s" % type(variables) )
    #exit()
  
  #frame= inspect.currentframe()
  #dictionary= frame.f_back.f_locals
  
  #print("")
  #for variable in variable_list :
    #msg= "%s: '%s'" % (variable, dictionary[variable])
    #if typeTF: msg+= " %s" % type(dictionary[variable])
    #print(msg)
      
  #del frame
  
  #if quitTF:
    #print('\nExiting printvars...')  # reminder in case I forget to take out the quit flag
    #exit()

def main():
  """
  Adapted from emancoords2spiderdoc.py
  """
  
  print(os.path.basename(__file__), MODIFIED)

  if sys.argv[1:]:
    infile = sys.argv[1]
    outputdoc = sys.argv[2]

    dictF = {}  # initialize dictionary
    key = 0  # initialize key

    if os.path.exists(infile) : 
      infile = open(infile,'r')
      line_list = infile.readlines()  # read line-by-line
      infile.close()

      ###headers = ['XCOORD','YCOORD','PARTICLE','PEAK_HT']
      headers= None
      
      # read contents
      for line_idx, curr_line in enumerate(line_list):
        # Check if first character is a comment-delimiter
        first_char= curr_line.strip()[0]
        if line_idx==0 and first_char=="#":
          # Split with multiple possible delimiters (adapted from https://stackoverflow.com/a/23720594s)
          headers= list( filter( None, re.split("[, \-!?:]+", curr_line.strip()[1:]) ) )
          ###printvars("headers")
        else:
          key += 1
          ###split = curr_line.split()
          split= list( filter( None, re.split("[, ]+", curr_line) ) )
          ###printvars('split', True, True)
          dictF[key] = split
      
      if writeSpiderDocFile(outputdoc, dictF, headers=headers, append=0):
        print('Wrote', key, 'keys to %s' % os.path.basename(outputdoc) )
      else:
        print( "Error!", "Unable to write to %s" % os.path.basename(outputdoc) )
    else:
      print("Error!", "Unable to read %s" % infile)
  else:
    print("Syntax: text2spiderdoc.py input_text_file output_spider_doc")
    
def getfilenumber(filepath):
  """
  UNTESTED IN PYTHON3
  
  Returns file number as a string with leading zeroes
  
  Adapted from Spiderutils.py
  """
  
  basename= os.path.basename(filepath)
  prefix, ext= os.path.splitext(basename)

  numstr= ""
  filename_list= list(prefix)
  filename_list.reverse()
  done= 0
  for ch in filename_list:
    if not done:
      try:
        int(ch)
        numstr= ch + numstr
      except:
        if numstr != "":
          done= 1

  return numstr
            
def writeSpiderDocFile(filename, data, headers=None, append=0, mode='w'):
  """
  Write data (in dictionary form) to a file in SPIDER document file format"
  
  Calls:
    writedoc
    isDictionary
    isListofLists
    fixHeaders
    writeSpireoutFile
  """
  
  if append > 0: mode = 'a'
  
  if mode == 'a':
    _APPEND = 1
  else: 
    _APPEND = 0
  
  if not isDictionary(data):
    # if it's not a dictionary, see if it's a list of lists
    if isListofLists(data):
      return writedoc(filename, columns=data, headers=headers, mode=mode)
    else:
      return 0
  try:
    fp = open(filename, mode)
  except:
    print("unable to open %s for writing" % filename)
    return 0
  
  # write Spider doc file header
  hdr = makeDocfileHeader(os.path.basename(filename))
  fp.write(hdr)
  
  # and any column headings
  if headers != None and type(headers) == type(["list"]):
    fp.write(fixHeaders(headers))

  # write data
  keys = list( data.keys() )
  
  ###printvars(['data', 'keys'], True, True)
  #print(f"157 data ({len(data)}) {type(data)}, keys ({len(keys)}) {type(keys)}")
  #print(f"158 data[0] ({len(data[keys[0]])}) {data[keys[0]]}")
  #exit()
  
  keys.sort()
  if len(keys) > 0:
    firstkey = keys[0]
    if firstkey in data:
      v1 = data[firstkey]
    else:
      print("writeSpiderDocFile: key not found in data")
  else:
    print("writeSpiderDocFile: empty data dictionary")
    return 0
      
  if isinstance(v1, list):
    for key in keys:
      values = data[key]
      n = len(values)
      h = "%5d %2d " % (int(key),int(n))
      for value in values:
        h += " %11g " % (float(value))
      fp.write(h+"\n")
  else:
    # it's supposed to be a list! But if it's not..
    for key in keys:
      value = data[key]
      try:
        f = float(value)
      except:
        print("writedoc: unable to convert %s" % str(value))
        print("writedoc: Dictionary elements must be lists!")
        return 0
      h = "%5d %2d %11g\n" % (int(key), 1, f)
      fp.write(h)
      
  fp.close()
  
  #if not _APPEND: # i.e. it's a new doc file
    #writeSpireoutFile(filename)
  
  return 1

def writedoc(filename, columns=None, lines=None, headers=None, keys=None, mode='w'):
  """
  Write data to a file in SPIDER document file format
  
  Calls:
    writeSpiderDocFile
    makeDocfileHeader
    getLastDocfileKey
    writeSpireoutFile
  """
  
  if not isListofLists(columns) and not isListofLists(lines):
    if isDictionary(columns):
      return writeSpiderDocFile(filename, columns, headers=headers, mode=mode)
    else:
      print("writedoc: columns or lines must be a list of lists")
      return

  # Filename must have data extension
  try:
    fp = open(filename, mode)
  except:
    print("Unable to open %s for writing." % filename)
    return

  # write Spider doc file header
  lastkey = None
  _APPEND = 0
  if mode == 'w':
    hdr = makeDocfileHeader(os.path.basename(filename))
    fp.write(hdr)
  elif mode == 'a':
    _APPEND = 1
    try:
      lastkey = getLastDocfileKey(filename)
    except:
      pass
  
  # write column headings
  if headers != None and type(headers) == type(["list"]):
      fp.write(fixHeaders(headers))

  datalines = []

  # write data columns
  if columns != None:
    ncol = len(columns)  # number of columns
    n = len(columns[0])  # length of 1st column (assumes all have same length)
    if keys == None:
      if lastkey == None:
        keys = range(1,n+1)
      else:
        keys = range(lastkey+1, lastkey+n+1)

    for i in range(n):
      dstr = "%5d %2d" % (int(keys[i]), int(ncol))
      for j in range(ncol):
        dstr += " %11g" % float(columns[j][i])
      datalines.append(dstr+"\n")

  # write data lines
  elif lines != None:
    n = len(lines)       # number of lines
    if keys == None:
      if lastkey == None:
        keys = range(1,n+1)
      else:
        keys = range(lastkey+1, lastkey+n+1)

    for i in range(n):
      line = lines[i]
      ncol = len(line) # number of columns
      dstr = "%5d %2d" % (int(keys[i]), ncol)
      for item in line:
        dstr += " %11g" % float(item)
      datalines.append(dstr+"\n")

  fp.writelines(datalines)
  fp.close()

  #if not _APPEND: # i.e. it's a new doc file
      #writeSpireoutFile(filename)

def makeDocfileHeader(filename, batext=None):
  """
  Create the comment line used at the top of SPIDER document files
  
  Calls:
    nowisthetime
  """
  
  filename = os.path.basename(filename)
  fn, ext = os.path.splitext(filename)
  ext = ext[1:]
  if batext == None:
    batext = 'spl'   # Spider Python Library
  date,time,idstr = nowisthetime()
  h = " ;%s/%s   %s AT %s   %s\n" % (batext,ext,date,time,filename)
  return h

def nowisthetime():
  """
  Return current time as tuple of 3 strings: (date, time, ID)
  """
  
  tt = time.localtime(time.time())
  
  # localtime return format: (2003, 10, 16, 12, 48, 30, 3, 289, 1)
  #t = string.split(time.asctime(tt))
  t = time.asctime(tt).split()
  
  # asctime return format: 'Thu Oct 16 12:50:17 2003'
  mo = t[1].upper()
  day = t[2]
  if len(day) < 2: day = '0' + day
  timestr = t[3]
  yr = t[4]
  datestr = "%s-%s-%s" % (day, mo, yr)

  yr = yr[-2:]
  
  #print('tt', tt, type(tt))
  #print('tt.tm_mon', tt.tm_mon, type(tt.tm_mon))
  #exit()
  
  # this is just to get the month as a number
  ##d = map(str,tt)   # stringify all numbers in the tuple
  ##mon = d[1]
  mon= str(tt.tm_mon)
  if len(mon) < 2: mon = '0' + mon
  
  #(h,m,s) = string.split(timestr,':')
  (h,m,s) = timestr.split(':')
  idstr = "%s%s%s%s%s%s" % (yr,mon,day,h,m,s)

  return (datestr, timestr, idstr)
  
def getLastDocfileKey(docfile):
  "return the last key of a doc file"
  if not os.path.exists(docfile):
    return None
  cmd = 'tail %s' % docfile
  res = getoutput(cmd)
  s = res.split("\n")
  s.reverse()

  for line in s:
    if len(line) > 1 and line[1] != ";":
      ss = line.split()
      try:
        i = int(ss[0])
        return i
      except:
        pass
  
  return None
  
def isDictionary(d):
  """
  Returns 1 if input is a Python dictionary
  """
  
  if isinstance(d, dict): 
    return 1
  else: 
    return 0

def isListofLists(d):
  """
  Returns 1 if input is a list, and 1st item in input is also a list
  Actually works for tuples as well. Only checks 1st element 
  """
  
  if not isListorTuple(d):
    return 0
  if len(d) < 1:
    return 0
  if isListorTuple(d[0]):
    return 1
  else:
    return 0
    
def isListorTuple(x):
  """
  Returns 1 if input is a list or a tuple
  """
  
  if isinstance(x, ListType) or isinstance(x, TupleType) : 
    return 1
  else: 
    return 0
    
def fixHeaders(headers):
  """
  Make all headers 11 characters in width; return doc string
  """
  
  w = 11
  docstr = " ; /    "
  for h in headers:
    d = len(h)
    if d > w:
      h = h[:w]
    docstr += h.rjust(w+1)
  docstr += "\n"
  
  return docstr
  
#def writeSpireoutFile(filename):
  #"""
  #This section added Aug 2006, for Spire compatibility
  #"""
  
  #if WRITE_SPIREOUT in os.environ:
    #spireout = os.environ[WRITE_SPIREOUT]
    #if os.path.exists(spireout):
      #fp = open(spireout, mode='a')
    #else:
      #fp = open(spireout, mode='w')
    #date, time, id = nowisthetime()
    #fn = os.path.basename(filename)
    #s = "  %s AT %s    OPENED NEW DOC FILE: %s\n" % (date, time, fn)
    #fp.write(s)
    #fp.close()

if __name__ == "__main__":
  main()
