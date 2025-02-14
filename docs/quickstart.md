# Quick run

## Installation

Either install warnet via pip, or clone the source and install:

### via pip

You can install warnet via `pip` into a virtual environment with

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install warnet
```

### via cloned source

You can install warnet from source into a virtual environment with

```bash
git clone https://github.com/bitcoin-dev-project/warnet.git
cd warnet
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Deploying a network

To get started first check you have all the necessary requirements:

```bash
warnet setup
```

Then create your first network:

```bash
# Create a new network in the current directory
warnet init

# Or in a directory of choice
warnet new <directory>
```

Follow the guide to configure network variables. Note that upon creating a new network, `networks`,
`plugins` and `scenarios` directories will have been created in your project directory and
populated with default content to get you started.

## Running a scenario

When you've created a new network, default scenarios will have been copied into your project directory
for your convenience. With a network deployed, you can run now run a [scenario](scenarios.md).

```bash
warnet run <path-to-scenario-file>

# reconnaissance scenario
warnet run scenarios/reconnaissance.py
```

## fork-observer

If you enabled [fork-observer](https://github.com/0xB10C/fork-observer), it will be available from the landing page at `localhost:2019`.
