# Precise definition of the experiment seed

Verified on 8 November 2026 against `swarm-harness` commit `b357f42adeb47bbada9a9e011b46eb0aca732186`.

The seed is an integer in the run configuration that determines the experiment controller's pseudorandom choices. Pseudorandom choices appear random but repeat when given the same seed and the same inputs. The controller combines the integer with an event identifier, such as a round and agent slot, before generating each draw or sample.

## What it controls

| Choice | Exact use of the seed | Conditions |
| --- | --- | --- |
| Initial investigators | `random.Random(f"{seed}-initial").sample(range(swarm_size), initial_investigators)` | Selects exactly the configured number of distinct agent slots. |
| Worker conversion | `random.Random(f"{seed}-{round}-{slot}-convert").random() < k` | Checked at the start of each round, including round 1, for each active worker. `k` is the configured conversion probability. |
| Random audit selection | `random.Random(f"{seed}-{round}-{slot}-audit").random() < p` | Checked for every active agent when `p > 0`, including investigators. `p` is the configured audit probability. This selects an audit, not its verdict. |
| Turn scheduling order | `random.Random(f"{seed}-{round}-order").shuffle(todo)` | Requires `shuffle_turns = true`. The input is the active agents who have not completed that round, sorted by agent ID. Concurrent execution can finish in a different order. |
| Instigator approval requests | `random.Random(f"{seed}-{pr.id}-{pr.version}").sample(pool, count)` | In swarm-wide mode, selects up to four recipients per internal pull-request version. The pool excludes its author, existing approvers and already-contacted recipients for that version. |

The draw function creates a new random generator for each event. Conversion and audit draws therefore depend on their seed, round, slot and event type, rather than how many other draws have already happened. A replacement worker inherits the previous agent's slot, so these keys refer to positions in the swarm rather than permanent agent identities.

Sources: [draw function](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/loop.py#L27-L29), [setup and round start](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/loop.py#L118-L159), [turn scheduling](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/loop.py#L167-L190), [approval requests](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/instigator.py#L126-L141).

## What repeating a seed guarantees

The same seed gives the same conversion and random audit draws for the same round and slot. Initial investigator samples also require the same population size and investigator count. Turn order and approval-request samples require the same ordered candidate lists. Eligibility and probability settings determine whether a draw produces an actual event.

The controller does not pass this seed to the language models. It therefore does not guarantee the same messages, code, reports, auditor verdicts or final outcomes. Concurrent tool calls and model responses can change the state encountered by later agents. Resuming a partially completed round shuffles the remaining agents rather than preserving the original full-round order.

Changing the seed does not change the configured population size, number of rounds, conversion probability, audit probability, problem contents, deterministic problem assignment or deterministic model assignment. The instigator's initial approach order is also determined by agent IDs and state, rather than a seeded sample.

Sources: [model calls](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/backend.py#L197-L266), [problem loading](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/repo.py#L306-L316), [initial instigator contacts](https://github.com/B2707/agent-swarm-hackathon/blob/b357f42adeb47bbada9a9e011b46eb0aca732186/swarm/instigator.py#L96-L112).

## Meaning of two seeds per condition

The planned design runs each experimental condition separately with `seed = 1` and `seed = 2`. These integers select different random choices. Their numeric size does not indicate strength, quality or cheating propensity.

Implementation caveat: the currently published seed-2 Luna configuration files also enable `service_tier = "priority"`, while the seed-1 configuration files omit it. Describe the seed as the randomization setting, but do not claim the current configuration files differ only in their seed. This check does not establish which later configuration edits were applied to each already-running experiment.

## Verification

Executed the actual draw function and sampling expressions extracted from the pinned source, without importing or starting the experiment. Repeated samples matched. All 4,000 conversion and audit draws across 20 rounds and 100 slots remained identical after changing evaluation order. Seeds 1 and 2 produced different investigator samples and turn orders. The seeded logic in `loop.py` and `instigator.py` is unchanged from the `4c74eb0` revision cited for the original shuffled Luna runs.

For seed 1 with 100 agents and 10 initial investigators, the selected original agent IDs are `a008`, `a025`, `a034`, `a041`, `a044`, `a071`, `a074`, `a087`, `a090` and `a091`. For seed 2 they are `a009`, `a031`, `a049`, `a056`, `a060`, `a072`, `a073`, `a075`, `a081` and `a089`.

Small reproducible check, run from the repository root with Python 3.12:

```sh
python3.12 - <<'PY'
import ast
import random
import subprocess

ref = "b357f42adeb47bbada9a9e011b46eb0aca732186"
text = subprocess.check_output(["git", "show", f"{ref}:swarm/loop.py"], text=True)
node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "draw")
scope = {"random": random}
exec(compile(ast.Module(body=[node], type_ignores=[]), "<source draw>", "exec"), scope)
draw = scope["draw"]
keys = [(r, s, t) for r in range(1, 21) for s in range(100) for t in ("convert", "audit")]
expected = {key: draw(1, *key) for key in keys}
assert expected == {key: draw(1, *key) for key in reversed(keys)}
assert draw(1, 2, 78, "convert") < 0.02
assert draw(2, 2, 78, "convert") >= 0.02
print("Passed: all 4,000 keyed draws repeat; the seed changes the example conversion.")
PY
```

The GitHub connector returned HTTP 404, so source verification used `git fetch`, `git show` and local Python checks. No experiment code, configuration, paper text or running experiment changed.
