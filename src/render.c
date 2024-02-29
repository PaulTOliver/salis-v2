#include <assert.h>
#include <stdio.h>
#include "types.h"
#include "memory.h"
#include "process.h"
#include "render.h"

#define MAX_ZOOM 0x10000
#define BLOCK_FLAG 0x40
#define IP_FLAG 0x80

static void apply_flag(
	uint32 origin, uint32 max_pos, uint32 cell_size, uint32 address,
	uint32 flag, uint8_p buffer
) {
	if (address >= origin && address < max_pos) {
		/* Flag falls inside rendered image. We can 'and' the bit to the
		corresponding pixel.
		*/
		uint32 pixel = (address - origin) / cell_size;
		buffer[pixel] |= flag;
	}
}

void sal_ren_get_image(
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
	uint32 max_pos;
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
		uint32 inst_sum = 0;
		uint32 alloc_flag = 0;
		uint32 cell_addr = origin + (i * cell_size);

		for (j = 0; j < cell_size; j++) {
			uint32 address = j + cell_addr;

			if (!sal_mem_is_address_valid(address)) {
				continue;
			}

			inst_sum += sal_mem_get_inst(address);

			if (sal_mem_is_allocated(address)) {
				alloc_flag = ALLOCATED_FLAG;
			}
		}

		buffer[i] = (uint8)(inst_sum / cell_size);
		buffer[i] |= (uint8)(alloc_flag);
	}

	/* We also iterate through all processes and append extra bit flags to the
	rendered image signaling process IP position and memory block limits.
	*/
	max_pos = origin + (cell_size * buff_size);

	#pragma omp parallel for
	for (i = 0; i < sal_proc_get_count(); i++) {
		if (!sal_proc_is_free(i)) {
			Process proc = sal_proc_get_proc(i);
			apply_flag(origin, max_pos, cell_size, proc.ip, IP_FLAG, buffer);
			apply_flag(
				origin, max_pos, cell_size, proc.mb1a, BLOCK_FLAG, buffer
			);

			if (proc.mb2s) {
				apply_flag(
					origin, max_pos, cell_size, proc.mb2a, BLOCK_FLAG, buffer
				);
			}
		}
	}
}
