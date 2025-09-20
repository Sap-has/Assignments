import json
import sys
import argparse

def is_terminator(instr):
    if 'op' not in instr:
        return False
    
    terminators = {'br', 'jmp', 'ret'}
    return instr['op'] in terminators

def form_blocks(instrs):
    if not instrs:
        return []
    
    blocks = []
    leaders = set([0])
    
    label_positions = {}
    for i, instr in enumerate(instrs):
        if 'label' in instr:
            label_positions[instr['label']] = i
    
    for i, instr in enumerate(instrs):
        if 'op' in instr:
            if instr['op'] in ['br', 'jmp']:
                if 'labels' in instr:
                    for label in instr['labels']:
                        if label in label_positions:
                            leaders.add(label_positions[label])
                
                if i + 1 < len(instrs):
                    leaders.add(i + 1)
            elif instr['op'] == 'ret':
                if i + 1 < len(instrs):
                    leaders.add(i + 1)
    
    leader_list = sorted(leaders)
    
    for i in range(len(leader_list)):
        start = leader_list[i]
        end = leader_list[i + 1] if i + 1 < len(leader_list) else len(instrs)
        
        block = instrs[start:end]
        if block:
            blocks.append(block)
    
    return blocks

def assign_block_names(blocks):
    block_names = []
    unnamed_counter = 0
    
    for block in blocks:
        if block and 'label' in block[0]:
            block_names.append(block[0]['label'])
        else:
            block_names.append(f"b{unnamed_counter}")
            unnamed_counter += 1
    
    return block_names

def create_name_to_block_map(blocks, block_names):
    name_to_block = {}
    
    for i, block in enumerate(blocks):
        name_to_block[block_names[i]] = block
    
    return name_to_block

def get_cfg(blocks, block_names):
    cfg = {}
    
    for block_name in block_names:
        cfg[block_name] = []
    
    for i, block in enumerate(blocks):
        if not block:
            continue
            
        block_name = block_names[i]
        
        last_instr = None
        for instr in reversed(block):
            if 'op' in instr:
                last_instr = instr
                break
        
        if last_instr is None:
            if i + 1 < len(blocks):
                next_block_name = block_names[i + 1]
                cfg[block_name].append(next_block_name)
            continue
        
        if last_instr.get('op') == 'jmp':
            if 'labels' in last_instr and last_instr['labels']:
                target_label = last_instr['labels'][0]
                cfg[block_name].append(target_label)
        elif last_instr.get('op') == 'br':
            if 'labels' in last_instr and len(last_instr['labels']) >= 2:
                true_label = last_instr['labels'][0]
                false_label = last_instr['labels'][1]
                cfg[block_name].append(true_label)
                cfg[block_name].append(false_label)
        elif last_instr.get('op') == 'ret':
            pass
        else:
            if i + 1 < len(blocks):
                next_block_name = block_names[i + 1]
                cfg[block_name].append(next_block_name)
    
    return cfg

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", choices=["pathlen", "rpo", "backedges", "reducible"])
    args = parser.parse_args()

    prog = json.load(sys.stdin)

    for func in prog["functions"]:
        func_name = func["name"]
        instrs = func["instrs"]

        blocks = form_blocks(instrs)
        if not blocks:
            continue

        block_names = assign_block_names(blocks)
        cfg = get_cfg(blocks, block_names)

        entry = block_names[0]

        if args.analysis:
            print(f"Function {func_name}:")
            run_analysis(cfg, entry, args.analysis)
        else:
            # Default = DOT graph
            print("digraph program {")
            print("  rankdir=TB;")
            print("  node [shape=box];")
            print(f'  subgraph cluster_{func_name} {{')
            print(f'    label = "{func_name}";')

            all_nodes = set(cfg.keys())
            for successors in cfg.values():
                all_nodes.update(successors)

            for node in sorted(all_nodes):
                escaped_node = node.replace(".", "_")
                print(f'    "{escaped_node}" [label="{node}"];')

            for block_name, successors in cfg.items():
                escaped_block = block_name.replace(".", "_")
                for successor in successors:
                    escaped_successor = successor.replace(".", "_")
                    print(f'    "{escaped_block}" -> "{escaped_successor}";')

            print("  }")
            print("}")

''' New Functions '''
def run_analysis(cfg, entry, analysis):
    if analysis == "pathlen":
        result = get_path_lengths(cfg, entry)
        print(f"pathlen: {result}")
    elif analysis == "rpo":
        result = reverse_postorder(cfg, entry)
        print(f"rpo: {result}")
    elif analysis == "backedges":
        result = find_back_edges(cfg, entry)
        print(f"backedges: {result}")
    elif analysis == "reducible":
        result = is_reducible(cfg, entry)
        print(f"reducible: {result}")
    else:
        raise ValueError(f"Unknown analysis: {analysis}")
    
from collections import deque

def get_path_lengths(cfg, entry):
    distances = {entry: 0}
    queue = deque([entry])

    while queue:
        u = queue.popleft()
        for v in cfg.get(u, []):
            if v not in distances:
                distances[v] = distances[u] + 1
                queue.append(v)
    return distances


def reverse_postorder(cfg, entry):
    visited = set()
    order = []

    def dfs(u):
        if u in visited:
            return
        visited.add(u)
        for v in cfg.get(u, []):
            dfs(v)
        order.append(u)

    dfs(entry)
    return list(reversed(order))


def find_back_edges(cfg, entry):
    back_edges = []
    visited = set()
    stack = []

    def dfs(u):
        visited.add(u)
        stack.append(u)
        for v in cfg.get(u, []):
            if v not in visited:
                dfs(v)
            elif v in stack:
                back_edges.append((u, v))
        stack.pop()

    dfs(entry)
    return back_edges


def is_reducible(cfg, entry):
    nodes = list(cfg.keys())
    dom = {n: set(nodes) for n in nodes}
    dom[entry] = {entry}

    changed = True
    while changed:
        changed = False
        for n in nodes:
            if n == entry:
                continue
            preds = [p for p in nodes if n in cfg.get(p, [])]
            if not preds:
                continue
            new_dom = set(nodes)
            for p in preds:
                new_dom &= dom[p]
            new_dom.add(n)
            if new_dom != dom[n]:
                dom[n] = new_dom
                changed = True

    for u, v in find_back_edges(cfg, entry):
        if v not in dom[u]:
            return False
    return True

if __name__ == '__main__':
    main()