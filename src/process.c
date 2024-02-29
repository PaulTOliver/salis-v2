#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "types.h"
#include "getter.h"
#include "instset.h"
#include "memory.h"
#include "evolver.h"
#include "common.h"
#include "process.h"

static boolean g_is_init;
static uint32 g_count;
static uint32 g_capacity;
static uint32 g_first;
static uint32 g_last;
static Process *g_procs;

void _sal_proc_init(void)
{
	/*
	* Initialize process module to its initial state. We initialize the reaper
	* queue with a capacity of 1. 'First' and 'last' organism pointers are
	* initialized to (uint32)-1 (to indicate they point to no organism, as no
	* organism exists yet).
	*/
	assert(!g_is_init);
	g_is_init = TRUE;
	g_capacity = 1;
	g_first = UINT32_MAX;
	g_last = UINT32_MAX;
	g_procs = calloc(g_capacity, sizeof(Process));
	assert(g_procs);
}

void _sal_proc_quit(void)
{
	/*
	* Reset process module back to zero; free up the process queue.
	*/
	assert(g_is_init);
	free(g_procs);
	g_is_init = FALSE;
	g_count = 0;
	g_capacity = 0;
	g_first = 0;
	g_last = 0;
	g_procs = NULL;
}

void _sal_proc_load_from(FILE *file)
{
	/*
	* Load process module state from a binary file.
	*/
	assert(!g_is_init);
	assert(file);
	fread(&g_is_init, sizeof(boolean), 1, file);
	fread(&g_count, sizeof(uint32), 1, file);
	fread(&g_capacity, sizeof(uint32), 1, file);
	fread(&g_first, sizeof(uint32), 1, file);
	fread(&g_last, sizeof(uint32), 1, file);
	g_procs = calloc(g_capacity, sizeof(Process));
	assert(g_procs);
	fread(g_procs, sizeof(Process), g_capacity, file);
}

void _sal_proc_save_into(FILE *file)
{
	/*
	* Save process module state to a binary file.
	*/
	assert(g_is_init);
	assert(file);
	fwrite(&g_is_init, sizeof(boolean), 1, file);
	fwrite(&g_count, sizeof(uint32), 1, file);
	fwrite(&g_capacity, sizeof(uint32), 1, file);
	fwrite(&g_first, sizeof(uint32), 1, file);
	fwrite(&g_last, sizeof(uint32), 1, file);
	fwrite(g_procs, sizeof(Process), g_capacity, file);
}

/*
* Getter methods for the process module.
*/
UINT32_GETTER(proc, count)
UINT32_GETTER(proc, capacity)
UINT32_GETTER(proc, first)
UINT32_GETTER(proc, last)

boolean sal_proc_is_free(uint32 proc_id)
{
	/*
	* In Salis, the reaper queue is implemented as a circular queue. Thus, at
	* any given time, a process ID (which actually denotes a process 'address'
	* or, more correctly, a process 'container address') might contain a living
	* process or be empty. This function checks for the 'living' state of a
	* given process ID.
	*/
	assert(g_is_init);
	assert(proc_id < g_capacity);

	if (!g_procs[proc_id].mb1s) {
		/*
		* When running in debug mode, we make sure that non-living processes
		* are completely set to zero, as this is the expected state.
		*/
		#ifndef NDEBUG
			Process dummy_proc;
			memset(&dummy_proc, 0, sizeof(Process));
			assert(!memcmp(&dummy_proc, &g_procs[proc_id], sizeof(Process)));
		#endif

		return TRUE;
	}

	return FALSE;
}

Process sal_proc_get_proc(uint32 proc_id)
{
	/*
	* Get a **copy** (not a reference) of the process with the given ID. Note,
	* this might be a non-living process.
	*/
	assert(g_is_init);
	assert(proc_id < g_capacity);
	return g_procs[proc_id];
}

void sal_proc_get_proc_data(uint32 proc_id, uint32_p buffer)
{
	/*
	* Get a **copy** (not a reference) of the process with the given ID
	* (represented as a string of 32 bit integers) written into the given
	* buffer. The buffer must be pre-allocated to a large enough size (i.e.
	* malloc(sizeof(Process))). Note, copied process might be in a non-living
	* state.
	*/
	assert(g_is_init);
	assert(proc_id < g_capacity);
	assert(buffer);
	memcpy(buffer, &g_procs[proc_id], sizeof(Process));
}

static boolean block_is_free_and_valid(uint32 address, uint32 size)
{
	/*
	* Iterate all addresses in the given memory block and check that they lie
	* within memory bounds and have the ALLOCATED flag unset.
	*/
	uint32 offset;

	for (offset = 0; offset < size; offset++) {
		uint32 off_addr = offset + address;
		if (!sal_mem_is_address_valid(off_addr)) return FALSE;
		if (sal_mem_is_allocated(off_addr)) return FALSE;
	}

	return TRUE;
}

static void realloc_queue(uint32 queue_lock)
{
	/*
	* Reallocate reaper queue into a new circular queue with double the
	* capacity. This function gets called whenever the reaper queue fills up
	* with new organisms.
	*
	* A queue_lock parameter may be provided, which 'centers' the reallocation
	* on a given process ID. This means that, after reallocating the queue, the
	* process with that ID will keep still have the same ID on the new queue.
	*/
	uint32 new_capacity;
	Process *new_queue;
	uint32 fwrd_idx;
	uint32 back_idx;
	assert(g_is_init);
	assert(g_count == g_capacity);
	assert(queue_lock < g_capacity);
	new_capacity = g_capacity * 2;
	new_queue = calloc(new_capacity, sizeof(Process));
	assert(new_queue);
	fwrd_idx = queue_lock;
	back_idx = (queue_lock - 1) % new_capacity;

	/*
	* Copy all organisms that lie forward from queue lock.
	*/
	while (TRUE) {
		uint32 old_idx = fwrd_idx % g_capacity;
		memcpy(&new_queue[fwrd_idx], &g_procs[old_idx], sizeof(Process));

		if (old_idx == g_last) {
			g_last = fwrd_idx;
			break;
		} else {
			fwrd_idx++;
		}
	}

	/*
	* Copy all organisms that lie backwards from queue lock, making sure to
	* loop around the queue (with modulo '%') whenever the process index goes
	* below zero.
	*/
	if (queue_lock != g_first) {
		while (TRUE) {
			uint32 old_idx = back_idx % g_capacity;
			memcpy(&new_queue[back_idx], &g_procs[old_idx], sizeof(Process));

			if (old_idx == g_first) {
				g_first = back_idx;
				break;
			} else {
				back_idx--;
				back_idx %= new_capacity;
			}
		}
	}

	/*
	* Free old reaper queue and re-link global pointer to new queue.
	*/
	free(g_procs);
	g_capacity = new_capacity;
	g_procs = new_queue;
}

static uint32 get_new_proc_from_queue(uint32 queue_lock)
{
	/*
	* Retrieve an unoccupied process ID from the reaper queue. This function
	* gets called whenever a new organism is generated (born).
	*/
	assert(g_is_init);

	/*
	* If reaper queue is full, reallocate to double its current size.
	*/
	if (g_count == g_capacity) {
		realloc_queue(queue_lock);
	}

	g_count++;

	if (g_count == 1) {
		g_first = 0;
		g_last = 0;
		return 0;
	} else {
		g_last++;
		g_last %= g_capacity;
		return g_last;
	}
}

static void proc_create(uint32 address, uint32 size, uint32 queue_lock,
	boolean allocate)
{
	/*
	* Give birth to a new process! We must specify the address and size of the
	* new organism.
	*/
	uint32 pidx;
	assert(g_is_init);
	assert(sal_mem_is_address_valid(address));
	assert(sal_mem_is_address_valid(address + size - 1));

	/*
	* When organisms are generated manually (by an user), we must explicitly
	* allocate its entire memory block. When organisms replicate by themselves,
	* we assume they have already allocated the child's memory, so we don't
	* need to do it here.
	*/
	if (allocate) {
		uint32 offset;
		assert(block_is_free_and_valid(address, size));

		for (offset = 0; offset < size; offset++) {
			uint32 off_addr = offset + address;
			_sal_mem_set_allocated(off_addr);
		}
	}

	/*
	* Get a new process ID for the child process. Also, set initial state of
	* the child process data structure.
	*/
	pidx = get_new_proc_from_queue(queue_lock);
	g_procs[pidx].mb1a = address;
	g_procs[pidx].mb1s = size;
	g_procs[pidx].ip = address;
	g_procs[pidx].sp = address;
}

void sal_proc_create(uint32 address, uint32 mb1s)
{
	/*
	* API function to create a new process. Memory address and size of new
	* process must be provided.
	*/
	assert(g_is_init);
	assert(block_is_free_and_valid(address, mb1s));
	proc_create(address, mb1s, 0, TRUE);
}

static void free_memory_block(uint32 address, uint32 size)
{
	/*
	* Deallocate a memory block.
	*/
	uint32 offset;
	assert(sal_mem_is_address_valid(address));
	assert(sal_mem_is_address_valid(address + size - 1));
	assert(size);

	for (offset = 0; offset < size; offset++) {
		/* Iterate all addresses in block and unset the ALLOCATED flag in them.
		*/
		uint32 off_addr = offset + address;
		assert(sal_mem_is_allocated(off_addr));
		_sal_mem_unset_allocated(off_addr);
	}
}

static void free_memory_owned_by(uint32 pidx)
{
	/*
	* Free memory specifically owned by the process with the given ID.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	free_memory_block(g_procs[pidx].mb1a, g_procs[pidx].mb1s);

	if (g_procs[pidx].mb2s) {
		/*
		* If process owns a child memory block, free it as well.
		*/
		free_memory_block(g_procs[pidx].mb2a, g_procs[pidx].mb2s);
	}
}

static void proc_kill(void)
{
	/*
	* Kill process on bottom of reaper queue (the oldest process).
	*/
	assert(g_is_init);
	assert(g_count);
	assert(g_first != UINT32_MAX);
	assert(g_last != UINT32_MAX);
	assert(!sal_proc_is_free(g_first));

	/*
	* Free up owned memory and reset process data structure back to zero.
	*/
	free_memory_owned_by(g_first);
	memset(&g_procs[g_first], 0, sizeof(Process));
	g_count--;

	if (g_first == g_last) {
		g_first = UINT32_MAX;
		g_last = UINT32_MAX;
	} else {
		g_first++;
		g_first %= g_capacity;
	}
}

void sal_proc_kill(void)
{
	/*
	* API function to kill a process. Make sure that at least one process is
	* alive, or 'assert()' will fail.
	*/
	assert(g_is_init);
	assert(g_count);
	assert(g_first != UINT32_MAX);
	assert(g_last != UINT32_MAX);
	assert(!sal_proc_is_free(g_first));
	proc_kill();
}

static boolean block_is_allocated(uint32 address, uint32 size)
{
	/*
	* Assert that a given memory block is fully allocated.
	*/
	uint32 offset;
	assert(g_is_init);

	for (offset = 0; offset < size; offset++) {
		uint32 off_addr = offset + address;
		assert(sal_mem_is_address_valid(off_addr));
		assert(sal_mem_is_allocated(off_addr));
	}

	return TRUE;
}

static boolean proc_is_valid(uint32 pidx)
{
	/*
	* Assert that the process with the given ID is in a valid state. This
	* means that all of its owned memory must be allocated and that the
	* allocated flags are set in place. IP and SP must be located in valid
	* addresses.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);

	if (!sal_proc_is_free(pidx)) {
		assert(sal_mem_is_address_valid(g_procs[pidx].ip));
		assert(sal_mem_is_address_valid(g_procs[pidx].sp));
		assert(block_is_allocated(g_procs[pidx].mb1a, g_procs[pidx].mb1s));

		if (g_procs[pidx].mb2s) {
			assert(block_is_allocated(g_procs[pidx].mb2a, g_procs[pidx].mb2s));
		}
	}

	return TRUE;
}

static boolean module_is_valid(void)
{
	/*
	* Check for validity of process module. This function only gets called when
	* Salis is running in debug mode. It makes Salis **very** slow in
	* comparison to when running optimized, but it is also **very** useful for
	* debugging!
	*/
	uint32 pidx;
	uint32 alloc_count = 0;
	assert(g_is_init);

	/*
	* Check that each individual process is in a valid state. We can do this
	* in a multi-threaded way.
	*/
	#pragma omp parallel for
	for (pidx = 0; pidx < g_capacity; pidx++) {
		assert(proc_is_valid(pidx));
	}

	/*
	* Iterate all processes, counting their memory blocks and adding up their
	* memory block sizes. At the end, we compare the sums to the flag counters of
	* the memory module.
	*/
	for (pidx = 0; pidx < g_capacity; pidx++) {
		if (!sal_proc_is_free(pidx)) {
			alloc_count += g_procs[pidx].mb1s;

			if (g_procs[pidx].mb2s) {
				assert(g_procs[pidx].mb1a != g_procs[pidx].mb2a);
				alloc_count += g_procs[pidx].mb2s;
			}
		}
	}

	assert(alloc_count == sal_mem_get_allocated());
	return TRUE;
}

static void on_fault(uint32 pidx)
{
	/*
	* For now, faults do nothing.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	(void)pidx;
}

static void increment_ip(uint32 pidx)
{
	/*
	* After executing each instruction, increment the given organism's IP to
	* the next valid address.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (sal_mem_is_address_valid(g_procs[pidx].ip + 1)) {
		g_procs[pidx].ip++;
	}

	/*
	* Wherever IP goes, SP follows. :P
	*/
	g_procs[pidx].sp = g_procs[pidx].ip;
}

static boolean are_templates_complements(uint32 source, uint32 complement)
{
	/*
	* Check whether 2 templates are complements. Templates are introduced in
	* Salis-2.0 and they function in the same way as templates in the original
	* Tierra. They consist of string of NOP0 and NOP1 instructions.
	*
	* We say that templates are complements whenever one is a 'negation' of
	* another (i.e. they are reverse copies of each other). So, on the
	* following example, the top template would be the complement of the bottom
	* template.
	*
	* >>> NOP0 - NOP1 - NOP1
	* >>> NOP1 - NOP0 - NOP0
	*
	* This function looks into 2 given addresses in memory and checks whether
	* there are complementing templates on those addresses.
	*/
	assert(g_is_init);
	assert(sal_mem_is_address_valid(source));
	assert(sal_mem_is_address_valid(complement));
	assert(sal_is_template(sal_mem_get_inst(source)));

	while (
		sal_mem_is_address_valid(source) &&
		sal_is_template(sal_mem_get_inst(source))
	) {
		/*
		* Iterate address by address, checking complementarity on each
		* consecutive byte pair.
		*/
		uint8 inst_src;
		uint8 inst_comp;

		/*
		* If complement head moves to an invalid address, complementarity
		* fails.
		*/
		if (!sal_mem_is_address_valid(complement)) {
			return FALSE;
		}

		inst_src = sal_mem_get_inst(source);
		inst_comp = sal_mem_get_inst(complement);
		assert(inst_src == NOP0 || inst_src == NOP1);

		if (inst_src == NOP0 && inst_comp != NOP1) {
			return FALSE;
		}

		if (inst_src == NOP1 && inst_comp != NOP0) {
			return FALSE;
		}

		source++;
		complement++;
	}

	/*
	* If we get to the end of a template in the source head, and target has
	* been complementary all the way through, we consider these blocks of
	* memory 'complements'.
	*/
	return TRUE;
}

static void increment_sp(uint32 pidx, boolean forward)
{
	/*
	* Increment or decrement SP to the next valid address. This function gets
	* called by organisms during jumps, searches, etc. (i.e. whenever the
	* seeker pointer gets sent on a 'mission').
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (forward && sal_mem_is_address_valid(g_procs[pidx].sp + 1)) {
		g_procs[pidx].sp++;
	}

	if (!forward && sal_mem_is_address_valid(g_procs[pidx].sp - 1)) {
		g_procs[pidx].sp--;
	}
}

static boolean jump_seek(uint32 pidx, boolean forward)
{
	/*
	* Search (via the seeker pointer) for template to jump into. This gets
	* called by organisms each cycle during a JMP instruction. Only when a
	* valid template is found, will this function return TRUE. Otherwise it
	* will return FALSE, signaling the calling process that a template has not
	* yet been found.
	*/
	uint32 next_addr;
	uint8 next_inst;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	next_addr = g_procs[pidx].ip + 1;

	/*
	* This function causes a 'fault' when there is no template right in front
	* of the caller organism's instruction pointer.
	*/
	if (!sal_mem_is_address_valid(next_addr)) {
		on_fault(pidx);
		increment_ip(pidx);
		return FALSE;
	}

	next_inst = sal_mem_get_inst(next_addr);

	if (!sal_is_template(next_inst)) {
		on_fault(pidx);
		increment_ip(pidx);
		return FALSE;
	}

	/*
	* Check for complementarity. Increment seeker pointer if template has not
	* been found yet.
	*/
	if (are_templates_complements(next_addr, g_procs[pidx].sp)) {
		return TRUE;
	}

	increment_sp(pidx, forward);
	return FALSE;
}

static void jump(uint32 pidx)
{
	/*
	* This gets called when an organism has finally found a template to jump
	* into (see function above). Only when in debug mode, we make sure that the
	* entire jump operation has been performed in a valid way.
	*/
	#ifndef NDEBUG
		uint32 next_addr;
		uint8 next_inst;
		uint8 sp_inst;
		assert(g_is_init);
		assert(pidx < g_capacity);
		assert(!sal_proc_is_free(pidx));
		next_addr = g_procs[pidx].ip + 1;
		assert(sal_mem_is_address_valid(next_addr));
		next_inst = sal_mem_get_inst(next_addr);
		sp_inst = sal_mem_get_inst(g_procs[pidx].sp);
		assert(sal_is_template(next_inst));
		assert(sal_is_template(sp_inst));
		assert(are_templates_complements(next_addr, g_procs[pidx].sp));
	#endif

	g_procs[pidx].ip = g_procs[pidx].sp;
}

static boolean addr_seek(uint32 pidx, boolean forward)
{
	/*
	* Search (via the seeker pointer) for template address in memory. This
	* gets called by organisms each cycle during a ADR instruction. Only when a
	* valid template is found, will this function return TRUE. Otherwise it
	* will return FALSE, signaling the calling process that a template has not
	* yet been found.
	*/
	uint32 next1_addr;
	uint32 next2_addr;
	uint8 next1_inst;
	uint8 next2_inst;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	next1_addr = g_procs[pidx].ip + 1;
	next2_addr = g_procs[pidx].ip + 2;

	/*
	* This function causes a 'fault' when there is no register modifier right
	* in front of the caller organism's instruction pointer, and a template
	* just after that.
	*/
	if (
		!sal_mem_is_address_valid(next1_addr) ||
		!sal_mem_is_address_valid(next2_addr)
	) {
		on_fault(pidx);
		increment_ip(pidx);
		return FALSE;
	}

	next1_inst = sal_mem_get_inst(next1_addr);
	next2_inst = sal_mem_get_inst(next2_addr);

	if (!sal_is_mod(next1_inst) || !sal_is_template(next2_inst)) {
		on_fault(pidx);
		increment_ip(pidx);
		return FALSE;
	}

	/*
	* Check for complementarity. Increment seeker pointer if template has not
	* been found yet.
	*/
	if (are_templates_complements(next2_addr, g_procs[pidx].sp)) {
		return TRUE;
	}

	increment_sp(pidx, forward);
	return FALSE;
}

static boolean get_register_pointers(
	uint32 pidx, uint32_p *regs, uint32 reg_count
) {
	/*
	* This function is used to get pointers to a calling organism registers.
	* Specifically, registers returned are those that will be used when
	* executing the caller organism's current instruction.
	*/
	uint32 ridx;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	assert(regs);
	assert(reg_count);
	assert(reg_count < 4);

	/*
	* Iterate 'reg_count' number of instructions forward from the IP, noting
	* down all found register modifiers. If less than 'reg_count' modifiers are
	* found, this function returns FALSE (triggering a 'fault').
	*/
	for (ridx = 0; ridx < reg_count; ridx++) {
		uint32 mod_addr = g_procs[pidx].ip + 1 + ridx;

		if (
			!sal_mem_is_address_valid(mod_addr) ||
			!sal_is_mod(sal_mem_get_inst(mod_addr))
		) {
			return FALSE;
		}

		switch (sal_mem_get_inst(mod_addr)) {
		case MODA:
			regs[ridx] = &g_procs[pidx].rax;
			break;
		case MODB:
			regs[ridx] = &g_procs[pidx].rbx;
			break;
		case MODC:
			regs[ridx] = &g_procs[pidx].rcx;
			break;
		case MODD:
			regs[ridx] = &g_procs[pidx].rdx;
			break;
		}
	}

	return TRUE;
}

static void addr(uint32 pidx)
{
	/*
	* This gets called when an organism has finally found a template and is
	* ready to store its address. Only when in debug mode, we make sure that
	* the entire search operation has been performed in a valid way.
	*/
	uint32_p reg;

	#ifndef NDEBUG
		uint32 next2_addr;
		uint8 next2_inst;
		uint8 sp_inst;
		assert(g_is_init);
		assert(pidx < g_capacity);
		assert(!sal_proc_is_free(pidx));
		next2_addr = g_procs[pidx].ip + 2;
		assert(sal_mem_is_address_valid(next2_addr));
		next2_inst = sal_mem_get_inst(next2_addr);
		sp_inst = sal_mem_get_inst(g_procs[pidx].sp);
		assert(sal_is_template(next2_inst));
		assert(sal_is_template(sp_inst));
		assert(are_templates_complements(next2_addr, g_procs[pidx].sp));
	#endif

	/*
	* Store address of complement into the given register.
	*/
	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	*reg = g_procs[pidx].sp;
	increment_ip(pidx);
}

static void free_child_block_of(uint32 pidx)
{
	/*
	* Free only the 'child' memory block (mb2) of the caller organism.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	assert(g_procs[pidx].mb2s);
	free_memory_block(g_procs[pidx].mb2a, g_procs[pidx].mb2s);
	g_procs[pidx].mb2a = 0;
	g_procs[pidx].mb2s = 0;
}

static void alloc(uint32 pidx, boolean forward)
{
	/*
	* Allocate a 'child' memory block of size stored in the first given
	* register, and save its address into the second given register. This
	* function is the basis of Salisian reproduction. It's a fairly complicated
	* function (as the seeker pointer must function in a procedural way), so
	* it's divided into a series of steps, documented below.
	*/
	uint32_p regs[2];
	uint32 block_size;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	/*
	* For this function to work, we need at least two register modifiers.
	* Then, we check for all possible error conditions. If any error conditions
	* are found, the instruction faults and returns.
	*/
	if (!get_register_pointers(pidx, regs, 2)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	block_size = *regs[0];

	/*
	* ERROR 1: requested child block is of size zero.
	*/
	if (!block_size) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	/*
	* ERROR 2: seeker pointer not adjacent to existing child block.
	*/
	if (g_procs[pidx].mb2s) {
		uint32 exp_addr;

		if (forward) {
			exp_addr = g_procs[pidx].mb2a + g_procs[pidx].mb2s;
		} else {
			exp_addr = g_procs[pidx].mb2a - 1;
		}

		if (g_procs[pidx].sp != exp_addr) {
			on_fault(pidx);
			increment_ip(pidx);
			return;
		}
	}

	/*
	* No errors were detected. We thus handle all correct conditions.
	* CONDITION 1: allocation was successful.
	*/
	if (g_procs[pidx].mb2s == block_size) {
		increment_ip(pidx);
		*regs[1] = g_procs[pidx].mb2a;
		return;
	}

	/*
	* CONDITION 2: seeker pointer has collided with allocated space. We free
	* child memory block and just continue searching.
	*/
	if (sal_mem_is_allocated(g_procs[pidx].sp)) {
		if (g_procs[pidx].mb2s) {
			free_child_block_of(pidx);
		}

		increment_sp(pidx, forward);
		return;
	}

	/*
	* CONDITION 3: no collision detected; enlarge child memory block and
	* increment seeker pointer.
	*/
	_sal_mem_set_allocated(g_procs[pidx].sp);

	if (!g_procs[pidx].mb2s || !forward) {
		g_procs[pidx].mb2a = g_procs[pidx].sp;
	}

	g_procs[pidx].mb2s++;
	increment_sp(pidx, forward);
}

static void swap(uint32 pidx)
{
	/*
	* Swap parent and child memory blocks. This function is the basis of
	* Salisian metabolism.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (g_procs[pidx].mb2s) {
		uint32 addr_temp = g_procs[pidx].mb1a;
		uint32 size_temp = g_procs[pidx].mb1s;
		g_procs[pidx].mb1a = g_procs[pidx].mb2a;
		g_procs[pidx].mb1s = g_procs[pidx].mb2s;
		g_procs[pidx].mb2a = addr_temp;
		g_procs[pidx].mb2s = size_temp;
	} else {
		on_fault(pidx);
	}

	increment_ip(pidx);
}

static void split(uint32 pidx)
{
	/*
	* Split child memory block into a new organism. A new baby is born. :-)
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (g_procs[pidx].mb2s) {
		proc_create(g_procs[pidx].mb2a, g_procs[pidx].mb2s, pidx, FALSE);
		g_procs[pidx].mb2a = 0;
		g_procs[pidx].mb2s = 0;
	} else {
		on_fault(pidx);
	}

	increment_ip(pidx);
}

static void one_reg_op(uint32 pidx, uint8 inst)
{
	/*
	* Here we group all 1-register operations. These include incrementing,
	* decrementing, placing zero or one on a register, and the negation
	* operation.
	*/
	uint32_p reg;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	assert(sal_is_inst(inst));

	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	switch (inst) {
	case INCN:
		(*reg)++;
		break;
	case DECN:
		(*reg)--;
		break;
	case SHFL:
		(*reg) <<= 1;
		break;
	case SHFR:
		(*reg) >>= 1;
		break;
	case ZERO:
		(*reg) = 0;
		break;
	case UNIT:
		(*reg) = 1;
		break;
	case NOTN:
		(*reg) = !(*reg);
		break;
	default:
		assert(FALSE);
	}

	increment_ip(pidx);
}

static void if_not_zero(uint32 pidx)
{
	/*
	* Conditional operator. Like in most programming languages, this
	* instruction is needed to allow organism execution to branch into
	* different execution streams.
	*/
	uint32_p reg;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	if (!(*reg)) {
		increment_ip(pidx);
	}

	increment_ip(pidx);
	increment_ip(pidx);
}

static void three_reg_op(uint32 pidx, uint8 inst)
{
	/*
	* Here we group all 3-register arithmetic operations. These include
	* addition, subtraction, multiplication and division.
	*/
	uint32_p regs[3];
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	assert(sal_is_inst(inst));

	if (!get_register_pointers(pidx, regs, 3)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	switch (inst) {
	case SUMN:
		*regs[0] = *regs[1] + *regs[2];
		break;
	case SUBN:
		*regs[0] = *regs[1] - *regs[2];
		break;
	case MULN:
		*regs[0] = *regs[1] * *regs[2];
		break;
	case DIVN:
		/*
		* Division by 0 is not allowed and causes a fault.
		*/
		if (!(*regs[2])) {
			on_fault(pidx);
			increment_ip(pidx);
			return;
		}

		*regs[0] = *regs[1] / *regs[2];
		break;
	default:
		assert(FALSE);
	}

	increment_ip(pidx);
}

static void load(uint32 pidx)
{
	/*
	* Load an instruction from a given address into a specified register. This
	* is used by organisms during their reproduction cycle.
	*/
	uint32_p regs[2];
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (
		!get_register_pointers(pidx, regs, 2) ||
		!sal_mem_is_address_valid(*regs[0])
	) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	if (g_procs[pidx].sp < *regs[0]) {
		increment_sp(pidx, TRUE);
	} else if (g_procs[pidx].sp > *regs[0]) {
		increment_sp(pidx, FALSE);
	} else {
		*regs[1] = sal_mem_get_inst(*regs[0]);
		increment_ip(pidx);
	}
}

static boolean is_writeable_by(uint32 pidx, uint32 address)
{
	/*
	* Check whether an organisms has writing rights on a specified address.
	* Any organism may write to any valid address that is either self owned or
	* not allocated.
	*/
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	assert(sal_mem_is_address_valid(address));

	if (!sal_mem_is_allocated(address)) {
		return TRUE;
	} else {
		uint32 lo1 = g_procs[pidx].mb1a;
		uint32 lo2 = g_procs[pidx].mb2a;
		uint32 hi1 = lo1 + g_procs[pidx].mb1s;
		uint32 hi2 = lo2 + g_procs[pidx].mb2s;
		return (
			(address >= lo1 && address < hi1) ||
			(address >= lo2 && address < hi2)
		);
	}
}

static void write(uint32 pidx)
{
	/*
	* Write instruction on a given register into a specified address. This is
	* used by organisms during their reproduction cycle.
	*/
	uint32_p regs[2];
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (
		!get_register_pointers(pidx, regs, 2) ||
		!sal_mem_is_address_valid(*regs[0]) || !sal_is_inst(*regs[1])
	) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	if (g_procs[pidx].sp < *regs[0]) {
		increment_sp(pidx, TRUE);
	} else if (g_procs[pidx].sp > *regs[0]) {
		increment_sp(pidx, FALSE);
	} else if (is_writeable_by(pidx, *regs[0])) {
		sal_mem_set_inst(*regs[0], *regs[1]);
		increment_ip(pidx);
	} else {
		on_fault(pidx);
		increment_ip(pidx);
	}
}

static void send(uint32 pidx)
{
	/*
	* Send instruction on given register into the common sender.
	*/
	uint32_p reg;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	if (!sal_is_inst(*reg)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	_sal_comm_send((uint8)(*reg));
	increment_ip(pidx);
}

static void receive(uint32 pidx)
{
	/*
	* Receive a single instruction from the common receiver and store it into
	* a specified register. In case the receiver is unset, it will return the
	* NOP0 instruction.
	*/
	uint32_p reg;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	*reg = _sal_comm_receive();
	assert(sal_is_inst(*reg));
	increment_ip(pidx);
}

static void push(uint32 pidx)
{
	/*
	* Push value on register into the stack. This is useful as a secondary
	* memory resource.
	*/
	uint32_p reg;
	uint32 sidx;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	for (sidx = 7; sidx; sidx--) {
		g_procs[pidx].stack[sidx] = g_procs[pidx].stack[sidx - 1];
	}

	g_procs[pidx].stack[0] = *reg;
	increment_ip(pidx);
}

static void pop(uint32 pidx)
{
	/*
	* Pop value from the stack into a given register.
	*/
	uint32_p reg;
	uint32 sidx;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));

	if (!get_register_pointers(pidx, &reg, 1)) {
		on_fault(pidx);
		increment_ip(pidx);
		return;
	}

	*reg = g_procs[pidx].stack[0];

	for (sidx = 1; sidx < 8; sidx++) {
		g_procs[pidx].stack[sidx - 1] = g_procs[pidx].stack[sidx];
	}

	g_procs[pidx].stack[7] = 0;
	increment_ip(pidx);
}

static void proc_cycle(uint32 pidx)
{
	/*
	* Cycle a process once. Organisms will always execute one instruction per
	* simulation cycle.
	*/
	uint8 inst;
	assert(g_is_init);
	assert(pidx < g_capacity);
	assert(!sal_proc_is_free(pidx));
	inst = sal_mem_get_inst(g_procs[pidx].ip);

	switch (inst) {
	case JMPB:
		if (jump_seek(pidx, FALSE)) jump(pidx);
		break;
	case JMPF:
		if (jump_seek(pidx, TRUE)) jump(pidx);
		break;
	case ADRB:
		if (addr_seek(pidx, FALSE)) addr(pidx);
		break;
	case ADRF:
		if (addr_seek(pidx, TRUE)) addr(pidx);
		break;
	case MALB:
		alloc(pidx, FALSE);
		break;
	case MALF:
		alloc(pidx, TRUE);
		break;
	case SWAP:
		swap(pidx);
		break;
	case SPLT:
		split(pidx);
		break;
	case INCN:
	case DECN:
	case SHFL:
	case SHFR:
	case ZERO:
	case UNIT:
	case NOTN:
		one_reg_op(pidx, inst);
		break;
	case IFNZ:
		if_not_zero(pidx);
		break;
	case SUMN:
	case SUBN:
	case MULN:
	case DIVN:
		three_reg_op(pidx, inst);
		break;
	case LOAD:
		load(pidx);
		break;
	case WRTE:
		write(pidx);
		break;
	case SEND:
		send(pidx);
		break;
	case RECV:
		receive(pidx);
		break;
	case PSHN:
		push(pidx);
		break;
	case POPN:
		pop(pidx);
		break;
	default:
		increment_ip(pidx);
	}
}

void _sal_proc_cycle(void)
{
	/*
	* The process module cycle consists of a series of steps, which are needed
	* to preserve overall correctness.
	*/
	assert(g_is_init);
	assert(module_is_valid());

	/*
	* Iterate through all organisms in the reaper queue. First organism to
	* execute is the one pointed to by 'g_last' (the one on top of the queue).
	* Last one to execute is 'g_first'. We go around the circular queue, making
	* sure to modulo (%) around when iterator goes below zero.
	*/
	if (g_count) {
		uint32 pidx = g_last;
		proc_cycle(pidx);

		while (pidx != g_first) {
			pidx--;
			pidx %= g_capacity;
			proc_cycle(pidx);
		}

		/*
		* Kill oldest processes whenever memory gets filled over capacity.
		*/
		while (sal_mem_get_allocated() > sal_mem_get_capacity()) {
			proc_kill();
		}
	}
}
