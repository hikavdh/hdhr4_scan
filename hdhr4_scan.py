#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys, os, io, re, argparse, time, curses, datetime, traceback
from threading import Thread
pyversion = sys.version_info[0]
if pyversion == 2:
    from StringIO import StringIO

else:
    from io import StringIO

try:
    from subprocess32 import Popen, PIPE, check_output, call

except:
    from subprocess import Popen, PIPE, check_output, call

'''
    Shell for the hdhomerun_config program to scan for channels,
    to compare a fresh scan for changes since the last stored scan
    or to play a channel with mplayer or ffmpeg and mpg123
    Configuration is stored in ~/.hdhr/hdhr_scan.cfg
    run hdhr4_scan.py --help for all options

    By Hika van den Hoven hikavdh at gmail dot com

    LICENSE

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
values = {
    'id': '',
    'tuner': '0',
    'radiostart': '',
    'radioend': '',
    'storedate': None,
    'scandate': None}
multiplexes = []
channels = []
refmultiplexes = {}
refchannels = {}
keys = {}
starttime = datetime.datetime.now()
cdir = ''
cgrp = {'config': 1, 'multiplexes': 2, 'services': 3, 'keys': 4}

class HDhomerunScan(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pid = Popen(args = ['hdhomerun_config', values['id'], 'scan', values['tuner']],
                universal_newlines = True,
                bufsize = -1, stdout = PIPE)
        self.result = StringIO(pid.communicate()[0])
#
class HDhomerunPlay(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        devnull = io.open('/dev/null', 'w')
        self.p1 = Popen(args = ['hdhomerun_config',values['id'], 'save', '/tuner%s' % values['tuner'], '-'],
                        stdout = PIPE)
        if mplayer['present']:
            p2 = Popen(args = ['mplayer', '-fs', '-'], stdin = self.p1.stdout, stdout = devnull)
            p2.wait()

        else:
            p2 = Popen(args = ['ffmpeg', '-i', '-', '-map', '0:a', '-f', 'mp3', '-'],
                    stdin = self.p1.stdout, stdout = PIPE, stderr = devnull)
            p3 = Popen(args = ['mpg123', '-'], stdin = p2.stdout, stderr = devnull)
            p3.wait()

        devnull.close()

    def stop(self):
        self.p1.terminate()
#
def read_commandline():
    parser = argparse.ArgumentParser(description = '', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--id', type = str, default = None, dest = 'id',
                    metavar = '<id or ip>', help = 'Give the id or ip-address of your hdhomerun.\n' +
                            'It will be stored and needs only be set again\n' +
                            'when another value is needed.\n')
    parser.add_argument('--tuner', type = str, default = None, dest = 'tuner',
                    metavar = '<nr>', help = 'Give the tunernr of your hdhomerun to use.\n' +
                            'It will be stored and needs only be set again\n' +
                            'when another value is needed.\n')
    parser.add_argument('--radioids', type = str, default = None, dest = 'radioids',
                    metavar = '"<min>-<max>"', help = 'Give the range of channelnumbers where the radio\n' +
                            'channels are located.\n' +
                            'It will be stored and needs only be set again\n' +
                            'when another value is needed. Set to "" to clear.\n')
    parser.add_argument('-r', '--rawscan', action = 'store_true', default = False, dest = 'rawscan',
                    help = 'Perform a new scan with hdhomerun_config and\n' +
                            'store it under the output name with extension ".raw"\n')
    parser.add_argument('-i', '--input', type = str, default = None, dest = 'input_file',
                    metavar = '<file>', help = 'Give the name of the outputfile from an earlier\n' +
                            'hdhomerun_config scan.\n' +
                            'An extension of ".raw" is added to the name.\n')
    parser.add_argument('-o', '--output', type = str, default = 'channelscan', dest = 'output_file',
                    metavar = '<file>',
                    help = 'Defaulting to "channelscan" with an extension of\n' +
                            '".txt" added. If neither -r nor -i is set and a file\n' +
                            'with the same name and an extention ".raw" exists,\n' +
                            'it will be taken as input file.\n' +
                            'Set to None or "" to output to screen.\n')
    parser.add_argument('-s', '--save', action = 'store_true', default = False, dest = 'save',
                    help = 'Save the current scan as a referencescan.\n')
    parser.add_argument('-d', '--diff', action = 'store_true', default = False, dest = 'diff',
                    help = 'Give the differences with the earlier stored scan.\n')
    parser.add_argument('-f', '--frequency', action = 'store_true', default = False, dest = 'frequency',
                    help = 'Sort the multiplexes by frequency i.s.o. by TSID')
    parser.add_argument('-c', '--sort', type = int, default = 1 , dest = 'sort',
                    metavar = '<nr>', help = 'Channel sorting:\n' +
                            '    1 = by serviceid (default)\n' +
                            '    2 = by channelnumber\n' +
                            '    3 = by channelname\n' +
                            '    4 = by multiplex:serviceid\n' +
                            '    5 = by multiplex:channelnumber\n' +
                            '    6 = by multiplex:channelname\n')
    parser.add_argument('-p', '--play', type = str, default = None, dest = 'play',
                    metavar = '<sid>or<key>', help = 'Play the stream from given serviceid or shortkey.\n')
    parser.add_argument('-k', '--key', type = str, default = None, dest = 'key',
                    metavar = '<sid:key>', help = 'Link the key to the serviceid for tuning.\n')

    return parser.parse_args()
#
def check_path(name, use_sudo = False):
    p = {'name': name, 'path': None, 'present': False}
    if use_sudo:
        try:
            path = check_output(['sudo', 'which', name], stderr = None)
            p['path'] = re.sub(b'\n', b'',path)
            p['present'] = True

        except:
            #~ traceback.print_exc()
            print('%s not Found!\n' % (name))

    else:
        try:
            path = check_output(['which', name], stderr = None)
            p['path'] = re.sub(b'\n', b'',path)
            p['present'] = True

        except:
            #~ traceback.print_exc()
            print('%s not Found!\n' % (name))

    return p
#
def open_file(file_name, extensie , mode = 'rb'):
    if file_name in (None,  'None', ''):
        return None

    name = '%s.%s' % (file_name, extensie)
    if 'r' in mode and not (os.path.isfile(name) and os.access(name, os.R_OK)):
        return None

    if ('a' in mode or 'w' in mode):
        if os.path.isfile(name) and not os.access(name, os.W_OK):
            return None

    try:
        if 'b' in mode:
            file_handler =  io.open(name, mode = mode)

        else:
            file_handler =  io.open(name, mode = mode, encoding = 'utf-8')

    except:
        return None

    return file_handler
#
def get_cdir():
    global cdir
    if cdir == '':
        hpath = os.environ.get('HOME', None)
        if hpath == None:
            return

        cdir = '%s/.hdhr' % hpath
        if not os.path.exists(cdir):
            os.mkdir(cdir)

    return cdir
#
def read_config():
    cfile = '%s/hdhr_scan' % get_cdir()
    f = open_file(cfile, 'cfg', 'r')
    if f == None:
        print('Can\'t open the configurationfile')
        return

    section = 0
    for line in f.readlines():
        try:
            line = line.strip('\n').strip()
            if len(line) == 0 or line[0] == '#':
                continue

            config_title = re.search('\[(.*?)\]', line)
            if config_title != None:
                if config_title.group(1) in cgrp.keys():
                    section = cgrp[config_title.group(1)]

                else:
                    section = 0

                continue

            if section == 1:
                v = re.split('=', line)
                if len(v) >1:
                    name = v[0].strip()
                    val = v[1].strip()
                    if name in ('id', 'tuner', 'radiostart', 'radioend'):
                        values[name] = val

                    if name == 'storedate':
                        if val in ('', '0', 'none'):
                            values[name] = None

                        else:
                            try:
                                values[name] = datetime.date.fromordinal(int(val))

                            except:
                                values[name] = None

            elif section == 2:
                v = {}
                v['TSID'], v['ONID'], v['symbol'], v['freq'] = re.split(';', line)
                v['TSID'] = int(v['TSID'])
                v['ONID'] = int(v['ONID'])
                v['freq'] = int(v['freq'])
                refmultiplexes[v['TSID']] = v

            elif section == 3:
                p = {}
                p['TSID'], p['sid'], p['cid'], p['name'], p['encrypt'], p['system'] = re.split(';', line)
                p['TSID'] = int(p['TSID'])
                #~ p['sid'] = int(p['sid'])
                p['cid'] = int(p['cid'])
                p['encrypt'] = int(p['encrypt'])
                p['system'] = int(p['system'])
                refchannels[p['sid']] = p

            elif section == 4:
                v = re.split('=', line)
                if len(v) >1:
                    keys[v[0].strip()] = v[1].strip()

        except:
            pass

    f.close()
#
def save_config(multiplexes=None, channels=None):
    cfile = '%s/hdhr_scan' % get_cdir()
    f = open_file(cfile, 'cfg', 'w')
    if f == None:
        print('Can\'t write the configurationfile')
        return

    f.write('[config]\n')
    for name in ('id', 'tuner', 'radiostart', 'radioend'):
        f.write('%s = %s\n' % (name, values[name]))

    if isinstance(values['storedate'], datetime.date):
        f.write('# %s\n' % (values['storedate'].strftime('%d %b %Y'), ))
        f.write('storedate = %s\n' % (values['storedate'].toordinal(), ))

    else:
        f.write('storedate = none\n')

    f.write('[keys]\n')
    for k, v in keys.items():
        f.write('%s = %s\n' % (k, v))

    f.write('[multiplexes]\n')
    if isinstance(multiplexes, (list, tuple)):
        for v in multiplexes:
            f.write('%s;%s;%s;%s\n' %
                    (v['TSID'], v['ONID'], v['symbol'], v['freq']))

    f.write('[services]\n')
    if isinstance(channels, (list, tuple)):
        for p in channels:
            f.write('%s;%s;%s;%s;%s;%s\n' %
                    (p['TSID'], p['sid'], p['cid'], p['name'], p['encrypt'], p['system']))

    f.close()
#
def save_key(value):
    if value == None:
        return False

    try:
        k = re.split(':', value)
        if len(k) == 2 and k[0] in refchannels.keys():
            keys[k[1]] = k[0]
            print('linking key "%s" to: %s' % (k[1], serviceline(refchannels[k[0]])))
            return True

    except:
        #~ traceback.print_exc()
        return False

    return False
#
def set_channel(key):
    sid = keys.get(key, key)
    if sid not in refchannels.keys():
        print('"%s" does not reference a valid channel!' % (sid, ))
        sys.exit(1)

    tsid = refchannels[sid]['TSID']
    freq = '%s000000' % refmultiplexes[tsid]['freq']
    print('Setting to: %s' % serviceline(refchannels[sid]))
    call(args = ['hdhomerun_config',
                    values['id'], 'set', '/tuner%s/channel' % values['tuner'], freq])
    call(args = ['hdhomerun_config',
                    values['id'], 'set', '/tuner%s/program' % values['tuner'], sid])
#
def scanning(win):
    curses.curs_set(0)
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        win.attrset(curses.color_pair(3))

    win.clearok(0)
    win.addstr(1, 30, values['id'])
    win.addstr(1, 36 + len(values['id']), values['tuner'])
    if curses.has_colors():
        win.attrset(curses.color_pair(1))

    win.addstr(1, 5, 'Scanning for channels on')
    win.addstr(1, 31 + len(values['id']), 'tuner')
    win.addstr(1, 38 + len(values['id']), 'using %s channelmap.' %
            (check_output(args = ['hdhomerun_config',
                    values['id'], 'get', '/tuner%s/channelmap' % values['tuner']]).decode('utf-8').strip('\n')))
    win.addstr(2, 10, 'Scanning')
    if curses.has_colors():
        win.attrset(curses.color_pair(2))

    hdhrscan.start()
    freq = 'none'
    while hdhrscan.is_alive():
        f = check_output(args = ['hdhomerun_config',
                    values['id'], 'get', '/tuner%s/channel' % values['tuner']]).decode('utf-8').strip('\n')
        if freq != f:
            freq = f
            if freq[-6:] == '000000':
                txt = '%s MHz' % (freq[:-6], )

            elif freq[-3:] == '000':
                txt = '%s kHz' % (freq[:-3], )

            else:
                txt = '%s Hz' % (freq, )

            win.clrtoeol()
            win.addstr(2, 19, txt)

        win.addstr(3, 19, ('%s' % (datetime.datetime.now() - starttime))[2:10])
        win.refresh()

    curses.curs_set(1)
#
def read_input(rawfile, rawscan):
    if rawscan:
        values['scandate'] = datetime.date.today()
        curses.wrapper(scanning)
        rawfile.write('#%s\n' % values['scandate'].toordinal())
        for line in hdhrscan.result.readlines():
            if sys.version_info[0] == 2:
                line = line.decode('utf-8')

            rawfile.write(line)
            line = line.strip('\n').strip()
            yield line

    else:
        for line in rawfile.readlines():
            line = line.strip('\n')
            if line[0] == '#':
                val = line[1:]
                if val in ('', '0', 'none'):
                    values['scandate'] = None

                else:
                    try:
                        values['scandate'] = datetime.date.fromordinal(int(val))

                    except:
                        values['scandate'] = None

                continue

            yield line
#
def scanline(line, f):
    v = re.split(':', line)
    if len(v) >1:
        if v[0] == 'SCANNING':
            return {'freq': int(v[2].strip(')')), 'freecount': 0, 'encryptcount': 0, 'othercount': 0}

        if v[0] == 'LOCK':
            values = re.split(' ', v[1].strip())
            if values[0] == 'none':
                return

            else:
                f['symbol'] = values[0]
                f['ss'] = int(re.split('=', values[1])[1])
                f['snq'] = int(re.split('=', values[2])[1])
                f['seq'] = int(re.split('=', values[3])[1].strip(')'))

        if v[0] == 'TSID':
            f['TSID'] = int(v[1], 16)

        if v[0] == 'ONID':
            f['ONID'] = int(v[1], 16)
            multiplexes.append(f)

        if v[0][:7] == 'PROGRAM':
            c = re.split(' ', v[1].strip(), 1)
            if len(c) != 2:
                c.append('')

            p = {
                'sid': re.split(' ', v[0])[1],
                'cid': int(c[0]),
                'name': c[1],
                'TSID': f['TSID'],
                'system': 0,
                'encrypt': 0}
            if len(p['name']) > 11 and p['name'][-11:] == '(encrypted)':
                p['encrypt'] = 1

            if (p['cid'] == 0 or p['name'] == ''or
                    len(p['name']) > 9 and p['name'][-9:] == '(control)'):
                f['othercount'] += 1
                p['system'] = 2

            elif p['encrypt']:
                f['encryptcount'] += 1

            else:
                f['freecount'] += 1

            channels.append(p)

        return f
#
def diff_scans():
    if not isinstance(values['storedate'], datetime.date):
        print('No proper referencescan stored.')
        return

    if not isinstance(values['scandate'], datetime.date):
        print('No fresh scan found or made.')
        return

    refm = list(refmultiplexes.keys())
    diffm = {'new': [], 'old': [], 'changed': []}
    for mp in multiplexes:
        if mp['TSID'] in refm:
            for k, v in refmultiplexes[mp['TSID']].items():
                if v != mp[k]:
                    #changed
                    diffm['changed'].append('old: %s' % multiplexline(refmultiplexes[mp['TSID']]))
                    diffm['changed'].append('new: %s\n' % multiplexline(mp))
                    break

            refm.remove(mp['TSID'])

        else:
            #new
            diffm['new'].append(multiplexline(mp))

    for ts in refm:
        #old
        diffm['old'].append(multiplexline(refmultiplexes[ts]))

    refs = list(refchannels.keys())
    diffs = {'new': [], 'old': [], 'changed': [], 'cname': [], 'ccid': []}
    for s in channels:
        if s['sid'] in refs:
            for k, v in refchannels[s['sid']].items():
                if k in ('name', 'cid', 'system'):
                    continue

                if v != s[k]:
                    #changed
                    diffs['changed'].append('old: %s' % serviceline(refchannels[s['sid']]))
                    diffs['changed'].append('new: %s\n' % serviceline(s))
                    break

            else:
                if refchannels[s['sid']]['name'] != s['name'] :
                    #changed
                    diffs['cname'].append('old: %s' % serviceline(refchannels[s['sid']]))
                    diffs['cname'].append('new: %s\n' % serviceline(s))

                elif refchannels[s['sid']]['cid'] != s['cid'] :
                    #changed
                    diffs['ccid'].append('old: %s' % serviceline(refchannels[s['sid']]))
                    diffs['ccid'].append('new: %s\n' % serviceline(s))

            refs.remove(s['sid'])

        else:
            #new
            diffs['new'].append(serviceline(s))

    for sid in refs:
        #old
        diffs['old'].append(serviceline(refchannels[sid]))

    print('Comparing referencescan from %s with scan from %s:\n' %
            (values['storedate'].strftime('%d-%m-%Y'), values['scandate'].strftime('%d-%m-%Y')))
    if len(diffm['changed']) == 0:
        print('  No changed multiplexes.')

    else:
        print('  Changed multiplexes:')
        for l in diffm['changed']:
            print('    %s' % l)

    if len(diffm['new']) == 0:
        print('  No new multiplexes.')

    else:
        print('  New multiplexes:')
        for l in diffm['new']:
            print('    %s' % l)

    if len(diffm['old']) == 0:
        print('  No removed multiplexes.')

    else:
        print('  Removed multiplexes:')
        for l in diffm['old']:
            print('    %s' % l)

    if len(diffs['new']) == 0:
        print('  No new services.')

    else:
        print('  New services:')
        for l in diffs['new']:
            print('    %s' % l)

    if len(diffs['old']) == 0:
        print('  No removed services.')

    else:
        print('  Removed services:')
        for l in diffs['old']:
            print('    %s' % l)

    if len(diffs['cname']) == 0:
        print('  No changed servicenames.')

    else:
        print('  Changed servicenames:')
        for l in diffs['cname']:
            print('    %s' % l)

    if len(diffs['ccid']) == 0:
        print('  No changed channelnumbers.')

    else:
        print('  Changed channelnumbers:')
        for l in diffs['ccid']:
            print('    %s' % l)

    if len(diffs['changed']) == 0:
        print('  No otherwise changed services.')

    else:
        print('  Otherwise changed services:')
        for l in diffs['changed']:
            print('    %s' % l)

#
def make_output():
    if args.frequency:
        multiplexes.sort(key=lambda p: (p['freq']))

    else:
        multiplexes.sort(key=lambda p: (p['TSID']))

    printline('<TSID>[<ONID>]: <modulation>:<freq>(MHz) (<quality>) (<chancount>)')
    for v in multiplexes:
        if v['freecount'] + v['encryptcount'] + v['othercount'] == 0:
            continue

        else:
            printline(multiplexline(v, True))

    if args.sort == 2:
        channels.sort(key=lambda p: (p['cid']))

    elif args.sort == 3:
        channels.sort(key=lambda p: (p['name']))

    elif args.sort == 4:
        channels.sort(key=lambda p: (p['TSID'], p['sid']))

    elif args.sort == 5:
        channels.sort(key=lambda p: (p['TSID'], p['cid']))

    elif args.sort == 6:
        channels.sort(key=lambda p: (p['TSID'], p['name']))

    else:
        channels.sort(key=lambda p: (p['sid']))

    ctype = -1
    for sgrp in ('free', 'encrypted', 'other'):
        printline('%s channels: <TSID>:<SID> = <channum> <name>' % sgrp)
        ctype += 1
        for p in channels:
            if p['encrypt'] + p['system'] == ctype or (ctype == 2 and p['system']):
                printline(serviceline(p))
#
def multiplexline(m, alldata=False):
    if alldata:
        return u'{:}[{:}]: {:}:{:} (ss={:>3}, snq={:>3}, seq={:>3}) ({:>2}, {:>2},{:>2})'.format(
                m['TSID'], m['ONID'], m['symbol'], m['freq'],
                m['ss'], m['snq'], m['seq'],
                m['freecount'], m['encryptcount'], m['othercount'])

    else:
        return u'{:}[{:}]: {:}:{:}'.format(
                m['TSID'], m['ONID'], m['symbol'], m['freq'])
#
def serviceline(s):
    return u'    {:}:{:} = ({:>3d}) "{:}"'.format(
            s['TSID'], s['sid'], s['cid'], s['name'])
#
def printline(text):
    if fout == None:
        print(text)

    else:
        fout.write(u'{:}\n'.format(text))

# Initialization
hdhr = check_path('hdhomerun_config')
if not hdhr['present']:
    print('Please first install the "hdhomerun_config" program!')
    sys.exit(1)

mplayer = check_path('mplayer')
ffmpeg = check_path('ffmpeg')
mpg123 = check_path('mpg123')
if mplayer['present']:
    can_play = True

elif ffmpeg['present'] and mpg123['present']:
    can_play = True
    print('Without "mplayer" you won\'t be able to play TV channels.')

else:
    can_play = False
    print('Without either "mplayer" or both "mpg123" and "ffmpeg" you won\'t be able to play any channels.')

args = read_commandline()
read_config()
if args.id != None:
    values['id'] = args.id

if args.tuner != None:
    values['tuner'] = args.tuner

if args.radioids != None:
    if args.radioids == '':
        values['radiostart'] = ''
        values['radioend'] = ''
    ids = re.split('-', args.radioids)
    if len(ids) == 2:
        values['radiostart'] = int(ids[0])
        values['radioend'] = int(ids[1])

if save_key(args.key):
    save_config(list(refmultiplexes.values()), list(refchannels.values()))
    sys.exit(0)

save_config(list(refmultiplexes.values()), list(refchannels.values()))
if args.play != None and can_play:
    set_channel(args.play)
    play = HDhomerunPlay()
    play.start()
    print('Press "Q" to quit')
    while True:
        if pyversion == 2:
            ans = raw_input()

        else:
            ans = input()

        if ans in ('q', 'Q') or not play.is_alive():
            break

    play.stop()
    sys.exit(0)

if not args.rawscan:
    fin = open_file(args.input_file, 'raw', 'r')
    if fin == None:
        fin = open_file(args.output_file, 'raw', 'r')

    if fin == None:
        args.rawscan = True

if args.rawscan:
    if values['id'] in ('', None):
        print('Please supply an id or ip-address for the HDhomerun device!')
        sys.exit(1)

    fin = open_file(args.output_file, 'raw', 'w')

fout = open_file(args.output_file, 'txt', 'w')
if fout == None and args.output_file not in (None,  'None', ''):
    print('Can\'t open "%s.txt" for writing!' % args.output_file)

else:
    print('Opened "%s.txt" for writing.' % args.output_file)

f = None
# The scan or reading of an earlier scan
hdhrscan = HDhomerunScan()
for line in read_input(fin, args.rawscan):
    if len(line) < 5:
        continue

    f = scanline(line, f)

# The output
if args.diff:
    diff_scans()

make_output()
if args.save:
    values['storedate'] = values['scandate']
    save_config(multiplexes, channels)

# Closeup
fin.close()
if args.rawscan:
    hdhrscan.result.close()

if fout != None:
    fout.close()

print('Scantime: ' + ('%s' % (datetime.datetime.now() - starttime))[2:10])
