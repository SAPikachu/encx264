import json
from urllib.request import urlopen
from urllib.error import URLError
import os

__all__ = ["update"]

base_url = "http://github.com/api/v2/json/"
base_path = os.path.dirname(__file__)
rev_record_file = os.path.join(base_path, ".current_rev")

def read_url(url):
    with urlopen(base_url + url) as u:
        return u.read()
    

def load_json(url):
    return json.loads(read_url(url).decode("utf-8"))

def write_tree(tree, base_dir):
    os.makedirs(base_dir, exist_ok=True)
        
    for name, val in tree.items():
        full_path = os.path.join(base_dir, name)
        if isinstance(val, dict):
            write_tree(val, full_path)
        else:
            with open(full_path, "wb") as f:
                f.write(val)

def download_tree(id):
    tree_resp = load_json("tree/show/SAPikachu/encx264/" + id)
    tree = {x["name"]: read_url("blob/show/SAPikachu/encx264/" + x["sha"])
            for x in tree_resp["tree"]
            if x["type"] == "blob"}

    tree.update({x["name"]: download_tree(x["sha"])
                 for x in tree_resp["tree"]
                 if x["type"] == "tree"})

    return tree

def update_impl(branch="stable"):
    current_rev = ""
    if os.path.isfile(rev_record_file):
        with open(rev_record_file, "r") as f:
            current_rev = f.read().strip()

    print("Current revision:", current_rev or "(packed version)")

    try:
        branches_resp = load_json("repos/show/SAPikachu/encx264/branches")
        branches = branches_resp["branches"]
        if branch not in branches:
            return "Invalid branch '{0}'".format(branch)

        rev = branches[branch]
        if rev == current_rev:
            print("We already have the latest version.")
            return

        print("Downloading latest revision:", rev)

        # separate download and write to avoid partial update
        write_tree(download_tree(rev), base_path)

        with open(rev_record_file, "w") as f:
            f.write(rev)

        print("Update completed.")
        
    except URLError:
        return "Network error while downloading updates."
    except KeyError:
        return "Invalid response."

def update(*args, **kwargs):
    msg = update_impl(*args, **kwargs)
    if msg:
        print("Update error:", msg)

    
if __name__ == "__main__":
    update()
