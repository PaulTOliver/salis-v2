/**
* @file salis.h
* @author Paul Oliver
*
* Main header file for the Salis library. Loading this header imports all API
* modules and functions. It may be loaded from C or C++.
*/

#ifndef SALIS_H
#define SALIS_H

#ifdef __cplusplus
	extern "C" {
#endif

#include <types.h>
#include <instset.h>
#include <memory.h>
#include <evolver.h>
#include <common.h>
#include <process.h>

/** Initialize Salis simulation.
* @param order Order of memory (memory_size == 1 << order)
* @param pipe Desired path and file name of common pipe
*/
SALIS_API void sal_main_init(uint32 order, string pipe);

/** Free resources and quit Salis.
*/
SALIS_API void sal_main_quit(void);

/** Load existing Salis simulation from saved file.
* @param file_name Path of the save file to be loaded
* @param pipe Desired path and file name of common pipe
*/
SALIS_API void sal_main_load(string file_name, string pipe);

/** Save Salis simulation to a file.
* @param file_name Path of the save file to be created
*/
SALIS_API void sal_main_save(string file_name);

/** Check if Salis simulation has been correctly initialized.
* @return Salis has been correctly initialized
*/
SALIS_API boolean sal_main_is_init(void);

/** Get current simulation cycle.
* @return Current simulation cycle
*/
SALIS_API uint32 sal_main_get_cycle(void);

/** Get current simulation epoch.
* @return Current simulation epoch (1 epoch == 2^32 cycles)
*/
SALIS_API uint32 sal_main_get_epoch(void);

/** Update simulation once. This will cycle all Salis modules and processes.
*/
SALIS_API void sal_main_cycle(void);

#ifdef __cplusplus
	}
#endif

#endif
