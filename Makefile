default:
	python3 -m venv .venv
	.venv/bin/pip install -Ur requirements.txt

clean:
	rm -rf .venv
