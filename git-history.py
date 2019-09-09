#!/usr/bin/python2.7

# I don't believe in license.
# You can do whatever you want with this program.

import os
import sys
import json
import re
import argparse
import random
import subprocess
import time
from os.path import expanduser
from termcolor import colored
from multiprocessing.dummy import Pool

parser = argparse.ArgumentParser()
parser.add_argument( "-p","--path",help="path to scan" )
parser.add_argument( "-d","--date",help="do no check commit before this date" )
parser.add_argument( "-c","--length",help="only check in first n characters" )
parser.add_argument( "-s","--search",help="term to search (regexp)" )
parser.add_argument( "-t","--threads",help="max threads, default 10" )
parser.parse_args()
args = parser.parse_args()

if args.path:
    path = args.path
else:
    parser.error( 'path is missing' )

if args.threads:
    max_threads = int(args.threads)
else:
    max_threads = 10

if args.date:
    max_date = int( time.mktime(time.strptime(args.date,'%Y-%m-%d')) )
    str_max_date = args.date
else:
    # no limit
    max_date = -1
    str_max_date = '-1 (no limit)'
    # max_date = '2018-01-01 00:00:00'

if args.length:
    max_length = int(args.length)
    str_max_length = args.length+' chars'
else:
    # no limit
    max_length = -1
    str_max_length = '-1 (no limit)'
    # max_length = 1000

t_regexp = []
if args.search:
    if os.path.isfile(args.search):
        sys.stdout.write( colored('[+] loading regexp: %s\n' %  args.search, 'green') )
        with open(args.search) as json_file:
            data = json.load(json_file)
        if 'pattern' in data:
            t_regexp.append( data['pattern'] )
        elif 'patterns' in data:
            for r in data['patterns']:
                t_regexp.append( r )
    else:
        t_regexp.append( args.search )
else:
    parser.error( 'search term is missing' )

# print(t_regexp)
l_regexp = len(t_regexp)
if not l_regexp:
    parser.error( 'search term is missing' )

sys.stdout.write( colored('[+] %d regexp found.\n' %  l_regexp, 'green') )
print( "\n".join(t_regexp) )
sys.stdout.write( colored('[+] scanning directory: %s\n' %  path, 'green') )

output = subprocess.check_output( "find "+path+" -type d -name '.git'", shell=True ) 
t_repo = output.strip().split("\n")
l_repo = len(t_repo)
sys.stdout.write( colored('[+] %d repositories found.\n' %  l_repo, 'green') )
sys.stdout.write( colored('[+] options are ->  max_threads: %d, max_date: %s, max_length: %s\n' %  (max_threads,str_max_date,str_max_length), 'green') )


def doCheckCommit( commit ):
    sys.stdout.write( 'progress: %d/%d\r' %  (t_stats['n_current'],t_stats['n_commit']) )
    sys.stdout.flush()
    t_stats['n_current'] = t_stats['n_current'] + 1

    if t_stats['max_date'] > -1 and int(commit['date']) < int(t_stats['max_date']):
        # print('skip %s %s %s\n' % (commit['commit'], commit['date'], t_stats['max_date']) )
        return

    try:
        content = subprocess.check_output( 'cd "'+t_stats['repo']+'"; git show '+commit['commit']+' 2>&1', shell=True )
    except Exception as e:
        sys.stdout.write( colored("[-] error occurred: %s" % e, 'red') )
        return

    if t_stats['max_length']:
        content = content[0:max_length]

    for regexp in t_regexp:
        r = re.findall( '(.{0,50})('+regexp+')(.{0,50})', content )
        # print(regexp)
        if r:
            for rr in r:
                if not rr[1] in t_stats['t_findings']:
                    t_stats['t_findings'].append( rr[1] )
                    str = commit['commit'] +' : ' + rr[0].lstrip() + colored('%s' %  rr[1], 'red') + rr[-1].rstrip()
                    sys.stdout.write( '%s\n' % str )


for repo in t_repo:
    repo = repo.replace('.git','')
    sys.stdout.write( '[+] %s\n' %  repo )

    try:
        output = subprocess.check_output( "cd "+repo+"; git log --pretty=format:'{\"commit\":\"%H\",\"date\":\"%at\"}' 2>&1", shell=True )
    except Exception as e:
        sys.stdout.write( colored("[-] error occurred: %s" % e, 'red') )
        continue

    t_commit = json.loads('['+output.replace('\n',',')+']')
    # print(t_commit)

    t_stats = {
        'max_date': max_date,
        'max_length': max_length,
        'n_current': 0,
        'n_commit': len(t_commit),
        'repo': repo,
        't_findings': []
    }

    pool = Pool( max_threads )
    pool.map( doCheckCommit, t_commit )
    pool.close()
    pool.join()

