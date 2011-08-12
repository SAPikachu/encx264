from collections import UserDict
import os
import json
import sys
from .utils import gen_cmd_line, AttrDict
from .encx264_impl import encode, get_params
from threading import Thread, Lock, Event
from uuid import uuid4
from time import sleep
from .console import clear as console_clear, colors as c_colors
from .console import get_cursor_position, set_cursor_position, \
                     get_text_color, set_text_color, \
                     clear_line_remaining
from io import StringIO
import subprocess

task_states = AttrDict({(k, k) for k in ["waiting",
                                         "running",
                                         "completed",
                                         "error"]})

state_colors = {
    "": c_colors.FOREGROUND_RED |
        c_colors.FOREGROUND_INTENSITY, # error color
    task_states.waiting: c_colors.FOREGROUND_GREY,
    task_states.running: c_colors.FOREGROUND_GREY |
                         c_colors.FOREGROUND_INTENSITY,
    task_states.completed: c_colors.FOREGROUND_GREEN,
}

# hack for fixing http://bugs.python.org/issue12739
popen_lock = Lock()

def popen_hook(*args, **kwargs):
    with popen_lock:
        return subprocess.Popen(*args, **kwargs)

class Task(AttrDict):
    def __init__(self,
                 params=None,
                 slot=1,
                 depends=None,
                 working_dir=None,
                 state=task_states.waiting,
                 data=None):
        self.id = str(uuid4())
        self.params = params
        self.slot = slot
        self.state = state
        self.depends = depends
        self.working_dir = working_dir
        if data:
            self.update(data)

tasks = []


default_task_file = os.getenv("ENCX264_TASK_FILE") or \
                    os.path.expandvars("%TEMP%\\.encx264_task")

def task_add_internal(params, slot=1, depends=None):
    t = Task(params, slot=slot, depends=depends, working_dir=os.path.abspath("."))
    tasks.append(t)
    return t
    
def task_add(params):
    p = get_params(params)
    if not p:
        # invalid parameter
        return 1

    if "pass2" in p.params:
        if "--pass" not in params:
            t1 = task_add_internal(["--1pass-only"] + params,
                                   p.params.get("slot_pass1", 1))
            task_add_internal(["--pass", "2", "--append-log"] + params,
                              p.params.get("slot_pass2", 2),
                              depends=t1.id)
        else:
            task_add_internal(params,
                              p.params.get(
                                  "slot_pass" + str(p.passN),
                                  p.passN))
    else:
        task_add_internal(params, p.params.get("slot", 2))

def task_remove(ids):
    ids = list(ids)
    ids.sort(reverse=True)
    for id in ids:
        del tasks[id]
        
def task_reset(ids):
    for id in ids:
        tasks[id].state = task_states.waiting

def task_list(print=print):
    old_color = get_text_color()
    for i in range(len(tasks)):
        task = tasks[i]
        color = task.state in state_colors and \
                state_colors[task.state] or \
                state_colors[""]
        set_text_color(color)
        print("[{0}] {1}".format(i,
                                 gen_cmd_line(task.params)))
        
        set_text_color(c_colors.FOREGROUND_INTENSITY)
        print("    (", end='')
        set_text_color(color)
        print(task.state, end='')
        set_text_color(c_colors.FOREGROUND_INTENSITY)
        print(") slot={1},dir={2}" \
              .format(task.state, task.slot, task.working_dir))
        
    set_text_color(old_color)

def task_clear():
    tasks[:] = []

def get_task_by_uuid(id):
    l = [t for t in tasks if t.id == id]
    if l:
        return l[0]

def padded_print(*args, **kwargs):
    if kwargs.get("end", "\n") == '':
        print(*args, **kwargs)
        return
        
    kwargs["end"] = ""
    print(*args, **kwargs)
    clear_line_remaining()

def print_status(threads, state):
    if "console_cleared" not in state:
        console_clear()
        state["console_cleared"] = True
        
    last_pos = get_cursor_position()
    set_cursor_position(0, 0)
        
    task_list(padded_print)

    running_tasks_title_printed = False
    for i in range(len(threads)):
        msg = threads[i][1].msg
        if msg:
            if not running_tasks_title_printed:
                padded_print("")
                padded_print("Running tasks:")
                running_tasks_title_printed = True
                
            padded_print(msg)

    current_pos = get_cursor_position()
    for i in range(last_pos[1] - current_pos[1]):
        padded_print("")

    set_cursor_position(*current_pos)


def task_run_impl(self, global_state, tasks):
    task_tag = ' '
    def print_hook(*args, **kwargs):
        if "file" in kwargs:
            print(*args, **kwargs)
        else:
            line = ' '.join(args).strip()
            if line:
                self.msg = '[{0}] {1}'.format(task_tag, line)

            if line.startswith("aborted at input"):
                # x264's return code will be 0,
                # so we must manually raise an error
                raise KeyboardInterrupt()

    def int_handler():
        # re-raise so that the outer handler can catch it
        raise KeyboardInterrupt()

    try:
        while True:
            current_task = None
            if global_state.exit_code is not None:
                global_state.event.set()
                return
            
            with global_state.lock:
                if not any([t.state == task_states.waiting for t in tasks]):
                    self.msg = ""
                    global_state.event.set()
                    return

                for i in range(1, global_state.slots + 1):
                    avail_tasks = \
                        [x for x in tasks
                         if x.slot == i and x.state == task_states.waiting]
                    
                    for t in avail_tasks:
                        if t.depends:
                            dep = get_task_by_uuid(t.depends)
                            if not dep:
                                t.state = "error: dependency not found"
                                continue

                            if dep.state.startswith("error"):
                                t.state = dep.state
                                global_state.event.set()
                                continue

                            if dep.state != task_states.completed:
                                continue

                        current_task = t
                        t.state = task_states.running
                        global_state.slots -= i
                        break

                    if current_task:
                        break

            task_save()
            if not current_task:
                self.msg = ""
                global_state.event.wait()
                with global_state.lock:
                    global_state.event.clear()
                
                continue

            task_tag = str(tasks.index(current_task))
            ret = encode(current_task.params,
                         print_hook,
                         working_dir=current_task.working_dir,
                         int_handler=int_handler,
                         Popen=popen_hook)

            if ret == -1073741510:
                # STATUS_CONTROL_C_EXIT
                raise KeyboardInterrupt
            
            if ret:
                current_task.state = "error: code {0}, {1}" \
                                     .format(ret, self.msg)
            else:
                current_task.state = task_states.completed

            self.msg = ''

            task_save()
            with global_state.lock:
                global_state.slots += current_task.slot
                global_state.event.set()
                
    except KeyboardInterrupt:
        task_save()
        print("Interrupted by user.")
        global_state.exit_code = 1
        return
    except:
        self.msg = str(sys.exc_info())
        raise
        
    
def task_run(max_slots=2, refresh_rate=1):
    for t in tasks:
        if t.state == task_states.running:
            t.state = task_states.waiting

    state = AttrDict()
    state.lock = Lock()
    state.event = Event()
    state.slots = max_slots
    state.exit_code = None

    threads = []

    try:
        for i in range(max_slots):
            thread_state = AttrDict({"id": i, "msg": ""})
            thread = Thread(target=task_run_impl,
                            args=(thread_state, state, tasks))
            thread.start()
            threads.append((thread, thread_state))

        while any([t[0].is_alive() for t in threads]):
            print_status(threads, state)
            if state.exit_code is not None:
                state.event.set()
                task_save()
                sys.exit(state.exit_code)
                
            sleep(refresh_rate)

        print_status(threads, state)
        print("")
        print("All tasks are completed")
            
    except KeyboardInterrupt:
        task_save()
        print("Interrupted by user.")
        state.exit_code = 1
        state.event.set()
        sys.exit(1)

def task_save(task_file=default_task_file):
    if tasks:
        with open(task_file, "w") as f:
            json.dump(tasks, f)
    else:
        if os.path.isfile(task_file):
            os.remove(task_file)

def task_load(task_file=default_task_file):
    global tasks
    if os.path.isfile(task_file):
        try:
            with open(task_file, "r") as f:
                tasks = json.load(f, object_hook=lambda d:Task(data=d))
        except ValueError:
            print("Warning: The task database is corrupted")
            tasks = []
    else:
        tasks = []

def task_help():
    print("Usage:")
    print(os.path.split(sys.argv[0])[-1], "!task <command> <arguments>")
    print("")
    print("Commands:")
    print("list")
    print("add <normal encode parameters>")
    print("remove <one or more task IDs>")
    print("clear")
    print("reset <one or more task IDs>")
    print("reset_all")
    print("clear")
    print("run [max slots] [output refresh rate]")

def task_do_command():
    if len(sys.argv) < 3:
        task_help()
        return
    
    command = sys.argv[2]
    args = sys.argv[3:]
    commands = {
        "help": task_help,
        "list": task_list,
        "add": lambda: task_add(args),
        "remove": lambda: task_remove([int(x) for x in args]),
        "clear": task_clear,
        "reset": lambda: task_reset([int(x) for x in args]),
        "reset_all": lambda: task_reset(range(len(tasks))),
        "run": lambda: eval('task_run(' + ','.join(args) + ')')
    }
    if command not in commands:
        print("Invalid command", command)
        task_help()
        return 1

    task_load()
    ret = commands[command]()
    task_save()

    sys.exit(ret)
