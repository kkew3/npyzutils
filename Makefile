APPS = $(foreach S,$(patsubst %.py,%,$(wildcard *.py)),dist/$S/$S)
BASEDIR = $(realpath .)
PREFIX ?= /usr/local/bin

.PHONY: all remove preview clean install

define install_app
	cd "$(PREFIX)" && rm -f "$(1)" && ln -s "$(BASEDIR)/dist/$(1)/$(1)" "$(1)"
endef

all: $(APPS)

dist/npycat/npycat : npycat.py
	pylint -E --score=no $<
	pyinstaller -y $<

dist/npyzshape/npyzshape : npyzshape.py
	pylint -E --score=no $<
	pyinstaller -y $<

remove:
	rm -rf dist

clean:
	rm -f *.spec

preview:
	@echo $(APPS)

install:
	$(call install_app,npycat)
	$(call install_app,npyzshape)
