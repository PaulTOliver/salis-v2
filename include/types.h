/**
* @file types.h
* @author Paul Oliver
*
* Declare main typedefs for the Salis library. Salis depends on fixed-width
* unsigned types being available. We use the limits header to define these in
* a C89 compliant way. Also, we typedef respective pointer types and a string
* type to aid in header parsing.
*/

#ifndef SALIS_TYPES_H
#define SALIS_TYPES_H

#include <limits.h>

#define UINT8_MAX 0xff
#define UINT32_MAX 0xffffffff

#if UCHAR_MAX == UINT8_MAX
	typedef unsigned char uint8;
	typedef unsigned char *uint8_p;
#else
	#error "Cannot define uint8/uint8_p types!"
#endif

#if ULONG_MAX == UINT32_MAX
	typedef unsigned long int uint32;
	typedef unsigned long int *uint32_p;
#elif UINT_MAX == UINT32_MAX
	typedef unsigned int uint32;
	typedef unsigned int *uint32_p;
#elif USHRT_MAX == UINT32_MAX
	typedef unsigned short int uint32;
	typedef unsigned short int *uint32_p;
#else
	#error "Cannot define uint32/uint32_p types!"
#endif

typedef int boolean;
typedef const char *string;

#define TRUE 1
#define FALSE 0

#endif
