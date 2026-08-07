<h1 align="center">
  <img src="https://raw.githubusercontent.com/jbaileydev/smal/master/src/assets/smal_logo.svg" width="300">
</h1><br>

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/smal-lang)](https://pypi.org/project/smal-lang/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/smal-lang)](https://pypi.org/project/smal-lang/)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
<!-- [![CI Status](https://github.com/aetheric-sh/smal/actions/workflows/ci.yml/badge.svg)](https://github.com/aetheric-sh/smal/actions) -->
[![Code Styling](https://img.shields.io/badge/style-ruff-purple?logo=ruff&logoColor=white)](https://github.com/aetheric-sh/smal)
[![Code Linting](https://img.shields.io/badge/linting-ruff-purple?logo=ruff&logoColor=white)](https://github.com/aetheric-sh/smal)
[![Release Version](https://img.shields.io/github/v/release/aetheric-sh/smal)](https://github.com/aetheric-sh/smal/releases)
[![Dependabot](https://img.shields.io/badge/dependabot-active-brightgreen?logo=dependabot)](https://github.com/aetheric-sh/smal/security/dependabot)
[![DSL YAML](https://img.shields.io/badge/DSL-YAML-blue)](https://github.com/aetheric-sh/smal)

**SMAL (State Machine Abstraction Language)** is a compact, human‑readable YAML DSL for defining fully functional state machines that are:

- **Simple** — easy to write, easy to read  
- **Robust** — validated, structured, and type‑safe  
- **Debuggable** — designed for real firmware workflows  

A `.smal` file describes your entire state machine — states, events, transitions, commands, messages, and error handling — in a clean, declarative format. From that single source of truth, SMAL can generate:

- **C, C++, and Rust firmware code**
- **A complete SVG state machine diagram**
- **Debug structures** for introspection and tooling
- **Human-readable reports** for developers and QA

SMAL is built for embedded systems, audio devices, wearables, robotics, and any environment where clarity, determinism, and debuggability matter.

SMAL also ships an interactive REPL CLI (`smal`) for working with your state machines directly from the terminal — load and validate `.smal` files, generate code and diagrams on demand, and connect to a live device to send messages and run scripted command sequences against it.

# ✨ Features

### 🧩 YAML-based DSL  
Define states, events, transitions, actions, etc. in a clean, expressive format.

### 🔧 Multi-language code generation  
Generate firmware-ready code in **C**. **C++** and **Rust** planned for future release.

### 🖼️ SVG diagram generation  
Produce a polished, auto‑layout state machine diagram directly from your `.smal` file.

### 🐞 Debug-friendly  
SMAL includes a structured debug layout that maps cleanly to firmware and tooling.

### 📬 Generic Messaging
A simple interface for defining how to communicate with your embedded device is provided so you can add comms directly to the REPL!

### 📝 Scripting
Want to write structured sequences of messages that you can send with a single command? SMAL provides that with an easy, YAML-based script structure (`*.smalscr`) that works seamlessly with your messaging paradigm of choice.

### 🛠️ Extensible  
Add custom generators, validators, or analysis tools.

# 📦 Installation

```bash
pip install smal-lang
```

Or, using [uv](https://docs.astral.sh/uv/):

```bash
uv tool install smal-lang   # install the `smal` CLI globally
uv add smal-lang            # or add it as a project dependency
```

# 🚀 Quick Start

Try it with one of the bundled examples in [`src/examples`](src/examples):

```bash
smal
smal> machine load src/examples/simple/simple.smal
smal> diagram ./out
```

This loads the machine and renders `out/simple_state_machine_diagram.svg`. Run `code generate <template> -o <output_dir>` to generate firmware code from the same file.

# 📄 License

MIT — see [LICENSE](LICENSE). See [CHANGELOG.md](CHANGELOG.md) for release history.
