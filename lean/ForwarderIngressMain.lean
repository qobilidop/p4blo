import P4blo.ForwarderIngressTests
open P4blo

def main : IO Unit := do
  let snapshots ← ForwarderIngressTests.cases.mapM ForwarderIngressTests.snapshot
  let raw ← [0, 1, 2, 3].mapM ForwarderIngressTests.rawSnapshot
  IO.println (Lean.Json.mkObj [
    ("program", Forwarder.program.toJson), ("snapshots", Lean.toJson snapshots),
    ("raw", Lean.toJson raw)]).compress
