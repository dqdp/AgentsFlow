# Domain Pack: cpp-low-latency

## Purpose

Rules for low-latency C++ systems where architecture boundaries and hot-path constraints matter.

## Rules

- Hot-path changes require explicit performance/risk notes.
- Avoid allocations and locks in hot-path modules unless approved.
- Architecture boundaries and ABI constraints must be preserved.
- Benchmark claims require evidence.


## Usage

Workflows may load this pack to parameterize contract writing, scenario design, impact mapping, and review.
