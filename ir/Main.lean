import P4bloIR
import P4bloIR.Observe
import P4bloIR.CertificateWire

/-!
`p4blo-lean`: the pipe endpoint for differential testing.

    p4blo-lean certificate-example-program
        Export the fixed low-level register/counter example as protobuf JSON.

    p4blo-lean check-example-certificate <artifact.json | ->
        Check a bounded execution claim for that exact example. Exit 0 means
        accepted, 1 means mismatch or exhaustion, and 2 means malformed input.
        This is a compiled checker, not an exported kernel proof term.

    p4blo-lean <program.json | ->
        Decode the program, build the name index and print a one-line
        summary. A decoding or indexing error goes to stderr with exit
        code 1.

    p4blo-lean run [--ports N] <program.json>
        Load the program under the switch architecture (`P4bloIR.Switch`)
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
        Every reply also carries `state`, the abstract extern observations
        from `P4bloIR.Observe`, including when the request cannot run.
-/

open P4bloIR

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
def answer (r : Except String SwitchResult) (externs : Externs) : String :=
  let j := match r with
    | .error e => Lean.Json.mkObj [("error", .str e), ("state", externs.observe)]
    | .ok result =>
      let outputs := result.outputs.map fun ((port, bytes) : Nat × ByteArray) =>
        Lean.Json.arr #[Lean.toJson port, .str (bytesToHex bytes)]
      Lean.Json.mkObj ([("outputs", Lean.Json.arr outputs.toArray), ("state", externs.observe)] ++
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
      stdout.putStrLn (answer (.ok result) externs)
    | .error e => stdout.putStrLn (answer (.error e) externs)
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
  | ["certificate-example-program"] =>
    IO.println (Lean.toJson ExecutionCertificate.Example.program).compress
    return 0
  | ["check-example-certificate", path] =>
    let text ← if path == "-" then (← IO.getStdin).readToEnd else IO.FS.readFile path
    match Lean.Json.parse text >>= CertificateWire.verify with
    | .ok verdict =>
      IO.println (Lean.Json.mkObj [("verdict", .str verdict)]).compress
      return if verdict == "accepted" then 0 else 1
    | .error message =>
      IO.println (Lean.Json.mkObj [("error", .str message)]).compress
      return 2
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
    IO.eprintln "usage: p4blo-lean <program.json | -> | run [--ports N] <program.json> | certificate-example-program | check-example-certificate <artifact.json | ->"
    return 2
