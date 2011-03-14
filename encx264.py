import sys
import os

# support build script
sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "pyd"))

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

    
