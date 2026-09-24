import P4blo.GuardedCallPrefixTests

def main : IO Unit := do
  let mut snapshots := []
  for c in P4blo.GuardedForwardTests.cases do
    for priorDrop in [false, true] do
      snapshots := snapshots ++ [← P4blo.GuardedCallPrefixTests.snapshot c priorDrop]
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.Program.toJson P4blo.CallBodyEntry.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson snapshots)]).compress
