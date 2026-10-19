"""SRE frontend config -> reviewable Python artifacts. Never executes edited/model code."""
from __future__ import annotations
import argparse
import ast
import json
import math
import operator
import re
from pathlib import Path

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}

def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected finite numeric input")
    return value

def condition_config(config):
    import keyword
    name = config.get("input")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) or keyword.iskeyword(name):
        raise ValueError("Invalid Python input name")
    if config.get("operator") not in OPS:
        raise ValueError("Unsupported comparison")
    numeric(config.get("threshold"))
    return config

def evaluate_branch(config, inputs):
    """Constrained declarative comparison, not eval/exec of user Python."""
    condition_config(config)
    value = numeric(inputs[config["input"]])
    return {"branch": "yes" if OPS[config["operator"]](value, config["threshold"]) else "no"}

def validate_source(source):
    if not isinstance(source, str) or len(source) > 30000:
        raise ValueError("Python source must be at most 30000 characters")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Python syntax error on line {exc.lineno}: {exc.msg}") from exc
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    if len(functions) != 1 or [arg.arg for arg in functions[0].args.args] != ["inputs", "context"] or functions[0].args.vararg or functions[0].args.kwarg or functions[0].args.kwonlyargs or functions[0].args.posonlyargs or len(functions[0].args.defaults) != 1 or not isinstance(functions[0].args.defaults[0], ast.Constant) or functions[0].args.defaults[0].value is not None:
        raise ValueError("Expected one def run(inputs, context=None) function")
    return tree

def starter_source(node):
    action = node["data"]["action"]
    config = node["data"].get("config", {})
    if action == "condition":
        c = config.get("condition")
        if c:
            condition_config(c)
            return ('# Editable Python starter. No LLM has been called.\n'
                    'def run(inputs, context=None):\n'
                    f'    {c["input"]} = inputs[{c["input"]!r}]\n'
                    f'    if isinstance({c["input"]}, bool) or not isinstance({c["input"]}, (int, float)):\n'
                    '        raise ValueError("Expected a numeric input")\n'
                    f'    return {{"branch": "yes" if {c["input"]} {c["operator"]} {c["threshold"]!r} else "no"}}\n')
        return 'def run(inputs, context=None):\n    return {"branch": "yes" if inputs["errors"] > 0 else "no"}\n'
    if action in {"start", "end"}:
        status = "started" if action == "start" else "completed"
        return f'def run(inputs, context=None):\n    return {{"status": {status!r}}}\n'
    payload = {key: config.get(key) for key in ("target", "region", "metrics", "timeRange", "method")}
    payload["action"] = action
    return ('# Integration and webpage perception are pending.\nimport json\n\n'
            'def run(inputs, context=None):\n'
            f'    config = json.loads({json.dumps(payload)!r})\n'
            '    return {"status": "pending", "config": config, "reason": "Execution adapter not connected"}\n')

def export_workflow(workflow):
    if not isinstance(workflow, dict) or workflow.get("version") != 1 or not isinstance(workflow.get("nodes"), list) or not 0 < len(workflow["nodes"]) <= 300:
        raise ValueError("Expected SRE workflow version1 with 1..300 nodes")
    nodes = workflow["nodes"]
    ids = [n.get("id") for n in nodes]
    if any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or duplicate node IDs")
    sources = []
    for index, node in enumerate(nodes):
        config = node["data"].get("config", {})
        code = config.get("python", {}).get("source")
        source = code if code is not None else starter_source(node)
        tree = validate_source(source)
        for item in tree.body:
            if isinstance(item, ast.FunctionDef) and item.name == "run":
                item.name = f"node_{index}"
        label = json.dumps({"id": node["id"], "label": node["data"].get("label", ""), "origin": config.get("python", {}).get("origin", "starter")})
        sources.append(f"# Node {label}\n" + ast.unparse(tree))
    return '# REVIEW-ONLY EXPORT. Never import or run unreviewed user/model code.\n# This exporter validates syntax, NOT safety. No code was executed.\n\n' + '\n\n'.join(sources) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workflow.stat().st_size > 1_000_000:
        parser.error("Workflow exceeds 1 MB")
    try:
        source = export_workflow(json.loads(args.workflow.read_text()))
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    args.output.write_text(source)
    print(f"Review-only Python written to {args.output}; no code executed")

if __name__ == "__main__":
    main()
