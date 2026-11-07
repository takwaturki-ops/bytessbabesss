"""9antra AI agents CLI.

  python main.py generate             # (re)generate SIMULATED datasets
  python main.py validate             # validate datasets
  python main.py demo                 # run the 5-agent demo
  python main.py workflow-demo        # run the complete purchase workflow (jury demo)
  python main.py eval                 # run evaluation scenarios + write reports/
  python main.py run <agent> '<json>' # run one agent on a JSON input (agent: sales|customer_intel|payment|financial|fraud)
"""
from __future__ import annotations

import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "help"
    if cmd == "generate":
        from data_generation.generate_all import main as gen
        print(json.dumps(gen()["counts"], indent=2))
    elif cmd == "validate":
        from data_generation.validate_data import validate
        errs = validate()
        print("VALIDATION PASSED" if not errs else "\n".join(["VALIDATION FAILED"] + errs))
        return 1 if errs else 0
    elif cmd == "demo":
        from examples.demo_all_agents import main as demo
        demo()
    elif cmd == "workflow-demo":
        from examples.demo_purchase_workflow import main as wdemo
        wdemo()
    elif cmd == "eval":
        from evaluation.run_eval import main as ev
        return ev()
    elif cmd == "run" and len(argv) >= 4:
        from agents import AGENTS
        if argv[2] not in AGENTS:
            print(f"unknown agent {argv[2]!r}; choose from {list(AGENTS)}")
            return 2
        resp = AGENTS[argv[2]]().run(json.loads(argv[3]))
        print(resp.model_dump_json(indent=2))
        return 0 if resp.status == "ok" else 1
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
