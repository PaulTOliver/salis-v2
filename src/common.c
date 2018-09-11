#include <assert.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "types.h"
#include "instset.h"
#include "common.h"

static boolean g_is_init;
static int g_file_desc;

void _sal_comm_init(string pipe)
{
	/* Initialize the common pipe. This module is the only one on Salis that
	makes use of Linux specific headers and types. If you want, feel free to
	port this code into other platforms (should be easy). If you do so, let me
	know and we can incorporate it into the Salis repository.
	*/
	assert(!g_is_init);
	mkfifo(pipe, 0666);
	g_is_init = TRUE;

	/* It's important to open the FIFO file in non-blocking mode, or else the
	simulators might halt if the pipe becomes empty.
	*/
	g_file_desc = open(pipe, O_RDWR | O_NONBLOCK);
	assert(g_file_desc != -1);
}

void _sal_comm_quit(void)
{
	/* Close the common pipe FIFO file from within this instance. An empty pipe
	file will remain unless it gets manually deleted.
	*/
	assert(g_is_init);
	close(g_file_desc);
	g_is_init = FALSE;
	g_file_desc = 0;
}

void _sal_comm_send(uint8 inst)
{
	/* Send a single byte (instruction) to the common pipe. This function is
	called by processes that execute the SEND instruction. Hopefully, some of
	them 'learn' to use this as an advantage.

	In the future, I want to make the common pipe able to communicate across
	local networks (LANs) and over the Internet.
	*/
	assert(g_is_init);
	assert(sal_is_inst(inst));
	write(g_file_desc, &inst, 1);
}

uint8 _sal_comm_receive(void)
{
	/* Receive a single byte (instruction) from the common pipe. This function
	is called by processes that execute the RCVE instruction. If the pipe is
	empty, this function returns the NOP0 instruction.
	*/
	uint8 inst;
	ssize_t res;
	assert(g_is_init);
	res = read(g_file_desc, &inst, 1);

	if (res) {
		assert(sal_is_inst(inst));
		return inst;
	} else {
		return NOP0;
	}
}
