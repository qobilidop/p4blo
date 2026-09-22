import Tests.Check

/-!
End-to-end replay of the forwarder's five STF vectors under the switch
architecture (`P4blo.Switch`), the same rules the Python driver in
`tests/test_corpus_forwarder.py` implements.

`Tests/forwarder_vectors.json` holds, per vector file, one run per `packet`
line: the entries installed before it, the ingress port, the packet, and
the `expect` lines that follow it, each with its per-nibble mask and
whether it ended in `$`. It was generated once from the repository root
with

    uv run python - <<'EOF'
    import json
    from pathlib import Path
    from p4blo import ir, stf
    corpus = Path("corpus/forwarder")
    index = ir.Index.build(ir.load_text(corpus / "forwarder.txtpb"))
    vectors = []
    for path in sorted(corpus.glob("*.stf")):
        installed, runs = [], []
        for s in stf.parse(path.read_text()):
            match s:
                case stf.Add() | stf.SetDefault():
                    installed.append(s)
                case stf.Packet():
                    entries = json.loads(ir.dump_json(stf.to_entries(index, installed)))
                    runs.append({"entries": entries, "port": s.port,
                                 "packet": s.data.hex(), "expects": []})
                case stf.Expect():
                    runs[-1]["expects"].append({"port": s.port, "data": s.data.hex(),
                                                "mask": s.mask.hex(), "exact": s.exact})
        vectors.append({"name": path.stem, "runs": runs})
    Path("lean/Tests/forwarder_vectors.json").write_text(json.dumps(vectors, indent=2) + "\n")
    EOF

and must be regenerated whenever the STF files change.
-/

open P4blo
open Lean (Json)

/-- One `expect` line: `mask` has `f` nibbles where the vector wrote a hex
digit and `0` where it wrote `*`; `exact` when the line ended in `$`. -/
structure Expect where
  port : Nat
  data : ByteArray
  mask : ByteArray
  exact : Bool

/-- As `stf.Expect.matches`: the output is at least as long, exactly as
long when `exact`, and agrees under the mask. -/
def Expect.matches (e : Expect) (packet : ByteArray) : Bool :=
  if packet.size < e.data.size || (e.exact && packet.size != e.data.size) then false
  else (List.range e.data.size).all fun i =>
    (packet[i]! &&& e.mask[i]!) == (e.data[i]! &&& e.mask[i]!)

structure VectorRun where
  entries : Entries
  port : Nat
  packet : ByteArray
  expects : List Expect

structure StfVector where
  name : String
  runs : List VectorRun

open Decode in
def Expect.decode (path : String) (j : Json) : Dec Expect := do
  pure { port := ← uint32Field path j "port",
         data := ← hexToBytes? (← strField path j "data"),
         mask := ← hexToBytes? (← strField path j "mask"),
         exact := ← boolField path j "exact" }

open Decode in
def VectorRun.decode (path : String) (j : Json) : Dec VectorRun := do
  pure { entries := ← msgField path j "entries" Entries.decode,
         port := ← uint32Field path j "port",
         packet := ← hexToBytes? (← strField path j "packet"),
         expects := ← listField path j "expects" Expect.decode }

open Decode in
def StfVector.decode (path : String) (j : Json) : Dec StfVector := do
  pure { name := ← strField path j "name", runs := ← listField path j "runs" VectorRun.decode }

def StfVector.decodeAll (text : String) : Except String (List StfVector) := do
  Decode.array "" (← Json.parse text) StfVector.decode

/-- Replay one vector file: the outputs of each run must be exactly, and in
order, what its `expect` lines claim. -/
def replay (sw : Switch) (v : StfVector) : T Unit := do
  let mut externs ← match Externs.bind sw.index with
    | .ok e => pure e
    | .error e => do
      IO.println s!"     bind: {e}"
      check s!"{v.name}: externs bind" false
      return
  for (run, i) in v.runs.zipIdx do
    let name := s!"{v.name} packet {i}"
    match sw.run externs run.entries run.port run.packet with
    | .error e =>
      IO.println s!"     error: {e}"
      check name false
    | .ok (result, externs') =>
      externs := externs'
      let outputs := result.outputs
      let mut ok := outputs.length == run.expects.length && result.diagnostic.isNone
      for ((port, bytes), e) in outputs.zip run.expects do
        if port != e.port || !e.matches bytes then
          IO.println s!"     expected port {e.port} {bytesToHex e.data}, got port {port} {bytesToHex bytes}"
          ok := false
      if outputs.length != run.expects.length then
        IO.println s!"     expected {run.expects.length} outputs, got {outputs.length}"
      if let some d := result.diagnostic then IO.println s!"     diagnostic: {d}"
      check name ok

def forwarderReplayTests (program : Program) (vectorsText : String) : T Unit := do
  let loaded := do
    let index ← Index.build program
    let sw ← Switch.load index 4
    let vectors ← StfVector.decodeAll vectorsText
    pure (sw, vectors)
  match loaded with
  | .error e =>
    IO.println s!"     got: {e}"
    check "forwarder vectors load" false
  | .ok (sw, vectors) =>
    check "five forwarder vectors" (vectors.map (·.name) == ["forward", "lpm_precedence", "miss", "non_ipv4", "too_short"])
    for v in vectors do
      replay sw v
