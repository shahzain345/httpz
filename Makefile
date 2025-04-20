.PHONY: all clean linux macos windows install dev test

OS := $(shell uname -s)

all:
	@echo "Building for detected OS: $(OS)"
ifeq ($(OS),Darwin)
	$(MAKE) macos
else ifeq ($(OS),Linux)
	$(MAKE) linux
else
	@echo "Windows detected, building with MinGW"
	$(MAKE) windows
endif

linux:
	@echo "Building for Linux..."
	cd azuretls && \
	GOOS=linux GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o ../libazuretls.so .

macos:
	@echo "Building for macOS..."
	cd azuretls && \
	GOOS=darwin GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o ../libazuretls.so .

windows:
	@echo "Building for Windows..."
	cd azuretls && \
	GOOS=windows GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o ../libazuretls.dll .

install: all
	pip install .

dev: all
	pip install -e .

test: all
	python -m pytest tests

clean:
	rm -f libazuretls.so libazuretls.dll libazuretls.dylib libazuretls.h
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete 