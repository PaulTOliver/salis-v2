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
		self._printer = printer
		self._sim = sim
		self._pos = 0
		self._zoom = 1
		self._set_world_colors()

	def render(self):
		""" Function for rendering the world. We get a pre-rendered buffer from
		Salis' memory module (its way faster to pre-render in C) and use that
		to assemble the world image in Python.
		"""
		# Window is so narrow that world is not visible.
		if self._printer.size[1] <= self.PADDING:
			return

		# Get pre-rendered image from Salis' memory module.
		line_width = self._printer.size[1] - self.PADDING
		print_area = self._printer.size[0] * line_width
		c_buffer = (c_uint8 * print_area)()
		self._sim.lib.sal_mem_render_image(
			self._pos, self._zoom, print_area, cast(c_buffer, POINTER(c_uint8))
		)

		# Get data elements of selected process, if it's running, and store
		# them into a convenient dict object.
		if self._sim.lib.sal_proc_is_free(self._printer.selected_proc):
			sel_data = None
		else:
			out_data = self._printer.selected_proc_data
			out_elem = self._printer.proc_elements
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

		for y in range(self._printer.size[0]):
			for x in range(line_width):
				xpad = x + self.PADDING
				addr = self._pos + (self._zoom * bidx)
				symb, attr = self._render_cell(c_buffer[bidx], addr, sel_data)

				# Curses raises an exception when printing on the edge of the
				# screen; we can just ignore it.
				try:
					self._printer.screen.addch(y, xpad, symb, attr)
				except curses.error:
					pass

				bidx += 1

	def zoom_out(self):
		""" Zoom out by a factor of 2 (zoom *= 2).
		"""
		if self._is_world_editable():
			self._zoom = min(self._zoom * 2, self._get_max_zoom())

	def zoom_in(self):
		""" Zoom in by a factor of 2 (zoom //= 2).
		"""
		if self._is_world_editable():
			self._zoom = max(self._zoom // 2, 1)

	def zoom_reset(self):
		""" Reset zoom to a valid value on certain events (i.e. during terminal
		resizing).
		"""
		self._zoom = min(self._zoom, self._get_max_zoom())

	def pan_left(self):
		""" Pan world to the left (pos -= zoom).
		"""
		if self._is_world_editable():
			self._pos = max(self._pos - self._zoom, 0)

	def pan_right(self):
		""" Pan world to the right (pos += zoom).
		"""
		if self._is_world_editable():
			max_pos = self._sim.lib.sal_mem_get_size() - 1
			self._pos = min(self._pos + self._zoom, max_pos)

	def pan_down(self):
		""" Pan world downward (pos += zoom * columns).
		"""
		if self._is_world_editable():
			self._pos = max(self._pos - self._get_line_area(), 0)

	def pan_up(self):
		""" Pan world upward (pos -= zoom * columns).
		"""
		if self._is_world_editable():
			max_pos = self._sim.lib.sal_mem_get_size() - 1
			self._pos = min(self._pos + self._get_line_area(), max_pos)

	def pan_reset(self):
		""" Set world position to zero.
		"""
		if self._is_world_editable():
			self._pos = 0

	def scroll_to(self, pos):
		""" Move world pos to a specified position.
		"""
		if self._is_world_editable():
			if self._sim.lib.sal_mem_is_address_valid(pos):
				self._pos = pos
			else:
				raise RuntimeError("Error: scrolling to an invalid address")

	@property
	def pos(self):
		return self._pos

	@property
	def zoom(self):
		return self._zoom

	@property
	def pair_sel_mb2(self):
		return self._pair_sel_mb2

	@property
	def pair_sel_mb1(self):
		return self._pair_sel_mb1

	@property
	def pair_sel_sp(self):
		return self._pair_sel_sp

	@property
	def pair_sel_ip(self):
		return self._pair_sel_ip

	def _set_world_colors(self):
		""" Define color pairs for rendering the world. Each color has a
		special meaning, referring to the selected process IP, SP and memory
		blocks, or to bit flags currently set on rendered cells.
		"""
		self._pair_free = self._printer.get_color_pair(
			curses.COLOR_BLUE
		)
		self._pair_alloc = self._printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_BLUE
		)
		self._pair_mbstart = self._printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_CYAN
		)
		self._pair_ip = self._printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_WHITE
		)
		self._pair_sel_mb2 = self._printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_GREEN
		)
		self._pair_sel_mb1 = self._printer.get_color_pair(
			curses.COLOR_BLACK, curses.COLOR_YELLOW
		)
		self._pair_sel_sp = self._printer.get_color_pair(
			 curses.COLOR_BLACK, curses.COLOR_MAGENTA
		)
		self._pair_sel_ip = self._printer.get_color_pair(
			 curses.COLOR_BLACK, curses.COLOR_RED
		)

	def _render_cell(self, byte, addr, sel_data=None):
		""" Render a single cell on the WORLD view. All cells are rendered by
		interpreting the values coming in from the buffer. We overlay special
		colors for representing the selected organism's state, on top of the
		more common colors used to represent memory state.
		"""
		# Paint black all cells that are out of memory bounds.
		if not self._sim.lib.sal_mem_is_address_valid(addr):
			return " ", curses.A_NORMAL

		# Check if cell contains part of the currently selected process.
		if sel_data:
			top_addr = addr + self._zoom
			top_mb1a = sel_data["mb1a"] + sel_data["mb1s"]
			top_mb2a = sel_data["mb2a"] + sel_data["mb2s"]

			if addr <= sel_data["ip"] < top_addr:
				pair = self._pair_sel_ip
			elif addr <= sel_data["sp"] < top_addr:
				pair = self._pair_sel_sp
			elif top_addr > sel_data["mb1a"] and top_mb1a > addr:
				pair = self._pair_sel_mb1
			elif top_addr > sel_data["mb2a"] and top_mb2a > addr:
				pair = self._pair_sel_mb2

		# No pair has been selected yet; select pair based on bit-flags.
		if not "pair" in locals():
			if byte >= 0x80:
				pair = self._pair_ip
			elif byte >= 0x40:
				pair = self._pair_mbstart
			elif byte >= 0x20:
				pair = self._pair_alloc
			else:
				pair = self._pair_free

		# Select symbol to represent instructions currently on cell.
		inst = byte % 32

		if self._zoom == 1:
			symb = self._printer.inst_list[inst][1]
		elif inst > 16:
			symb = ":"
		else:
			symb = "."

		# Return tuple containing our post-redered cell.
		return symb, curses.color_pair(pair)

	def _get_max_zoom(self):
		""" Calculate maximum needed zoom so that the entire world fits on the
		terminal window.
		"""
		max_zoom = 1
		line_size = self._printer.size[1] - self.PADDING
		coverage = self._printer.size[0] * line_size

		# We fix a maximum zoom level; otherwise, program may halt on extreme
		# zoom levels.
		while (
			(coverage * max_zoom) < self._sim.lib.sal_mem_get_size() and
			max_zoom < 2 ** 16
		):
			max_zoom *= 2

		return max_zoom

	def _is_world_editable(self):
		""" For this to return True, printer's current page must be WORLD page.
		Additionally, the WORLD panel must be visible on the terminal window
		(i.e. curses.COLS > data_margin).
		"""
		correct_page = self._printer.current_page == "WORLD"
		correct_size = self._printer.size[1] > self.PADDING
		return correct_page and correct_size

	def _get_line_area(self):
		""" Return amount of bytes contained in a printed WORLD line.
		"""
		line_size = self._printer.size[1] - self.PADDING
		line_area = self._zoom * line_size
		return line_area
