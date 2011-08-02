from optparse import OptionParser
import os
from datetime import datetime
import re
import subprocess
import sys

__all__ = ["encode"]

from .encx264_defaults import *

try:
    from encx264_targets import *
except ImportError:
    print("Can't find encx264_targets.py.")
    print("Please create one from encx264_targets.py.sample.")
    sys.exit(1)

priority_values = {
    "idle": 0x40,
    "below_normal": 0x4000,
    "normal": 0x20,
    "above_normal": 0x8000,
    "high": 0x80,
}

def check_return_code(p):
    p.communicate()
    if p.returncode != 0:
        print("x264 exited with return code", p.returncode)
        sys.exit(p.returncode)

def encode_impl():
    parser = OptionParser()
    parser.add_option("--target")
    parser.add_option("--infile", dest="inFile")
    parser.add_option("--outfile", dest="outFile")
    parser.add_option("--crf", type="int")
    parser.add_option("--pass", type="int", default=1, dest="passN")
    parser.add_option("--bitrate", type="int", default=-1)
    parser.add_option("--sar")
    parser.add_option("--tc", default=None)
    parser.add_option("--ref", type="int")
    parser.add_option("--infile-2pass", dest="inFile_2pass")
    parser.add_option("--1pass-only", dest="p1_only", action="store_true",
                      default=False)
    parser.add_option("--append-log", dest="append_log", action="store_true",
                      default=False)
    parser.add_option("--bitrate-ratio", type="float", default=-1,
                      dest="bitrate_ratio")
    parser.add_option("--priority")

    if "--" in sys.argv:
        extra_args = ' '.join([(" " in x) and '"{0}"'.format(x) or x \
                     for x in sys.argv[sys.argv.index("--")+1:]])
        sys.argv = sys.argv[:sys.argv.index("--")]
    else:
        extra_args = ""

    sys.argv = [x.lower() if x.startswith("-") else x for x in sys.argv]

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
    p1_only = opt.p1_only
    append_log = opt.append_log

    if opt.bitrate_ratio == -1:
        opt.bitrate_ratio = params.get("bitrate_ratio", 1.0)

    if inFile is None:
        print("You have not specified input file!")
        return

    if not os.path.isfile(inFile):
        print("{0} doesn't exist!".format(inFile))
        return

    inFile_2pass = opt.inFile_2pass or inFile 

    if not os.path.isfile(inFile_2pass):
        print("{0} doesn't exist!".format(inFile_2pass))
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

    priority = opt.priority or default_priority
    priority = priority.lower()

    if priority not in priority_values:
        print("Invalid priority:", priority)
        return

    priority_value = priority_values[priority]

    x264_exec = "x264_path" in params and params["x264_path"] or x264_path

    x264_exec = '"{0}"'.format(os.path.join(
                                os.path.dirname(sys.argv[0]),
                                x264_exec))


    start = pass1time = datetime.now()

    print("")
    print("Encode is starting...")
    print("Current time: " + str(start))
    print("")

    with open(outFile + ".log", append_log and "a" or "w") as log:
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
            print("First pass command line: ", cmdline)
            print("")

            p =  subprocess.Popen(cmdline,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.STDOUT,
                                  creationflags = priority_value,
                                  universal_newlines = True)
            for l in p.stdout:
                if l.startswith("["):
                    if log_progress:
                        log.write(l)
                    print(l.strip().ljust(78),end='\r')
                else:
                    log.write(l)
                    print(l,end='')
                    if bitrate == -1:
                        m = re.search("kb\/s\:([0-9]+)",l)
                        if m:
                            bitrate = int(m.group(1))
                            with open(outFile + ".bitrate.txt","w") as f:
                                f.write(str(bitrate))

            print("")
            print("")
            check_return_code(p)

            pass1time = datetime.now()
            print("1st pass completed.")
            print("Current time: " + str(pass1time))
            print("Time elapsed: " + str(pass1time - start))
            print("")
            print("")

        if p1_only:
            return

        if "pass2" not in params:
            print("Encode completed.")
        else:
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
            
            cmdline = '{0} {1} {2} {3} {4} {{extra_args}} "{{inFile_2pass}}"' \
                      .format(x264_exec,
                              common_params,
                              common_params_pass2,
                              params["common"],
                              params["pass2"])
            cmdline = cmdline.format(**locals())

            print("Second pass command line: ", cmdline, file=log)
            print("", file=log)
            print("Second pass command line: ", cmdline)
            print("")

            
            p =  subprocess.Popen(cmdline,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.STDOUT,
                                      creationflags = priority_value,
                                      universal_newlines = True)

                    
            for l in p.stdout:
                if l.startswith("["):
                    if log_progress:
                        log.write(l)
                    print(l.strip().ljust(78),end='\r')
                else:
                    log.write(l)
                    print(l,end='')

            print("")
            print("")
            check_return_code(p)
            pass2time = datetime.now()
            print("2nd pass completed.")
            print("Current time: " + str(pass2time))
            print("Time elapsed: " + str(pass2time - pass1time))
            print("Total: " + str(pass2time - start))
            print("")
            print("")

def encode():
    try:
        encode_impl()
    except KeyboardInterrupt:
        print("")
        print("")
        print("Encode interrupted by user.")
        
if __name__ == "__main__":
    encode()
