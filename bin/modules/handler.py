""" SALIS: Viewer/controller for the SALIS simulator.

File: handler.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

This module should be considered the 'controller' part of the Salis simulator.
It receives and parses all user input via keyboard and console commands. It
also takes care of genome compilation (via genome files located on the
'genomes' directory).

An user may open the Salis console by pressing the 'c' key while in a running
session. A nice quirk is the possibility to run python commands from within the
Salis console. As an example, to get the memory size, an user could type:

>>> exec output = self.__sim.lib.sal_mem_get_size()

Note that 'output' denotes a storage variable that will get printed on the
console response. This ability gives an user a whole lot of power, and should
be used with care.
"""

import curses
import os
import time


class Handler:
	KEY_ESCAPE = 27
	CYCLE_TIMEOUT = 0.1

	def __init__(self, sim):
		""" Handler constructor. Simply link this class to the main simulation
		class and printer class and create symbol dictionary.
		"""
		self.__sim = sim
		self.__printer = sim.printer
		self.__min_commands = [
			ord("M"),
			ord(" "),
			ord("X"),
			curses.KEY_RESIZE,
			self.KEY_ESCAPE,
		]
		self.inst_dict = self.__get_inst_dict()
		self.console_history = []

		# Set short delay for ESCAPE key (which is used to exit the simulator).
		os.environ.setdefault("ESCDELAY", "25")

	def process_cmd(self, cmd):
		""" Process incoming commands from curses. Commands are received via
		ncurses' getch() function, thus, they must be transformed into their
		character representations with 'ord()'.
		"""
		# If in minimal mode, only listen to a subset of commands.
		if self.__sim.minimal and cmd not in self.__min_commands:
			return

		if cmd == self.KEY_ESCAPE:
			self.__on_quit([None], save=True)
		elif cmd == ord("M"):
			self.__printer.screen.clear()
			self.__sim.minimal = not self.__sim.minimal
		elif cmd == ord(" "):
			self.__sim.toggle_state()
		elif cmd == curses.KEY_LEFT:
			self.__printer.flip_page(-1)
		elif cmd == curses.KEY_RIGHT:
			self.__printer.flip_page(1)
		elif cmd == curses.KEY_DOWN:
			self.__printer.scroll_main(-1)
		elif cmd == curses.KEY_UP:
			self.__printer.scroll_main(1)
		elif cmd == curses.KEY_RESIZE:
			self.__printer.on_resize()
		elif cmd == ord("X"):
			self.__printer.toggle_hex()
		elif cmd == ord("x"):
			self.__printer.world.zoom_out()
		elif cmd == ord("z"):
			self.__printer.world.zoom_in()
		elif cmd == ord("a"):
			self.__printer.world.pan_left()
			self.__printer.proc_scroll_left()
			self.__printer.comm_scroll_left()
		elif cmd == ord("d"):
			self.__printer.world.pan_right()
			self.__printer.proc_scroll_right()
			self.__printer.comm_scroll_right()
		elif cmd == ord("s"):
			self.__printer.world.pan_down()
			self.__printer.proc_scroll_down()
		elif cmd == ord("w"):
			self.__printer.world.pan_up()
			self.__printer.proc_scroll_up()
		elif cmd == ord("S"):
			self.__printer.world.pan_down(fast=True)
			self.__printer.proc_scroll_down(fast=True)
		elif cmd == ord("W"):
			self.__printer.world.pan_up(fast=True)
			self.__printer.proc_scroll_up(fast=True)
		elif cmd == ord("Q"):
			self.__printer.world.pan_reset()
			self.__printer.proc_scroll_vertical_reset()
		elif cmd == ord("A"):
			self.__printer.world.pan_reset()
			self.__printer.proc_scroll_horizontal_reset()
			self.__printer.comm_scroll_horizontal_reset()
		elif cmd == ord("o"):
			self.__printer.proc_select_prev()
		elif cmd == ord("p"):
			self.__printer.proc_select_next()
		elif cmd == ord("f"):
			self.__printer.proc_select_first()
		elif cmd == ord("l"):
			self.__printer.proc_select_last()
		elif cmd == ord("k"):
			self.__printer.proc_scroll_to_selected()
		elif cmd == ord("g"):
			self.__printer.proc_toggle_gene_view()
		elif cmd == ord("i"):
			self.__printer.world.toggle_ip_view()
		elif cmd == ord("\n"):
			self.__printer.run_cursor()
		elif cmd == ord("c"):
			self.__printer.run_console()
		else:
			# Check for numeric input. Number keys [1 to 0] cycle the
			# simulation [2 ** ((n - 1) % 10] times.
			try:
				if chr(cmd).isdigit():
					factor = int(chr(cmd))
					factor = int(2 ** ((factor - 1) % 10))
					self.__cycle_sim(factor)
			except ValueError:
				pass

	def handle_console(self, command_raw):
		""" Process console commands. We parse and check for input errors. Any
		python exception messages are redirected to the console-response
		window.
		"""
		if command_raw:
			command = command_raw.split()

			try:
				# Handle both python and self-thrown exceptions.
				if command[0] in ["q", "quit"]:
					self.__on_quit(command, save=True)
				elif command[0] in ["q!", "quit!"]:
					self.__on_quit(command, save=False)
				elif command[0] in ["i", "input"]:
					self.__on_input(command)
				elif command[0] in ["c", "compile"]:
					self.__on_compile(command)
				elif command[0] in ["n", "new"]:
					self.__on_new(command)
				elif command[0] in ["k", "kill"]:
					self.__on_kill(command)
				elif command[0] in ["e", "exec"]:
					self.__on_exec(command)
				elif command[0] in ["s", "scroll"]:
					self.__on_scroll(command)
				elif command[0] in ["p", "process"]:
					self.__on_proc_select(command)
				elif command[0] in ["r", "rename"]:
					self.__on_rename(command)
				elif command[0] in ["save"]:
					self.__on_save(command)
				elif command[0] in ["a", "auto"]:
					self.__on_set_autosave(command)
				elif command[0] in ["l", "link"]:
					self.__on_link_to_self(command)
				elif command[0] in ["source"]:
					self.__on_add_source(command)
				elif command[0] in ["target"]:
					self.__on_add_target(command)
				elif command[0] in ["rem_source"]:
					self.__on_remove_source(command)
				elif command[0] in ["rem_target"]:
					self.__on_remove_target(command)
				elif command[0] in ["net_load"]:
					self.__on_network_load(command)
				elif command[0] in ["net_save"]:
					self.__on_network_save(command)
				else:
					# Raise if a non-existing command has been given.
					self.__raise("Invalid command: '{}'".format(command[0]))
			except BaseException as exep:
				# We parse and redirect python exceptions to the error
				# console-window.
				message = str(exep).strip()
				message = message[0].upper() + message[1:]
				self.__printer.show_console_error(message)
			finally:
				# Store command on console history.
				self.console_history.append(command_raw.strip())


	###############################
	# Private methods
	###############################

	def __raise(self, message):
		""" Generic exception thrower. Throws a 'RuntimeError' initialized with
		the given message.
		"""
		raise RuntimeError("ERROR: {}".format(message))

	def __respond(self, message):
		""" Generic console responder. Throws a 'RuntimeError' initialized with
		the given message.
		"""
		raise RuntimeError(message)

	def __cycle_sim(self, factor):
		""" Simply cycle Salis 'factor' number of times. Do not cycle for more
		than a given amount of time.
		"""
		time_max = time.time() + self.CYCLE_TIMEOUT

		for _ in range(factor):
			self.__sim.cycle()

			if time.time() > time_max:
				break

	def __get_inst_dict(self):
		""" Transform the instruction list of the printer module into a
		dictionary that's more useful for genome compilation. Instruction
		symbols are keys, values are the actual byte representation.
		"""
		inst_dict = {}

		for i, inst in enumerate(self.__printer.inst_list):
			inst_dict[inst[1]] = i

		return inst_dict

	def __on_quit(self, command, save):
		""" Exit simulation. We can choose whether to save the simulation into
		a save file or not.
		"""
		if len(command) > 1:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		if save:
			self.__sim.lib.sal_main_save(
				self.__sim.save_file_path.encode("utf-8")
			)

		self.__sim.exit()

	def __write_genome(self, genome, address_list):
		""" Write genome stream into a given list of memory addresses. All
		addresses must be valid or an exception is thrown.
		"""
		# All addresses we will write to must be valid.
		for base_addr in address_list:
			address = int(base_addr, 0)

			for _ in range(len(genome)):
				if not self.__sim.lib.sal_mem_is_address_valid(address):
					self.__raise("Address '{}' is invalid".format(address))

				address += 1

		# All looks well! Let's compile the genome into memory.
		for base_addr in address_list:
			address = int(base_addr, 0)

			for symbol in genome:
				self.__sim.lib.sal_mem_set_inst(
					address, self.inst_dict[symbol]
				)
				address += 1

	def __on_input(self, command):
		""" Compile organism from user typed input. Compilation can only occur
		on valid memory addresses. An exception will be thrown when trying to
		write into non-valid address or when input stream is invalid.
		"""
		if len(command) < 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		# All characters in file must be actual instruction symbols.
		for character in command[1]:
			if character not in self.inst_dict:
				self.__raise("Invalid symbol '{}' found on stream".format(
					character
				))

		# All looks well, Let's write the genome into memory.
		self.__write_genome(command[1], command[2:])

	def __on_compile(self, command):
		""" Compile organism from source genome file. Genomes must be placed on
		the './genomes' directory. Compilation can only occur on valid memory
		addresses. An exception will be thrown when trying to write into
		non-valid address or when genome file is invalid.
		"""
		if len(command) < 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		# Open genome file for compilation.
		gen_file = os.path.join(self.__sim.path, "genomes", command[1])

		with open(gen_file, "r") as f:
			genome = f.read().strip()

		# Entire genome must be written on a single line.
		if "\n" in genome:
			self.__raise("Newline detected on '{}'".format(gen_file))

		# All characters in file must be actual instruction symbols.
		for character in genome:
			if character not in self.inst_dict:
				self.__raise("Invalid symbol '{}' found on '{}'".format(
					character, gen_file
				))

		# All looks well, Let's write the genome into memory.
		self.__write_genome(genome, command[2:])

	def __on_new(self, command):
		""" Instantiate new organism of given size on given address. These
		memory areas must be free and valid or an exception is thrown.
		"""
		if len(command) < 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		# Check that all addresses we will allocate are free and valid.
		for base_addr in command[2:]:
			address = int(base_addr, 0)

			for _ in range(int(command[1])):
				if not self.__sim.lib.sal_mem_is_address_valid(address):
					self.__raise("Address '{}' is invalid".format(address))
				elif self.__sim.lib.sal_mem_is_allocated(address):
					self.__raise("Address '{}' is allocated".format(address))

				address += 1

		# All looks well! Let's instantiate our new organism.
		for base_addr in command[2:]:
			address = int(base_addr, 0)
			size = int(command[1], 0)
			self.__sim.lib.sal_proc_create(address, size)

	def __on_kill(self, command):
		""" Kill organism on bottom of reaper queue.
		"""
		if len(command) > 1:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		# Call proc kill function only if there's any organisms to kill.
		if not self.__sim.lib.sal_proc_get_count():
			self.__raise("No organisms currently alive")
		else:
			self.__sim.lib.sal_proc_kill()

	def __on_exec(self, command):
		""" Allow a user to execute a python command from within the console.
		Using this is very hack-ish, and not recommended unless you're certain
		of what you're doing!
		"""
		if len(command) < 2:
			self.__raise(
				"'{}' must be followed by an executable string".format(
					command[0]
				)
			)

		# User may query any simulation variable or status and the console will
		# respond. For example, to query memory size or order, type one of the
		# following:
		#
		#     >>> exec output = self.__sim.lib.sal_mem_get_size()
		#     >>> exec output = self.__sim.lib.sal_mem_get_order()
		#
		output = {}
		exec(" ".join(command[1:]), locals(), output)
		self.__sim.printer.screen.clear()
		self.__sim.printer.print_page()

		if output:
			self.__respond("EXEC RESPONDS: {}".format(str(output)))

	def __on_scroll(self, command):
		""" We can scroll to a specific process (on PROCESS view) or to a
		specific world address (on WORLD view) via the console.
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		target = int(command[1], 0)

		# If on PROCESS page, scroll to given process.
		if self.__printer.current_page == "PROCESS":
			if target < self.__sim.lib.sal_proc_get_capacity():
				self.__printer.proc_scroll_to(target)
			else:
				self.__raise("No process with ID '{}' found".format(target))
		elif self.__printer.current_page == "WORLD":
			if self.__sim.lib.sal_mem_is_address_valid(target):
				self.__printer.world.scroll_to(target)
			else:
				self.__raise("Address '{}' is invalid".format(address))
		else:
			self.__raise("'{}' must be called on PROCESS or WORLD page".format(
				command[0])
			)

	def __on_proc_select(self, command):
		""" Select a specific process (on PROCESS or WORLD page).
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		target = int(command[1], 0)

		# If on PROCESS page, scroll to given process.
		if target < self.__sim.lib.sal_proc_get_capacity():
			self.__printer.proc_select_by_id(target)
		else:
			self.__raise("No process with ID '{}' found".format(target))

	def __on_rename(self, command):
		""" Set a new simulation name. Future auto-saved files will use this
		name as prefix.
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		self.__sim.rename(command[1])

	def __on_save(self, command):
		""" Save simulation on its current state.
		"""
		if len(command) != 1:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		self.__sim.lib.sal_main_save(self.__sim.save_file_path.encode("utf-8"))

	def __on_set_autosave(self, command):
		""" Set the simulation's auto save interval. Provide any integer
		between 0 and (2**32 - 1). If zero is provided, auto saving will be
		disabled.
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		self.__sim.set_autosave(int(command[1], 0))

	def __on_link_to_self(self, command):
		""" Add self as network target and source.
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		port = int(command[1])
		self.__sim.common.link_to_self(int(command[1]))

	def __on_add_source(self, command):
		""" Add new network source.
		"""
		if len(command) != 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		address = command[1]
		port = int(command[2])
		self.__sim.common.add_source(address, port)

	def __on_add_target(self, command):
		""" Add new network target.
		"""
		if len(command) != 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		address = command[1]
		port = int(command[2])
		self.__sim.common.add_target(address, port)

	def __on_remove_source(self, command):
		""" Remove existing network source.
		"""
		if len(command) != 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		address = command[1]
		port = int(command[2])
		self.__sim.common.remove_source(address, port)

	def __on_remove_target(self, command):
		""" Remove existing network target.
		"""
		if len(command) != 3:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		address = command[1]
		port = int(command[2])
		self.__sim.common.remove_target(address, port)

	def __on_network_load(self, command):
		""" Load network settings from JSON file (located on network settings
		directory.
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		self.__sim.common.load_network_config(command[1])

	def __on_network_save(self, command):
		""" Save network settings to a JSON file (which will be placed on the
		network settings directory).
		"""
		if len(command) != 2:
			self.__raise("Invalid parameters for '{}'".format(command[0]))

		self.__sim.common.save_network_config(command[1])
