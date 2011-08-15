from optparse import OptionParser
import os
from datetime import datetime
import re
import subprocess
import sys
from .utils import gen_cmd_line, AttrDict


__all__ = ["encode", "parse_encode_result_line"]

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

    return p.returncode

def parse_args(args=None):
    args = args or sys.argv[1:]
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

    args = [x.lower() if x.startswith("-") else x for x in args]
    (opt, extra_args) = parser.parse_args(args)
    return (opt, extra_args)

def get_params(raw_args=None, print=print, working_dir=None):
    (opt, args) = parse_args(raw_args)
    
    target = opt.target or args.pop(0)
    
    if target not in encode_targets:
        print("Invalid target {0}!".format(target))
        return None
    
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

    extra_args = gen_cmd_line(args)
    
    if opt.bitrate_ratio == -1:
        opt.bitrate_ratio = params.get("bitrate_ratio", 1.0)

    if inFile is None:
        print("You have not specified input file!")
        return None

    if not outFile:
        outFile = os.path.splitext(inFile)[0] + ".mp4"

    inFile_2pass = opt.inFile_2pass or inFile 

    if tc is None:
        tc = os.path.join(os.path.dirname(inFile), "timecode.txt")

    if working_dir:
        inFile = os.path.abspath(os.path.join(working_dir, inFile))
        inFile_2pass = os.path.abspath(os.path.join(working_dir, inFile_2pass))
        outFile = os.path.abspath(os.path.join(working_dir, outFile))
        
        if tc:
            tc = os.path.abspath(os.path.join(working_dir, tc))

    if not os.path.isfile(inFile):
        print("{0} doesn't exist!".format(inFile))
        return None

    if not os.path.isfile(inFile_2pass):
        print("{0} doesn't exist!".format(inFile_2pass))
        return None

    if tc:
        if not os.path.isfile(tc):
            print("Timecode file {0} doesn't exist!".format(tc))
            return None

        tc = ' --tcfile-in "{0}"'.format(tc)

    if not sar:
        if not "default_sar" in params:
            print("sar must be specified!")
            return None
        sar = params["default_sar"]

    statsFile = outFile + ".x264_stats"

    priority = opt.priority or default_priority
    priority = priority.lower()

    if priority not in priority_values:
        print("Invalid priority:", priority)
        return None

    priority_value = priority_values[priority]

    x264_exec = "x264_path" in params and params["x264_path"] or x264_path

    script_dir = sys.path[0]
    if not os.path.isdir(script_dir):
        # frozen
        script_dir = os.path.dirname(script_dir)
        
    x264_exec = os.path.abspath(os.path.join(
                                script_dir,
                                x264_exec))

    if not os.path.isfile(x264_exec):
        print("Can't find x264 executable", x264_exec)
        return None

    x264_exec = '"{0}"'.format(x264_exec)

    ret = AttrDict(locals())
    ret.common_params = common_params
    ret.common_params_pass1 = common_params_pass1
    ret.common_params_pass2 = common_params_pass2

    return ret

def parse_encode_result_line(line):
    pat = r"\s*encoded \d+ frames, ([\d\.]+) fps, ([\d\.]+) kb/s\s*"
    m = re.match(pat, line)
    if not m:
        return None

    return {
        "fps": float(m.group(1)),
        "bitrate": int(float(m.group(2))),
    }

def encode_impl(raw_args=None,
                print=print,
                working_dir=None,
                Popen=subprocess.Popen):
    args = get_params(raw_args, print, working_dir)

    if not args:
        return 1

    start = pass1time = datetime.now()

    print("")
    print("Encode is starting...")
    print("Current time: " + str(start))
    print("")

    with open(args.outFile + ".log",
              args.append_log and "a" or "w",
              buffering=1) as log:
        if args.passN <= 1:
            if os.path.isfile(args.statsFile):
                os.remove(args.statsFile)
                
            cmdline = ('{x264_exec} {common_params} {common_params_pass1} ' + \
                       '{params[common]} {params[pass1]} ' + \
                       '{extra_args} "{inFile}"') \
                      .format(**args).format(**args)
            # format 2 times to substitute parameters in target

            print("First pass command line:", cmdline, file=log)
            print("", file=log)
            print("First pass command line:", cmdline)
            print("")

            p =  Popen(cmdline,
                      stdout = subprocess.PIPE,
                      stderr = subprocess.STDOUT,
                      cwd = working_dir,
                      creationflags = args.priority_value,
                      universal_newlines = True)

            try:
                for l in p.stdout:
                    if l.startswith("["):
                        if log_progress:
                            log.write(l)
                            
                        print(l.strip().ljust(78),end='\r')
                    else:
                        log.write(l)
                        print(l,end='')
                        if args.bitrate == -1:
                            m = parse_encode_result_line(l)
                            if m:
                                args.bitrate = m["bitrate"]
                                with open(args.outFile + ".bitrate.txt","w") \
                                     as f:
                                    f.write(str(args.bitrate))
            except:
                p.kill()
                raise

            print("")
            print("")
            return_code = check_return_code(p)
            if return_code:
                return return_code

            pass1time = datetime.now()
            print("1st pass completed.")
            print("Current time: " + str(pass1time))
            print("Time elapsed: " + str(pass1time - start))
            print("")
            print("")

        if args.p1_only:
            return

        if "pass2" not in args.params:
            print("Encode completed.")
        else:
            log.write("\n")
            log.write("---------------------------------------------\n")
            log.write("\n")
            if args.bitrate == -1:
                if os.path.isfile(args.outFile + ".bitrate.txt"):
                    with open(args.outFile + ".bitrate.txt","r") as f:
                        args.bitrate = int(f.read().strip())
                else:
                    print("Bitrate is unknown!")
                    return 1

            args.bitrate = int(args.bitrate * args.opt.bitrate_ratio)
            
            cmdline = ('{x264_exec} {common_params} {common_params_pass2} ' + \
                       '{params[common]} {params[pass2]} ' + \
                       '{extra_args} "{inFile_2pass}"') \
                      .format(**args).format(**args)

            print("Second pass command line:", cmdline, file=log)
            print("", file=log)
            print("Second pass command line:", cmdline)
            print("")

            
            p =  Popen(cmdline,
                      stdout = subprocess.PIPE,
                      stderr = subprocess.STDOUT,
                      cwd = working_dir,
                      creationflags = args.priority_value,
                      universal_newlines = True)

            try:
                for l in p.stdout:
                    if l.startswith("["):
                        if log_progress:
                            log.write(l)
                        print(l.strip().ljust(78),end='\r')
                    else:
                        log.write(l)
                        print(l,end='')
            except:
                p.kill()
                raise

            print("")
            print("")
            return_code = check_return_code(p)
            if return_code:
                return return_code
            
            pass2time = datetime.now()
            print("2nd pass completed.")
            print("Current time: " + str(pass2time))
            print("Time elapsed: " + str(pass2time - pass1time))
            print("Total: " + str(pass2time - start))
            print("")
            print("")

def encode(args=None,
           print=print,
           working_dir=None,
           int_handler=None,
           Popen=subprocess.Popen):
    try:
        return encode_impl(args, print, working_dir=working_dir, Popen=Popen)
    except KeyboardInterrupt:
        print("")
        print("")
        print("Encode interrupted by user.")
        if int_handler:
            return int_handler()
        
        return 1
        
if __name__ == "__main__":
    encode()
