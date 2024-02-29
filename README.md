## SALIS 2.0 - WIP

### Main differences from Salis 1.0
1. Tierran templates will be used instead of keys/locks
2. The instruction set is thus shorter
3. Organisms can send/receive instructions to/from a common pipe
4. Organisms can "eat" information
5. Organisms are rewarded for eating
6. Organisms are punished on faults
7. A better naming convention will be used

### Python integration
1. Salis controller/viewer will be written in python/curses
2. Salis header files will be parsed for easier DLL loading
3. We can now show organisms' IPs on WORLD view
4. Console can make use of readline via curses.textbox
5. Compilation/loading/saving will be done via python
6. Salis may be run as a daemon process

### New instruction set (32 instructions in total)
+ NOOP0
+ NOOP1
+ MOD0
+ MOD1
+ MOD2
+ MOD3
+ IF
+ NOT
+ JUMPB
+ JUMPF
+ ADDRB
+ ADDRF
+ MALLB
+ MALLF
+ BSWAP
+ SPLIT
+ INC
+ DEC
+ ZERO
+ ONE
+ ADD
+ SUB
+ MUL
+ DIV
+ LOAD
+ WRITE
+ SEND
+ RECEIVE
+ PUSH
+ POP
+ EATB
+ EATF
