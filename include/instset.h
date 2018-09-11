/**
* @file instset.h
* @author Paul Oliver
*
* Here we declare the complete instruction set of the Salis virtual machine.
* Additionally, some helper functions are declared for determining instruction
* type and validity.
*/

#ifndef SALIS_INSTSET_H
#define SALIS_INSTSET_H

#define INST_COUNT 32

/** Salis instruction set. The 'SALIS_INST' macro and inline doc-comments help
* python parse this file. Don't edit these unless you know what you're doing!
*/
enum {
	SALIS_INST NOP0, /**< . Template constructor */
	SALIS_INST NOP1, /**< : Template constructor */
	SALIS_INST MODA, /**< a Register modifier */
	SALIS_INST MODB, /**< b Register modifier */
	SALIS_INST MODC, /**< c Register modifier */
	SALIS_INST MODD, /**< d Register modifier */
	SALIS_INST JMPB, /**< ( Jump back to template complement */
	SALIS_INST JMPF, /**< ) Jump forward to template complement */
	SALIS_INST ADRB, /**< [ Search back for template complement */
	SALIS_INST ADRF, /**< ] Search forward for template complement */
	SALIS_INST MALB, /**< { Allocate backwards */
	SALIS_INST MALF, /**< } Allocate forward */
	SALIS_INST SWAP, /**< % Swap memory blocks */
	SALIS_INST SPLT, /**< $ Split child memory block */
	SALIS_INST INCN, /**< ^ Increment register */
	SALIS_INST DECN, /**< v Decrement register */
	SALIS_INST ZERO, /**< 0 Zero out register */
	SALIS_INST UNIT, /**< 1 Place 1 on register */
	SALIS_INST NOTN, /**< ! Negation operator */
	SALIS_INST IFNZ, /**< ? Conditional operator */
	SALIS_INST SUMN, /**< + Add two registers */
	SALIS_INST SUBN, /**< - Subtract two registers */
	SALIS_INST MULN, /**< * Multiply two registers */
	SALIS_INST DIVN, /**< / Divide two registers */
	SALIS_INST LOAD, /**< L Load instruction from memory */
	SALIS_INST WRTE, /**< W Write instruction into memory */
	SALIS_INST SEND, /**< S Send instruction to common pipe */
	SALIS_INST RECV, /**< R Receive instruction from common pipe */
	SALIS_INST PSHN, /**< # Push value to stack */
	SALIS_INST POPN, /**< ~ Pop value from stack */
	SALIS_INST EATB, /**< < Eat backwards */
	SALIS_INST EATF  /**< > Eat forward */
};

/** Determine if an unsigned integer contains a valid instruction.
* @param byte Any unsigned integer up to 32 bits
* @return Whether or nor integer contains a valid instruction
*/
SALIS_API boolean sal_is_inst(uint32 word);

/** Determine if instruction is a template constructor [NOP0-NOP1].
* @param inst Must contain a valid instruction
* @return Whether or not instruction is a template constructor
*/
SALIS_API boolean sal_is_template(uint32 inst);

/** Determine if instruction a register modifier [MOD0-MOD3].
* @param inst Must contain a valid instruction
* @return Whether or not instruction is a register modifier
*/
SALIS_API boolean sal_is_mod(uint32 inst);

#endif
