#!/usr/bin/env bash

ALL_BOOST_LIBS=$(wildcard boost/libs/*/)

extract.so: extract.cpp boost/libs/container/include
	-git submodule update --init --recursive
	g++ $(patsubst %,-I %,$(wildcard boost/libs/*/include)) -shared -fPIC -Wall -g -o extract.so extract.cpp
	@echo "To dump the chip2platform table:"
	@echo " - put extract.so and extract.gdb in the same folder as flash_tool"
	@echo " - run: gdb -batch -x extract.gdb flash_tool"
	@echo " - perform a download agent operation with a device"
	@echo ""
	@echo "It seems like this is needed very rarely so it hasn't been further automated."
	@echo "Automation could be implemented by calling chip2platform from the c++ code."
