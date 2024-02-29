/**
* @file evolver.h
* @author Paul Oliver
*
* This module controls all random events in Salis. At its heart lies a
* XOR-Shift pseudo-random number generator with 128 bits of state. It controls
* cosmic rays and rises simulation entropy whenever organisms 'eat'
* information.
*/

#ifndef SALIS_EVOLVER_H
#define SALIS_EVOLVER_H

void _sal_evo_init(void);
void _sal_evo_quit(void);
void _sal_evo_load_from(FILE *file);
void _sal_evo_save_into(FILE *file);

/** Get address where the last cosmic ray landed.
* @return Last address changed by a cosmic ray
*/
SALIS_API uint32 sal_evo_get_last_changed_address(void);

/** Get amount of random numbers generated during the last simulation cycle.
* @return Number of calls to the random number generator during the last cycle
*/
SALIS_API uint32 sal_evo_get_calls_on_last_cycle(void);

/** Access the internal state of the XOR-Shift random number generator.
* @param state_index Index of one of the 32 bit state-blocks [0-4]
* @return State of the 32 bit block
*/
SALIS_API uint32 sal_evo_get_state(uint8 state_index);

void _sal_evo_randomize_at(uint32 address);
void _sal_evo_cycle(void);

#endif
