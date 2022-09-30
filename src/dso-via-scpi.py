#!/usr/bin/python3

import sys;
import io;
import os;
import time;
import pyvisa;
import struct;
import json;

debug_flag = 0
progress_flag = sys.stderr.isatty()
next_progress = time.time() + 1;
max_progress_len = 0


def progress(what, done):
    global next_progress, max_progress_len, progress_flag
    if not progress_flag:
        return 0

    if done < 0:
        sys.stderr.write("\r%*s\r" % (max_progress_len, ""))
    else:
        now = time.time()
        if now >= next_progress:
            progress = "%5.1f%% %s" % (done * 100.0, what)

            pl = len(progress);
            if pl > max_progress_len:
                max_progress_len = pl

            next_progress = now + 1
            sys.stderr.write("\r" + progress + ("%*s" % (max(0, max_progress_len-pl), "")) + "\r")

    sys.stderr.flush()


def debug(*args):
    global debug_flag
    if debug_flag:
        # TODO: timestamp?
        if type(args) == type('str'):
            sys.stderr.write(args)
        else:
            sys.stderr.write(str(args))
        sys.stderr.write("\n")

def channelMetaData(o, chan):
    coup = False
    try:
        coup = o.query(':CHANnel%d:COUPling?' % chan)
    except Exception as e:
        # Channel not available
        sys.stderr.write("+++ error %s\n" % e)
        return False
        #pass
    #if coup == False:
    #    return False
    probe = o.query(':CHANnel%d:PROBe?' % chan)
    scale = o.query(':CHANnel%d:SCALe?' % chan)
    return { 
            'channel': chan,
            'coupling': coup,
            'probe': probe,
            'scale': scale,
            }

def readWaveform(o):

    # Can only be queried?
    #print(o.query("WAVeform:SOURce CHANnel%d" % chan))
    #print(o.query("WAVeform:BYTeorder LSBF"))
    #print(o.query("WAVeform:FORMat?")) # word?
    #print(o.query("WAVeform:UNSigned 0"))
    #print(o.query("WAVeform:POINts:MODE?")) # NORMal
    #print(o.query("WAVeform:XORigin?"))
    #print(o.query("WAVeform:STARt?"))
    points = int(o.query("ACQuire:POINts?"))
    #points = o.query("WAVeform:POINts?")

    #print(points)

    samples_data = bytes()
    samples_total = -1
    samples_got = 0
    channel_count = 0

    meta = bytes()

    def readPacket():
        nonlocal samples_total
        nonlocal samples_data
        nonlocal samples_got
        nonlocal meta
        nonlocal samples_got

        o.write("PRIVate:WAVeform:DATA:ALL?\n")
        #o.write("WAVeform:DATA:ALL?\n")
        inp = o.read_raw()
        assert(chr(inp[0]) == '#')
        assert(chr(inp[1]) == '9')

        this_len = int(inp[2:11].decode())
        if this_len == 0:
            return False

        total_smpls = int(inp[11:20].decode())
        cur_pos = int(inp[20:29].decode())

        #with io.open("/tmp/cur-%d.bin" % cur_pos, mode="wb") as f:
        #    f.write(inp)

        start = 29
        end_of_meta = 128

        if samples_total == -1:
            samples_total = total_smpls
            samples_data  = bytearray(samples_total)
            meta = inp[start:end_of_meta]
            debug("got %d total length" % samples_total)
        else:
            assert(samples_total == total_smpls)

        cur_len = len(inp) - end_of_meta
        for i in range(0, cur_len):
            samples_data[cur_pos+i] = inp[end_of_meta+i]
        samples_got += cur_len

        progress("Fetching samples: %dK of %dK done" % (samples_got/1000, samples_total/1000),
                samples_got/samples_total);
        return samples_got == samples_total

    def channelMeta(chan, volt, en):
        nonlocal points
        nonlocal meta
        nonlocal samples_data

        res = { 'channel': chan,
                'enable': en == b'1',
                'voltage': float(volt),
                #'offset': float(off),
                }
        if res['enable']:
            # TODO: blocksize?
            res['samples'] = channelSamples(chan, samples_data, 2000)
            res['voltage'] = absoluteVoltages(res)

        return res

    def channelSamples(chan, data, block_len):
        nonlocal points
        nonlocal channel_count

        # data is split up??
        #  |chan1a|chan2a|chan1b|chan2b|
        # For more than 4k Samples:
        #  |chan1a|chan2a|chan1b|chan2b|chan1c|chan2c|...

        samples = list()
        for i in range((chan-1)*block_len, len(data), block_len*channel_count):
            debug("ch%s from %s to %s" % (chan, i, i+block_len))
            samples.extend( struct.unpack('%db' % block_len, data[i:i+block_len]))

        return samples
            
    def absoluteVoltages(channel):
        nonlocal o
        off   = float(o.query(':CHANnel%d:OFFSet?' % channel['channel']))
        probe = float(o.query(':CHANnel%d:PROBe?' % channel['channel'])) # already factored in scale
        scale = float(o.query(':CHANnel%d:SCALe?' % channel['channel']))

        # TODO: Inverted, unsigned, ...
        grid_y = 25 # ??

        channel['offset'] = off
        channel['probe']  = probe
        channel['scale']  = scale
        return [ v/grid_y*scale-off for v in channel['samples']]

    while not readPacket():
        #debug("now %d bytes of %d\n" % (len(data), total))
        pass

    progress("", -1)

    #with io.open("/tmp/meta", mode="wb") as f:
    #    f.write(meta)
    #with io.open("/tmp/samples", mode="wb") as f:
    #    f.write(samples_data)

    # 00000000 -30 30-00 f2 05 2a 01 00  00 00 32 00 b5 ff 00 00  |00...*....2.....|
    # 00000010  00 00-32 2e 30 65 2b 30  30-32 2e 30 65 2b 30 30  |..2.0e+002.0e+00|
    # 00000020 -31 2e 30 65 2b 30 30-31  2e 30 65 2b 30 30-31-31  |1.0e+001.0e+0011|
    #    channel enable 3,4; sampling_rate
    # 00000030 -30-30-35 2e 30 30 30 65  2b 30 34-30 30 30 30 30  |005.000e+0400000|
    #         multiple; 9x; trigger_time
    # 00000040  31-00 00 00 00 00 00 00  00 00 2b 30 2e 30 30 65  |1.........+0.00e|
    #               acq_start?
    # 00000050  2b 30 30-30 30 30 30 31  30 00 b0 2f 30 30 32 30  |+00000010../0020|
    # 00000060  30 30 00                                          |00.|

    res = struct.unpack('cc 16x 7s7s7s7s cccc 9s 6s 9x 9s 6s 10x', meta)
    (running, trigger, 
            v1, v2, v3, v4,
            c1e, c2e, c3e, c4e,
            sampling_rate, sampling_multiple,
            trigger_time, acq_start ) = res
    debug(res)

    channel_count = sum([int(c1e), int(c2e), int(c3e), int(c4e)])
    channels = [ 
            channelMeta(1, v1, c1e),
            channelMeta(2, v2, c2e),
            channelMeta(3, v3, c3e),
            channelMeta(4, v4, c4e)
            ]

    return {
            'trigger': True if trigger == b'1' else False,
            'running': True if running == b'1' else False,
            'channels': channels,
            'samples': points,
            'sampling_rate': float(sampling_rate),
            'sampling_multiple': float(sampling_multiple),
            'trigger_time': float(trigger_time),
            'acq_start?': float(acq_start)
            }

def getDSOs(resources):
    return resources.list_resources("USB0::1183::20574:?*")

def getDSO():
    #nonlocal debug_flag

    resources = pyvisa.ResourceManager('@py')
    probable = getDSOs(resources)

    if len(probable) != 1:
        sys.stderr.write("Not exactly one device with USB ID found.\n")
        sys.exit(1)

    oscilloscope = resources.open_resource( probable[0] )

    #if debug_flag:
    #    print("found a (%s)\n" % oscilloscope.query('*IDN?'))

    return oscilloscope


def getConfig(items):
    o = getDSO()
    if len(items) == 0:
        sys.stderr.write("No items specified.\n")
    for item in items:
        try:
            res = o.query(item)
            # only print key in verbose mode?
            print("%s = %s" % (item, json.dumps(res)))
        except pyvisa.errors.VisaIOError as c:
            print("%s ERRORed: %s" % (item, c))

def saveConfig(filename):
    output = io.open(filename, 'wt') if filename else sys.stdout
    o = getDSO()
    output.write(o.query(":SETUp:NORMal?"))
    output.close

def saveWave(filename):
    output = io.open(filename, 'wt') if filename else sys.stdout
    o = getDSO()
    wave = readWaveform(o)

    enabled = list(filter(lambda ch: ch['enable'], wave['channels']))
    header = ['nr', 'time'] + ["ch%d" % ch['channel'] for ch in enabled] + ["ch%ds" % ch['channel'] for ch in enabled]

    def put(sep):
        nonlocal output, wave, enabled

        def line(x):
            nonlocal sep
            return sep.join(x) + "\n"

        def row(i):
            nonlocal enabled, wave
            # With 4M points we need quite a few digits for the time;
            # the channels only have 8 to 10bit, they can be shorter
            return [str(i), "%8g" % (i/wave['sampling_rate'] - wave['trigger_time'])] + ["%4g" % ch['voltage'][i] for ch in enabled] + [str(ch['samples'][i]) for ch in enabled]

        output.write(line(header))
        output.writelines([line(row(i)) for i in range(0, wave['samples'])])

    if filename.endswith(".csv"):
        put(",")
    elif filename.endswith(".json"):
        output.write(json.dumps(wave))
    else: # TSV
        put("\t")

    output.close()


#sampling_rate = oscilloscope.query(':ACQ:SRAT?')

#print(channelData(oscilloscope, 1))

#max_channels = int(oscilloscope.query(':SYST:RAM?')) # doesn't work for my 2d15
##print("%d channels\n" % max_channels)
#
#max_channels = 2

#print(oscilloscope.query(":SYSTem:LOCKed OFF"))

# oscilloscope.write("PRIVate:WAVeform:DATA:ALL?\n")
# with io.open("/tmp/pwda.bin", mode="wb") as f:
#     f.write(oscilloscope.read_raw())
# sys.exit(0)


args = list(sys.argv[1:])
direction = 's'
if len(args) > 0 and args[0] == 'save':
    args.pop(0)
elif len(args) > 0 and args[0] == 'get':
    args.pop(0)
    direction = 'g'
elif len(args) > 0 and args[0] == 'load':
    args.pop(0)
    direction = 'l'
elif len(args) > 0 and args[0] == 'list':
    resources = pyvisa.ResourceManager('@py')
    print(getDSOs(resources))
    sys.exit(0)
elif len(args) > 0 and args[0] == 'example':
    args.pop(0)
    if len(args) > 0 and args[0] == 'wavegen':
        args.pop(0)
    output = io.open(args[0], 'wt') if args[0] else sys.stdout
    output.write("... NIY")
    output.flush()
    output.close()
    sys.exit(0)

what='w'
if len(args) > 0 and args[0] == 'config':
    what = 'c'
    args.pop(0)
elif len(args) > 0 and args[0] == 'waveform':
    args.pop(0)
elif len(args) > 0 and args[0] == 'wavegen':
    what = 'g'
    args.pop(0)

todo = direction + what
if todo == 'gc':
    getConfig(args)
    sys.exit(0)


if len(args) > 1:
    sys.stderr.write("Too many or wrong arguments (%s).\n" % json.dumps(args))
    sys.exit(1)

filename = args.pop(0) if len(args) else ''

if todo == 'sw':
    saveWave(filename)
elif todo == 'sc':
    saveConfig(filename)
elif todo == 'lc':
    loadConfig(filename)
else:
    sys.stderr.write("Unsupported/Not yet implemented operation %s.\n" % todo)
    sys.exit(1)
    

sys.exit(0)

while True:
    wave = readWaveform(oscilloscope)
    with io.open(name, mode="wt") as f:
        f.write(json.dumps(wave))

    gp = os.popen("gnuplot", "w")
    #gp = io.open("/tmp/gnuplot", "wt")

    src = ["'-' with lines title 'CH%d'" % (ch["channel"]) 
            for ch in wave["channels"] if ch['enable']]

    gp.writelines([
                "plot " + ", ".join(src) + "\n",
        ])
    for ch in wave["channels"]:
        if ch['enable']:
            gp.writelines([str(sample)+"\n" for sample in ch['samples']]) # ch["voltage"]])
            gp.writelines(["e\n"])

    gp.flush()

    time.sleep(100)
    gp.close()
    sys.exit(0) 


while False:
    wave = readWaveform(oscilloscope, 1)


    print(wave['channels'][0]['data'][0:30])
    print(wave['channels'][1]['data'][0:30])
    print("")
    break
    time.sleep(1)
