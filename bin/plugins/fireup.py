#!/usr/bin/env python3

""" FIREUP: Plugin for the SALIS simulator.

File: fireup.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

NOTE: REQUIRES TMUX TO WORK!

Use this script to run one (or several) previously saved simulations in the
background. Each simulator will be started inside a tmux session, already
running and in minimal mode.

Remember to give this file correct permissions (chmod +x). To use, call it
followed by an autosave interval (mandatory) and the list of save-files to
load. Save-file paths are always relative to the './bin/sims/' directory.
For example:

$ ./bin/plugins/fireup.py -a 0x100000 -f 20.01.sim 20.02.sim 20.03.sim

"""

import argparse
import os
import subprocess


# Parse CLI arguments with the argparse module. Required arguments are the
# autosave interval (zero means no autosaving) and a list of previously saved
# simulation files.
parser = argparse.ArgumentParser(
	description="TMUX launcher for pre-saved Salis simulations."
)
parser.add_argument(
	"-f", "--files", required=True, type=str, nargs="+", metavar="FILE",
	help="File name(s) of simulation(s) to load."
)
parser.add_argument(
	"-a", "--auto", required=True, type=lambda x: int(x, 0), metavar="INT",
	help="Auto-save interval for the loaded simulation(s)."
)
args = parser.parse_args()

# Store the path of this script and the main Salis simulation script.
path = os.path.dirname(__file__)
salis = os.path.join(path, "../salis.py")

# Revise that *all* listed files exist inside the './bin/sims/' directory.
# Otherwise throw an exception.
for fname in args.files:
	abs_path = os.path.join(path, "../sims", fname)

	if not os.path.isfile(abs_path):
		parser.error("Save file '{}' not found.".format(abs_path))

# Also, check that no file names are repeated.
if len(args.files) != len(set(args.files)):
	parser.error("Repeated file name detected.")

# Everything seems OK! Let's fire up the TMUX sessions, one for every saved
# file. Tmux sessions will be named similarly to their contained simulations.
# We can, at any time, re-attach to any running session, or make use of all
# other tmux commands.
print("Firing up Salis simulations.")

for fname in args.files:
	session = "salis-{}".format(fname).replace(".", "-")
	salis_cmd = "{} -m -r load -f {} -a {}".format(salis, fname, args.auto)
	subprocess.run(["tmux", "new-session", "-d", "-s", session])
	subprocess.run(["tmux", "send-keys", "-t", session, salis_cmd])
	subprocess.run(["tmux", "send-keys", "-t", session, "Enter"])
	print("New tmux session '{}' is running '{}' in the background.".format(
		session, fname
	))
