PYTHON        = python
PIP           = pip
RUN_TESTS     = tests/runTests.sh


clean:
	@find . -name '*.pyc' -delete

python-deps:
	@$(PIP) install -r requirements.txt

tests:
	@sh $(RUN_TESTS) --quick --projectq

tests_qutip:
	@sh $(RUN_TESTS) --quick --qutip

tests_projectq:
	@sh $(RUN_TESTS) --quick --projectq

full_tests:
	@sh $(RUN_TESTS) --full --projectq

full_tests_qutip:
	@sh $(RUN_TESTS) --full --qutip

full_tests_projectq:
	@sh $(RUN_TESTS) --full --projectq

tests_allBackends: tests_qutip tests_projectq

full_tests_allBackends: full_tests_qutip full_tests_projectq

verify: clean python-deps tests

.PHONY: clean python-deps tests full_tests verify
