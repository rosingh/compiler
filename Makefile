TESTS=

tests: $(TESTS)

$(TESTS):
	python ast.py $(TESTS)
clean:
	rm *.pyc
