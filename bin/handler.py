""" SALIS: Viewer/controller for the SALIS simulator.

file: handler.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

This module should be considered the 'controller' part of the Salis simulator.
It receives and parses all user input via keyboard and console commands. It
also takes care of genome compilation (via genome files located on the
'genomes' directory).

An user may open the Salis console by pressing the 'c' key while in a running
session. A nice quirk is the possibility to run python commands from within the
Salis console. As an example, to get the memory size, an user could type:

>>> exec output = self._sim.lib.sal_mem_get_size()

Note that 'output' denotes a storage variable that will get printed on the
console response. This ability gives an user a whole lot of power, and should
be used with care.
"""

import os
import curses


class Handler:
	ESCAPE_KEY = 27

	def __init__(self, sim):
		""" Handler constructor. Simply link this class to the main simulation
		class and printer class and create symbol dictionary.
		"""
		self._sim = sim
		self._printer = sim.printer
		self._inst_dict = self._get_inst_dict()
		self._console_history = []

	def process_cmd(self, cmd):
		""" Process incoming commands from curses. Commands are received via
		ncurses' getch() function, thus, they must be transformed into their
		character representations with 'ord()'.
		"""
		if cmd == self.ESCAPE_KEY:
			self._sim.lib.sal_main_save(
				self._sim.save_file_path.encode("utf-8")
			)
			self._sim.exit()
		elif cmd == ord(" "):
			self._sim.toggle_state()
		elif cmd == curses.KEY_LEFT:
			self._printer.flip_page(-1)
		elif cmd == curses.KEY_RIGHT:
			self._printer.flip_page(1)
		elif cmd == curses.KEY_DOWN:
			self._printer.scroll_main(-1)
		elif cmd == curses.KEY_UP:
			self._printer.scroll_main(1)
		elif cmd == curses.KEY_RESIZE:
			self._printer.on_resize()
		elif cmd == ord("X"):
			self._printer.toggle_hex()
		elif cmd == ord("x"):
			self._printer.world.zoom_out()
		elif cmd == ord("z"):
			self._printer.world.zoom_in()
		elif cmd == ord("a"):
			self._printer.world.pan_left()
			self._printer.proc_scroll_left()
		elif cmd == ord("d"):
			self._printer.world.pan_right()
			self._printer.proc_scroll_right()
		elif cmd == ord("s"):
			self._printer.world.pan_down()
			self._printer.proc_scroll_down()
		elif cmd == ord("w"):
			self._printer.world.pan_up()
			self._printer.proc_scroll_up()
		elif cmd == ord("S"):
			self._printer.world.pan_reset()
			self._printer.proc_scroll_vertical_reset()
		elif cmd == ord("A"):
			self._printer.world.pan_reset()
			self._printer.proc_scroll_horizontal_reset()
		elif cmd == ord("o"):
			self._printer.proc_select_prev()
		elif cmd == ord("p"):
			self._printer.proc_select_next()
		elif cmd == ord("f"):
			self._printer.proc_select_first()
		elif cmd == ord("l"):
			self._printer.proc_select_last()
		elif cmd == ord("k"):
			self._printer.proc_scroll_to_selected()
		elif cmd == ord("g"):
			self._printer.proc_toggle_gene_view()
		elif cmd == ord("\n"):
			self._printer.run_cursor()
		elif cmd == ord("c"):
			self._printer.run_console()
		else:
			# Check for numeric input. Number keys [1 to 0] cycle the
			# simulation [2 ** ((n - 1) % 10] times.
			try:
				if chr(cmd).isdigit():
					factor = int(chr(cmd))
					factor = int(2 ** ((factor - 1) % 10))
					self._cycle_sim(factor)
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
					self._on_quit(command, save=True)
				elif command[0] in ["q!", "quit!"]:
					self._on_quit(command, save=False)
				elif command[0] in ["i", "input"]:
					self._on_input(command)
				elif command[0] in ["c", "compile"]:
					self._on_compile(command)
				elif command[0] in ["n", "new"]:
					self._on_new(command)
				elif command[0] in ["k", "kill"]:
					self._on_kill(command)
				elif command[0] in ["e", "exec"]:
					self._on_exec(command)
				elif command[0] in ["s", "scroll"]:
					self._on_scroll(command)
				elif command[0] in ["p", "process"]:
					self._on_proc_select(command)
				elif command[0] in ["r", "rename"]:
					self._on_rename(command)
				elif command[0] in ["save"]:
					self._on_save(command)
				elif command[0] in ["a", "auto"]:
					self._on_set_autosave(command)
				else:
					# Raise if a non-existing command has been given.
					self._raise("Invalid command: '{}'".format(command[0]))
			except BaseException as exep:
				# We parse and redirect python exceptions to the error
				# console-window.
				message = str(exep).strip()
				message = message[0].upper() + message[1:]
				self._printer.show_console_error(message)
			finally:
				# Store command on console history.
				self._console_history.append(command_raw.strip())

	@property
	def console_history(self):
		return self._console_history

	def _raise(self, message):
		""" Generic exception thrower. Throws a 'RuntimeError' initialized with
		the given message.
		"""
		raise RuntimeError("ERROR: {}".format(message))

	def _respond(self, message):
		""" Generic console responder. Throws a 'RuntimeError' initialized with
		the given message.
		"""
		raise RuntimeError(message)

	def _cycle_sim(self, factor):
		""" Simply cycle Salis 'factor' number of times.
		"""
		for _ in range(factor):
			self._sim.lib.sal_main_cycle()
			self._sim.check_autosave()

	def _get_inst_dict(self):
		""" Transform the instruction list of the printer module into a
		dictionary that's more useful for genome compilation. Instruction
		symbols are keys, values are the actual byte representation.
		"""
		inst_dict = {}

		for i, inst in enumerate(self._printer.inst_list):
			inst_dict[inst[1]] = i

		return inst_dict

	def _on_quit(self, command, save):
		""" Exit simulation. We can choose whether to save the simulation into a
		save file or not.
		"""
		if len(command) > 1:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		if save:
			self._sim.lib.sal_main_save(
				self._sim.save_file_path.encode("utf-8")
			)

		self._sim.exit()

	def _write_genome(self, genome, address_list):
		""" Write genome stream into a given list of memory addresses. All
		addresses must be valid or an exception is thrown.
		"""
		# All addresses we will write to must be valid.
		for base_addr in address_list:
			address = int(base_addr, 0)

			for _ in range(len(genome)):
				if not self._sim.lib.sal_mem_is_address_valid(address):
					self._raise("Address '{}' is invalid".format(address))

				address += 1

		# All looks well! Let's compile the genome into memory.
		for base_addr in address_list:
			address = int(base_addr, 0)

			for symbol in genome:
				self._sim.lib.sal_mem_set_inst(
					address, self._inst_dict[symbol]
				)
				address += 1

	def _on_input(self, command):
		""" Compile organism from user typed input. Compilation can only occur
		on valid memory addresses. An exception will be thrown when trying to
		write into non-valid address or when input stream is invalid.
		"""
		if len(command) < 3:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		# All characters in file must be actual instruction symbols.
		for character in command[1]:
			if character not in self._inst_dict:
				self._raise("Invalid symbol '{}' found on stream".format(
					character
				))

		# All looks well, Let's write the genome into memory.
		self._write_genome(command[1], command[2:])

	def _on_compile(self, command):
		""" Compile organism from source genome file. Genomes must be placed on
		the './genomes' directory. Compilation can only occur on valid memory
		addresses. An exception will be thrown when trying to write into
		non-valid address or when genome file is invalid.
		"""
		if len(command) < 3:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		# Open genome file for compilation.
		gen_file = os.path.join(self._sim.path, "genomes", command[1])

		with open(gen_file, "r") as f:
			genome = f.read().strip()

		# Entire genome must be written on a single line.
		if "\n" in genome:
			self._raise("Newline detected on '{}'".format(gen_file))

		# All characters in file must be actual instruction symbols.
		for character in genome:
			if character not in self._inst_dict:
				self._raise("Invalid symbol '{}' found on '{}'".format(
					character, gen_file
				))

		# All looks well, Let's write the genome into memory.
		self._write_genome(genome, command[2:])

	def _on_new(self, command):
		""" Instantiate new organism of given size on given address. These
		memory areas must be free and valid or an exception is thrown.
		"""
		if len(command) < 3:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		# Check that all addresses we will allocate are free and valid.
		for base_addr in command[2:]:
			address = int(base_addr, 0)

			for _ in range(int(command[1])):
				if not self._sim.lib.sal_mem_is_address_valid(address):
					self._raise("Address '{}' is invalid".format(address))
				elif self._sim.lib.sal_mem_is_allocated(address):
					self._raise("Address '{}' is allocated".format(address))

				address += 1

		# All looks well! Let's instantiate our new organism.
		for base_addr in command[2:]:
			address = int(base_addr, 0)
			size = int(command[1], 0)
			self._sim.lib.sal_proc_create(address, size)

	def _on_kill(self, command):
		""" Kill organism on bottom of reaper queue.
		"""
		if len(command) > 1:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		# Call proc kill function only if there's any organisms to kill.
		if not self._sim.lib.sal_proc_get_count():
			self._raise("No organisms currently alive")
		else:
			self._sim.lib.sal_proc_kill()

	def _on_exec(self, command):
		""" Allow a user to execute a python command from within the console.
		Using this is very hack-ish, and not recommended unless you're certain
		of what you're doing!
		"""
		if len(command) < 2:
			self._raise("'{}' must be followed by an executable string".format(
				command[0])
			)

		# User may query any simulation variable or status and the console will
		# respond. For example, to query memory size or order, type one of the
		# following:
		#
		#     >>> exec output = self._sim.lib.sal_mem_get_size()
		#     >>> exec output = self._sim.lib.sal_mem_get_order()
		#
		output = {}
		exec(" ".join(command[1:]), locals(), output)

		if output:
			self._respond("EXEC RESPONDS: {}".format(str(output)))

	def _on_scroll(self, command):
		""" We can scroll to a specific process (on PROCESS view) or to a
		specific world address (on WORLD view) via the console.
		"""
		if len(command) != 2:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		target = int(command[1], 0)

		# If on PROCESS page, scroll to given process.
		if self._printer.current_page == "PROCESS":
			if target < self._sim.lib.sal_proc_get_capacity():
				self._printer.proc_scroll_to(target)
			else:
				self._raise("No process with ID '{}' found".format(target))
		elif self._printer.current_page == "WORLD":
			if self._sim.lib.sal_mem_is_address_valid(target):
				self._printer.world.scroll_to(target)
			else:
				self._raise("Address '{}' is invalid".format(address))
		else:
			self._raise("'{}' must be called on PROCESS or WORLD page".format(
				command[0])
			)

	def _on_proc_select(self, command):
		""" Select a specific process (on PROCESS or WORLD page).
		"""
		if len(command) != 2:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		target = int(command[1], 0)

		# If on PROCESS page, scroll to given process.
		if target < self._sim.lib.sal_proc_get_capacity():
			self._printer.proc_select_by_id(target)
		else:
			self._raise("No process with ID '{}' found".format(target))

	def _on_rename(self, command):
		""" Set a new simulation name. Future auto-saved files will use this
		name as prefix.
		"""
		if len(command) != 2:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		self._sim.rename(command[1])

	def _on_save(self, command):
		""" Save simulation on its current state.
		"""
		if len(command) != 1:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		self._sim.lib.sal_main_save(self._sim.save_file_path.encode("utf-8"))

	def _on_set_autosave(self, command):
		""" Set the simulation's auto save interval. Provide any integer
		between 0 and (2**32 - 1). If zero is provided, auto saving will be
		disabled.
		"""
		if len(command) != 2:
			self._raise("Invalid parameters for '{}'".format(command[0]))

		self._sim.set_autosave(int(command[1], 0))
