""" SALIS: Viewer/controller for the SALIS simulator.

File: common.py
Author: Paul Oliver
Email: paul.t.oliver.design@gmail.com

Network communications module for Salis simulator. This module allows for IPC
between individual Salis organisms and different simulations via UDP sockets.
"""

import json
import os
import socket

from ctypes import c_int, c_uint8, CFUNCTYPE


class Common:
	SENDER_TYPE = CFUNCTYPE(c_int, c_uint8)
	RECEIVER_TYPE = CFUNCTYPE(c_uint8)

	def __init__(self, sim, max_buffer_size=4096):
		""" Initialize module with a default buffer size of 4 KiB.
		"""
		self.__sim = sim
		self.__settings_path = self.__get_settings_path()
		self.max_buffer_size = max_buffer_size
		self.in_buffer = bytearray()
		self.out_buffer = bytearray()
		self.sources = []
		self.targets = []

		# Use a global client socket for all output operations.
		self.__client = self.__get_socket()

	def define_functors(self):
		""" Define the C callbacks which we'll pass to the Salis simulator.
		These simply push and pop instructions from the input and output
		buffers whenever organisms call the SEND and RCVE instructions.
		"""
		def sender(inst):
			if len(self.out_buffer) < self.max_buffer_size:
				self.out_buffer.append(inst)

		def receiver():
			if len(self.in_buffer):
				res = self.in_buffer[0]
				self.in_buffer = self.in_buffer[1:]
				return c_uint8(res)
			else:
				return c_uint8(0)

		self.__sender = self.SENDER_TYPE(sender)
		self.__receiver = self.RECEIVER_TYPE(receiver)
		self.__sim.lib.sal_comm_set_sender(self.__sender)
		self.__sim.lib.sal_comm_set_receiver(self.__receiver)

	def add_source(self, address, port):
		""" Create new input socket.
		"""
		sock = self.__get_server(address, port)
		self.sources.append(sock)

	def add_target(self, address, port):
		""" Create new output address/port tuple. We use global output socket
		('self.__client') for output operations.
		"""
		self.targets.append((address, port))

	def remove_source(self, address, port):
		""" Remove an input socket.
		"""
		source = (address, port)
		self.sources = [s for s in self.sources if s.getsockname() != source]

	def remove_target(self, address, port):
		""" Remove an output address/port pair.
		"""
		target = (address, port)
		self.targets = [t for t in self.targets if t != target]

	def link_to_self(self, port):
		""" Create input and output links to 'localhost'.
		"""
		self.add_source(socket.gethostbyname(socket.gethostname()), port)
		self.add_target(socket.gethostbyname(socket.gethostname()), port)

	def cycle(self):
		""" We push all data on the output buffer to all targets and clear it.
		We withdraw incoming data from all source sockets and append it to the
		input buffer.
		"""
		if len(self.out_buffer) and self.targets:
			for target in self.targets:
				self.__client.sendto(self.out_buffer, target)

			# Clear output buffer.
			self.out_buffer = bytearray()

		# Receive data and store on input buffer.
		if len(self.in_buffer) < self.max_buffer_size:
			for source in self.sources:
				try:
					self.in_buffer += source.recv(
						self.max_buffer_size - len(self.in_buffer)
					)
				except socket.error:
					pass

	def load_network_config(self, filename):
		""" Load network configuration from a JSON file.
		"""
		with open(os.path.join(self.__settings_path, filename), "r") as f:
			in_dict = json.load(f)

		self.max_buffer_size = in_dict["max_buffer_size"]

		for source in in_dict["sources"]:
			self.add_source(*source)

		for target in in_dict["targets"]:
			self.add_target(*target)

		for inst in in_dict["in_buffer"]:
			self.in_buffer.append(self.__sim.handler.inst_dict[inst])

		for inst in in_dict["out_buffer"]:
			self.out_buffer.append(self.__sim.handler.inst_dict[inst])

	def save_network_config(self, filename):
		""" Save network configuration to a JSON file.
		"""
		out_dict = {
			"max_buffer_size": self.max_buffer_size,
			"in_buffer": "",
			"out_buffer": "",
			"sources": [s.getsockname() for s in self.sources],
			"targets": self.targets,
		}

		for byte in self.in_buffer:
			out_dict["in_buffer"] += self.__sim.printer.inst_list[byte][1]

		for byte in self.out_buffer:
			out_dict["out_buffer"] += self.__sim.printer.inst_list[byte][1]

		with open(os.path.join(self.__settings_path, filename), "w") as f:
			json.dump(out_dict, f, indent="\t")


	###############################
	# Private methods
	###############################

	def __get_settings_path(self):
		""" Get path to network settings directory.
		"""
		self_path = os.path.dirname(__file__)
		return os.path.join(self_path, "../network")

	def __get_socket(self):
		""" Generate a non-blocking UDP socket.
		"""
		sock = socket.socket(
			socket.AF_INET, socket.SOCK_DGRAM | socket.SOCK_NONBLOCK
		)
		return sock

	def __get_server(self, address, port):
		""" Generate a socket and bind to an address/port pair.
		"""
		serv_socket = self.__get_socket()
		serv_socket.bind((address, port))
		return serv_socket
