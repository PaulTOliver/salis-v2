/**
* @file process.h
* @author Paul Oliver
*
* This module allows access to Salis processes, or procs. Procs are the actual
* organisms in the simulation. They consist of a virtual CPU with 4 registers
* and a stack of 8. The instruction pointer (IP) and seeker pointer (SP)
* coordinate the execution of all instructions.
*/

#ifndef SALIS_PROCESS_H
#define SALIS_PROCESS_H

/**
* The Process data-structure. The 'SALIS_PROC_ELEMENT' macro helps python
* parse the struct, so don't change it!
*/
struct Process
{
	SALIS_PROC_ELEMENT uint32 mb1a;
	SALIS_PROC_ELEMENT uint32 mb1s;
	SALIS_PROC_ELEMENT uint32 mb2a;
	SALIS_PROC_ELEMENT uint32 mb2s;
	SALIS_PROC_ELEMENT uint32 ip;
	SALIS_PROC_ELEMENT uint32 sp;
	SALIS_PROC_ELEMENT uint32 rax;
	SALIS_PROC_ELEMENT uint32 rbx;
	SALIS_PROC_ELEMENT uint32 rcx;
	SALIS_PROC_ELEMENT uint32 rdx;
	SALIS_PROC_ELEMENT uint32 stack[8];
};

typedef struct Process Process;

/**
* Get process count.
* @return Amount of running (living) processes
*/
SALIS_API uint32 sal_proc_get_count(void);

/**
* Get reaper queue capacity.
* @return Currently allocated size of reaper queue
*/
SALIS_API uint32 sal_proc_get_capacity(void);

/**
* Get first process.
* @return Process currently on top of reaper queue
*/
SALIS_API uint32 sal_proc_get_first(void);

/**
* Get last process.
* @return Process currently on bottom of reaper queue (closest to death)
*/
SALIS_API uint32 sal_proc_get_last(void);

/**
* Check if process is currently free.
* @param proc_id ID of process whose status we want to check
* @return Status (either free or running) of the process with the given ID
*/
SALIS_API boolean sal_proc_is_free(uint32 proc_id);

/**
* Get process.
* @param proc_id ID of Process being queried
* @return A copy of the process with the given ID
*/
SALIS_API Process sal_proc_get_proc(uint32 proc_id);

/**
* Get process data.
* @param proc_id ID of Process being queried
* @param buffer Pre-allocated buffer to store data on [ > sizeof(Process)]
*/
SALIS_API void sal_proc_get_proc_data(uint32 proc_id, uint32_p buffer);

/**
* Create new process.
* @param address Address we want to allocate our process into
* @param mb1_size Size of the memory block we want to allocate for our process
*/
SALIS_API void sal_proc_create(uint32 address, uint32 mb1_size);

/**
* Kill process on bottom of reaper queue.
*/
SALIS_API void sal_proc_kill(void);

/**
* Mutate a process by performing a register shift.
* @param proc_id ID of Process being mutated
* @param rand_int Pregenerated random number to be used
*/
SALIS_API void sal_proc_mutate(uint32 proc_id, uint32 rand_int);

/*******************************
* PRIVATES                     *
*******************************/

void _sal_proc_init(void);
void _sal_proc_quit(void);
void _sal_proc_load_from(FILE *file);
void _sal_proc_save_into(FILE *file);
void _sal_proc_cycle(void);

#endif
