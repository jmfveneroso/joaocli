init:
	pip install -r requirements.txt

test:
	python3 tests/file_manager_test.integration.py
