run:
	uv run src/main.py

subscribe:
	uv run src/lib/subscriptions.py

coins:
	uv run src/lib/coin_subscriptions.py

watch:
	uv run src/watch.py uv run src/main.py

watch-coins:
	uv run src/watch.py uv run src/lib/coin_subscriptions.py

.PHONY: run subscribe coins watch watch-coins