/**
* @file getter.h
* @author Paul Oliver
*
* We declare a helper macro for easy 'getting' of module state variables. Other
* similar, more specific macros are defined inside the module sources. Don't
* repeat yourself! :-)
*/

#ifndef SALIS_GETTER_H
#define SALIS_GETTER_H

#define UINT32_GETTER(mod, name) \
uint32 sal_##mod##_get_##name(void) \
{ \
	assert(g_is_init); \
	return g_##name; \
}

#endif
