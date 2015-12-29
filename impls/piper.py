#!/usr/bin/env python3

import sys
import subprocess


def main(argv):
    if argv[0] == "--del-last-arg":
        argv = argv[1:-1]

    try:
        splitter_index = argv.index("----")
    except ValueError:
        print("No splitter found.")
        sys.exit(1)

    cmd1 = argv[:splitter_index]
    cmd2 = argv[splitter_index+1:]
    if not cmd1:
        print("Command 1 is empty")
        sys.exit(1)

    if not cmd2:
        print("Command 2 is empty")
        sys.exit(1)

    print("Command 1:", cmd1)
    print("Command 2:", cmd2)

    p1 = None
    p2 = None
    try:
        p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(cmd2, stdin=p1.stdout)
        p1.stdout.close()
        p1.stdout = None
        p1.wait()
        p2.wait()
        sys.exit(p2.returncode)
    finally:
        try:
            if p1 and p1.poll():
                print("Process 1 is still alive, killing...")
                p1.kill()
        except Exception:
            pass

        try:
            if p2 and p2.poll():
                print("Process 2 is still alive, killing...")
                p2.kill()
        except Exception:
            pass


def piper_subcommand():
    main(sys.argv[2:])


if __name__ == "__main__":
    main(sys.argv[1:])
