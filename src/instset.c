#include <assert.h>
#include "types.h"
#include "instset.h"

boolean sal_is_inst(uint32 word)
{
	/*
	* Test if a given 32 bit integer contains a valid Salis instruction.
	*/
	return word < INST_COUNT;
}

static boolean is_in_between(uint32 inst, uint32 low, uint32 hi)
{
	/*
	* Test whether a Salis instruction lies within a given range. This is
	* useful for identifying template instructions and/or register modifiers.
	*/
	assert(sal_is_inst(inst));
	assert(sal_is_inst(low));
	assert(sal_is_inst(hi));
	return (inst >= low) && (inst <= hi);
}

boolean sal_is_template(uint32 inst)
{
	/*
	* Test whether a given instruction is a template element (i.e. NOP0 or
	* NOP1).
	*/
	assert(sal_is_inst(inst));
	return is_in_between(inst, NOP0, NOP1);
}

boolean sal_is_mod(uint32 inst)
{
	/*
	* Test whether a given instruction is a register modifier (i.e. MODA, MODB,
	* MODC or MODD).
	*/
	assert(sal_is_inst(inst));
	return is_in_between(inst, MODA, MODD);
}
