# Control Flow Graph

## Usage

### Basic CFG Generation
```bash
bril2json < program.bril | python3 mycfg.py
```
Outputs a DOT graph that can be converted to PDF using Graphviz:
```bash
bril2json < program.bril | python3 mycfg.py | dot -Tpdf -o output.pdf
```

### Analysis Options
```bash
# Path lengths from entry node
bril2json < program.bril | python3 mycfg.py --analysis=pathlen

# Reverse postorder traversal
bril2json < program.bril | python3 mycfg.py --analysis=rpo

# Back edges detection
bril2json < program.bril | python3 mycfg.py --analysis=backedges

# Reducibility check
bril2json < program.bril | python3 mycfg.py --analysis=reducible
```

## Testing

### Running All Tests
```bash
turnt tests/*.bril
```

### Running Specific Analysis Tests
```bash
turnt tests/*.bril -c pathlen
turnt tests/*.bril -c rpo
turnt tests/*.bril -c backedges
turnt tests/*.bril -c reducible
```

### Running Single Test
```bash
turnt tests/loop.bril
turnt tests/branch.bril -c pathlen
```

## Test Cases

- **linear.bril**: Simple sequential code
- **branch.bril**: Basic branching with if-else
- **loop.bril**: Single loop with back edge
- **nested.bril**: Nested conditionals
- **multiple-loops.bril**: Multiple separate loops
- **while-loop.bril**: While loop pattern
- **complex.bril**: Nested loops with multiple paths
- **irreducible.bril**: Irreducible CFG example
- **no-return.bril**: Infinite loop without return
- **empty-blocks.bril**: Blocks with no instructions
- **multi-function.bril**: Multiple function definitions

## Analysis Outputs

- **pathlen**: Distance from entry node to each reachable node
- **rpo**: Reverse postorder traversal of the CFG
- **backedges**: List of back edges (source, target) pairs
- **reducible**: Boolean indicating if the CFG is reducible

## Dependencies

- Python 3
- Bril (bril2json)
- Turnt (for testing)
- Graphviz (for PDF generation)