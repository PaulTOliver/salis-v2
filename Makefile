CC := gcc
LIB := bin/lib/libsalis.so
SOURCES := $(wildcard src/*.c)
OBJECTS := $(patsubst src/%.c,build/%.o,$(SOURCES))
DEPS := $(patsubst %.o,%.d,$(OBJECTS))
LFLAGS := -shared

# uncomment for debug
# OFLAGS := -ggdb

# uncomment for release
OFLAGS := -O3 -DNDEBUG -Wno-unused-function -Wno-unused-result \
	-Wno-unused-variable

CFLAGS := -Iinclude -c $(OFLAGS) -MMD -Wall -Wextra -std=c89 -fPIC -fopenmp \
	-DSALIS_API="" -DSALIS_INST="" -DSALIS_PROC_ELEMENT="" -pedantic-errors \
	-Wmissing-prototypes -Wstrict-prototypes -Wold-style-definition

all: $(OBJECTS)
	$(CC) $(LFLAGS) -fopenmp -o $(LIB) $(OBJECTS)

-include $(DEPS)

$(OBJECTS): $(patsubst build/%.o,src/%.c,$@)
	$(CC) $(CFLAGS) $(patsubst build/%.o,src/%.c,$@) -o $@

clean:
	-rm build/*
	-rm $(LIB)
