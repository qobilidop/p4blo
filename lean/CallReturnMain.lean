import P4blo.CallReturnTests

def main : IO Unit :=
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.CallEntry.program.toJson),
    ("params", Lean.toJson (P4bloIR.PlainCallEntry.params.map P4bloIR.Param.toJson)),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson ([false, true].flatMap fun ev =>
      [false, true].map fun iv => P4blo.CallReturnTests.snapshot ev iv))]).compress
