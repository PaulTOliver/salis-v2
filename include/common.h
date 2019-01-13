/**
* @file common.h
* @author Paul Oliver
*
* This module controls the common sender and receiver functors, through which
* communication between different simulations can occur. By calling SEND,
* processes may output local instructions through a network. These instructions
* may then be read by processes running on a different simulation somewhere
* else.
*/

#ifndef SALIS_COMMON_H
#define SALIS_COMMON_H

/* Typedef sender functor type for easy python parsing.
*/
typedef void (*Sender)(uint8 inst);

/* Typedef receiver functor type for easy python parsing.
*/
typedef uint8 (*Receiver)(void);

/* Set sender functor. When unset, SEND instruction does nothing.
* @param sender Sender functor
*/
SALIS_API void sal_comm_set_sender(Sender sender);

/* Set receiver functor. When unset, RCVE instruction does nothing.
* @param receiver Receiver functor
*/
SALIS_API void sal_comm_set_receiver(Receiver receiver);

void _sal_comm_send(uint8 inst);
uint8 _sal_comm_receive(void);

#endif
