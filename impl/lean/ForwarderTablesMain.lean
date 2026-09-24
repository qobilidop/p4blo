import P4blo.ForwarderTableTests

def main : IO Unit := do
  let configurations ← P4blo.ForwarderTableTests.profiles.mapM P4blo.ForwarderTableTests.snapshot
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.Forwarder.program.toJson),
    ("index", P4blo.CallReturnTests.indexJson P4blo.Forwarder.index),
    ("configurations", Lean.toJson configurations)]).compress
