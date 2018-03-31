PACKAGE = $(shell sed -ne "s/^name=//p" metadata.txt | tr '[:upper:]' '[:lower:]')
VERSION = $(shell sed -ne "s/^version=//p" metadata.txt)

TS_FILES = $(wildcard *.py)
UI_FILES = $(wildcard *.ui)

all:

zip: $(PACKAGE)-$(VERSION).zip

$(PACKAGE)-$(VERSION).zip:
	git archive --format=zip --prefix=$(PACKAGE)/ HEAD >$(PACKAGE)-$(VERSION).zip

upload: $(PACKAGE)-$(VERSION).zip
	python2 plugin_upload.py $(PACKAGE)-$(VERSION).zip

pep8:
	# run pep8
	# exclude query builder because it has very long lines ( needs to be refactored anyway)
	# and resources.py because it has some binary
	pep8 *.py --exclude query_builder.py,resources.py --max-line-length=120
