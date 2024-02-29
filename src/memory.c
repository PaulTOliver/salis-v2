#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "types.h"
#include "getter.h"
#include "instset.h"
#include "memory.h"

#define MAX_ZOOM 0x10000

static boolean g_is_init;
static uint32 g_order;
static uint32 g_size;
static uint32 g_ip_count;
static uint32 g_block_start_count;
static uint32 g_allocated_count;
static uint32 g_capacity;
static uint32 g_inst_counter[INST_COUNT];
static uint8_p g_memory;

void _sal_mem_init(uint32 order)
{
	/* Set memory module to its initial state. We calculate memory size based
	on its order (size = 1 << order) and allocate an array of such size. We
	also initialize the array completely to zero.
	*/
	assert(!g_is_init);
	assert(order < 32);
	g_is_init = TRUE;
	g_order = order;
	g_size = 1 << g_order;
	g_capacity = g_size / 2;
	g_inst_counter[0] = g_size;
	g_memory = calloc(g_size, 1);
	assert(g_memory);
}

void _sal_mem_quit(void)
{
	/* Reset memory module entirely back to zero. That way, we can load several
	simulations without restarting the application entirely.
	*/
	assert(g_is_init);
	free(g_memory);
	g_is_init = FALSE;
	g_order = 0;
	g_size = 0;
	g_ip_count = 0;
	g_block_start_count = 0;
	g_allocated_count = 0;
	g_capacity = 0;
	memset(g_inst_counter, 0, sizeof(uint32) * INST_COUNT);
	g_memory = NULL;
}

void _sal_mem_load_from(FILE *file)
{
	/* Load memory state from a binary file.
	*/
	assert(!g_is_init);
	assert(file);
	fread(&g_is_init, sizeof(boolean), 1, file);
	fread(&g_order, sizeof(uint32), 1, file);
	fread(&g_size, sizeof(uint32), 1, file);
	fread(&g_ip_count, sizeof(uint32), 1, file);
	fread(&g_block_start_count, sizeof(uint32), 1, file);
	fread(&g_allocated_count, sizeof(uint32), 1, file);
	fread(&g_capacity, sizeof(uint32), 1, file);
	fread(g_inst_counter, sizeof(uint32), INST_COUNT, file);
	g_memory = calloc(g_size, sizeof(uint8));
	assert(g_memory);
	fread(g_memory, sizeof(uint8), g_size, file);
}

void _sal_mem_save_into(FILE *file)
{
	/* Save memory state to a binary file.
	*/
	assert(g_is_init);
	assert(file);
	fwrite(&g_is_init, sizeof(boolean), 1, file);
	fwrite(&g_order, sizeof(uint32), 1, file);
	fwrite(&g_size, sizeof(uint32), 1, file);
	fwrite(&g_ip_count, sizeof(uint32), 1, file);
	fwrite(&g_block_start_count, sizeof(uint32), 1, file);
	fwrite(&g_allocated_count, sizeof(uint32), 1, file);
	fwrite(&g_capacity, sizeof(uint32), 1, file);
	fwrite(g_inst_counter, sizeof(uint32), INST_COUNT, file);
	fwrite(g_memory, sizeof(uint8), g_size, file);
}

/* Getter methods for the memory module.
*/
UINT32_GETTER(mem, order)
UINT32_GETTER(mem, size)
UINT32_GETTER(mem, ip_count)
UINT32_GETTER(mem, block_start_count)
UINT32_GETTER(mem, allocated_count)
UINT32_GETTER(mem, capacity)

uint32 sal_mem_get_inst_count(uint8 inst)
{
	/* Return number of times a certain instruction appears in memory. The
	instruction counter gets updated dynamically during each cycle.
	*/
	assert(g_is_init);
	assert(sal_is_inst(inst));
	return g_inst_counter[inst];
}

boolean sal_mem_is_over_capacity(void)
{
	/* Check if memory is filled above 50%. If so, old organisms will be popped
	out of the reaper queue!
	*/
	assert(g_is_init);
	return g_allocated_count > g_capacity;
}

boolean sal_mem_is_address_valid(uint32 address)
{
	/* Check if given address is valid.
	*/
	assert(g_is_init);
	return address < g_size;
}

/* We declare a standard macro to test whether a specific FLAG is set on a given
byte. Remember, a Salis byte contains a 5 bit instruction (of 32 possible) plus
3 flags: IP, BLOCK_START and ALLOCATED. These flags help organisms identify
where there is free memory space to reproduce on, and tell the python printer
module how to color each byte.
*/
#define FLAG_TEST(name, flag) \
boolean sal_mem_is_##name(uint32 address) \
{ \
	assert(g_is_init); \
	assert(sal_mem_is_address_valid(address)); \
	return !!(g_memory[address] & flag); \
}

FLAG_TEST(ip, IP_FLAG)
FLAG_TEST(block_start, BLOCK_START_FLAG)
FLAG_TEST(allocated, ALLOCATED_FLAG)

/* We define a standard macro for 'setting' one of the 3 FLAGS into a given
memory address.
*/
#define FLAG_SETTER(name, flag) \
void _sal_mem_set_##name(uint32 address) \
{ \
	assert(g_is_init); \
	assert(sal_mem_is_address_valid(address)); \
\
	if (!sal_mem_is_##name(address)) { \
		g_memory[address] ^= flag; \
		g_##name##_count++; \
	} \
}

FLAG_SETTER(ip, IP_FLAG)
FLAG_SETTER(block_start, BLOCK_START_FLAG)
FLAG_SETTER(allocated, ALLOCATED_FLAG)

/* We define a standard macro for 'unsetting' one of the 3 FLAGS into a given
memory address.
*/
#define FLAG_UNSETTER(name, flag) \
void _sal_mem_unset_##name(uint32 address) \
{ \
	assert(g_is_init); \
	assert(sal_mem_is_address_valid(address)); \
\
	if (sal_mem_is_##name(address)) { \
		g_memory[address] ^= flag; \
		g_##name##_count--; \
	} \
}

FLAG_UNSETTER(ip, IP_FLAG)
FLAG_UNSETTER(block_start, BLOCK_START_FLAG)
FLAG_UNSETTER(allocated, ALLOCATED_FLAG)

uint8 sal_mem_get_flags(uint32 address)
{
	/* Get FLAG bits currently set on a specified address (byte). These may be
	queried by using a bitwise 'and' operator against the returned byte.
	*/
	assert(g_is_init);
	assert(sal_mem_is_address_valid(address));
	return g_memory[address] & ~INSTRUCTION_MASK;
}

uint8 sal_mem_get_inst(uint32 address)
{
	/* Get instruction currently set on a specified address (byte), with the
	FLAG bits turned off.
	*/
	assert(g_is_init);
	assert(sal_mem_is_address_valid(address));
	return g_memory[address] & INSTRUCTION_MASK;
}

void sal_mem_set_inst(uint32 address, uint8 inst)
{
	/* Set instruction at given address. This is useful when performing manual
	memory manipulations (like compiling organism genomes).
	*/
	assert(g_is_init);
	assert(sal_mem_is_address_valid(address));
	assert(sal_is_inst(inst));
	g_inst_counter[sal_mem_get_inst(address)]--;
	g_memory[address] &= ~INSTRUCTION_MASK;
	g_memory[address] |= inst;
	g_inst_counter[inst]++;
}

uint8 sal_mem_get_byte(uint32 address)
{
	/* Get unadulterated byte at given address. This could be used, for
	example, to render nice images of the memory state.
	*/
	assert(g_is_init);
	assert(sal_mem_is_address_valid(address));
	return g_memory[address];
}

void sal_mem_render_image(
	uint32 origin, uint32 cell_size, uint32 buff_size, uint8_p buffer
) {
	/* Render a 1D image of a given section of memory, at a given resolution
	(zoom) and store it in a pre-allocated 'buffer'.

	On the Salis python handler we draw memory as a 1D 'image' on the WORLD
	page. If we were to render this image directly on python, it would be
	excruciatingly slow, as we have to iterate over large areas of memory!
	Therefore, this memory module comes with a built-in, super fast renderer.
	*/
	uint32 i;
	assert(g_is_init);
	assert(sal_mem_is_address_valid(origin));
	assert(cell_size);
	assert(cell_size <= MAX_ZOOM);
	assert(buff_size);
	assert(buffer);

	/* We make use of openmp for multi-threaded looping. This allows even
	faster render times, wherever openmp is supported.
	*/
	#pragma omp parallel for
	for (i = 0; i < buff_size; i++) {
		uint32 j;
		uint32 flag_sum = 0;
		uint32 inst_sum = 0;
		uint32 cell_addr = origin + (i * cell_size);

		for (j = 0; j < cell_size; j++) {
			uint32 address = j + cell_addr;

			if (sal_mem_is_address_valid(address)) {
				flag_sum |= sal_mem_get_flags(address);
				inst_sum += sal_mem_get_inst(address);
			}
		}

		buffer[i] = (uint8)(inst_sum / cell_size);
		buffer[i] |= (uint8)(flag_sum);
	}
}

static boolean inst_count_is_correct(void)
{
	/* Check that the instruction counter is in a valid state
	(i.e. SUM inst_counter[0..(INST_COUNT - 1)] == memory_size).
	*/
	uint32 i;
	uint32 sum = 0;
	assert(g_is_init);

	for (i = 0; i < INST_COUNT; i++) {
		assert(g_inst_counter[i] <= sal_mem_get_size());
		sum += g_inst_counter[i];
	}

	return sum == g_size;
}

static boolean module_is_valid(void)
{
	/* Check for validity of memory module. This function only gets called when
	Salis is running in debug mode. It makes Salis **very** slow in comparison
	to when running optimized, but it is also **very** useful for debugging!
	*/
	uint32 bidx;
	uint32 ip_count = 0;
	uint32 block_start_count = 0;
	uint32 allocated_count = 0;
	assert(g_is_init);
	assert(g_capacity <= g_size / 2);
	assert(inst_count_is_correct());

	/* Iterate through all memory, counting the flags set on each address. We
	then compare the sum to the flag counters to assert module validity.
	*/
	for (bidx = 0; bidx < g_size; bidx++) {
		if (sal_mem_is_ip(bidx)) ip_count++;
		if (sal_mem_is_block_start(bidx)) block_start_count++;
		if (sal_mem_is_allocated(bidx)) allocated_count++;
	}

	assert(ip_count == g_ip_count);
	assert(block_start_count == g_block_start_count);
	assert(allocated_count == g_allocated_count);
	return TRUE;
}

void _sal_mem_cycle(void)
{
	/* Cycle memory module. Simply assert validity when running in debug mode.
	When running optimized, this function does nothing.
	*/
	assert(g_is_init);
	assert(module_is_valid());
}
