""" SALIS: Viewer/controller for the SALIS simulator.

File: world.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

This module should be considered an extension of the 'printer' module. It takes
care of getting a pre-redered image from Salis and post-processing it in order
to print it into the curses screen. It also keeps track of user cntrollable
rendering parameters (position and zoom).
"""

import curses
from ctypes import c_uint8, cast, POINTER


class World:
	PADDING = 25

	def __init__(self, printer, sim):
		""" World constructor. We link to the printer and main simulation
		classes. We also setup the colors for rendering the world.
		"""
		self.__printer = printer
		self.__sim = sim
		self.__set_world_colors()
		self.__show_ip = True
		self.pos = 0
		self.zoom = 1

	def render(self):
		""" Function for rendering the world. We get a pre-rendered buffer from
		Salis' memory module (its way faster to pre-render in C) and use that
		to assemble the world image in Python.
		"""
		# Window is so narrow that world is not visible.
		if self.__printer.size[1] <= self.PADDING:
			return

		# Get pre-rendered image from Salis' memory module.
		line_width = self.__printer.size[1] - self.PADDING
		print_area = self.__printer.size[0] * line_width
		c_buffer = (c_uint8 * print_area)()
		self.__sim.lib.sal_ren_get_image(
			self.pos, self.zoom, print_area, cast(c_buffer, POINTER(c_uint8))
		)

		# Get data elements of selected process, if it's running, and store
		# them into a convenient dict object.
		if self.__sim.lib.sal_proc_is_free(self.__printer.selected_proc):
			sel_data = None
		else:
			out_data = self.__printer.selected_proc_data
			out_elem = self.__printer.proc_elements
			sel_data = {
				"ip": out_data[out_elem.index("ip")],
				"sp": out_data[out_elem.index("sp")],
				"mb1a": out_data[out_elem.index("mb1a")],
				"mb1s": out_data[out_elem.index("mb1s")],
				"mb2a": out_data[out_elem.index("mb2a")],
				"mb2s": out_data[out_elem.index("mb2s")],
			}

		# Iterate all cells on printable area and print the post-rendered
		# cells. Rendered cells contain info about bit flags and instructions
		# currently written into memory.
		bidx = 0

		for y in range(self.__printer.size[0]):
			for x in range(line_width):
				xpad = x + self.PADDING
				addr = self.pos + (self.zoom * bidx)
				symb, attr = self.__render_cell(c_buffer[bidx], addr, sel_data)

				# Curses raises an exception when printing on the edge of the
				# screen; we can just ignore it.
				try:
					self.__printer.screen.addstr(y, xpad, symb, attr)
				except curses.error:
					pass

				bidx += 1

	def zoom_out(self):
		""" Zoom out by a factor of 2 (zoom *= 2).
		"""
		if self.__is_world_editable():
			self.zoom = min(self.zoom * 2, self.__get_max_zoom())

	def zoom_in(self):
		""" Zoom in by a factor of 2 (zoom //= 2).
		"""
		if self.__is_world_editable():
			self.zoom = max(self.zoom // 2, 1)

	def zoom_reset(self):
		""" Reset zoom to a valid value on certain events (i.e. during terminal
		resizing).
		"""
		self.zoom = min(self.zoom, self.__get_max_zoom())

	def pan_left(self):
		""" Pan world to the left (pos -= zoom).
		"""
		if self.__is_world_editable():
			self.pos = max(self.pos - self.zoom, 0)

	def pan_right(self):
		""" Pan world to the right (pos += zoom).
		"""
		if self.__is_world_editable():
			max_pos = self.__sim.lib.sal_mem_get_size() - 1
			self.pos = min(self.pos + self.zoom, max_pos)

	def pan_down(self):
		""" Pan world downward (pos += zoom * columns).
		"""
		if self.__is_world_editable():
			self.pos = max(self.pos - self.__get_line_area(), 0)

	def pan_up(self):
		""" Pan world upward (pos -= zoom * columns).
		"""
		if self.__is_world_editable():
			max_pos = self.__sim.lib.sal_mem_get_size() - 1
			self.pos = min(self.pos + self.__get_line_area(), max_pos)

	def pan_reset(self):
		""" Set world position to zero.
		"""
		if self.__is_world_editable():
			self.pos = 0

	def scroll_to(self, pos):
		""" Move world pos to a specified position.
		"""
		if self.__is_world_editable():
			if self.__sim.lib.sal_mem_is_address_valid(pos):
				self.pos = pos
			else:
				raise RuntimeError("Error: scrolling to an invalid address")

	def toggle_ip_view(self):
		""" Turn on/off IP visualization. Turning off IPs might make it easier
		to visualize the underlying memory block structure.
		"""
		if self.__is_world_editable():
			self.__show_ip = not self.__show_ip

	def __set_world_colors(self):
		""" Define color pairs for rendering the world. Each color has a
		special meaning, referring to the selected process IP, SP and memory
		blocks, or to bit flags currently set on rendered cells.
		"""
		self.pair_free = self.__printer.get_color_pair(
			curses.COLOR_BLUE
		)
		self.pair_alloc = self.__printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_BLUE
		)
		self.pair_mbstart = self.__printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_CYAN
		)
		self.pair_ip = self.__printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_WHITE
		)
		self.pair_sel_mb2 = self.__printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_GREEN
		)
		self.pair_sel_mb1 = self.__printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_YELLOW
		)
		self.pair_sel_sp = self.__printer.get_color_pair(
			 curses.COLOR_BLACK, curses.COLOR_MAGENTA
		)
		self.pair_sel_ip = self.__printer.get_color_pair(
			 curses.COLOR_BLACK, curses.COLOR_RED
		)

	def __render_cell(self, byte, addr, sel_data=None):
		""" Render a single cell on the WORLD view. All cells are rendered by
		interpreting the values coming in from the buffer. We overlay special
		colors for representing the selected organism's state, on top of the
		more common colors used to represent memory state.
		"""
		# Paint black all cells that are out of memory bounds.
		if not self.__sim.lib.sal_mem_is_address_valid(addr):
			return " ", curses.A_NORMAL

		# Check if cell contains part of the currently selected process.
		if sel_data:
			top_addr = addr + self.zoom
			top_mb1a = sel_data["mb1a"] + sel_data["mb1s"]
			top_mb2a = sel_data["mb2a"] + sel_data["mb2s"]

			if addr <= sel_data["ip"] < top_addr:
				pair = self.pair_sel_ip
			elif addr <= sel_data["sp"] < top_addr:
				pair = self.pair_sel_sp
			elif top_addr > sel_data["mb1a"] and top_mb1a > addr:
				pair = self.pair_sel_mb1
			elif top_addr > sel_data["mb2a"] and top_mb2a > addr:
				pair = self.pair_sel_mb2

		# No pair has been selected yet; select pair based on bit-flags.
		if not "pair" in locals():
			if self.__show_ip and byte >= 0x80:
				pair = self.pair_ip
			elif (byte % 0x80) >= 0x40:
				pair = self.pair_mbstart
			elif (byte % 0x40) >= 0x20:
				pair = self.pair_alloc
			else:
				pair = self.pair_free

		# Select symbol to represent instructions currently on cell.
		inst = byte % 32

		if self.zoom == 1:
			symb = self.__printer.inst_list[inst][1]
		elif inst > 16:
			symb = ":"
		else:
			symb = "."

		# Return tuple containing our post-redered cell.
		return symb, curses.color_pair(pair)

	def __get_max_zoom(self):
		""" Calculate maximum needed zoom so that the entire world fits on the
		terminal window.
		"""
		max_zoom = 1
		line_size = self.__printer.size[1] - self.PADDING
		coverage = self.__printer.size[0] * line_size

		# We fix a maximum zoom level; otherwise, program may halt on extreme
		# zoom levels.
		while (
			(coverage * max_zoom) < self.__sim.lib.sal_mem_get_size() and
			max_zoom < 2 ** 16
		):
			max_zoom *= 2

		return max_zoom

	def __is_world_editable(self):
		""" For this to return True, printer's current page must be WORLD page.
		Additionally, the WORLD panel must be visible on the terminal window
		(i.e. curses.COLS > data_margin).
		"""
		correct_page = self.__printer.current_page == "WORLD"
		correct_size = self.__printer.size[1] > self.PADDING
		return correct_page and correct_size

	def __get_line_area(self):
		""" Return amount of bytes contained in a printed WORLD line.
		"""
		line_size = self.__printer.size[1] - self.PADDING
		line_area = self.zoom * line_size
		return line_area
