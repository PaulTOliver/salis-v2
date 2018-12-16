CC := gcc
LIB_DEB := bin/lib/libsalis-deb.so
LIB_REL := bin/lib/libsalis-rel.so
SOURCES := $(wildcard src/*.c)
OBJECTS_DEB := $(patsubst src/%.c,build/debug/%.o,$(SOURCES))
OBJECTS_REL := $(patsubst src/%.c,build/release/%.o,$(SOURCES))
DEPS_DEB := $(patsubst %.o,%.d,$(OBJECTS_DEB))
DEPS_REL := $(patsubst %.o,%.d,$(OBJECTS_REL))
LFLAGS := -shared

# Compiler flags for debug build.
DEB_FLAGS := -ggdb

# Compiler flags for release build.
REL_FLAGS := -O3 -DNDEBUG -Wno-unused-function -Wno-unused-result \
	-Wno-unused-variable

# General compiler flags.
CFLAGS := -Iinclude -c -MMD -Wall -Wextra -std=c89 -fPIC -fopenmp \
	-DSALIS_API="" -DSALIS_INST="" -DSALIS_PROC_ELEMENT="" -pedantic-errors \
	-Wmissing-prototypes -Wstrict-prototypes -Wold-style-definition

# By default, keep a debug and release build available.
all: debug release

debug: $(OBJECTS_DEB)
	$(CC) $(LFLAGS) -fopenmp -o $(LIB_DEB) $(OBJECTS_DEB)

release: $(OBJECTS_REL)
	$(CC) $(LFLAGS) -fopenmp -o $(LIB_REL) $(OBJECTS_REL)

-include $(DEPS_DEB)

$(OBJECTS_DEB): $(patsubst build/debug/%.o,src/%.c,$@)
	$(CC) $(DEB_FLAGS) $(CFLAGS) $(patsubst build/debug/%.o,src/%.c,$@) -o $@

-include $(DEPS_REL)

$(OBJECTS_REL): $(patsubst build/release/%.o,src/%.c,$@)
	$(CC) $(REL_FLAGS) $(CFLAGS) $(patsubst build/release/%.o,src/%.c,$@) -o $@

clean:
	-rm build/debug/*
	-rm build/release/*
	-rm $(LIB_DEB)
	-rm $(LIB_REL)
