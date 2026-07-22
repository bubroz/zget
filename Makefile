.PHONY: bootstrap serve

bootstrap:
	chmod +x bootstrap.sh
	./bootstrap.sh

serve:
	uv run zget-server --port 9989 --open
