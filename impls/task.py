from collections import UserDict
import os
import json
import sys
from .utils import gen_cmd_line, AttrDict
from .encx264_impl import encode, get_params
from threading import Thread, Lock, Event
from uuid import uuid4
from time import sleep

task_states = AttrDict({(k, k) for k in ["waiting",
                                         "running",
                                         "completed",
                                         "error"]})

class Task(AttrDict):
    def __init__(self,
                 params=None,
                 slot=1,
                 depends=None,
                 state=task_states.waiting,
                 data=None):
        self.id = str(uuid4())
        self.params = params
        self.slot = slot
        self.state = state
        self.depends = depends
        if data:
            self.update(data)

tasks = []


default_task_file = os.path.expandvars("%TEMP%\\.encx264_task")

def task_add_internal(params, slot=1, depends=None):
    t = Task(params, slot=slot, depends=depends)
    tasks.append(t)
    return t
    
def task_add(params):
    p = get_params(params)
    if not p:
        # invalid parameter
        return 1

    if "pass2" in p.params:
        t1 = task_add_internal(params + ["--1pass-only"], 1)
        task_add_internal(params + ["--pass", "2", "--append-log"],
                          2,
                          depends=t1.id)
    else:
        task_add_internal(params, 2)

def task_remove(ids):
    ids = list(ids)
    ids.sort(reverse=True)
    for id in ids:
        del tasks[id]
        
def task_reset(ids):
    for id in ids:
        tasks[id].state = task_states.waiting

def task_list():
    for i in range(len(tasks)):
        print("[{0}] ({1}) {2}".format(i,
                                       tasks[i].state,
                                       gen_cmd_line(tasks[i].params)))

def task_clear():
    tasks[:] = []

def get_task_by_uuid(id):
    l = [t for t in tasks if t.id == id]
    if l:
        return l[0]

def print_status(threads):
    os.system("cls")
    task_list()
    print("")
    
    print("Processes:")
    for i in range(len(threads)):
        print("[{0}]".format(i), threads[i][1].msg)

def task_run_impl(self, global_state, tasks):
    def print_hook(*args, **kwargs):
        if "file" in kwargs:
            print(*args, **kwargs)
        else:
            line = ' '.join(args).strip()
            if line:
                self.msg = line

            if line.startswith("aborted at input"):
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
                    self.msg = "No more tasks, thread exited"
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
                self.msg = "No available task"
                global_state.event.wait()
                global_state.event.clear()
                continue

            ret = encode(current_task.params, print_hook, int_handler)
            if ret:
                current_task.state = "error: code " + str(ret)
            else:
                current_task.state = task_states.completed

            task_save()
            with global_state.lock:
                global_state.slots += current_task.slot
                global_state.event.set()
                
    except KeyboardInterrupt:
        task_save()
        print("Interrupted by user.")
        global_state.exit_code = 1
        return
        
    
def task_run(max_slots=2):
    for t in tasks:
        if t.state == task_states.running:
            t.state = task_states.waiting
        
    print("Tasks:")
    task_list()

    state = AttrDict()
    state.lock = Lock()
    state.event = Event()
    state.slots = max_slots
    state.exit_code = None

    threads = []

    try:
        for i in range(max_slots):
            thread_state = AttrDict({"id": i, "msg": ""})
            thread = Thread(target=task_run_impl, args=(thread_state, state, tasks))
            thread.start()
            threads.append((thread, thread_state))

        while any([t[0].is_alive() for t in threads]):
            print_status(threads)
            if state.exit_code is not None:
                state.event.set()
                sys.exit(state.exit_code)
                
            sleep(1)

        print_status(threads)
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
        with open(task_file, "r") as f:
            tasks = json.load(f, object_hook=lambda d:Task(data=d))
    else:
        tasks = []

def task_do_command():
    command = sys.argv[2]
    args = sys.argv[3:]
    commands = {
        "list": task_list,
        "add": lambda: task_add(args),
        "remove": lambda: task_remove([int(x) for x in args]),
        "clear": task_clear,
        "reset": lambda: task_reset([int(x) for x in args]),
        "run": lambda: task_run(*[int(x) for x in args])
    }
    if command not in commands:
        print("Invalid command", command)
        return 1

    task_load()
    ret = commands[command]()
    task_save()

    sys.exit(ret)
