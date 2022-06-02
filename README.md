# CBC-API-Tools

## Introduction

This code repository is dedicated to the publishing of tools based on the interaction with the [VMware Carbon Black Cloud API](https://developer.carbonblack.com/reference/carbon-black-cloud/) using the [VMware Carbon Black Cloud Python SDK](https://github.com/carbonblack/carbon-black-cloud-sdk-python).

## License

Use of the tools published in this repository is governed by the license found in [LICENSE](LICENSE)

## Requirements

### Packages

It is a requirement to install Carbon Black Cloud Python SDK first. You can install the package:

```bash
pip install -r base-requirements.txt
```

Each tool will define the required packages to install. Including this one.

### API Access Level

Each tool will describe the required API Access Level.

### CBC profile

Define the [CBC profile](https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/authentication/#authentication-methods) with the appropriate API key in the host where the tools will run.

## Tools

| Name | Description |
|---|---|
| [process_events_exporter](process_events_exporter/README.md) | Exports the events and the childproc tree related to a process within a given timeframe. |