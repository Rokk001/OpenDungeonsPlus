# Workshop order scheduling

On `feature/workshop-order-scheduling`, based on complete fork `8f5a80d4`,
an idle workshop selects the earliest reachable trap order still needing a
crafted item. Previously, required items were grouped by type and the next type
was selected randomly. Existing owned, uncarried stock now covers the earliest
matching orders first, including separate orders of the same type.

`GameMap::addTrap` appends accepted orders and the reachable-building query
preserves their order. Gameplay saves now preserve this sequence rather than
sorting by type; the loader already restores traps in file order. Editor exports
retain their existing sorting. There are no new serialized fields, and older
saves remain readable, but their lost original order cannot be recovered.

## Verification

From the compiler environment described in [BUILDING.md](BUILDING.md), run:

```powershell
python source/tests/check_workshop_order.py
```

The tracked probe compiles the actual scheduling and trap-save blocks with
simulated world services. Thirteen scenarios pass; three fail against the
preceding `8f5a80d4` source using `--source-ref 8f5a80d4`. They cover mixed types,
repeated types, partial stock, completed/reserved orders, filtered-out orders,
stock eligibility, ongoing work, no worker, no demand and save ordering.
This is not a live gameplay or full save/load test: pathfinding, workers, trap
quantities and stock are fixture inputs; serialization uses minimal trap IDs.
The unchanged loader was inspected for sequential restoration.

Windows Release compilation and runtime preparation pass. Logs are
`build/windows/workshop-order-before.log`, `workshop-order-after.log`,
`workshop-order-build.log` and `workshop-order-runtime.log`.

On September 8, the user confirmed mixed trap manufacturing order, including
preservation across a save/load cycle, and explicitly accepted this task as
complete. This closes the pending gameplay check alongside the automated and
build evidence above. Production already in progress is retained; parallel
workshops and delivery timing are outside this focused scheduling check.

Before commit, the version and README were reviewed: this is not a release and
does not change setup, controls or documented README behavior, so neither needs
an update. Current build evidence is recorded in BUILDING.md. The upstream
issue/PR review on September 8 found no contribution specifically covering
workshop scheduling; no issue closure is claimed. No push or game launch occurred.
