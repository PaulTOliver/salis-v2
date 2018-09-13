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
	def __init__(self, sim):
		""" Printer constructor. It takes care of starting up curses, defining
		the data pages and setting the printer on its initial state.
		"""
		self._sim = sim
		self._color_pair_count = 0
		self._screen = self._get_screen()
		self._inst_list = self._get_inst_list()
		self._proc_elements = self._get_proc_elements()
		self._main = self._get_main()
		self._pages = self._get_pages()
		self._size = self._screen.getmaxyx()
		self._current_page = "MEMORY"
		self._main_scroll = 0
		self._selected_proc = 0
		self._selected_proc_data = (c_uint32 * len(self._proc_elements))()
		self._proc_list_scroll = 0
		self._proc_element_scroll = 0
		self._proc_gene_scroll = 0
		self._proc_gene_view = False
		self._curs_y = 0
		self._curs_x = 0
		self._print_hex = False
		self._world = World(self, self._sim)

	def __del__(self):
		""" Printer destructor exits curses.
		"""
		curses.endwin()

	def get_color_pair(self, fg, bg=-1):
		""" We use this method to set new color pairs, keeping track of the
		number of pairs already set. We return the new color pair ID.
		"""
		self._color_pair_count += 1
		curses.init_pair(self._color_pair_count, fg, bg)
		return self._color_pair_count

	def get_cmd(self):
		""" This returns the pressed key from the curses handler. It's called
		during the simulation's main loop. Flushing input is important when in
		non-blocking mode.
		"""
		ch = self._screen.getch()
		curses.flushinp()
		return ch

	def set_nodelay(self, nodelay):
		""" Toggles between blocking and non-blocking mode on curses.
		"""
		self._screen.nodelay(nodelay)

	def toggle_hex(self):
		""" Toggle between decimal or hexadecimal printing of all simulation
		state elements.
		"""
		self._print_hex = not self._print_hex

	def on_resize(self):
		""" Called whenever the terminal window gets resized.
		"""
		self._size = self._screen.getmaxyx()
		self.scroll_main()
		self._world.zoom_reset()

	def flip_page(self, offset):
		""" Change data page by given offset (i.e. '1' for next page or '-1'
		for previous one).
		"""
		pidx = list(self._pages.keys()).index(self._current_page)
		pidx = (pidx + offset) % len(self._pages)
		self._current_page = list(self._pages.keys())[pidx]
		self.scroll_main()

	def scroll_main(self, offset=0):
		""" Scrolling is allowed whenever the current page does not fit inside
		the terminal window. This method gets called, with no offset, under
		certain situations, like changing pages, just to make sure the screen
		gets cleared and at least some of the data is always scrolled into
		view.
		"""
		self._screen.clear()
		len_main = len(self._main)
		len_page = len(self._pages[self._current_page])
		max_scroll = (len_main + len_page + 5) - self._size[0]
		self._main_scroll += offset
		self._main_scroll = max(0, min(self._main_scroll, max_scroll))

	def proc_scroll_left(self):
		""" Scroll process data elements or genomes (on PROCESS view) to the
		left.
		"""
		if self._current_page == "PROCESS":
			if self._proc_gene_view:
				self._proc_gene_scroll -= 1
				self._proc_gene_scroll = max(0, self._proc_gene_scroll)
			else:
				self._proc_element_scroll -= 1
				self._proc_element_scroll = max(0, self._proc_element_scroll)

	def proc_scroll_right(self):
		""" Scroll process data elements or genomes (on PROCESS view) to the
		right.
		"""
		if self._current_page == "PROCESS":
			if self._proc_gene_view:
				self._proc_gene_scroll += 1
			else:
				self._proc_element_scroll += 1
				max_scroll = len(self._proc_elements) - 1
				self._proc_element_scroll = min(
					max_scroll, self._proc_element_scroll
				)

	def proc_scroll_down(self):
		""" Scroll process data table (on PROCESS view) up.
		"""
		if self._current_page == "PROCESS":
			self._proc_list_scroll = max(0, self._proc_list_scroll - 1)

	def proc_scroll_up(self):
		""" Scroll process data table (on PROCESS view) down.
		"""
		if self._current_page == "PROCESS":
			self._proc_list_scroll = min(
				self._sim.lib.sal_proc_get_capacity() - 1,
				self._proc_list_scroll + 1
			)

	def proc_scroll_to(self, proc_id):
		""" Scroll process data table (on PROCESS view) to a specific position.
		"""
		if self._current_page == "PROCESS":
			if proc_id < self._sim.lib.sal_proc_get_capacity():
				self._proc_list_scroll = proc_id
			else:
				raise RuntimeError("Error: scrolling to invalid process")

	def proc_scroll_vertical_reset(self):
		""" Scroll process data table (on PROCESS view) back to top.
		"""
		if self._current_page == "PROCESS":
			self._proc_list_scroll = 0

	def proc_scroll_horizontal_reset(self):
		""" Scroll process data or genome table (on PROCESS view) back to the
		left.
		"""
		if self._current_page == "PROCESS":
			if self._proc_gene_view:
				self._proc_gene_scroll = 0
			else:
				self._proc_element_scroll = 0

	def proc_select_prev(self):
		""" Select previous process.
		"""
		if self._current_page in ["PROCESS", "WORLD"]:
			self._selected_proc -= 1
			self._selected_proc %= self._sim.lib.sal_proc_get_capacity()

	def proc_select_next(self):
		""" Select next process.
		"""
		if self._current_page in ["PROCESS", "WORLD"]:
			self._selected_proc += 1
			self._selected_proc %= self._sim.lib.sal_proc_get_capacity()

	def proc_select_first(self):
		""" Select first process on reaper queue.
		"""
		if self._current_page in ["PROCESS", "WORLD"]:
			if self._sim.lib.sal_proc_get_count():
				self._selected_proc = self._sim.lib.sal_proc_get_first()

	def proc_select_last(self):
		""" Select last process on reaper queue.
		"""
		if self._current_page in ["PROCESS", "WORLD"]:
			if self._sim.lib.sal_proc_get_count():
				self._selected_proc = self._sim.lib.sal_proc_get_last()

	def proc_select_by_id(self, proc_id):
		""" Select process from given ID.
		"""
		if proc_id < self._sim.lib.sal_proc_get_capacity():
			self._selected_proc = proc_id
		else:
			raise RuntimeError("Error: attempting to select non-existing proc")

	def proc_scroll_to_selected(self):
		""" Scroll WORLD or PROCESS page so that selected process becomes
		visible.
		"""
		if self._current_page == "PROCESS":
			self._proc_list_scroll = self._selected_proc
		elif self._current_page == "WORLD":
			if not self._sim.lib.sal_proc_is_free(self._selected_proc):
				index = self._proc_elements.index("mb1a")
				address = self._selected_proc_data[index]
				self._world.scroll_to(address)

	def proc_toggle_gene_view(self):
		""" Toggle between data element or genome view on PROCESS page.
		"""
		if self._current_page == "PROCESS":
			self._proc_gene_view = not self._proc_gene_view

	def run_cursor(self):
		""" We can toggle a visible cursor on WORLD view to aid us in selecting
		processes.
		"""
		if self._current_page == "WORLD" and self._size[1] > World.PADDING:
			curses.curs_set(True)

			while True:
				self._curs_y = max(0, min(self._curs_y, self._size[0] - 1))
				self._curs_x = max(World.PADDING, min(
					self._curs_x, self._size[1] - 1
				))
				self._screen.move(self._curs_y, self._curs_x)
				cmd = self._screen.getch()

				if cmd in [ord("c"), curses.KEY_RESIZE, Handler.ESCAPE_KEY]:
					self.on_resize()
					break
				elif cmd == curses.KEY_LEFT:
					self._curs_x -= 1
				elif cmd == curses.KEY_RIGHT:
					self._curs_x += 1
				elif cmd == curses.KEY_DOWN:
					self._curs_y += 1
				elif cmd == curses.KEY_UP:
					self._curs_y -= 1
				elif cmd == ord("\n"):
					self._proc_select_by_cursor()
					break

			curses.curs_set(False)

	def run_console(self):
		""" Run the Salis console. You can use the console to control all main
		aspects of the simulation, like compiling genomes into memory, creating
		or killing organisms, setting auto-save interval, among other stuff.
		"""
		# Print a pythonic prompt.
		self._print_line(self._size[0] - 1, ">>> ", scroll=False)
		self._screen.refresh()

		# Create the console child window. We turn it into a Textbox object in
		# order to allow line-editing and extract output easily.
		console = curses.newwin(1, self._size[1] - 5, self._size[0] - 1, 5)
		textbox = curses.textpad.Textbox(console, insert_mode=True)
		textbox.stripspaces = True

		# Grab a copy of the console history and instantiate a pointer to the
		# last element.
		history = self._sim.handler.console_history + [""]
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

			if cmd in [curses.KEY_RESIZE, Handler.ESCAPE_KEY]:
				console.clear()
				return EXIT
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

		# Finally, extract data from console and send to handler.
		self._sim.handler.handle_console(output)
		self._screen.clear()

	def show_console_error(self, message):
		""" Shows Salis console error messages, if any. These messages might
		contain actual python exception output.
		"""
		self._print_line(self._size[0] - 1, ">>>", curses.color_pair(
			self._pair_error
		) | curses.A_BOLD)
		self._screen.refresh()

		# We also use a Textbox object, just so that execution gets halted
		# until a key gets pressed (even on non-blocking mode).
		console = curses.newwin(1, self._size[1] - 5, self._size[0] - 1, 5)
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
		self._screen.clear()

	def print_page(self):
		""" Print current page to screen. We use the previously generated
		'_pages' dictionary to easily associate a label to a Salis function.
		"""
		# Update selected proc data if in WORLD view.
		if self._current_page == "WORLD":
			self._sim.lib.sal_proc_get_proc_data(self._selected_proc, cast(
				self._selected_proc_data, POINTER(c_uint32)
			))

		# Print MAIN simulation data.
		self._print_line(
			1, "SALIS[{}]".format(self._sim.args.file), curses.color_pair(
				self._pair_header
			) | curses.A_BOLD
		)
		self._print_widget(2, self._main)

		# Print data of currently selected page.
		main_lines = len(self._main) + 3
		self._print_header(main_lines, self._current_page)
		self._print_widget(main_lines + 1, self._pages[self._current_page])

		# Print special widgets (WORLD view and PROCESS list).
		if self._current_page == "WORLD":
			self._world.render()
		elif self._current_page == "PROCESS":
			self._print_proc_list()

	@property
	def screen(self):
		return self._screen

	@property
	def inst_list(self):
		return self._inst_list

	@property
	def proc_elements(self):
		return self._proc_elements

	@property
	def size(self):
		return self._size

	@property
	def current_page(self):
		return self._current_page

	@property
	def selected_proc(self):
		return self._selected_proc

	@property
	def selected_proc_data(self):
		return self._selected_proc_data

	@property
	def proc_list_scroll(self):
		return self._proc_list_scroll

	@property
	def world(self):
		return self._world

	def _set_colors(self):
		""" Define the color pairs for the data printer.
		"""
		curses.start_color()
		curses.use_default_colors()
		self._pair_header = self.get_color_pair(curses.COLOR_BLUE)
		self._pair_selected = self.get_color_pair(curses.COLOR_YELLOW)
		self._pair_error = self.get_color_pair(curses.COLOR_RED)

	def _get_screen(self):
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
			self._set_colors()
		else:
			raise RuntimeError("Error: no color support.")

		return screen

	def _get_inst_list(self):
		""" Parse instruction set from C header file named 'instset.h'. We're
		using the keyword 'SALIS_INST' to identify an instruction definition,
		so be careful not to use this keyword anywhere else on the headers.
		"""
		inst_list = []
		inst_file = os.path.join(self._sim.path, "../include/instset.h")

		with open(inst_file, "r") as f:
			lines = f.read().splitlines()

		for line in lines:
			if line and line.split()[0] == "SALIS_INST":
				inst_name = line.split()[1][:4]
				inst_symb = line.split()[3]
				inst_list.append((inst_name, inst_symb))

		return inst_list

	def _get_proc_elements(self):
		""" Parse process structure member variables from C header file named
		'process.h'. We're using the keyword 'SALIS_PROC_ELEMENT' to identify
		element declarations, so be careful not to use this keyword anywhere
		else on the headers.
		"""
		proc_elem_list = []
		proc_elem_file = os.path.join(self._sim.path, "../include/process.h")

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

	def _get_main(self):
		""" Generate main set of data fields to be printed. We associate, on a
		list object, a label to each Salis function to be called. The following
		elements get printed on all pages.
		"""
		return [
			("e", "cycle", self._sim.lib.sal_main_get_cycle),
			("e", "epoch", self._sim.lib.sal_main_get_epoch),
			("e", "state", lambda: self._sim.state),
			("e", "autosave", lambda: self._sim.autosave),
		]

	def _get_pages(self):
		""" Generate data fields to be printed on each page. We associate, on a
		list object, a label to each Salis function to be called. Each list
		represents a PAGE. We initialize all pages inside an ordered dictionary
		object.
		"""
		# The following widgets help up print special sets of data elements.
		# The use of nested lambdas is needed to receive updated values.
		# Instruction counter widget:
		inst_widget = [("e", inst[0], (lambda j: (
			lambda: self._sim.lib.sal_mem_get_inst_count(j)
		))(i)) for i, inst in enumerate(self._inst_list)]

		# Evolver module state widget:
		state_widget = [("e", "state[{}]".format(i), (lambda j: (
			lambda: self._sim.lib.sal_evo_get_state(j)
		))(i)) for i in range(4)]

		# Selected process state widget:
		selected_widget = [("p", element, (lambda j: (
			lambda: self._selected_proc_data[j]
		))(i)) for i, element in enumerate(self._proc_elements)]

		# With the help of the widgets above, we can declare the PAGES
		# dictionary object.
		return OrderedDict([
			("MEMORY", [
				("e", "order", self._sim.lib.sal_mem_get_order),
				("e", "size", self._sim.lib.sal_mem_get_size),
				("e", "blocks", self._sim.lib.sal_mem_get_block_start_count),
				("e", "allocated", self._sim.lib.sal_mem_get_allocated_count),
				("e", "ips", self._sim.lib.sal_mem_get_ip_count),
				("s", ""),
				("h", "INSTRUCTIONS"),
			] + inst_widget),
			("EVOLVER", [
				("e", "last", self._sim.lib.sal_evo_get_last_changed_address),
				("e", "calls", self._sim.lib.sal_evo_get_calls_on_last_cycle),
			] + state_widget),
			("PROCESS", [
				("e", "count", self._sim.lib.sal_proc_get_count),
				("e", "capacity", self._sim.lib.sal_proc_get_capacity),
				("e", "first", self._sim.lib.sal_proc_get_first),
				("e", "last", self._sim.lib.sal_proc_get_last),
				("e", "exec",
					self._sim.lib.sal_proc_get_instructions_executed
				),
			]),
			("WORLD", [
				("e", "position", lambda: self._world.pos),
				("e", "zoom", lambda: self._world.zoom),
				("e", "selected", lambda: self._selected_proc),
				("s", ""),
				("h", "SELECTED PROC"),
			] + selected_widget),
		])

	def _print_line(self, ypos, line, attrs=curses.A_NORMAL, scroll=True):
		""" Print a single line on screen only when it's visible.
		"""
		if scroll:
			ypos -= self._main_scroll

		if 0 <= ypos < self._size[0]:
			# Curses raises an exception each time we print on the screen's
			# edge. We can just catch and ignore it.
			try:
				line = line[:self._size[1] - 1]
				self._screen.addstr(ypos, 1, line, attrs)
			except curses.error:
				pass

	def _print_header(self, ypos, line):
		""" Print a bold header.
		"""
		header_attr = curses.A_BOLD | curses.color_pair(self._pair_header)
		self._print_line(ypos, line, header_attr)

	def _print_value(self, ypos, element, value, attr=curses.A_NORMAL):
		""" Print a label:value pair.
		"""
		if type(value) == int:
			if value == ((2 ** 32) - 1):
				# In Salis, UINT32_MAX is used to represent NULL. We print NULL
				# as three dashes.
				value = "---"
			elif self._print_hex:
				value = hex(value)

		line = "{:<10} : {:>10}".format(element, value)
		self._print_line(ypos, line, attr)

	def _print_proc_element(self, ypos, element, value):
		""" Print elements of currently selected process. We highlight in
		YELLOW if the selected process is running.
		"""
		if self._sim.lib.sal_proc_is_free(self._selected_proc):
			attr = curses.A_NORMAL
		else:
			attr = curses.color_pair(self._pair_selected)

		self._print_value(ypos, element, value, attr)

	def _print_widget(self, ypos, widget):
		""" Print a widget (data PAGE) on screen.
		"""
		for i, element in enumerate(widget):
			if element[0] == "s":
				continue
			elif element[0] == "h":
				self._print_header(i + ypos, element[1])
			elif element[0] == "e":
				self._print_value(i + ypos, element[1], element[2]())
			elif element[0] == "p":
				self._print_proc_element(i + ypos, element[1], element[2]())

	def _clear_line(self, ypos):
		""" Clear the specified line.
		"""
		if 0 <= ypos < self._size[0]:
			self._screen.move(ypos, 0)
			self._screen.clrtoeol()

	def _print_proc_data_list(self):
		""" Print list of process data elements in PROCESS page. We can toggle
		between printing the data elements or the genomes by pressing the 'g'
		key.
		"""
		# First, print the table header, by extracting element names from the
		# previously generated proc element list.
		ypos = len(self._main) + len(self._pages["PROCESS"]) + 5
		header = " | ".join(["{:<10}".format("pidx")] + [
			"{:>10}".format(element)
			for element in self._proc_elements[self._proc_element_scroll:]
		])
		self._clear_line(ypos)
		self._print_header(ypos, header)
		ypos += 1
		proc_id = self._proc_list_scroll

		# Print all proc elements in decimal or hexadecimal format, depending
		# on hex-flag being set.
		if self._print_hex:
			data_format = lambda x: hex(x)
		else:
			data_format = lambda x: x

		# Lastly, iterate all lines and print as much process data as it fits.
		# We can scroll the process data table using the 'wasd' keys.
		while ypos < self._size[0]:
			self._clear_line(ypos)

			if proc_id < self._sim.lib.sal_proc_get_capacity():
				if proc_id == self._selected_proc:
					# Always highlight the selected process.
					attr = curses.color_pair(self._pair_selected)
				else:
					attr = curses.A_NORMAL

				# Retrieve a copy of the selected process state and store it in
				# a list object.
				proc_data = (c_uint32 * len(self._proc_elements))()
				self._sim.lib.sal_proc_get_proc_data(proc_id, cast(
					proc_data, POINTER(c_uint32))
				)

				# Lastly, assemble and print the next table row.
				row = " | ".join(["{:<10}".format(proc_id)] + [
					"{:>10}".format(data_format(element))
					for element in proc_data[self._proc_element_scroll:]
				])
				self._print_line(ypos, row, attr)

			proc_id += 1
			ypos += 1

	def _print_proc_gene_block(self, ypos, gidx, xpos, mbs, mba, ip, sp, pair):
		""" Print a sub-set of a process genome. Namely, on of its two memory
		blocks.
		"""
		while gidx < mbs and xpos < curses.COLS:
			gaddr = mba + gidx

			if gaddr == ip:
				attr = curses.color_pair(self._world.pair_sel_ip)
			elif gaddr == sp:
				attr = curses.color_pair(self._world.pair_sel_sp)
			else:
				attr = curses.color_pair(pair)

			# Retrieve instruction from memory and transform it to correct
			# symbol.
			inst = self._sim.lib.sal_mem_get_inst(gaddr)
			symb = self._inst_list[inst][1]

			# Curses raises an exception each time we print on the screen's
			# edge. We can just catch and ignore it.
			try:
				self._screen.addch(ypos, xpos, symb, attr)
			except curses.error:
				pass

			gidx += 1
			xpos += 1

		return xpos

	def _print_proc_gene(self, ypos, proc_id):
		""" Print a single process genome on the genome table. We use the same
		colors to represent memory blocks, IP and SP of each process, as those
		used to represent the selected process on WORLD view.
		"""
		# There's nothing to print if process is free.
		if self._sim.lib.sal_proc_is_free(proc_id):
			return

		# Process is alive. Retrieve a copy of the current process state and
		# store it in a list object.
		proc_data = (c_uint32 * len(self._proc_elements))()
		self._sim.lib.sal_proc_get_proc_data(proc_id, cast(
			proc_data, POINTER(c_uint32))
		)

		# Let's extract all data of interest.
		mb1a = proc_data[self._proc_elements.index("mb1a")]
		mb1s = proc_data[self._proc_elements.index("mb1s")]
		mb2a = proc_data[self._proc_elements.index("mb2a")]
		mb2s = proc_data[self._proc_elements.index("mb2s")]
		ip = proc_data[self._proc_elements.index("ip")]
		sp = proc_data[self._proc_elements.index("sp")]

		# Always print MAIN memory block (mb1) first (on the left side). That
		# way we can keep most of our attention on the parent.
		xpos = self._print_proc_gene_block(
			ypos, self._proc_gene_scroll, 14, mb1s, mb1a, ip, sp,
			self._world.pair_sel_mb1
		)

		# Reset gene counter and print child memory block, if it exists.
		if mb1s < self._proc_gene_scroll:
			gidx = self._proc_gene_scroll - mb1s
		else:
			gidx = 0

		self._print_proc_gene_block(
			ypos, gidx, xpos, mb2s, mb2a, ip, sp, self._world.pair_sel_mb2
		)

	def _print_proc_gene_list(self):
		""" Print list of process genomes in PROCESS page. We can toggle
		between printing the genomes or the data elements by pressing the 'g'
		key.
		"""
		# First, print the table header. We print the current gene-scroll
		# position for easy reference. Return back to zero scroll with the 'A'
		# key.
		ypos = len(self._main) + len(self._pages["PROCESS"]) + 5
		header = "{:<10} | genes {} -->".format(
			"pidx", self._proc_gene_scroll
		)
		self._clear_line(ypos)
		self._print_header(ypos, header)
		ypos += 1
		proc_id = self._proc_list_scroll

		# Iterate all lines and print as much genetic data as it fits. We can
		# scroll the gene data table using the 'wasd' keys.
		while ypos < self._size[0]:
			self._clear_line(ypos)

			if proc_id < self._sim.lib.sal_proc_get_capacity():
				if proc_id == self._selected_proc:
					# Always highlight the selected process.
					attr = curses.color_pair(self._pair_selected)
				else:
					attr = curses.A_NORMAL

				# Assemble and print the next table row.
				row = "{:<10} |".format(proc_id)
				self._print_line(ypos, row, attr)
				self._print_proc_gene(ypos, proc_id)

			proc_id += 1
			ypos += 1

	def _print_proc_list(self):
		""" Print list of process genomes or process data elements in PROCESS
		page. We can toggle between printing the genomes or the data elements
		by pressing the 'g' key.
		"""
		if self._proc_gene_view:
			self._print_proc_gene_list()
		else:
			self._print_proc_data_list()

	def _proc_select_by_cursor(self):
		""" Select process located on address under cursor, if any exists.
		"""
		# First, calculate address under cursor.
		ypos = self._curs_y
		xpos = self._curs_x - World.PADDING
		line_size = self._size[1] - World.PADDING
		address = self._world.pos + (
			((ypos * line_size) + xpos) * self._world.zoom
		)

		# Now, iterate all living processes and try to find one that owns the
		# calculated address.
		if self._sim.lib.sal_mem_is_address_valid(address):
			for proc_id in range(self._sim.lib.sal_proc_get_capacity()):
				if not self._sim.lib.sal_proc_is_free(proc_id):
					proc_data = (c_uint32 * len(self._proc_elements))()
					self._sim.lib.sal_proc_get_proc_data(proc_id, cast(
						proc_data, POINTER(c_uint32))
					)
					mb1a = proc_data[self._proc_elements.index("mb1a")]
					mb1s = proc_data[self._proc_elements.index("mb1s")]
					mb2a = proc_data[self._proc_elements.index("mb2a")]
					mb2s = proc_data[self._proc_elements.index("mb2s")]

					if (
						mb1a <= address < (mb1a + mb1s) or
						mb2a <= address < (mb2a + mb2s)
					):
						self._selected_proc = proc_id
						break
