.PHONY: bootstrap serve

bootstrap:
	chmod +x bootstrap.sh
	./bootstrap.sh

serve:
	uv run zget-server --port 8000 --host 0.0.0.0
