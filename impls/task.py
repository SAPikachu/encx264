from collections import UserDict
import os
import json
import sys
from .utils import gen_cmd_line, AttrDict
from .encx264_impl import encode, get_params, parse_encode_result_line
from threading import Thread, Lock, Event
from uuid import uuid4
from time import sleep
from .console import clear as console_clear, colors as c_colors
from .console import get_cursor_position, set_cursor_position, \
                     get_text_color, set_text_color, \
                     clear_line_remaining, set_title
from io import StringIO
import subprocess

__all__ = ["task_do_command"]

task_states = AttrDict({(k, k) for k in ["waiting",
                                         "running",
                                         "completed",
                                         "error"]})

state_colors = {
    task_states.error: c_colors.FOREGROUND_RED |
                       c_colors.FOREGROUND_INTENSITY,
    task_states.waiting: c_colors.FOREGROUND_GREY,
    task_states.running: c_colors.FOREGROUND_GREY |
                         c_colors.FOREGROUND_INTENSITY,
    task_states.completed: c_colors.FOREGROUND_GREEN,
}


popen_lock = Lock()

def popen_hook(*args, **kwargs):
    creation_flags = kwargs.get("creationflags", 0)
    # DETACHED_PROCESS, prevent x264 from changing console title
    creation_flags |= 0x8
    kwargs["creationflags"] = creation_flags

    # hack for fixing http://bugs.python.org/issue12739
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
        self.state_message = ''
        if data:
            self.update(data)

    def set_state(self, state, message=''):
        self.state = state
        self.state_message = message

    def get_state_display(self):
        if self.state_message:
            return '{0}: {1}'.format(self.state, self.state_message)
        else:
            return self.state

class MainThreadExiting(Exception):
    pass

tasks = []

task_save_lock = Lock()

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
        tasks[id].set_state(task_states.waiting)

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
        print(task.get_state_display(), end='')
        set_text_color(c_colors.FOREGROUND_INTENSITY)
        print(") slot={slot},dir={dir}" \
              .format(slot=task.slot, 
                      dir=task.working_dir))
        
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

    title_msgs = []

    running_tasks_title_printed = False
    for i in range(len(threads)):
        thread_obj = threads[i][1]
        msg = thread_obj.msg
        if msg:
            if not running_tasks_title_printed:
                padded_print("")
                padded_print("Running tasks:")
                running_tasks_title_printed = True
                
            padded_print(msg)

        if thread_obj.title_msg:
            title_msgs.append(thread_obj.title_msg)

    current_pos = get_cursor_position()
    for i in range(last_pos[1] - current_pos[1]):
        padded_print("")

    set_cursor_position(*current_pos)

    completed = len([t for t in tasks if t.state == task_states.completed])
    new_title = "ENCX264 - {0} / {1} completed" \
                .format(completed, len(tasks))

    if title_msgs:
        new_title += ' - ' + ' '.join(title_msgs)
    set_title(new_title)

def task_run_impl(self, global_state, tasks):
    task_tag = ' '
    def check_global_exit_code():
        if global_state.exit_code is not None:
            global_state.event.set()
            raise MainThreadExiting()
            
    def print_hook(*args, **kwargs):
        check_global_exit_code()
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

            if line.startswith("["):
                percentage = line[1:line.index(']')]
                self.title_msg = '[{0}] {1}'.format(task_tag, percentage)
            else:
                self.title_msg = ''

            result = parse_encode_result_line(line)
            if result:
                self.encode_result = result

    def int_handler():
        # re-raise so that the outer handler can catch it
        raise KeyboardInterrupt()

    try:
        while True:
            current_task = None
            check_global_exit_code()
            
            with global_state.lock:
                if not any([t.state == task_states.waiting for t in tasks]):
                    self.msg = ""
                    global_state.event.set()
                    return

                if global_state.running_tasks > 0:
                    avail_slots = global_state.slots
                else:
                    # make sure at least 1 task can be run
                    avail_slots = max([t.slot for t in tasks])

                for i in range(1, avail_slots + 1):
                    avail_tasks = \
                        [x for x in tasks
                         if x.slot == i and x.state == task_states.waiting]
                    
                    for t in avail_tasks:
                        if t.depends:
                            dep = get_task_by_uuid(t.depends)
                            if not dep:
                                t.set_state(task_states.error, 
                                            "dependency not found")
                                continue

                            if dep.state == task_states.error:
                                t.set_state(dep.state, dep.state_message)
                                global_state.event.set()
                                continue

                            if dep.state != task_states.completed:
                                continue

                        current_task = t
                        t.set_state(task_states.running)
                        global_state.slots -= i
                        global_state.running_tasks += 1
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
                current_task.set_state(
                        task_states.error, 
                        "code {0}, {1}".format(ret, self.msg))
            else:
                current_task.set_state(task_states.completed)
                if self.encode_result:
                    current_task.state_message = \
                        "{fps} fps, {bitrate} kbps" \
                            .format(**self.encode_result)
                    self.encode_result = None

            self.msg = ''

            task_save()
            with global_state.lock:
                global_state.slots += current_task.slot
                global_state.running_tasks -= 1
                global_state.event.set()
                
    except KeyboardInterrupt:
        task_save()
        print("Interrupted by user.")
        global_state.exit_code = 1
        return
    except MainThreadExiting:
        task_save()
        return
    except Exception as e:
        self.msg = str(e)
        raise
        
    
def task_run(max_slots=2, refresh_rate=1):
    for t in tasks:
        if t.state == task_states.running:
            t.set_state(task_states.waiting)

    state = AttrDict()
    state.lock = Lock()
    state.event = Event()
    state.slots = max_slots
    state.exit_code = None
    state.running_tasks = 0

    threads = []

    try:
        for i in range(max_slots):
            thread_state = AttrDict({
                "id": i, "msg": "", 
                "title_msg": "",
            })
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
    with task_save_lock:
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
