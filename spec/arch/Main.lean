import P4bloArch.Assembly
import P4bloIR
import P4bloArch
import P4bloIR.Observe
import P4bloArch.Coverage

/-!
`p4blo-lean`: the pipe endpoint for differential testing.

    p4blo-lean coverage-inventory
        Print every rule tag of `P4bloIR.Coverage`, one per line, as the
        tag, a tab, and its docstring on one line.

    p4blo-lean check <program.json | -> ...
        Decode each program and check its validity with
        `P4bloArch.BlockAssembly.check`. Prints one line per program, in order:
        `accept`, or `reject CODE PATH: MESSAGE` with the first problem,
        where `CODE` is the Python validator's code, or `DECODE` when the
        program does not decode. Exit code 0 means every program was
        accepted, 1 that one was rejected, 2 that an input was unreadable.

    p4blo-lean check-library <library.json | -> ...
        Check core declarations and blocks without architecture bindings.

    p4blo-lean <program.json | ->
        Decode the program, build the name index and print a one-line
        summary. A decoding or indexing error goes to stderr with exit
        code 1.

    p4blo-lean run [--ports N] <program.json>
        Load the program under the switch architecture (`P4bloArch.Switch`)
        with the reference extern families (`P4bloArch.Externs`)
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
        from `P4bloIR.Observe`, including when the request cannot run, and
        `coverage`, the sorted names of the rule tags the request exercised
        (`P4bloArch.Coverage`): up to the failure on an error reply, and
        empty when the request line itself does not decode.
-/

open P4bloIR P4bloArch

/-- The one-line summary of a program. -/
def summary (p : BlockAssembly) (index : Index) : String :=
  let tables := p.blocks.foldl (fun n b => n + b.tables.length) 0
  s!"{p.name}: {p.headerTypes.length} header types, {p.structTypes.length} struct types, " ++
  s!"{p.enumTypes.length} enum types, {p.externTypes.length} extern types, " ++
  s!"{p.blocks.length} blocks, {tables} tables, {index.errors.size} errors"

/-- Read and index a program from `path`, or from stdin with `-`. -/
def loadProgram (path : String) : IO (Except String (BlockAssembly × Index)) := do
  let text ← if path == "-" then (← IO.getStdin).readToEnd else IO.FS.readFile path
  pure (BlockAssembly.fromJsonString text >>= fun p => (p, ·) <$> Index.build p)

/-- The verdict line for one program text, and whether it was accepted. -/
def verdict (text : String) : String × Bool :=
  match BlockAssembly.fromJsonString text with
  | .error e => (s!"reject DECODE {e}", false)
  | .ok p =>
    match p.check with
    | .ok _ => ("accept", true)
    | .error d => (s!"reject {d.code.name} {d.path}: {d.message}", false)

/-- Check an architecture-free library without imposing entry bindings. -/
def libraryVerdict (text : String) : String × Bool :=
  match BlockLibrary.fromJsonString text with
  | .error e => (s!"reject DECODE {e}", false)
  | .ok p =>
    match Validity.check p with
    | .ok _ => ("accept", true)
    | .error d => (s!"reject {d.code.name} {d.path}: {d.message}", false)

/-- The `check` mode: decode, then check validity; one verdict line per
program. -/
def checkMode (paths : List String) (library : Bool := false) : IO UInt32 := do
  let mut code : UInt32 := 0
  for path in paths do
    let text ← try
        if path == "-" then (← IO.getStdin).readToEnd else IO.FS.readFile path
      catch e =>
        IO.eprintln s!"error: {e}"
        return 2
    let (line, ok) := if library then libraryVerdict text else verdict text
    IO.println line
    if !ok then code := 1
  return code

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

/-- The JSON line answering a request, with the rule tags it exercised. -/
def answer (r : Except String SwitchResult) (externs : Externs) (coverage : List String) :
    String :=
  let tags := ("coverage", Lean.Json.arr (coverage.map Lean.Json.str).toArray)
  let j := match r with
    | .error e => Lean.Json.mkObj [("error", .str e), ("state", externs.observe), tags]
    | .ok result =>
      let outputs := result.outputs.map fun ((port, bytes) : Nat × ByteArray) =>
        Lean.Json.arr #[Lean.toJson port, .str (bytesToHex bytes)]
      Lean.Json.mkObj ([("outputs", Lean.Json.arr outputs.toArray), ("state", externs.observe),
        tags] ++ (result.diagnostic.map fun d => ("diagnostic", Lean.Json.str d)).toList)
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
    let request := Request.decode line
    -- The observer traces the same inputs from the same extern state.
    let coverage := match request with
      | .ok r => (Coverage.run sw externs r.entries r.ingressPort r.packet).sorted
      | .error _ => []
    let outcome := do
      let request ← request
      sw.run externs request.entries request.ingressPort request.packet
    match outcome with
    | .ok (result, externs') =>
      externs := externs'
      stdout.putStrLn (answer (.ok result) externs coverage)
    | .error e => stdout.putStrLn (answer (.error e) externs coverage)
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
  | .ok (program, index) =>
    match Switch.load index program.toBlockBindings ports, P4bloArch.bind index with
    | .ok sw, .ok externs =>
      serve sw externs
      return 0
    | .error e, _ | _, .error e =>
      IO.eprintln s!"error: {e}"
      return 1

def main (args : List String) : IO UInt32 := do
  match args with
  | ["coverage-inventory"] =>
    for info in P4bloIR.Coverage.all do
      IO.println s!"{info.name}\t{info.doc}"
    return 0
  | "run" :: rest => runMode rest
  | "check" :: paths@(_ :: _) => checkMode paths
  | "check-library" :: paths@(_ :: _) => checkMode paths true
  | [path] =>
    match ← loadProgram path with
    | .ok (p, index) =>
      IO.println (summary p index)
      return 0
    | .error e =>
      IO.eprintln s!"error: {e}"
      return 1
  | _ =>
    IO.eprintln "usage: p4blo-lean <program.json | -> | check <program.json | -> ... | run [--ports N] <program.json> | coverage-inventory"
    return 2
