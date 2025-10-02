import sys
import json
from collections import namedtuple

from form_blocks import form_blocks
import cfg

# A single dataflow analysis consists of these part:
# - forward: True for forward, False for backward.
# - init: An initial value (bottom or top of the latice).
# - merge: Take a list of values and produce a single value.
# - transfer: The transfer function.
Analysis = namedtuple("Analysis", ["forward", "init", "merge", "transfer"])


def union(sets):
    out = set()
    for s in sets:
        out.update(s)
    return out


def intersect(sets):
    """Intersection of multiple sets"""
    sets_list = list(sets)
    if not sets_list:
        return set()
    result = set(sets_list[0])
    for s in sets_list[1:]:
        result.intersection_update(s)
    return result


def df_worklist(blocks, analysis):
    """The worklist algorithm for iterating a data flow analysis to a
    fixed point.
    """
    preds, succs = cfg.edges(blocks)

    # Switch between directions.
    if analysis.forward:
        first_block = list(blocks.keys())[0]  # Entry.
        in_edges = preds
        out_edges = succs
    else:
        first_block = list(blocks.keys())[-1]  # Exit.
        in_edges = succs
        out_edges = preds

    # Initialize.
    in_ = {first_block: analysis.init}
    out = {node: analysis.init for node in blocks}

    # Iterate.
    worklist = list(blocks.keys())
    while worklist:
        node = worklist.pop(0)

        inval = analysis.merge(out[n] for n in in_edges[node])
        in_[node] = inval

        outval = analysis.transfer(node, blocks[node], inval)  # Pass block name

        if outval != out[node]:
            out[node] = outval
            worklist += out_edges[node]

    if analysis.forward:
        return in_, out
    else:
        return out, in_


def fmt(val):
    """Guess a good way to format a data flow value. (Works for sets and
    dicts, at least.)
    """
    if isinstance(val, set):
        if val:
            return ", ".join(v for v in sorted(val))
        else:
            return "∅"
    elif isinstance(val, dict):
        if val:
            return ", ".join("{}: {}".format(k, v) for k, v in sorted(val.items()))
        else:
            return "∅"
    else:
        return str(val)


def run_df(bril, analysis):
    for func in bril["functions"]:
        # Form the CFG.
        blocks = cfg.block_map(form_blocks(func["instrs"]))
        cfg.add_terminators(blocks)

        in_, out = df_worklist(blocks, analysis)
        for block in blocks:
            print("{}:".format(block))
            print("  in: ", fmt(in_[block]))
            print("  out:", fmt(out[block]))


def gen(block):
    """Variables that are written in the block."""
    return {i["dest"] for i in block if "dest" in i}


def use(block):
    """Variables that are read before they are written in the block."""
    defined = set()  # Locally defined.
    used = set()
    for i in block:
        used.update(v for v in i.get("args", []) if v not in defined)
        if "dest" in i:
            defined.add(i["dest"])
    return used


def cprop_transfer(block_name, block, in_vals):
    out_vals = dict(in_vals)
    for instr in block:
        if "dest" in instr:
            if instr["op"] == "const":
                out_vals[instr["dest"]] = instr["value"]
            else:
                out_vals[instr["dest"]] = "?"
    return out_vals


def cprop_merge(vals_list):
    out_vals = {}
    for vals in vals_list:
        for name, val in vals.items():
            if val == "?":
                out_vals[name] = "?"
            else:
                if name in out_vals:
                    if out_vals[name] != val:
                        out_vals[name] = "?"
                else:
                    out_vals[name] = val
    return out_vals


# Reaching Definitions Analysis Implementation
def reaching_defs_transfer(block_name, block, in_vals):
    out_vals = set(in_vals)
    
    for i, instr in enumerate(block):
        if "dest" in instr:
            var = instr["dest"]
            out_vals = {defn for defn in out_vals if not defn.startswith(var + ".")}
            out_vals.add(f"{var}.{block_name}.{i}")
    
    return out_vals


# Available Expressions Analysis Implementation
def get_expressions(block):
    generated = []
    killed_vars = []
    
    for i, instr in enumerate(block):
        if instr.get("op") in ["add", "sub", "mul", "div", "eq", "lt", "gt", 
                               "le", "ge", "ne", "and", "or", "sum"]:
            if "args" in instr and len(instr["args"]) == 2:
                expr = f"{instr['op']} {instr['args'][0]} {instr['args'][1]}"
                generated.append((expr, i))
        
        if "dest" in instr:
            killed_vars.append((instr["dest"], i))
    
    return generated, killed_vars


def available_expr_transfer(block_name, block, in_vals):
    out_vals = set(in_vals)
    generated_in_block = set()
    
    for instr in block:
        generated_expr = None
        if instr.get("op") in ["add", "sub", "mul", "div", "eq", "lt", "gt", 
                               "le", "ge", "ne", "and", "or"]:
            if "args" in instr and len(instr["args"]) == 2:
                expr = f"{instr['op']} {instr['args'][0]} {instr['args'][1]}"
                generated_expr = expr
                out_vals.add(expr)
                generated_in_block.add(expr)
        
        if "dest" in instr:
            var = instr["dest"]
            out_vals = {
                expr for expr in out_vals 
                if expr in generated_in_block or var not in expr.split()[1:]
            }
    
    return out_vals


def available_expr_merge(vals_list):
    vals_list = list(vals_list)
    if not vals_list:
        return set()
    return intersect(vals_list)


ANALYSES = {
    # A really really basic analysis that just accumulates all the
    # currently-defined variables.
    "defined": Analysis(
        True,
        init=set(),
        merge=union,
        transfer=lambda block_name, block, in_: in_.union(gen(block)),
    ),
    # Live variable analysis: the variables that are both defined at a
    # given point and might be read along some path in the future.
    "live": Analysis(
        False,
        init=set(),
        merge=union,
        transfer=lambda block_name, block, out: use(block).union(out - gen(block)),
    ),
    # A simple constant propagation pass.
    "cprop": Analysis(
        True,
        init={},
        merge=cprop_merge,
        transfer=cprop_transfer,
    ),
    # Reaching definitions analysis
    "reaching": Analysis(
        True,
        init=set(),
        merge=union,
        transfer=reaching_defs_transfer,
    ),
    # Available expressions analysis - starts with EMPTY set
    "available": Analysis(
        True,
        init=set(),  # Start with empty set - no expressions available at entry
        merge=available_expr_merge,
        transfer=available_expr_transfer,
    ),
}

if __name__ == "__main__":
    bril = json.load(sys.stdin)
    analysis_name = sys.argv[1]
    run_df(bril, ANALYSES[analysis_name])