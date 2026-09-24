import P4blo.CallEntryTests

def main : IO Unit := do
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.Program.toJson P4blo.CallEntry.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson ([false, true].flatMap fun ev =>
      [false, true].map fun iv => P4blo.CallEntryTests.snapshot ev iv))]).compress
