#!/usr/bin/env python3

""" SALIS: Viewer/controller for the SALIS simulator.

File: salis.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

Main handler for the Salis simulator. The Salis class takes care of
initializing, running and shutting down the simulator and other sub-modules. It
also takes care of parsing the command-line arguments and linking to the Salis
library with the help of ctypes.

To execute this script, make sure to have python3 installed and in your path,
as well as the cython package. Also, make sure it has correct execute
permissions (chmod).
"""

import os
import re
import sys
import time
import traceback
from argparse import ArgumentParser, HelpFormatter
from ctypes import CDLL, c_bool, c_uint8, c_uint32, c_char_p, POINTER
from handler import Handler
from printer import Printer


__version__ = "2.0"


class Salis:
	def __init__(self):
		""" Salis constructor. Arguments are passed through the command line
		and parsed with the 'argparse' module. Library is loaded with 'CDLL'
		and C headers are parsed to detect function argument and return types.
		"""
		self._path = self._get_path()
		self._args = self._parse_args()
		self._log = self._open_log_file()
		self._save_file_path = self._get_save_file_path()
		self._common_pipe = self._get_common_pipe()
		self._lib = self._parse_lib()
		self._printer = Printer(self)
		self._handler = Handler(self)
		self._state = "paused"
		self._autosave = "---"
		self._exit = False

		# Based on CLI arguments, initialize a new Salis simulation or load
		# existing one from file.
		if self._args.action == "new":
			self._lib.sal_main_init(
				self._args.order, self._common_pipe.encode("utf-8")
			)
		elif self._args.action == "load":
			self._lib.sal_main_load(
				self._save_file_path.encode("utf-8"),
				self._common_pipe.encode("utf-8")
			)

	def __del__(self):
		""" Salis destructor.
		"""
		# In case an error occurred early during initialization, checks whether
		# Salis has been initialized correctly before attempting to shut it
		# down.
		if hasattr(self, "_lib") and hasattr(self._lib, "sal_main_quit"):
			if self._lib.sal_main_is_init():
				self._lib.sal_main_quit()

		# If simulation ended correctly, 'error.log' should be empty. Delete
		# file it exists and its empty.
		if (
			hasattr(self, "_log") and
			os.path.isfile(self._log) and
			os.stat(self._log).st_size == 0
		):
			os.remove(self._log)

	def run(self):
		""" Runs main simulation loop. Curses may be placed on non-blocking
		mode, which allows simulation to run freely while still listening to
		user input.
		"""
		while not self._exit:
			self._printer.print_page()
			self._handler.process_cmd(self._printer.get_cmd())

			# If in non-blocking mode, re-print data once every 15
			# milliseconds.
			if self._state == "running":
				end = time.time() + 0.015

				while time.time() < end:
					self._lib.sal_main_cycle()
					self.check_autosave()

	def toggle_state(self):
		""" Toggle between 'paused' and 'running' states. On 'running' curses
		gets placed in non-blocking mode.
		"""
		if self._state == "paused":
			self._state = "running"
			self._printer.set_nodelay(True)
		else:
			self._state = "paused"
			self._printer.set_nodelay(False)

	def rename(self, new_name):
		""" Give the simulation a new name.
		"""
		self._args.file = new_name
		self._save_file_path = self._get_save_file_path()

	def set_autosave(self, interval):
		""" Set the simulation's auto-save interval. When set to zero, auto
		saving is disabled,
		"""
		if not interval:
			self._autosave = "---"
		else:
			self._autosave = interval

	def check_autosave(self):
		""" Save simulation to './sims/auto/*' whenever the autosave interval
		is reached. We use the following naming convention for auto-saved files:

		>>> ./sims/auto/<file-name>.<sim-epoch>.<sim-cycle>.auto
		"""
		if self._autosave != "---":
			if not self._lib.sal_main_get_cycle() % self._autosave:
				auto_path = os.path.join(self._path, "sims/auto", ".".join([
					self._args.file,
					"{:08x}".format(self._lib.sal_main_get_epoch()),
					"{:08x}".format(self._lib.sal_main_get_cycle()),
					"auto"
				]))
				self._lib.sal_main_save(auto_path.encode("utf-8"))

	def exit(self):
		""" Signal we want to exit the simulator.
		"""
		self._exit = True

	@property
	def path(self):
		return self._path

	@property
	def save_file_path(self):
		return self._save_file_path

	@property
	def common_pipe(self):
		return self._common_pipe

	@property
	def args(self):
		return self._args

	@property
	def lib(self):
		return self._lib

	@property
	def printer(self):
		return self._printer

	@property
	def handler(self):
		return self._handler

	@property
	def state(self):
		return self._state

	@property
	def autosave(self):
		return self._autosave

	def _get_path(self):
		""" Retrieve the absolute path of this script. We need to do this in
		order to detect the './lib', './sims' and './genomes' subdirectories.
		"""
		return os.path.dirname(__file__)

	def _get_save_file_path(self):
		""" Retrieve the absolute path of the file to which we will save this
		simulation when we exit Salis.
		"""
		return os.path.join(self._path, "sims", self._args.file)

	def _get_common_pipe(self):
		""" Get absolute path of the common pipe. This FIFO object may be used
		by concurrent Salis simulations to share data between themselves.
		"""
		return os.path.join(self._path, "common/pipe")

	def _parse_args(self):
		""" Parse command-line arguments with the 'argparse' module. To learn
		more about each command, invoke the simulator in one of the following
		ways:

			(venv) $ python tsalis.py --help
			(venv) $ python tsalis.py new --help
			(venv) $ python tsalis.py load --help

		"""
		# Custom formatter helps keep all help data aligned.
		formatter = lambda prog: HelpFormatter(prog, max_help_position=30)

		# Initialize the main parser with our custom formatter.
		parser = ArgumentParser(
			description="Viewer/controller for the Salis simulator.",
			formatter_class=formatter
		)
		parser.add_argument(
			'-v', '--version', action='version',
			version="Salis: A-Life Simulator (" + __version__ + ")"
		)

		# Initialize the 'new/load' action subparsers.
		subparsers = parser.add_subparsers(
			dest="action", help="Possible actions..."
		)
		subparsers.required = True

		# Set up subparser for the create 'new' action.
		new_parser = subparsers.add_parser("new", formatter_class=formatter)
		new_parser.add_argument(
			"-o", "--order", required=True, type=lambda x: int(x, 0),
			metavar="[1-31]", help="Create new simulation of given ORDER"
		)
		new_parser.add_argument(
			"-f", "--file", required=True, type=str, metavar="FILE",
			help="Name of FILE to save simulation to on exit"
		)

		# Set up subparser for the 'load' existing action.
		load_parser = subparsers.add_parser("load", formatter_class=formatter)
		load_parser.add_argument(
			"-f", "--file", required=True, type=str, metavar="FILE",
			help="Load previously saved simulation from FILE"
		)

		# Finally, parse all arguments.
		args = parser.parse_args()

		# Revise that parsed CL arguments are valid.
		if args.action == "new":
			if args.order not in range(1, 32):
				parser.error("Order must be an integer between 1 and 31")
		else:
			savefile = os.path.join(self._path, "sims", args.file)

			# No save-file with given name has been detected.
			if not os.path.isfile(savefile):
				parser.error(
					"Save file provided '{}' does not exist".format(savefile)
				)

		return args

	def _open_log_file(self):
		""" Create a log file to store errors on. It will get deleted if no
		errors are detected.
		"""
		log_file = os.path.join(self._path, "error.log")
		sys.stderr = open(log_file, 'w')
		return log_file

	def _parse_lib(self):
		""" Dynamically parse the Salis library C header files. We do this in
		order to more easily set the correct input/output types of all loaded
		functions. C functions to be parsed must be declared in a '.h' file
		located on the '../include' directory, using the following syntax:

			SALIS_API restype func_name(arg1_type arg1, arg2_type arg2);

		Note to developers: the 'SALIS_API' keyword should *NOT* be used
		anywhere else in the header files (not even in comments)!
		"""
		lib = CDLL(os.path.join(self._path, "lib/libsalis.so"))
		include_dir = os.path.join(self._path, "../include")
		c_includes = [
			os.path.join(include_dir, f)
			for f in os.listdir(include_dir)
			# Only parse '.h' header files.
			if os.path.isfile(os.path.join(include_dir, f)) and f[-2:] == ".h"
		]
		funcs_to_set = []

		for include in c_includes:
			with open(include, "r") as f:
				text = f.read()

			# Regexp to detect C functions to parse. This is a *very lazy*
			# parser. So, if you want to expand/tweak Salis, be careful when
			# declaring new functions!
			funcs = re.findall(r"SALIS_API([\s\S]+?);", text, re.MULTILINE)

			for func in funcs:
				func = func.replace("\n", "")
				func = func.replace("\t", "")
				func = func.strip()
				restype = func.split()[0]
				name = func.split()[1].split("(")[0]
				args = [
					arg.split()[0]
					for arg in func.split("(")[1].split(")")[0].split(",")
				]
				funcs_to_set.append({
					"name": name,
					"restype": restype,
					"args": args
				})

		# All Salis typedefs must be included here, associated to their CTYPES
		# equivalents.
		type_convert = {
			"void": None,
			"boolean": c_bool,
			"uint8": c_uint8,
			"uint8_p": POINTER(c_uint8),
			"uint32": c_uint32,
			"uint32_p": POINTER(c_uint32),
			"string": c_char_p,
			"Process": None,
		}

		# Finally, set correct arguments and return types of all Salis
		# functions.
		for func in funcs_to_set:
			func["restype"] = type_convert[func["restype"]]
			func["args"] = [type_convert[arg] for arg in func["args"]]
			getattr(lib, func["name"]).restype = func["restype"]
			getattr(lib, func["name"]).argtype = func["args"]

		return lib

if __name__ == "__main__":
	""" Entry point of the application. As this is a curses application, we
	capture any stack trace output in order to be able to print runtime errors
	to the terminal.
	"""
	Salis().run()
