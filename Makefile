DC ?= docker compose

up:
	$(DC) up -d

up-build:
	$(DC) up -d --build

down:
	$(DC) down

restart:
	$(MAKE) down
	$(MAKE) up

restart-b:
	$(MAKE) down
	$(MAKE) up-build

# Restart a single service, e.g. `make restart-fastapi_worker`
restart-%:
	$(DC) build $*
	$(DC) up -d $*