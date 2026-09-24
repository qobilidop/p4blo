import P4blo.ForwarderApplyTests

def main : IO Unit := do
  let snapshots ← P4blo.ForwarderApplyTests.cases.mapM P4blo.ForwarderApplyTests.snapshot
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.Forwarder.program.toJson),
    ("snapshots", Lean.toJson snapshots)]).compress
