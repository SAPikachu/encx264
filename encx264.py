import sys
import os

# support build script
sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "pyd"))
if not sys.argv[0]:
    entry_point = sys.path[0]
    if (not entry_point.lower().endswith(".py")) and \
       (not entry_point.lower().endswith(".exe")):
        entry_point = os.path.join(entry_point, "encx264.py")
    sys.argv[0] = entry_point
    
if len(sys.argv) > 1 and sys.argv[1][0] == "!":
    from impls.functions import functions
    name = sys.argv[1][1:]
    if name not in functions:
        print("Invalid function", name)
        sys.exit(1)

    functions[name]()
else:
    from impls.encx264_impl import encode
    encode()

    
