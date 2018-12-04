/**
* @file memory.h
* @author Paul Oliver
*
* This module gives access to Salis memory. You can check the state of each
* byte (instruction and alloc-flag) at any time and also perform manual memory
* manipulations.
*/

#ifndef SALIS_MEMORY_H
#define SALIS_MEMORY_H

#define ALLOCATED_FLAG 0x20
#define INSTRUCTION_MASK 0x1f

void _sal_mem_init(uint32 order);
void _sal_mem_quit(void);
void _sal_mem_load_from(FILE *file);
void _sal_mem_save_into(FILE *file);

/** Get memory order.
* @return Order of memory (memory_size == 1 << order)
*/
SALIS_API uint32 sal_mem_get_order(void);

/** Get memory size.
* @return Size of memory (memory_size == 1 << order)
*/
SALIS_API uint32 sal_mem_get_size(void);

/** Get amount of addresses with the allocated flag set on them.
* @return Amount of addresses with the allocated flag set
*/
SALIS_API uint32 sal_mem_get_allocated(void);

/** Get memory capacity.
* @return Memory capacity (capacity == size / 2)
*/
SALIS_API uint32 sal_mem_get_capacity(void);

/** Get amount of addresses with a given instruction written on them.
* @param inst Instruction whose amount we want to count
* @return Amount of addresses with given instruction
*/
SALIS_API uint32 sal_mem_get_inst_count(uint8 inst);

/** Determine if memory is above its capacity.
* @return Memory is above capacity
*/
SALIS_API boolean sal_mem_is_over_capacity(void);

/** Check validity of address.
* @param address Address being queried
* @return Validity of address (validity == address < size)
*/
SALIS_API boolean sal_mem_is_address_valid(uint32 address);

/** Check if given address has the allocated flag set.
* @param address Address being queried
* @return Allocated flag is set on this address
*/
SALIS_API boolean sal_mem_is_allocated(uint32 address);

void _sal_mem_set_allocated(uint32 address);
void _sal_mem_unset_allocated(uint32 address);

/** Get current instruction at address.
* @param address Address being queried
* @return Instruction currently written at address
*/
SALIS_API uint8 sal_mem_get_inst(uint32 address);

/** Write instruction into address.
* @param address Address being set
* @param inst Instruction to write at given address
*/
SALIS_API void sal_mem_set_inst(uint32 address, uint8 inst);

/** Get current byte at address.
* @param address Address being queried
* @return Byte currently written at address (includes alloc-flag & instruction)
*/
SALIS_API uint8 sal_mem_get_byte(uint32 address);

/** Render a 1D image of a given block of memory. This is useful, as rendering
* directly in python would be too slow. We use openmp for multi-threaded image
* generation.
*
* @param origin Low bound of rendered image
* @param cell_size Amount of bytes per rendered pixel (cell)
* @param buff_size Amount of pixels (cells) to be generated
* @param buffer Pre-allocated buffer to store the rendered pixels into
*/
SALIS_API void sal_mem_render_image(
	uint32 origin, uint32 cell_size, uint32 buff_size, uint8_p buffer
);

void _sal_mem_cycle(void);

#endif
