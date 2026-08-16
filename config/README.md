# Configuration Rationalizer

A modular Python wrapper for safe post-upgrade configuration comparison
and rationalization.

## Project principle

The pre-upgrade configuration is authoritative.

The rationalizer must:

- preserve existing configuration values;
- add only genuinely new vendor configuration;
- retain entries removed by the vendor;
- avoid modifying live configuration in the MVP;
- produce auditable snapshots, reports and candidates;
- fail safely when configuration cannot be interpreted reliably.

## Development stages

1. Foundation
2. Properties comparison
3. Properties rationalization
4. Full run lifecycle
5. Component ownership
6. YAML
7. XML schema analysis
8. XML rationalization
9. Reporting and security hardening
10. Integration and MVP validation
11. Operationalization
12. Post-MVP enhancements

## Stage 1

Stage 1 establishes:

- Python package structure;
- CLI foundation;
- configuration loading;
- common domain models;
- enums;
- application exceptions;
- structured audit logging;
- run status model;
- initial tests.

Stage 1 does not implement:

- configuration scanning;
- snapshots;
- properties parsing;
- comparison;
- rationalization;
- YAML processing;
- XML processing;
- candidate generation;
- live configuration changes.

## Requirements

- Python 3.11+
- pip

## Development setup

Create a virtual environment:

```bash
python3.11 -m venv .venv