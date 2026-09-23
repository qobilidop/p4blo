import P4blo.CallBodyEntryTests

def main : IO Unit := do
  let mut snapshots := []
  for (name, body) in P4blo.CallBodyEntryTests.profiles do
    for ev in [false, true] do
      for iv in [false, true] do
        snapshots := snapshots ++ [← P4blo.CallBodyEntryTests.snapshot name body ev iv]
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.Program.toJson P4blo.CallBodyEntry.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson snapshots)]).compress
