from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

import os
import subprocess
import sys

# NOTE: this command is found in the AAFSDK
aaffmtconv = "aaffmtconv"

if __name__ == "__main__":

    dir_path = sys.argv[1]
    assert os.path.isdir(dir_path)

    for root, dirs, files in os.walk(dir_path, topdown=False):
        for filename in files:
            name, ext = os.path.splitext(filename)
            aaf_file = os.path.join(root, filename)
            xml_file = os.path.join(root, name + ".xml")

            if ext.lower() in ('.aaf',) and name[0] != '.':
                cmd = [aaffmtconv, '-xml', aaf_file, xml_file]
                print(subprocess.list2cmdline(cmd))
                subprocess.call(cmd)
