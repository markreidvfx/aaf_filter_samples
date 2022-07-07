from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

import os
import subprocess
import sys
import json

def parse(f, parameter_map):
    data = json.load(f)
    # print(data['name'])
    mob_name = data['name']

    # get the global parameter_definitions
    for uid, value in data.get("parameter_definitions", {}).items():
        existing = parameter_map.get(uid, None)
        name = value[1]
        name = name.strip()
        parameter_map[uid] = name

    for op, d in data['operations'].items():
        # print(" ", op)

        param_defs = d.get("ParameterDefinitions", {})

        for uid, value in param_defs.items():
            existing = parameter_map.get(uid, None)
            if existing:
                continue

            name = value[1]
            # if not name:
            #     name = "{} {}".format(op, uid)

            # some names have trailing whitespace ? why
            name = name.strip()

            parameter_map[uid] = name


        parameters = d.get("Parameters", [])

        for param in parameters:
            # print(param[0])
            split = param[0].split(" ")
            uid = split[0]
            name = " ".join(split[1:])
            existing = parameter_map.get(uid, None)


            if existing:
                continue

            # if not name:
            #     name = "{} ".format(op, uid)

            # some names have trailing whitespace ? why
            name = name.strip()
            parameter_map[uid] = name

if __name__ == "__main__":
    parameter_map = {}

    dir_paths = sys.argv[1:]
    for dir_path in dir_paths:
        assert os.path.isdir(dir_path)
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for filename in files:
                name, ext = os.path.splitext(filename)
                json_file = os.path.join(root, filename)

                if ext.lower() in ('.json',) and name[0] != '.':
                    with open(json_file, 'r') as f:
                        data = parse(f, parameter_map)

    with open("parameter_uuids.py", 'w') as f:
        f.write("# These UUIDS are extracted from AAF files\n")
        f.write("PARAMETER_UUIDS = {\n")

        for key, value in sorted(parameter_map.items()):
            if value:
                f.write('    "{}": u"{}",\n'.format(key, value))
            # print(key, value)

        f.write("}\n")