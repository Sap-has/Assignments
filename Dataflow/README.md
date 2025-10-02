# Dataflow Analysis Framework

A Python-based dataflow analysis framework for Bril (Big Red Intermediate Language) programs. This tool implements various classic compiler dataflow analyses using a worklist algorithm.

## Features

This framework implements the following dataflow analyses:

- **Defined Variables Analysis** (`defined`): Tracks all currently-defined variables (forward analysis)
- **Live Variable Analysis** (`live`): Identifies variables that are defined and might be read in the future (backward analysis)
- **Constant Propagation** (`cprop`): Propagates constant values through the program (forward analysis)
- **Reaching Definitions** (`reaching`): Determines which definitions reach each program point (forward analysis)
- **Available Expressions** (`available`): Identifies expressions whose values are available at each program point (forward analysis)

## Prerequisites

- Python 3.x
- Bril toolchain (specifically `bril2json`)
- [Turnt](https://github.com/cucapra/turnt) (optional, for testing)

## Usage

### Using bril2json (Direct Execution)

#### Run one file with one analysis

```bash
bril2json < test/df/test1.bril | python3 df.py available
```

#### Run one file with multiple analyses

```bash
# Run each analysis separately
bril2json < test/df/test1.bril | python3 df.py reaching
bril2json < test/df/test1.bril | python3 df.py available
bril2json < test/df/test1.bril | python3 df.py cprop
```

#### Run many files with one analysis

```bash
for file in test/df/test*.bril; do
  echo "=== $file ==="
  bril2json < "$file" | python3 df.py available
  echo
done
```

#### Run many files with many analyses

```bash
for file in test/df/test*.bril; do
  echo "=== $file ==="
  for analysis in reaching available; do
    echo "--- Analysis: $analysis ---"
    bril2json < "$file" | python3 df.py $analysis
  done
  echo
done
```

### Using Turnt (Automated Testing)

Turnt automatically runs analyses and compares outputs against expected results in `.out` files.

#### Run one file with one analysis

```bash
cd test/df
turnt -e available test1.bril
```

#### Run one file with multiple analyses

```bash
cd test/df
turnt -e reaching -e available test1.bril
```

#### Run many files with one analysis

```bash
cd test/df
turnt -e available test*.bril
```

#### Run many files with many analyses

```bash
cd test/df
turnt -e reaching -e available test*.bril

# Or run all configured analyses
turnt test*.bril
```

## Output Format

For each basic block, the analysis outputs:
- **in**: The dataflow value at the entry of the block
- **out**: The dataflow value at the exit of the block

Example output:
```
b1:
  in:  ∅
  out: add a b, mul a b, add c d
```

The format varies by analysis:
- Sets are displayed as comma-separated values (or ∅ for empty)
- Dicts show key-value pairs (constant propagation)

## Project Structure

```
Dataflow/
├── README.md          # This file
├── df.py              # Main dataflow analysis implementation
├── cfg.py             # Control flow graph utilities
├── form_blocks.py     # Basic block formation
└── test/
    └── df/
        ├── test*.bril     # Test Bril programs
        ├── cond*.bril     # Conditional test programs
        ├── fact.bril      # Factorial test
        ├── *.out          # Expected output files
        └── turnt.toml     # Test configuration
```

## Implementation Details

The framework uses a worklist algorithm that:
1. Forms basic blocks from the instruction stream
2. Builds a control flow graph
3. Iteratively computes dataflow values until reaching a fixed point
4. Supports both forward and backward analyses through a unified interface

Each analysis is defined by:
- **Direction**: Forward or backward
- **Initial value**: Bottom or top of the lattice
- **Merge function**: Combines values from multiple predecessors/successors
- **Transfer function**: Computes output from input for a basic block

## Available Analyses

| Analysis | Command | Direction | Description |
|----------|---------|-----------|-------------|
| Defined Variables | `defined` | Forward | All currently-defined variables |
| Live Variables | `live` | Backward | Variables that might be read in the future |
| Constant Propagation | `cprop` | Forward | Tracks constant values |
| Reaching Definitions | `reaching` | Forward | Which definitions reach each point |
| Available Expressions | `available` | Forward | Which expressions are available |

## Examples

### Simple straight-line code (test1.bril)
```bash
bril2json < test/df/test1.bril | python3 df.py available
```

### Control flow with branches (test2.bril)
```bash
bril2json < test/df/test2.bril | python3 df.py reaching
```

### Loops (test4.bril)
```bash
bril2json < test/df/test4.bril | python3 df.py live
```

## License

This project is part of the Bril compiler infrastructure.