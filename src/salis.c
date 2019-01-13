#include <assert.h>
#include <stdio.h>
#include "getter.h"
#include "salis.h"

static boolean g_is_init;
static uint32 g_cycle;
static uint32 g_epoch;

void sal_main_init(uint32 order)
{
	/* Initialize all Salis modules to their initial states. We pass along any
	arguments to their respective modules.
	*/
	assert(!g_is_init);
	_sal_mem_init(order);
	_sal_evo_init();
	_sal_proc_init();
	g_is_init = TRUE;
}

void sal_main_quit(void)
{
	/* Reset Salis and all of its modules back to zero. We may, thus, shutdown
	Salis and re-initialize it with different parameters without having to
	reload the library (useful, for example, when running data gathering
	scripts that must iterate through many save files).
	*/
	assert(g_is_init);
	_sal_proc_quit();
	_sal_evo_quit();
	_sal_mem_quit();
	g_is_init = FALSE;
	g_cycle = 0;
	g_epoch = 0;
}

void sal_main_load(string file_name)
{
	/* Load simulation state from file. This file must have been created by
	'sal_main_save()'.
	*/
	FILE *file;
	assert(!g_is_init);
	assert(file_name);
	file = fopen(file_name, "rb");
	assert(file);
	fread(&g_is_init, sizeof(boolean), 1, file);
	fread(&g_cycle, sizeof(uint32), 1, file);
	fread(&g_epoch, sizeof(uint32), 1, file);
	_sal_mem_load_from(file);
	_sal_evo_load_from(file);
	_sal_proc_load_from(file);
	fclose(file);
}

void sal_main_save(string file_name)
{
	/* Save simulation state to a file. This file may later be re-loaded with
	'sal_main_load()'. We save in binary format (to save space), which means
	save files might not be entirely portable.
	*/
	FILE *file;
	assert(g_is_init);
	assert(file_name);
	file = fopen(file_name, "wb");
	assert(file);
	fwrite(&g_is_init, sizeof(boolean), 1, file);
	fwrite(&g_cycle, sizeof(uint32), 1, file);
	fwrite(&g_epoch, sizeof(uint32), 1, file);
	_sal_mem_save_into(file);
	_sal_evo_save_into(file);
	_sal_proc_save_into(file);
	fclose(file);
}

boolean sal_main_is_init(void)
{
	/* Check if Salis is currently initialized/running.
	*/
	return g_is_init;
}

/* Getter methods for the Salis main module.
*/
UINT32_GETTER(main, cycle)
UINT32_GETTER(main, epoch)

void sal_main_cycle(void)
{
	/* Cycle the Salis simulator once. The combination of a cycle * epoch
	counter allows us to track simulations for an insane period of time
	(2^64 cycles).
	*/
	g_cycle++;

	if (!g_cycle) {
		g_epoch++;
	}

	/* Cycle all of the Salis modules.
	*/
	_sal_mem_cycle();
	_sal_evo_cycle();
	_sal_proc_cycle();
}
