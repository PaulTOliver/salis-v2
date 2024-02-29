/**
* @file common.h
* @author Paul Oliver
*
* This module controls the 'common pipe', which is the FIFO file through which
* communication between different simulations can occur. By calling SEND,
* processes may output local instructions through the pipe. These instructions
* may then be read by processes running on a different simulation instance.
*/

#ifndef SALIS_COMMON_H
#define SALIS_COMMON_H

void _sal_comm_init(string pipe);
void _sal_comm_quit(void);
void _sal_comm_send(uint8 inst);
uint8 _sal_comm_receive(void);

#endif
