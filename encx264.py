from optparse import OptionParser
import os
from datetime import datetime
import re
import subprocess
import sys
from functools import reduce

from encx264_targets import *

def doEncode():
    parser = OptionParser()
    parser.add_option("--target")
    parser.add_option("--inFile")
    parser.add_option("--outFile")
    parser.add_option("--crf", type="int")
    parser.add_option("--pass", type="int", default=1, dest="passN")
    parser.add_option("--bitrate", type="int", default=-1)
    parser.add_option("--sar")
    parser.add_option("--tc", default=None)
    parser.add_option("--ref", type="int")
    parser.add_option("--bitrate-ratio", type="float", default=-1,
                      dest="bitrate_ratio")

    if "--" in sys.argv:
        extra_args = \
            reduce(lambda cur, x: 
                       (" " in x
                        and '{0} "{1}"'
                        or '{0} {1}').format(cur, x),
                   sys.argv[sys.argv.index("--")+1:],
                   "")
        sys.argv = sys.argv[:sys.argv.index("--")]
    else:
        extra_args = ""

    (opt, args) = parser.parse_args()
    
    target = opt.target or args.pop(0)
    
    if target not in encode_targets:
        print("Invalid target {0}!".format(target))
        return
    
    params = encode_targets[target]

    inFile = opt.inFile or args.pop(0)
    outFile = opt.outFile or (len(args) > 0 and args.pop(0) or None)
    crf = opt.crf or (len(args) > 0 and args.pop(0) or None)
    passN = opt.passN
    bitrate = opt.bitrate
    sar = opt.sar
    tc = opt.tc
    ref = opt.ref or params["default_ref"]

    if opt.bitrate_ratio == -1:
        opt.bitrate_ratio = params.get("bitrate_ratio", 1.0)

    if inFile is None:
        print("You have not specified input file!")
        return

    if not os.path.isfile(inFile):
        print("{0} doesn't exist!".format(inFile))
        return

    if tc is None:
        tc = os.path.join(os.path.dirname(inFile), "timecode.txt")

    if tc:
        if not os.path.isfile(tc):
            print("Timecode file {0} doesn't exist!".format(tc))
            return
        tc = ' --tcfile-in "{0}"'.format(tc)

    if not outFile:
        outFile = os.path.splitext(inFile)[0] + ".mp4"

    if not sar:
        if not "default_sar" in params:
            print("sar must be specified!")
            return
        sar = params["default_sar"]

    statsFile = outFile + ".x264_stats"


    x264_exec = '"{0}"'.format(os.path.join(
                                os.path.dirname(sys.argv[0]),
                                x264_path))


    start = pass1time = datetime.now()

    print("")
    print("Encode is starting...")
    print("Current time: " + str(start))
    print("")

    with open(outFile + ".log", "w") as log:
        if passN <= 1:
            if os.path.isfile(statsFile):
                os.remove(statsFile)
            cmdline = '{0} {1} {2} {3} {4} {{extra_args}} "{{inFile}}"' \
                      .format(x264_exec,
                              common_params,
                              common_params_pass1,
                              params["common"],
                              params["pass1"])
            cmdline = cmdline.format(**locals())

            print("First pass command line: ", cmdline, file=log)
            print("", file=log)

            p =  subprocess.Popen(cmdline,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.STDOUT,
                                  universal_newlines = True)
            for l in p.stdout:
                log.write(l)
                if l.startswith("["):
                    print(l.strip().ljust(78),end='\r')
                else:
                    print(l,end='')
                    if bitrate == -1:
                        m = re.search("kb\/s\:([0-9]+)",l)
                        if m:
                            bitrate = int(m.group(1))
                            with open(outFile + ".bitrate.txt","w") as f:
                                f.write(str(bitrate))
            print("")
            print("")
            pass1time = datetime.now()
            print("1st pass completed.")
            print("Current time: " + str(pass1time))
            print("Time elapsed: " + str(pass1time - start))
            print("")
            print("")

            log.write("\n")
            log.write("---------------------------------------------\n")
            log.write("\n")

        if bitrate == -1:
            if os.path.isfile(outFile + ".bitrate.txt"):
                with open(outFile + ".bitrate.txt","r") as f:
                    bitrate = int(f.read().strip())
            else:
                print("Bitrate is unknown!")
                return

        bitrate = int(bitrate * opt.bitrate_ratio)
        
        cmdline = '{0} {1} {2} {3} {4} {{extra_args}} "{{inFile}}"' \
                  .format(x264_exec,
                          common_params,
                          common_params_pass2,
                          params["common"],
                          params["pass2"])
        cmdline = cmdline.format(**locals())

        print("Second pass command line: ", cmdline, file=log)
        print("", file=log)

        
        p =  subprocess.Popen(cmdline,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.STDOUT,
                                  universal_newlines = True)

                
        for l in p.stdout:
            log.write(l)
            if l.startswith("["):
                print(l.strip().ljust(78),end='\r')
            else:
                print(l,end='')

        print("")
        print("")
        pass2time = datetime.now()
        print("2nd pass completed.")
        print("Current time: " + str(pass2time))
        print("Time elapsed: " + str(pass2time - pass1time))
        print("Total: " + str(pass2time - start))
        print("")
        print("")

if __name__ == "__main__":
    try:
        doEncode()
    except KeyboardInterrupt:
        print("")
