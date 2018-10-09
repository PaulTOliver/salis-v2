## Salis.py: Viewer/Controller Interface for the Salis Simulator
*Salis.py* is a text user interface (TUI) written in Python, designed to
communicate with the *SALIS* library via the `ctypes` module. To run it, you
must have Python3 installed and in your PATH, as well as the Cython package
installed.

### Running SALIS
You may run SALIS in one of the following ways. Top example creates a new
simulation of order 16 and gives it the name `./bin/sims/16.sim`. The second
one attempts to load an existing save-file from the `./bin/sims` directory.
```bash
$ ./bin/salis.py new --order 16 --file 16.sim
$ ./bin/salis.py load --file 16.sim
```

### Keyboard commands
|Key |Action |
|:---|------:|
|Left/Right arrow |Previous/next page |
|Up/Down arrows   |Scroll page up/down if it can't fit terminal |
|`wasd`           |Scroll/pan (PROCESS and WORLD page) |
|`S`              |Scroll to top (PROCESS and WORLD page) |
|`A`              |Scroll to left (PROCESS page) |
|`zx`             |Zoom in/out (WORLD page) |
|`i`              |Toggle IP view (WORLD page) |
|`op`             |Select previous/next organism |
|`g`              |Toggle data/gene view (PROCESS page) |
|`c`              |Open console (pauses simulation) |
|Space            |Run/pause simulation |
|`fl`             |Select first/last organism |
|`k`              |Scroll/go to selected (PROCESS and WORLD page) |
|`X`              |Toggle hex/decimal value printing |
|Numbers `[1..0]` |Cycle simulation `2^((n-1) % 10)` steps |
|Enter            |Activate cursor (WORLD page) |

### Console commands
The console opens up when `c` is pressed. Commands, with their respective
parameters separated by whitespace, may be written in order to modify or
control some aspects of the simulation.

|Command |Arg. 1 |Arg. 2+ |Description |
|:-------|:------|:-------|-----------:|
|`q \| quit`    |---      |---       |Save and quit simulation |
|`q! \| quit!`  |---      |---       |Quit without saving |
|`i \| input`   |genome   |addresses |Write genome into given addresses |
|`c \| compile` |file     |addresses |Compile genome on file into addresses |
|`n \| new`     |size     |addresses |Initialize new organism(s) into addresses |
|`k \| kill`    |---      |---       |Kill organism on bottom of queue |
|`e \| exec`    |command  |---       |Execute python string as command |
|`s \| scroll`  |value    |---       |Scroll to Nth process or memory address |
|`p \| process` |id       |---       |Select process by ID |
|`r \| rename`  |name     |---       |Give simulation a new name |
|`s \| save`    |---      |---       |Save simulation |
|`a \| auto`    |interval |---       |Set simulation's auto-save interval |

### Color Legend
In WORLD view, as well as in PROCESS view (when gene mode is selected), each
cell is colored according to the following legend:

|Background color |Meaning |
|:----------------|-------:|
|BLACK   |Non-allocated cell |
|BLUE    |Allocated cell |
|CYAN    |Start of memory block |
|WHITE   |IP(s) currently at address |
|YELLOW  |Main memory block of selected organism |
|GREEN   |Child memory block of selected organism |
|MAGENTA |SP of selected organism |
|RED     |IP of selected organism |
