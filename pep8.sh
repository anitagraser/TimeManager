# run pep8 
# exclude query builder because it has very long lines ( needs to be refactored anyway)
# and resources.py because it has some binary
pep8 *.py --exclude query_builder.py,resources.py --max-line-length=120
