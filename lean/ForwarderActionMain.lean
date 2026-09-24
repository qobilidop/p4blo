import P4blo.ForwarderActionTests

def main : IO Unit := do
  let snapshots ← P4blo.ForwarderActionTests.cases.mapM P4blo.ForwarderActionTests.snapshot
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.Forwarder.program.toJson),
    ("action", P4blo.Forwarder.forwardAction.toJson),
    ("snapshots", Lean.toJson snapshots)]).compress
