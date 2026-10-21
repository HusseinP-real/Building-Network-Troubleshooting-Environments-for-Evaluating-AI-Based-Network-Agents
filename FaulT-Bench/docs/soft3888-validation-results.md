# Executed SOFT3888 validation

These are lab/tool tests without LLM inference or agent scores. Historical failures are retained.

Current deliverables: Kath5_Jiayuan_75Devices and NIKA_Clos_Jiayuan_92Devices (required range: 75–100 devices each). Clos_Jiayuan_41Devices is an undersized historical prototype; its successful tests do not satisfy Topology 2 acceptance.

| Topology / lab | Outcome | Current configuration | Passed stages / attempts | Evidence |
|---|---|---|---|---|
| Kath5_Jiayuan_75Devices / soft3888-07f21b2e12da | FAIL | no | 1 / 6 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-07f21b2e12da.json) |
| Kath5_Jiayuan_75Devices / soft3888-11333250e25d | PASS | no | 29 / 39 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-11333250e25d.json) |
| Kath5_Jiayuan_75Devices / soft3888-18d0f5f4ec85 | PASS | yes | 29 / 39 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-18d0f5f4ec85.json) |
| Kath5_Jiayuan_75Devices / soft3888-1dd3cc3a6b38 | ABORTED | no | 0 / 26 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-1dd3cc3a6b38.json) |
| Kath5_Jiayuan_75Devices / soft3888-27635e511342 | FAIL | no | 0 / 31 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-27635e511342.json) |
| Kath5_Jiayuan_75Devices / soft3888-3108a5c796bb | CONTROL PASS | yes | 5 / 9 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-3108a5c796bb.json) |
| Kath5_Jiayuan_75Devices / soft3888-319ba929029a | FAIL | no | 1 / 25 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-319ba929029a.json) |
| Kath5_Jiayuan_75Devices / soft3888-893c34ff2f58 | FAIL | no | 0 / 0 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-893c34ff2f58.json) |
| Kath5_Jiayuan_75Devices / soft3888-acad988ca23c | ABORTED | no | 2 / 28 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-acad988ca23c.json) |
| Kath5_Jiayuan_75Devices / soft3888-e9d9055024a5 | FAIL | no | 3 / 8 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-e9d9055024a5.json) |
| Kath5_Jiayuan_75Devices / soft3888-f7fb60b8e769 | FAIL | no | 7 / 46 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle1-soft3888-f7fb60b8e769.json) |
| Kath5_Jiayuan_75Devices / soft3888-39b7495778cf | FAIL | no | 0 / 21 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle2-soft3888-39b7495778cf.json) |
| Kath5_Jiayuan_75Devices / soft3888-50be7409696e | PASS | yes | 29 / 38 | [JSON](validation/soft3888/Kath5_Jiayuan_75Devices-cycle2-soft3888-50be7409696e.json) |
| NIKA_Clos_Jiayuan_92Devices / soft3888-334b26835113 | PASS | yes | 25 / 30 | [JSON](validation/soft3888/NIKA_Clos_Jiayuan_92Devices-cycle1-soft3888-334b26835113.json) |
| NIKA_Clos_Jiayuan_92Devices / soft3888-b5401538db83 | EXPERIMENT PASS | yes | 11 / 11 | [JSON](validation/soft3888/NIKA_Clos_Jiayuan_92Devices-cycle1-soft3888-b5401538db83.json) |
| NIKA_Clos_Jiayuan_92Devices / soft3888-f082c7c43304 | CONTROL PASS | yes | 5 / 5 | [JSON](validation/soft3888/NIKA_Clos_Jiayuan_92Devices-cycle1-soft3888-f082c7c43304.json) |
| NIKA_Clos_Jiayuan_92Devices / soft3888-d44d6583784d | PASS | yes | 25 / 29 | [JSON](validation/soft3888/NIKA_Clos_Jiayuan_92Devices-cycle2-soft3888-d44d6583784d.json) |

A failed convergence attempt is not a failed final stage if a later attempt passed. A PASS requires successful exact-lab cleanup. “Current configuration” compares saved topology/scenario content hashes with present files; consult the report for runtime and harness hashes.

Paid SADE evaluation remains unrun until Anthropic/OpenAI credentials are supplied securely. MCP smoke tests verify tools and inventory, not model diagnosis quality.
