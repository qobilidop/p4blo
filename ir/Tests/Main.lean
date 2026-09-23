import Tests.Check
import Tests.Interp
import Tests.Forwarder
import Tests.ScalarTyping
import Tests.Execution
import Tests.ExecutionCertificate
import Tests.CertificateWire
import Tests.CRC
import Tests.ExternFamilies

/-!
Tests for the decoder, the index and the interpreter, run by `lake test`
from the `ir/` directory (the fixture paths may also be given as
arguments: the program JSON, then the vectors JSON).

`Tests/forwarder.json` is `p4blo.ir.dump_json` of
`tests/corpus/forwarder/forwarder.txtpb`; regenerate it from the repository root
with

    uv run python -c 'from pathlib import Path; from p4blo import ir; \
      print(ir.dump_json(ir.load_text(Path("tests/corpus/forwarder/forwarder.txtpb"))))' \
      > ir/Tests/forwarder.json
-/

open P4blo

def forwarderTests (p : Program) : T Unit := do
  check "program name" (p.name == "forwarder")
  check "seven core errors" (p.errors.length == 7 && p.errors.head? == some "NoError")
  check "three blocks" (p.blocks.length == 3)
  check "block kinds" (p.blocks.map (·.kind) == [.parser, .control, .deparser])
  check "headers and metadata" (p.headers == "headers" && p.metadata == "metadata")
  check "three exports" (p.exports.map (·.role) == ["parser", "control", "deparser"])
  let parser := p.blocks[0]!
  check "parser start state" (parser.startState == "start")
  check "parser has three states" (parser.states.length == 3)
  check "start transitions directly" (parser.states[0]!.transition == .direct (.state "parse_ethernet"))
  check "parse_ethernet selects on etherType"
    (match parser.states[1]!.transition with
     | .select [.member (.member (.var "hdr") "ethernet") "etherType"] cases =>
       cases.length == 2 &&
       cases[0]! == { sets := [.exact (.bits 16 2048)], target := .state "parse_ipv4" } &&
       cases[1]! == { sets := [.dontCare], target := .accept }
     | _ => false)
  let control := p.blocks[1]!
  check "control has one table" (control.tables.length == 1)
  let table := control.tables[0]!
  check "table has one lpm key"
    (table.keys.map (·.matchKind) == [.lpm] && table.name == "ipv4_lpm" && table.size == 1024)
  check "table default action" (table.defaultAction == some { action := "drop", args := [] })
  check "table actions" (table.actions == ["ipv4_forward", "drop", "NoAction"])
  check "control has three actions" (control.actions.map (·.name) == ["NoAction", "drop", "ipv4_forward"])
  check "ipv4_forward params are action data"
    (control.actions[2]!.params.map (·.direction) == [.none, .none])
  check "ttl decrement"
    (match control.actions[2]!.body[3]! with
     | .assign _ (.binary .sub _ (.literal (.bits 8 1))) => true
     | _ => false)
  check "control body applies the table"
    (control.body == [.conditional (.isValid (.member (.var "hdr") "ipv4")) [.apply "ipv4_lpm" none] []])
  let deparser := p.blocks[2]!
  check "deparser emits two headers"
    (deparser.body.length == 2 && deparser.params.map (·.direction) == [.«in»])

def roundtripTests (p : Program) : T Unit := do
  let field (j : Lean.Json) (outer inner : String) := do
    (← j.getObjVal? outer).getObjVal? inner >>= Lean.Json.getStr?
  check "zero bits encode as a present decimal string"
    (field (Literal.bits 8 0).toJson "bits" "value" matches .ok "0")
  check "zero LPM value encodes as a present decimal string"
    (field (KeyValue.lpm 0 0).toJson "lpm" "value" matches .ok "0")
  check "zero ternary value encodes as a present decimal string"
    (field (KeyValue.ternary 0 0).toJson "ternary" "value" matches .ok "0")
  check "zero ternary mask encodes as a present decimal string"
    (field (KeyValue.ternary 0 0).toJson "ternary" "mask" matches .ok "0")
  let encoded := (Lean.toJson p).pretty
  match Program.fromJsonString encoded with
  | .ok p' => check "decode (encode p) == p" (p' == p)
  | .error e =>
    IO.println s!"     got: {e}"
    check "decode (encode p) succeeds" false
  -- Encoding omits defaults exactly as dump_json does, so the fixture
  -- itself must survive a parse-render cycle unchanged in structure.
  check "encode p renders the fixture's keys"
    ((encoded.splitOn "\"const_default_action\"").length == 1 &&
     (encoded.splitOn "\"start_state\"").length == 2)

def indexTests (p : Program) : T Unit := do
  match Index.build p with
  | .ok index =>
    check "index builds" true
    check "index has the three blocks" (index.blocks.size == 3 && index.scopes.size == 3)
    check "index errors are positional" (index.errors["NoMatch"]? == some 2)
    check "index resolves the table" ((index.scopes["MyIngress"]?.bind (·.tables["ipv4_lpm"]?)).isSome)
    check "action params resolve from the action"
      ((index.scopes["MyIngress"]?.bind (·.var? "port" (some "ipv4_forward"))).map (·.name)
        == some "port")
    check "action params do not leak into the block"
      ((index.scopes["MyIngress"]?.bind (·.var? "port")).isNone)
    check "exported control" ((index.exported? "control").map (·.name) == some "MyIngress")
    check "field index" (index.fieldIndex? "ipv4_t" "ttl" == some 7)
  | .error e =>
    IO.println s!"     got: {e}"
    check "index builds" false
  let dupBlock := { p with blocks := p.blocks ++ [p.blocks[0]!] }
  checkError "duplicate block name" (Index.build dupBlock) "'MyParser' declared twice in program"
  let dupType := { p with structTypes := p.structTypes ++ [{ name := "ethernet_t", fields := [] }] }
  checkError "type name reused across kinds" (Index.build dupType) "'ethernet_t' declared twice in program"
  let control := p.blocks[1]!
  let shadow := { p with blocks := p.blocks.map fun b =>
    if b.name == control.name then { b with locals := [{ name := "ipv4_t", type := .bits 1 }] } else b }
  checkError "block-level name reuses a program-level one" (Index.build shadow)
    "'ipv4_t' declared twice in block 'MyIngress'"
  let dupParam := { p with blocks := p.blocks.map fun b =>
    if b.name == control.name then
      { b with actions := b.actions.map fun a =>
        if a.name == "ipv4_forward" then { a with params := a.params ++ [{ name := "hdr", type := .bits 1, direction := .none }] } else a }
    else b }
  checkError "action param reuses a block name" (Index.build dupParam)
    "'hdr' declared twice in action 'ipv4_forward' of block 'MyIngress'"
  let empty := { p with enumTypes := [{ name := "", members := [] }] }
  checkError "empty name" (Index.build empty) "empty name in program"
  let dupError := { p with errors := p.errors ++ ["NoError"] }
  checkError "duplicate error" (Index.build dupError) "error 'NoError' at 7"

def negativeTests : T Unit := do
  checkError "unset oneof"
    (Program.fromJsonString
      "{\"name\": \"x\", \"blocks\": [{\"name\": \"b\", \"kind\": \"BLOCK_KIND_PARSER\", \
       \"states\": [{\"name\": \"s\", \"transition\": {}}]}]}")
    "blocks[0].states[0].transition: no kind set"
  checkError "absent oneof message"
    (Program.fromJsonString "{\"header_types\": [{\"name\": \"h\", \"fields\": [{\"name\": \"f\"}]}]}")
    "header_types[0].fields[0].type: no kind set"
  checkError "two oneof cases"
    (Program.fromJsonString "{\"header_types\": [{\"fields\": [{\"type\": {\"bits\": 1, \"boolean\": {}}}]}]}")
    "header_types[0].fields[0].type: more than one kind set"
  checkError "unspecified enum"
    (Program.fromJsonString "{\"blocks\": [{\"name\": \"b\", \"kind\": \"BLOCK_KIND_UNSPECIFIED\"}]}")
    "blocks[0].kind: unspecified"
  checkError "missing enum"
    (Program.fromJsonString "{\"blocks\": [{\"name\": \"b\"}]}")
    "blocks[0].kind: unspecified"
  checkError "non-decimal literal"
    (Lean.fromJson? (α := Literal) (Lean.Json.mkObj [("bits", Lean.Json.mkObj [("width", 8), ("value", "0x1")])]))
    "bits.value: expected a decimal number"
  checkError "uint32 overflow"
    (Lean.fromJson? (α := Ty) (Lean.Json.mkObj [("bits", (4294967296 : Nat))]))
    "does not fit in uint32"
  checkError "wrong scalar type"
    (Program.fromJsonString "{\"name\": 3}")
    "name: expected a string"
  check "unknown keys are ignored"
    (Program.fromJsonString "{\"name\": \"x\", \"source_file\": \"x.p4\"}" matches .ok _)
  check "empty program decodes" (Program.fromJsonString "{}" matches .ok _)
  check "null is absent"
    (match Program.fromJsonString "{\"name\": null}" with
     | .ok p => p == { (default : Program) with name := "" }
     | .error _ => false)

def main (args : List String) : IO UInt32 := do
  let fixture := args.head?.getD "Tests/forwarder.json"
  let vectors := (args.drop 1).head?.getD "Tests/forwarder_vectors.json"
  let text ← IO.FS.readFile fixture
  let vectorsText ← IO.FS.readFile vectors
  let ((), failures) ← (do
    match Program.fromJsonString text with
    | .ok p =>
      check "fixture decodes" true
      forwarderTests p
      roundtripTests p
      indexTests p
      forwarderReplayTests p vectorsText
    | .error e =>
      IO.println s!"     got: {e}"
      check "fixture decodes" false
    negativeTests
    interpTests
    ScalarTypingTests.tests
    ExecutionTests.tests
    ExecutionCertificateTests.tests
    CRCTests.tests
    ExternFamiliesTests.tests
    certificateWireTests).run []
  if failures.isEmpty then
    IO.println "all tests passed"
    return 0
  else
    IO.println s!"{failures.length} failed: {failures}"
    return 1
