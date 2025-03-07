SHELL:=bash

COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz

ifdef REGISTRY_URL
	REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

FLAVOR:=3.22

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

SRCDIR=$(shell realpath .)

tests:
	@mkdir -p $$(pwd)/.local $(LOCAL_HOME)/.cache
	@docker run --rm --name qgis-server-lizmap-test-$(FLAVOR)-$(COMMITID) -w /src/test/ \
		-u $(BECOME_USER) \
		-v $(SRCDIR):/src \
		-v $$(pwd)/.local:/.local \
		-v $(LOCAL_HOME)/.cache:/.cache \
		-e PIP_CACHE_DIR=/.cache \
		-e QGIS_SERVER_LIZMAP_REVEAL_SETTINGS=TRUE \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./run-tests.sh
