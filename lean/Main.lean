import P4blo

/-!
`p4blo-lean`: the pipe endpoint for differential testing. Reads a JSON
program from the file named on the command line, or from stdin with `-`,
decodes it, builds the name index and prints a one-line summary. A decoding
or indexing error goes to stderr with exit code 1.
-/

open P4blo

/-- The one-line summary of a program. -/
def summary (p : Program) (index : Index) : String :=
  let tables := p.blocks.foldl (fun n b => n + b.tables.length) 0
  s!"{p.name}: {p.headerTypes.length} header types, {p.structTypes.length} struct types, " ++
  s!"{p.enumTypes.length} enum types, {p.externTypes.length} extern types, " ++
  s!"{p.blocks.length} blocks, {tables} tables, {index.errors.size} errors"

def main (args : List String) : IO UInt32 := do
  let text ← match args with
    | ["-"] => (← IO.getStdin).readToEnd
    | [path] => IO.FS.readFile path
    | _ =>
      IO.eprintln "usage: p4blo-lean <program.json | ->"
      return 2
  match Program.fromJsonString text >>= fun p => (p, ·) <$> Index.build p with
  | .ok (p, index) =>
    IO.println (summary p index)
    return 0
  | .error e =>
    IO.eprintln s!"error: {e}"
    return 1
