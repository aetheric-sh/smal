<h1 align="center">
  <img src="https://raw.githubusercontent.com/jbaileydev/smal/master/src/assets/smal_header.svg" width="300">
</h1><br>

[![Python Versions](https://img.shields.io/pypi/pyversions/smal.svg)](https://pypi.org/project/smal/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/smal.svg?label=PyPI%20downloads)](https://pypi.org/project/smal/)
[![License](https://img.shields.io/badge/license-%20%20GNU%20GPLv3%20-green)](LICENSE)
<!-- [![CI Status](https://github.com/jbaileydev/smal/actions/workflows/ci.yml/badge.svg)](https://github.com/jbaileydev/smal/actions) -->
[![Code Styling](https://img.shields.io/badge/style-ruff-purple?logo=ruff&logoColor=white)](https://github.com/jbaileydev/smal)
[![Code Linting](https://img.shields.io/badge/linting-ruff-purple?logo=ruff&logoColor=white)](https://github.com/jbaileydev/smal)
[![Release Version](https://img.shields.io/github/v/release/jbaileydev/smal)](https://github.com/jbaileydev/smal/releases)
[![Dependabot](https://img.shields.io/badge/dependabot-active-brightgreen?logo=dependabot)](https://github.com/jbaileydev/smal/security/dependabot)
[![DSL YAML](https://img.shields.io/badge/DSL-YAML-blue)](https://github.com/jbaileydev/smal)

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

# ✨ Features

### 🧩 YAML-based DSL  
Define states, events, transitions, and actions in a clean, expressive format.

### 🔧 Multi-language code generation  
Generate firmware-ready code in **C**, **C++**, and **Rust**.

### 🖼️ SVG diagram generation  
Produce a polished, auto‑layout state machine diagram directly from your `.smal` file.

### 🐞 Debug-friendly  
SMAL includes a structured debug layout that maps cleanly to firmware and tooling.

### 🛠️ Extensible  
Add custom generators, validators, or analysis tools.

# 📦 Installation

```bash
pip install smal
```
