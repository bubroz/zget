.PHONY: bootstrap test

bootstrap:
	chmod +x bootstrap.sh
	./bootstrap.sh

test:
	uv run --extra dev pytest
