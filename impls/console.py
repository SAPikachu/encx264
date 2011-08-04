from ctypes import windll, Structure, c_short, c_ushort, c_int, byref

SHORT = c_short
WORD = c_ushort
INT = c_int

class COORD(Structure):
  """struct in wincon.h."""
  _fields_ = [
    ("X", SHORT),
    ("Y", SHORT)]

class SMALL_RECT(Structure):
  """struct in wincon.h."""
  _fields_ = [
    ("Left", SHORT),
    ("Top", SHORT),
    ("Right", SHORT),
    ("Bottom", SHORT)]

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
  """struct in wincon.h."""
  _fields_ = [
    ("dwSize", COORD),
    ("dwCursorPosition", COORD),
    ("wAttributes", WORD),
    ("srWindow", SMALL_RECT),
    ("dwMaximumWindowSize", COORD)]

# winbase.h
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

# wincon.h
FOREGROUND_BLACK     = 0x0000
FOREGROUND_BLUE      = 0x0001
FOREGROUND_GREEN     = 0x0002
FOREGROUND_CYAN      = 0x0003
FOREGROUND_RED       = 0x0004
FOREGROUND_MAGENTA   = 0x0005
FOREGROUND_YELLOW    = 0x0006
FOREGROUND_GREY      = 0x0007
FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

BACKGROUND_BLACK     = 0x0000
BACKGROUND_BLUE      = 0x0010
BACKGROUND_GREEN     = 0x0020
BACKGROUND_CYAN      = 0x0030
BACKGROUND_RED       = 0x0040
BACKGROUND_MAGENTA   = 0x0050
BACKGROUND_YELLOW    = 0x0060
BACKGROUND_GREY      = 0x0070
BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

stdout_handle = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
FillConsoleOutputCharacterA = windll.kernel32.FillConsoleOutputCharacterA
FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition

def clear():
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    GetConsoleScreenBufferInfo(stdout_handle, byref(csbi))
    top_left = COORD(0, 0)
    written = INT()
    FillConsoleOutputCharacterA(stdout_handle,
                                0x20,
                                csbi.dwSize.X * csbi.dwSize.Y,
                                top_left,
                                byref(written))
    FillConsoleOutputAttribute(stdout_handle,
                                FOREGROUND_GREY,
                                csbi.dwSize.X * csbi.dwSize.Y,
                                top_left,
                                byref(written))
    SetConsoleCursorPosition(stdout_handle, top_left)

    
  
