from .update import update
from .task import task_do_command
import os

__all__  = ["function"]

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

functions = {
    "update": lambda: update(base_path=base_dir),
    "task": task_do_command,
}
