""" SALIS: Viewer/controller for the SALIS simulator.

File: printer.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

This module should be considered the 'view' part of the Salis simulator. It
takes care of displaying the simulator's state in a nicely formatted, intuitive
format. It makes use of the curses library for terminal handling.
"""

import curses
import curses.textpad
import os
import time

from collections import OrderedDict
from ctypes import c_uint8, c_uint32, cast, POINTER
from handler import Handler
from world import World


class Printer:
	ESCAPE_KEY = 27

	def __init__(self, sim):
		""" Printer constructor. It takes care of starting up curses, defining
		the data pages and setting the printer on its initial state.
		"""
		self.__sim = sim
		self.__color_pair_count = 0

		# Initialize curses screen, instruction and proc-element list before
		# other private elements that depend on them.
		self.screen = self.__get_screen()
		self.inst_list = self.__get_inst_list()
		self.proc_elements = self.__get_proc_elements()

		# We can now initialize all other privates.
		self.__main = self.__get_main()
		self.__pages = self.__get_pages()
		self.__main_scroll = 0
		self.__proc_element_scroll = 0
		self.__proc_gene_scroll = 0
		self.__proc_gene_view = False
		self.__curs_y = 0
		self.__curs_x = 0
		self.__print_hex = False
		self.size = self.screen.getmaxyx()
		self.current_page = "MEMORY"
		self.selected_proc = 0
		self.selected_proc_data = (c_uint32 * len(self.proc_elements))()
		self.proc_list_scroll = 0
		self.world = World(self, self.__sim)

	def __del__(self):
		""" Printer destructor exits curses.
		"""
		curses.endwin()

	def get_color_pair(self, fg, bg=-1):
		""" We use this method to set new color pairs, keeping track of the
		number of pairs already set. We return the new color pair ID.
		"""
		self.__color_pair_count += 1
		curses.init_pair(self.__color_pair_count, fg, bg)
		return self.__color_pair_count

	def get_cmd(self):
		""" This returns the pressed key from the curses handler. It's called
		during the simulation's main loop. Flushing input is important when in
		non-blocking mode.
		"""
		ch = self.screen.getch()
		curses.flushinp()
		return ch

	def set_nodelay(self, nodelay):
		""" Toggles between blocking and non-blocking mode on curses.
		"""
		self.screen.nodelay(nodelay)

	def toggle_hex(self):
		""" Toggle between decimal or hexadecimal printing of all simulation
		state elements.
		"""
		self.__print_hex = not self.__print_hex

	def on_resize(self):
		""" Called whenever the terminal window gets resized.
		"""
		self.size = self.screen.getmaxyx()
		self.scroll_main()
		self.world.zoom_reset()

	def flip_page(self, offset):
		""" Change data page by given offset (i.e. '1' for next page or '-1'
		for previous one).
		"""
		pidx = list(self.__pages.keys()).index(self.current_page)
		pidx = (pidx + offset) % len(self.__pages)
		self.current_page = list(self.__pages.keys())[pidx]
		self.scroll_main()

	def scroll_main(self, offset=0):
		""" Scrolling is allowed whenever the current page does not fit inside
		the terminal window. This method gets called, with no offset, under
		certain situations, like changing pages, just to make sure the screen
		gets cleared and at least some of the data is always scrolled into
		view.
		"""
		self.screen.clear()
		len_main = len(self.__main)
		len_page = len(self.__pages[self.current_page])
		max_scroll = (len_main + len_page + 5) - self.size[0]
		self.__main_scroll += offset
		self.__main_scroll = max(0, min(self.__main_scroll, max_scroll))

	def proc_scroll_left(self):
		""" Scroll process data elements or genomes (on PROCESS view) to the
		left.
		"""
		if self.current_page == "PROCESS":
			if self.__proc_gene_view:
				self.__proc_gene_scroll -= 1
				self.__proc_gene_scroll = max(0, self.__proc_gene_scroll)
			else:
				self.__proc_element_scroll -= 1
				self.__proc_element_scroll = max(0, self.__proc_element_scroll)

	def proc_scroll_right(self):
		""" Scroll process data elements or genomes (on PROCESS view) to the
		right.
		"""
		if self.current_page == "PROCESS":
			if self.__proc_gene_view:
				self.__proc_gene_scroll += 1
			else:
				self.__proc_element_scroll += 1
				max_scroll = len(self.proc_elements) - 1
				self.__proc_element_scroll = min(
					max_scroll, self.__proc_element_scroll
				)

	def proc_scroll_down(self, fast=False):
		""" Scroll process data table (on PROCESS view) up.
		"""
		if self.current_page == "PROCESS":
			if fast:
				len_page = len(self.__main) + len(self.__pages["PROCESS"]) + 6
				scroll = max(0, self.size[0] - len_page)
			else:
				scroll = 1

			self.proc_list_scroll = max(0, self.proc_list_scroll - scroll)

	def proc_scroll_up(self, fast=False):
		""" Scroll process data table (on PROCESS view) down.
		"""
		if self.current_page == "PROCESS":
			if fast:
				len_page = len(self.__main) + len(self.__pages["PROCESS"]) + 6
				scroll = max(0, self.size[0] - len_page)
			else:
				scroll = 1

			self.proc_list_scroll = min(
				self.__sim.lib.sal_proc_get_capacity() - 1,
				self.proc_list_scroll + scroll
			)

	def proc_scroll_to(self, proc_id):
		""" Scroll process data table (on PROCESS view) to a specific position.
		"""
		if self.current_page == "PROCESS":
			if proc_id < self.__sim.lib.sal_proc_get_capacity():
				self.proc_list_scroll = proc_id
			else:
				raise RuntimeError("Error: scrolling to invalid process")

	def proc_scroll_vertical_reset(self):
		""" Scroll process data table (on PROCESS view) back to top.
		"""
		if self.current_page == "PROCESS":
			self.proc_list_scroll = 0

	def proc_scroll_horizontal_reset(self):
		""" Scroll process data or genome table (on PROCESS view) back to the
		left.
		"""
		if self.current_page == "PROCESS":
			if self.__proc_gene_view:
				self.__proc_gene_scroll = 0
			else:
				self.__proc_element_scroll = 0

	def proc_select_prev(self):
		""" Select previous process.
		"""
		if self.current_page in ["PROCESS", "WORLD"]:
			self.selected_proc -= 1
			self.selected_proc %= self.__sim.lib.sal_proc_get_capacity()

	def proc_select_next(self):
		""" Select next process.
		"""
		if self.current_page in ["PROCESS", "WORLD"]:
			self.selected_proc += 1
			self.selected_proc %= self.__sim.lib.sal_proc_get_capacity()

	def proc_select_first(self):
		""" Select first process on reaper queue.
		"""
		if self.current_page in ["PROCESS", "WORLD"]:
			if self.__sim.lib.sal_proc_get_count():
				self.selected_proc = self.__sim.lib.sal_proc_get_first()

	def proc_select_last(self):
		""" Select last process on reaper queue.
		"""
		if self.current_page in ["PROCESS", "WORLD"]:
			if self.__sim.lib.sal_proc_get_count():
				self.selected_proc = self.__sim.lib.sal_proc_get_last()

	def proc_select_by_id(self, proc_id):
		""" Select process from given ID.
		"""
		if proc_id < self.__sim.lib.sal_proc_get_capacity():
			self.selected_proc = proc_id
		else:
			raise RuntimeError("Error: attempting to select non-existing proc")

	def proc_scroll_to_selected(self):
		""" Scroll WORLD or PROCESS page so that selected process becomes
		visible.
		"""
		if self.current_page == "PROCESS":
			self.proc_list_scroll = self.selected_proc
		elif self.current_page == "WORLD":
			if not self.__sim.lib.sal_proc_is_free(self.selected_proc):
				index = self.proc_elements.index("mb1a")
				address = self.selected_proc_data[index]
				self.world.scroll_to(address)

	def proc_toggle_gene_view(self):
		""" Toggle between data element or genome view on PROCESS page.
		"""
		if self.current_page == "PROCESS":
			self.__proc_gene_view = not self.__proc_gene_view

	def run_cursor(self):
		""" We can toggle a visible cursor on WORLD view to aid us in selecting
		processes.
		"""
		if self.current_page == "WORLD" and self.size[1] > World.PADDING:
			curses.curs_set(True)

			while True:
				self.__curs_y = max(0, min(self.__curs_y, self.size[0] - 1))
				self.__curs_x = max(World.PADDING, min(
					self.__curs_x, self.size[1] - 1
				))
				self.screen.move(self.__curs_y, self.__curs_x)
				cmd = self.screen.getch()

				if cmd in [ord("c"), curses.KEY_RESIZE, self.ESCAPE_KEY]:
					self.on_resize()
					break
				elif cmd == curses.KEY_LEFT:
					self.__curs_x -= 1
				elif cmd == curses.KEY_RIGHT:
					self.__curs_x += 1
				elif cmd == curses.KEY_DOWN:
					self.__curs_y += 1
				elif cmd == curses.KEY_UP:
					self.__curs_y -= 1
				elif cmd == ord("\n"):
					self.__proc_select_by_cursor()
					break

			curses.curs_set(False)

	def run_console(self):
		""" Run the Salis console. You can use the console to control all main
		aspects of the simulation, like compiling genomes into memory, creating
		or killing organisms, setting auto-save interval, among other stuff.
		"""
		# Print a pythonic prompt.
		self.__print_line(self.size[0] - 1, ">>> ", scroll=False)
		self.screen.refresh()

		# Create the console child window. We turn it into a Textbox object in
		# order to allow line-editing and extract output easily.
		console = curses.newwin(1, self.size[1] - 5, self.size[0] - 1, 5)
		textbox = curses.textpad.Textbox(console, insert_mode=True)
		textbox.stripspaces = True

		# Grab a copy of the console history and instantiate a pointer to the
		# last element.
		history = self.__sim.handler.console_history + [""]
		pointer = len(history) - 1

		# Nested method reinserts recorded commands from history into console.
		def access_history(cmd):
			nonlocal pointer

			if pointer == len(history) - 1:
				history[-1] = console.instr().strip()

			if cmd == "up" and pointer != 0:
				pointer -= 1
			elif cmd == "down" and pointer < len(history) - 1:
				pointer += 1

			console.clear()
			console.addstr(0, 0, history[pointer])
			console.refresh()

		# Declare custom validator to control special commands.
		def validator(cmd):
			EXIT = 7

			if cmd in [curses.KEY_RESIZE, self.ESCAPE_KEY]:
				console.clear()
				return EXIT
			# Provide general code for back-space key, in case it's not
			# correctly defined.
			elif cmd in [127, curses.KEY_BACKSPACE]:
				return curses.KEY_BACKSPACE
			elif cmd == curses.KEY_UP:
				access_history("up")
			elif cmd == curses.KEY_DOWN:
				access_history("down")
			else:
				return cmd

		# Run the Textbox object with our custom validator.
		curses.curs_set(True)
		output = textbox.edit(validator)
		curses.curs_set(False)

		# Finally, extract data from console and send to handler. Respond to
		# any possible resize event here.
		self.__sim.handler.handle_console(output)
		self.screen.clear()
		self.on_resize()

	def show_console_error(self, message):
		""" Shows Salis console error messages, if any. These messages might
		contain actual python exception output.
		"""
		self.__print_line(self.size[0] - 1, ">>>", curses.color_pair(
			self._pair_error
		) | curses.A_BOLD)
		self.screen.refresh()

		# We also use a Textbox object, just so that execution gets halted
		# until a key gets pressed (even on non-blocking mode).
		console = curses.newwin(1, self.size[1] - 5, self.size[0] - 1, 5)
		textbox = curses.textpad.Textbox(console)

		# Curses may raise an exception if printing on the edge of the screen;
		# we can just ignore it.
		try:
			console.addstr(0, 0, message, curses.color_pair(
				self._pair_error
			) | curses.A_BOLD)
		except curses.error:
			pass

		# Custom validator simply exits on any key.
		def validator(cmd):
			EXIT = 7
			return EXIT

		textbox.edit(validator)
		self.screen.clear()
		self.on_resize()

	def print_page(self):
		""" Print current page to screen. We use the previously generated
		'__pages' dictionary to easily associate a label to a Salis function.
		"""
		# Update selected proc data if in WORLD view.
		if self.current_page == "WORLD":
			self.__sim.lib.sal_proc_get_proc_data(self.selected_proc, cast(
				self.selected_proc_data, POINTER(c_uint32)
			))

		# Print MAIN simulation data.
		self.__print_line(
			1, "SALIS[{}]".format(self.__sim.args.file), curses.color_pair(
				self._pair_header
			) | curses.A_BOLD
		)
		self.__print_widget(2, self.__main)

		# Print data of currently selected page.
		main_lines = len(self.__main) + 3
		self.__print_header(main_lines, self.current_page)
		self.__print_widget(main_lines + 1, self.__pages[self.current_page])

		# Print special widgets (WORLD view and PROCESS list).
		if self.current_page == "WORLD":
			self.world.render()
		elif self.current_page == "PROCESS":
			self.__print_proc_list()


	###############################
	# Private methods
	###############################

	def __set_colors(self):
		""" Define the color pairs for the data printer.
		"""
		curses.start_color()
		curses.use_default_colors()
		self._pair_header = self.get_color_pair(curses.COLOR_BLUE)
		self._pair_selected = self.get_color_pair(curses.COLOR_YELLOW)
		self._pair_error = self.get_color_pair(curses.COLOR_RED)

	def __get_screen(self):
		""" Prepare and return the main curses window. We also set a shorter
		delay when responding to a pressed escape key.
		"""
		# Set a shorter delay to the ESCAPE key, so that we may use it to exit
		# Salis.
		os.environ.setdefault("ESCDELAY", "25")

		# Prepare curses screen.
		screen = curses.initscr()
		curses.noecho()
		curses.cbreak()
		screen.keypad(True)
		curses.curs_set(False)

		# We need color support in order to run the printer module.
		if curses.has_colors():
			self.__set_colors()
		else:
			raise RuntimeError("Error: no color support.")

		return screen

	def __get_inst_list(self):
		""" Parse instruction set from C header file named 'instset.h'. We're
		using the keyword 'SALIS_INST' to identify an instruction definition,
		so be careful not to use this keyword anywhere else on the headers.
		"""
		inst_list = []
		inst_file = os.path.join(self.__sim.path, "../include/instset.h")

		with open(inst_file, "r") as f:
			lines = f.read().splitlines()

		for line in lines:
			if line and line.split()[0] == "SALIS_INST":
				inst_name = line.split()[1][:4]
				inst_symb = line.split()[3]
				inst_list.append((inst_name, inst_symb))

		return inst_list

	def __get_proc_elements(self):
		""" Parse process structure member variables from C header file named
		'process.h'. We're using the keyword 'SALIS_PROC_ELEMENT' to identify
		element declarations, so be careful not to use this keyword anywhere
		else on the headers.
		"""
		proc_elem_list = []
		proc_elem_file = os.path.join(self.__sim.path, "../include/process.h")

		with open(proc_elem_file, "r") as f:
			lines = f.read().splitlines()

		for line in lines:
			if line and line.split()[0] == "SALIS_PROC_ELEMENT":
				proc_elem_name = line.split()[2].split(";")[0]

				if proc_elem_name == "stack[8]":
					# The stack is a special member variable, an array. We
					# translate it by returning a list of stack identifiers.
					proc_elem_list += ["stack[{}]".format(i) for i in range(8)]
				else:
					# We can assume all other struct elements are single
					# variables.
					proc_elem_list.append(proc_elem_name)

		return proc_elem_list

	def __get_main(self):
		""" Generate main set of data fields to be printed. We associate, on a
		list object, a label to each Salis function to be called. The following
		elements get printed on all pages.
		"""
		return [
			("e", "cycle", self.__sim.lib.sal_main_get_cycle),
			("e", "epoch", self.__sim.lib.sal_main_get_epoch),
			("e", "state", lambda: self.__sim.state),
			("e", "autosave", lambda: self.__sim.autosave),
		]

	def __get_pages(self):
		""" Generate data fields to be printed on each page. We associate, on a
		list object, a label to each Salis function to be called. Each list
		represents a PAGE. We initialize all pages inside an ordered dictionary
		object.
		"""
		# The following comprehensions build up widgets to help up print sets
		# of data elements. The use of nested lambdas is needed to receive
		# updated values.
		# Instruction counter widget:
		inst_widget = [("e", inst[0], (lambda j: (
			lambda: self.__sim.lib.sal_mem_get_inst_count(j)
		))(i)) for i, inst in enumerate(self.inst_list)]

		# Evolver module state widget:
		state_widget = [("e", "state[{}]".format(i), (lambda j: (
			lambda: self.__sim.lib.sal_evo_get_state(j)
		))(i)) for i in range(4)]

		# Selected process state widget:
		selected_widget = [("p", element, (lambda j: (
			lambda: self.selected_proc_data[j]
		))(i)) for i, element in enumerate(self.proc_elements)]

		# With the help of the widgets above, we can declare the PAGES
		# dictionary object.
		return OrderedDict([
			("MEMORY", [
				("e", "order", self.__sim.lib.sal_mem_get_order),
				("e", "size", self.__sim.lib.sal_mem_get_size),
				("e", "allocated", self.__sim.lib.sal_mem_get_allocated),
				("s", ""),
				("h", "INSTRUCTIONS"),
			] + inst_widget),
			("EVOLVER", [
				("e", "last", self.__sim.lib.sal_evo_get_last_changed_address),
				("e", "calls", self.__sim.lib.sal_evo_get_calls_on_last_cycle),
			] + state_widget),
			("PROCESS", [
				("e", "count", self.__sim.lib.sal_proc_get_count),
				("e", "capacity", self.__sim.lib.sal_proc_get_capacity),
				("e", "first", self.__sim.lib.sal_proc_get_first),
				("e", "last", self.__sim.lib.sal_proc_get_last),
				("e", "selected", lambda: self.selected_proc),
			]),
			("WORLD", [
				("e", "position", lambda: self.world.pos),
				("e", "zoom", lambda: self.world.zoom),
				("e", "selected", lambda: self.selected_proc),
				("s", ""),
				("h", "SELECTED PROC"),
			] + selected_widget),
		])

	def __print_line(self, ypos, line, attrs=curses.A_NORMAL, scroll=True):
		""" Print a single line on screen only when it's visible.
		"""
		if scroll:
			ypos -= self.__main_scroll

		if 0 <= ypos < self.size[0]:
			# Curses raises an exception each time we print on the screen's
			# edge. We can just catch and ignore it.
			try:
				line = line[:self.size[1] - 1]
				self.screen.addstr(ypos, 1, line, attrs)
			except curses.error:
				pass

	def __print_header(self, ypos, line):
		""" Print a bold header.
		"""
		header_attr = curses.A_BOLD | curses.color_pair(self._pair_header)
		self.__print_line(ypos, line, header_attr)

	def __print_value(self, ypos, element, value, attr=curses.A_NORMAL):
		""" Print a label:value pair.
		"""
		if type(value) == int:
			if value == ((2 ** 32) - 1):
				# In Salis, UINT32_MAX is used to represent NULL. We print NULL
				# as three dashes.
				value = "---"
			elif self.__print_hex:
				value = hex(value)

		line = "{:<10} : {:>10}".format(element, value)
		self.__print_line(ypos, line, attr)

	def __print_proc_element(self, ypos, element, value):
		""" Print elements of currently selected process. We highlight in
		YELLOW if the selected process is running.
		"""
		if self.__sim.lib.sal_proc_is_free(self.selected_proc):
			attr = curses.A_NORMAL
		else:
			attr = curses.color_pair(self._pair_selected)

		self.__print_value(ypos, element, value, attr)

	def __print_widget(self, ypos, widget):
		""" Print a widget (data PAGE) on screen.
		"""
		for i, element in enumerate(widget):
			if element[0] == "s":
				continue
			elif element[0] == "h":
				self.__print_header(i + ypos, element[1])
			elif element[0] == "e":
				self.__print_value(i + ypos, element[1], element[2]())
			elif element[0] == "p":
				self.__print_proc_element(i + ypos, element[1], element[2]())

	def __clear_line(self, ypos):
		""" Clear the specified line.
		"""
		if 0 <= ypos < self.size[0]:
			self.screen.move(ypos, 0)
			self.screen.clrtoeol()

	def __print_proc_data_list(self):
		""" Print list of process data elements in PROCESS page. We can toggle
		between printing the data elements or the genomes by pressing the 'g'
		key.
		"""
		# First, print the table header, by extracting element names from the
		# previously generated proc element list.
		ypos = len(self.__main) + len(self.__pages["PROCESS"]) + 5
		header = " | ".join(["{:<10}".format("pidx")] + [
			"{:>10}".format(element)
			for element in self.proc_elements[self.__proc_element_scroll:]
		])
		self.__clear_line(ypos)
		self.__print_header(ypos, header)
		ypos += 1
		proc_id = self.proc_list_scroll

		# Print all proc IDs and elements in decimal or hexadecimal format,
		# depending on hex-flag being set.
		if self.__print_hex:
			data_format = lambda x: hex(x)
		else:
			data_format = lambda x: x

		# Lastly, iterate all lines and print as much process data as it fits.
		# We can scroll the process data table using the 'wasd' keys.
		while ypos < self.size[0]:
			self.__clear_line(ypos)

			if proc_id < self.__sim.lib.sal_proc_get_capacity():
				if proc_id == self.selected_proc:
					# Always highlight the selected process.
					attr = curses.color_pair(self._pair_selected)
				else:
					attr = curses.A_NORMAL

				# Retrieve a copy of the selected process state and store it in
				# a list object.
				proc_data = (c_uint32 * len(self.proc_elements))()
				self.__sim.lib.sal_proc_get_proc_data(proc_id, cast(
					proc_data, POINTER(c_uint32))
				)

				# Lastly, assemble and print the next table row.
				row = " | ".join(["{:<10}".format(data_format(proc_id))] + [
					"{:>10}".format(data_format(element))
					for element in proc_data[self.__proc_element_scroll:]
				])
				self.__print_line(ypos, row, attr)

			proc_id += 1
			ypos += 1

	def __print_proc_gene_block(
		self, ypos, gidx, xpos, mbs, mba, ip, sp, pair
	):
		""" Print a sub-set of a process genome. Namely, on of its two memory
		blocks.
		"""
		while gidx < mbs and xpos < self.size[1]:
			gaddr = mba + gidx

			if gaddr == ip:
				attr = curses.color_pair(self.world.pair_sel_ip)
			elif gaddr == sp:
				attr = curses.color_pair(self.world.pair_sel_sp)
			else:
				attr = curses.color_pair(pair)

			# Retrieve instruction from memory and transform it to correct
			# symbol.
			inst = self.__sim.lib.sal_mem_get_inst(gaddr)
			symb = self.inst_list[inst][1]

			# Curses raises an exception each time we print on the screen's
			# edge. We can just catch and ignore it.
			try:
				self.screen.addstr(ypos, xpos, symb, attr)
			except curses.error:
				pass

			gidx += 1
			xpos += 1

		return xpos

	def __print_proc_gene(self, ypos, proc_id):
		""" Print a single process genome on the genome table. We use the same
		colors to represent memory blocks, IP and SP of each process, as those
		used to represent the selected process on WORLD view.
		"""
		# There's nothing to print if process is free.
		if self.__sim.lib.sal_proc_is_free(proc_id):
			return

		# Process is alive. Retrieve a copy of the current process state and
		# store it in a list object.
		proc_data = (c_uint32 * len(self.proc_elements))()
		self.__sim.lib.sal_proc_get_proc_data(proc_id, cast(
			proc_data, POINTER(c_uint32))
		)

		# Let's extract all data of interest.
		mb1a = proc_data[self.proc_elements.index("mb1a")]
		mb1s = proc_data[self.proc_elements.index("mb1s")]
		mb2a = proc_data[self.proc_elements.index("mb2a")]
		mb2s = proc_data[self.proc_elements.index("mb2s")]
		ip = proc_data[self.proc_elements.index("ip")]
		sp = proc_data[self.proc_elements.index("sp")]

		# Always print MAIN memory block (mb1) first (on the left side). That
		# way we can keep most of our attention on the parent.
		xpos = self.__print_proc_gene_block(
			ypos, self.__proc_gene_scroll, 14, mb1s, mb1a, ip, sp,
			self.world.pair_sel_mb1
		)

		# Reset gene counter and print child memory block, if it exists.
		if mb1s < self.__proc_gene_scroll:
			gidx = self.__proc_gene_scroll - mb1s
		else:
			gidx = 0

		self.__print_proc_gene_block(
			ypos, gidx, xpos, mb2s, mb2a, ip, sp, self.world.pair_sel_mb2
		)

	def __print_proc_gene_list(self):
		""" Print list of process genomes in PROCESS page. We can toggle
		between printing the genomes or the data elements by pressing the 'g'
		key.
		"""
		# Print all proc IDs and gene scroll in decimal or hexadecimal format,
		# depending on hex-flag being set.
		if self.__print_hex:
			data_format = lambda x: hex(x)
		else:
			data_format = lambda x: x

		# First, print the table header. We print the current gene-scroll
		# position for easy reference. Return back to zero scroll with the 'A'
		# key.
		ypos = len(self.__main) + len(self.__pages["PROCESS"]) + 5
		header = "{:<10} | genes {} -->".format(
			"pidx", data_format(self.__proc_gene_scroll)
		)
		self.__clear_line(ypos)
		self.__print_header(ypos, header)
		ypos += 1
		proc_id = self.proc_list_scroll

		# Iterate all lines and print as much genetic data as it fits. We can
		# scroll the gene data table using the 'wasd' keys.
		while ypos < self.size[0]:
			self.__clear_line(ypos)

			if proc_id < self.__sim.lib.sal_proc_get_capacity():
				if proc_id == self.selected_proc:
					# Always highlight the selected process.
					attr = curses.color_pair(self._pair_selected)
				else:
					attr = curses.A_NORMAL

				# Assemble and print the next table row.
				row = "{:<10} |".format(data_format(proc_id))
				self.__print_line(ypos, row, attr)
				self.__print_proc_gene(ypos, proc_id)

			proc_id += 1
			ypos += 1

	def __print_proc_list(self):
		""" Print list of process genomes or process data elements in PROCESS
		page. We can toggle between printing the genomes or the data elements
		by pressing the 'g' key.
		"""
		if self.__proc_gene_view:
			self.__print_proc_gene_list()
		else:
			self.__print_proc_data_list()

	def __proc_select_by_cursor(self):
		""" Select process located on address under cursor, if any exists.
		"""
		# First, calculate address under cursor.
		ypos = self.__curs_y
		xpos = self.__curs_x - World.PADDING
		line_size = self.size[1] - World.PADDING
		address = self.world.pos + (
			((ypos * line_size) + xpos) * self.world.zoom
		)

		# Now, iterate all living processes and try to find one that owns the
		# calculated address.
		if self.__sim.lib.sal_mem_is_address_valid(address):
			for proc_id in range(self.__sim.lib.sal_proc_get_capacity()):
				if not self.__sim.lib.sal_proc_is_free(proc_id):
					proc_data = (c_uint32 * len(self.proc_elements))()
					self.__sim.lib.sal_proc_get_proc_data(proc_id, cast(
						proc_data, POINTER(c_uint32))
					)
					mb1a = proc_data[self.proc_elements.index("mb1a")]
					mb1s = proc_data[self.proc_elements.index("mb1s")]
					mb2a = proc_data[self.proc_elements.index("mb2a")]
					mb2s = proc_data[self.proc_elements.index("mb2s")]

					if (
						mb1a <= address < (mb1a + mb1s) or
						mb2a <= address < (mb2a + mb2s)
					):
						self.selected_proc = proc_id
						break
