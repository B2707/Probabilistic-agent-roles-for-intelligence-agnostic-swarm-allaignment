# Seed definition handoff

Complete at source commit `b357f42adeb47bbada9a9e011b46eb0aca732186`. [Update-1.md](Update-1.md) defines the seed, records all five uses, links the exact source and contains a runnable verification command.

The seed is the run configuration integer used to generate repeatable pseudorandom investigator selections, conversion draws, random audit selections, turn scheduling permutations and instigator approval-request samples. Draws use event-specific keys. The seed is not passed to the language models and does not make complete runs deterministic. Actual events also depend on probabilities, agent eligibility and the current candidate lists.

Read-only checks executed the source expressions and confirmed repeatability of 4,000 keyed draws. The current seed-2 Luna configs also specify priority service, so avoid asserting that the published seed variants differ only in their seed. No implementation or paper edits were requested or made. No unresolved blocker remains for the definition.
