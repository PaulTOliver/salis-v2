#include <assert.h>
#include "types.h"
#include "instset.h"
#include "common.h"

static Sender g_sender;
static Receiver g_receiver;

void sal_comm_set_sender(Sender sender)
{
	/* Set sender functor. Whenever an organism calls the SEND instruction,
	this function will get called. When unset, SEND instruction is ignored.
	*/
	assert(sender);
	g_sender = sender;
}

void sal_comm_set_receiver(Receiver receiver)
{
	/* Set receiver functor. Whenever an organism calls the RCVE instruction,
	this function will get called. When unset, RCVE instruction is ignored.
	*/
	assert(receiver);
	g_receiver = receiver;
}

void _sal_comm_send(uint8 inst)
{
	/* Send a single byte (instruction) to the sender. This function is called
	by processes that execute the SEND instruction.
	*/
	assert(sal_is_inst(inst));

	if (g_sender) {
		g_sender(inst);
	}
}

uint8 _sal_comm_receive(void)
{
	/* Receive a single byte (instruction) from the receiver. This function is
	called by processes that execute the RCVE instruction. It returns NOP0 is
	receiver is unset.
	*/
	if (g_receiver) {
		uint8 inst = g_receiver();
		assert(sal_is_inst(inst));
		return inst;
	} else {
		return NOP0;
	}
}
