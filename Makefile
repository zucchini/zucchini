VERSION = $(shell git describe || echo "UNKNOWN")

.PHONY: clean

# Produce an executable zip file full of Python code
# More info:
# https://docs.python.org/3/library/zipapp.html#the-python-zip-application-archive-format
# Why I didn't just use the zipapp module:
# https://bugs.python.org/issue26277
zucc: $(wildcard zucchini/*.py)
	printf 'import runpy\nrunpy.run_module("zucchini", init_globals={"VERSION": "%s"})\n' $(VERSION) >__main__.py
	rm -f zucc.zip
	zip -x '*/.*' '*.pyc' '*/__pycache__/' -r zucc.zip __main__.py zucchini/
	rm __main__.py
	printf '#!/usr/bin/env python3\n' >$@
	cat zucc.zip >>$@
	rm zucc.zip
	chmod +x $@

clean:
	rm -f __main__.py zucc zucc.zip
