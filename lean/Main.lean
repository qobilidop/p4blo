import P4blo

/-!
`p4blo-lean`: the pipe endpoint for differential testing.

    p4blo-lean <program.json | ->
        Decode the program, build the name index and print a one-line
        summary. A decoding or indexing error goes to stderr with exit
        code 1.

    p4blo-lean run [--ports N] <program.json>
        Load the program under the switch architecture (`P4blo.Switch`)
        and answer requests read from stdin, one JSON object per line:

            {"entries": <Entries>, "ingress_port": n, "packet": "<hex>"}

        with one JSON line per request:

            {"outputs": [[port, "<hex>"], ...]}            the packets that left
            {"outputs": [], "diagnostic": "..."}           dropped by the architecture
            {"error": "..."}                               the request could not run

        `entries` is the host's `Entries` message in the protobuf JSON
        mapping and may be omitted; `ingress_port` defaults to 0. Extern
        state persists across requests. `--ports N` (default 4) is the
        number of ports a flood reaches.
-/

open P4blo

/-- The one-line summary of a program. -/
def summary (p : Program) (index : Index) : String :=
  let tables := p.blocks.foldl (fun n b => n + b.tables.length) 0
  s!"{p.name}: {p.headerTypes.length} header types, {p.structTypes.length} struct types, " ++
  s!"{p.enumTypes.length} enum types, {p.externTypes.length} extern types, " ++
  s!"{p.blocks.length} blocks, {tables} tables, {index.errors.size} errors"

/-- Read and index a program from `path`, or from stdin with `-`. -/
def loadProgram (path : String) : IO (Except String (Program × Index)) := do
  let text ← if path == "-" then (← IO.getStdin).readToEnd else IO.FS.readFile path
  pure (Program.fromJsonString text >>= fun p => (p, ·) <$> Index.build p)

/-- One request of the `run` mode. -/
structure Request where
  entries : Entries
  ingressPort : Nat
  packet : ByteArray

/-- Decode a request line. -/
def Request.decode (line : String) : Except String Request := do
  let j ← Lean.Json.parse line
  let entries ← match ← Decode.get? "" j "entries" with
    | none => pure { tables := [] }
    | some e => Entries.decode "entries" e
  let ingressPort ← Decode.uint32Field "" j "ingress_port"
  let packet ← hexToBytes? (← Decode.strField "" j "packet")
  pure { entries, ingressPort, packet }

/-- The JSON line answering a request. -/
def answer (r : Except String SwitchResult) : String :=
  let j := match r with
    | .error e => Lean.Json.mkObj [("error", .str e)]
    | .ok result =>
      let outputs := result.outputs.map fun ((port, bytes) : Nat × ByteArray) =>
        Lean.Json.arr #[Lean.toJson port, .str (bytesToHex bytes)]
      Lean.Json.mkObj ([("outputs", Lean.Json.arr outputs.toArray)] ++
        (result.diagnostic.map fun d => ("diagnostic", Lean.Json.str d)).toList)
  j.compress

/-- Answer requests from stdin until it ends, threading the extern state. -/
partial def serve (sw : Switch) (externs : Externs) : IO Unit := do
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  let mut externs := externs
  repeat
    let line ← stdin.getLine
    if line.isEmpty then break
    let line := line.trimAscii.toString
    if line.isEmpty then continue
    let outcome := do
      let request ← Request.decode line
      sw.run externs request.entries request.ingressPort request.packet
    match outcome with
    | .ok (result, externs') =>
      externs := externs'
      stdout.putStrLn (answer (.ok result))
    | .error e => stdout.putStrLn (answer (.error e))
    stdout.flush

/-- The `run` mode: parse its flags, load the program, serve. -/
def runMode (args : List String) : IO UInt32 := do
  let (ports, rest) ← match args with
    | "--ports" :: n :: rest =>
      match n.toNat? with
      | some n => pure (n, rest)
      | none =>
        IO.eprintln s!"error: --ports wants a number, got {repr n}"
        return 2
    | rest => pure (4, rest)
  let [path] := rest | do
    IO.eprintln "usage: p4blo-lean run [--ports N] <program.json>"
    return 2
  match ← loadProgram path with
  | .error e =>
    IO.eprintln s!"error: {e}"
    return 1
  | .ok (_, index) =>
    match Switch.load index ports, Externs.bind index with
    | .ok sw, .ok externs =>
      serve sw externs
      return 0
    | .error e, _ | _, .error e =>
      IO.eprintln s!"error: {e}"
      return 1

def main (args : List String) : IO UInt32 := do
  match args with
  | "run" :: rest => runMode rest
  | [path] =>
    match ← loadProgram path with
    | .ok (p, index) =>
      IO.println (summary p index)
      return 0
    | .error e =>
      IO.eprintln s!"error: {e}"
      return 1
  | _ =>
    IO.eprintln "usage: p4blo-lean <program.json | -> | p4blo-lean run [--ports N] <program.json>"
    return 2
