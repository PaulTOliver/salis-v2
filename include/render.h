/**
* @file render.h
* @author Paul Oliver
*
* This module implements a multi-threaded memory render function that iterates
* over a given area of memory and returns a 1D image. OMP is used to up
* performance.
*/

#ifndef SALIS_RENDER_H
#define SALIS_RENDER_H

/**
* Render a 1D image of a given block of memory. This is useful, as rendering
* directly in python would be too slow. We use openmp for multi-threaded image
* generation.
*
* @param origin Low bound of rendered image
* @param cell_size Amount of bytes per rendered pixel (cell)
* @param buff_size Amount of pixels (cells) to be generated
* @param buffer Pre-allocated buffer to store the rendered pixels into
*/
SALIS_API void sal_ren_get_image(
	uint32 origin, uint32 cell_size, uint32 buff_size, uint8_p buffer
);

#endif
