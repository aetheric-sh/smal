# 🌐 **SMAL — State Machine Abstraction Language**

<p align="center">
  <img src="assets/smal_header_.svg" alt="SMAL Logo" width="420">
</p>

<p align="center">
  <strong>A YAML-based description language for simple, robust and debuggable state machines.</strong>
</p>

---

<p align="center">

  <!-- PyPI version -->
  <a href="https://pypi.org/project/smal/">
    <img src="https://img.shields.io/pypi/v/smal.svg?color=3776AB&label=PyPI&logo=python&logoColor=white" alt="PyPI version">
  </a>

  <!-- Python versions -->
  <a href="https://pypi.org/project/smal/">
    <img src="https://img.shields.io/pypi/pyversions/smal.svg?logo=python&logoColor=white" alt="Python versions">
  </a>

  <!-- License -->
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  </a>

  <!-- Build status -->
  <a href="https://github.com/YOUR_USERNAME/smal/actions">
    <img src="https://github.com/YOUR_USERNAME/smal/workflows/CI/badge.svg" alt="Build Status">
  </a>

  <!-- Code style -->
  <a href="https://github.com/psf/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  </a>

  <!-- Documentation -->
  <a href="https://YOUR_DOCS_URL">
    <img src="https://img.shields.io/badge/docs-latest-blue.svg" alt="Documentation">
  </a>

</p>

---

# 🚀 Overview

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

---

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

---

# 📦 Installation

```bash
pip install smal
```