import locale
import sys

if hasattr(sys, "frozen") and sys.frozen:
    # workaround for a MSVC CRT bug, which causes console output very slow
    locale.setlocale(locale.LC_CTYPE, "C")
