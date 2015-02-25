import re
from subprocess import Popen, PIPE, STDOUT

class X264Error(Exception):
    def __init__(self, return_code):
        self.return_code = return_code

    def __str__(self):
        return "x264 exited with return code 0x" + hex(self.return_code)

class X264ParamItem:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

class X264Params:
    def __init__(
        self, 
        x264_path, 
        input_file, 
        working_dir,
        creation_flags=0,
        command_params=[]):

        self.x264_path = x264_path
        self.input_file = input_file
        self.working_dir = working_dir
        self.creation_flags = creation_flags
        self.command_params = []
        self.append_params(command_params)

    def build_command_line(self):
        result = []

        assert self.x264_path
        result.append(self.x264_path)

        assert self.input_file
        result.append(self.input_file)

        used_params = dict()

        # ensure parameters are not duplicated
        for param in reversed(self.command_params):
            if param.name in used_params:
                continue

            used_params[param.name] = param.value
            result.append(param.name)
            if param.value:
                result.append(param.value)

        return result

    def build_command_line_str(self):
        def convert_item(item):
            if " " in item:
                return '"{}"'.format(item)
            else:
                return item

        return [convert_item(x) for x in \
                sum([[y.name, y.value] for y in self.command_params]) \
                if x]


    def append_params_str(self, param_str):
        self.append_params_str_list(split_params(param_str))

    def append_params_str_list(self, str_list):
        assert get_list_type(str_list) is str

        while str_list:
            name = str_list.pop(0)
            if name[0] != "-":
                raise ValueError("Invalid parameter: " + name)

            value = None
            if not str_list[0].startswith("-"):
                value = str_list.pop(0)

            self.command_params.append(X264ParamItem(name, value))


    def append_params_item(self, item_list):
        assert get_list_type(item_list) is X264ParamItem

        self.command_params += item_list

    def append_params(self, params):
        if isinstance(params, str):
            self.append_params_str(params)
        elif isinstance(params, list):
            if len(params) == 0:
                return

            list_type = get_list_type(params)
            if list_type is str:
                self.append_params_str_list(params)
            elif list_type is X264ParamItem:
                self.append_params_item(params)

        raise TypeError("Invalid parameter type.")

def get_list_type(l):
    item_type = l[0].__class__
    for item in l:
        if not isinstance(item, item_type):
            return None

    return item_type


def split_params(param_str):
    return [m.group(0).strip().strip('"') for m in
            re.finditer(r'\s*([^" ].*?|".*?")(\s|$)', param_str, re.I)]

def try_parse_encode_result_line(line):
    pat = r"\s*encoded \d+ frames,.*"
    m = re.match(pat, line)
    if not m:
        return None

    fps = re.search(r",\s*([\d\.]+)\s*fps", line).group(1)
    bitrate = re.search(r",\s*([\d\.]+)\s*kb/s", line).group(1)

    return {
        "fps": float(fps),
        "bitrate": int(float(bitrate)),
    }

def print_output(msg, line_type, print=print):
    if line_type == "normal":
        end = "\n"
    elif line_type == "progress":
        end = "\r"
    else:
        raise ValueError("Invalid line type.")

    print(msg, end=end)


def check_return_code(p):
    p.communicate()
    if p.returncode != 0:
        raise X264Error(p.returncode)

def run_x264(
    params, 
    print_output=print_output,
    Popen=Popen):
    assert isinstance(params, X264Params)

    result = None

    with Popen(params.build_command_line(),
        stdout=PIPE,
        stderr=STDOUT,
        cwd=params.working_dir,
        creationflags=params.creation_flags,
        universal_newlines=True) as p:

        try:
            for l in p.stdout:
                l = l.rstrip()
                if l.startswith("["):
                    print_output(l.ljust(78), "progress")
                else:
                    if not result:
                        result = try_parse_encode_result_line(l)

                    print_output(l, "normal")

        except:
            try:
                p.kill()
            except:
                pass

            raise

        check_return_code(p)

        if not result:
            raise ValueError("Can't read encoding information from x264 output")

