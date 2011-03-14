import sys

if len(sys.argv) > 1 and sys.argv[1].lower() == "update":
    from impls.update import update
    update()
else:
    from impls.encx264_impl import encode
    encode()

    
