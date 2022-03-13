#!/usr/bin/python3

import sys;
import io;
import os;
import time;
import pyvisa;
import struct;
import json;

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

        cur_len = int(inp[2:11].decode())
        if cur_len == 0:
            return True

        total_smpls = int(inp[11:20].decode())
        cur_pos = int(inp[20:29].decode())

        with io.open("/tmp/cur-%d.bin" % cur_pos, mode="wb") as f:
            f.write(inp)

        start = 29
        end_of_meta = 128

        if samples_total == -1:
            samples_total = total_smpls
            samples_data  = bytearray(samples_total)
            meta = inp[start:end_of_meta]
            print("got %d total length" % samples_total)
        else:
            assert(samples_total == total_smpls)

        cur_len = len(inp) - end_of_meta
        for i in range(0, cur_len):
            samples_data[cur_pos+i] = inp[end_of_meta+i]
        samples_got += cur_len

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
            res['samples'] = channelSamples(chan, samples_data, int(points/2))
        return res

    def channelSamples(chan, data, block_len):
        nonlocal points
        nonlocal channel_count

        # data is split up??
        #  |chan1a|chan2a|chan1b|chan2b|
        pos1 = (chan-1)*block_len
        pos2 = pos1 + channel_count*block_len
        print("%s %s %s %s %s %s" % (chan, pos2, pos1, channel_count, points, block_len))

        samples = list(struct.unpack('%dB' % block_len, data[pos1:pos1+block_len]))
        samples.extend(struct.unpack('%dB' % block_len, data[pos2:pos2+block_len]))
        return samples
            

    while not readPacket():
        #print("now %d bytes of %d\n" % (len(data), total))
        pass

    with io.open("/tmp/meta", mode="wb") as f:
        f.write(meta)
    with io.open("/tmp/samples", mode="wb") as f:
        f.write(samples_data)

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
    print(res)

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
            'sampling_rate': float(sampling_rate),
            'sampling_multiple': float(sampling_multiple),
            'trigger_time': float(trigger_time),
            'acq_start?': float(acq_start)
            }


resources = pyvisa.ResourceManager('@py')
#print(resources.list_resources())

oscilloscope = resources.open_resource( 'USB0::1183::20574::111::0::INSTR' )

print("found a (%s)\n" % oscilloscope.query('*IDN?'))

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


name = sys.argv[1]

while True:
    wave = readWaveform(oscilloscope)
    with io.open(name, mode="wt") as f:
        f.write(json.dumps(wave))

    gp = os.popen("gnuplot", "w")
    gp.writelines(["plot '-', '-'\n"])
    for ch in wave["channels"]:
        if ch['enable']:
            gp.writelines([str(sample)+"\n" for sample in ch["samples"]])
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
