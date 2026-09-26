import P4bloArchTest.Check

namespace V1ModelTests
open P4bloIR P4bloArch

private def value : Expr := .member (.member (.var "h") "h") "value"
private def target : LValue := .member (.member (.var "h") "h") "value"
private def metadataField (name : String) : LValue := .member (.var "m") name
private def lit (width n : Nat) : Expr := .literal (.bits width n)
private def update (op : BinaryOp) (n : Nat) : Stmt := .assign target (.binary op value (lit 8 n))
private def destination (n : Nat) : Stmt := .assign (metadataField "egress_spec") (lit 9 n)
private def count (n : Nat) : Stmt := .callExtern "counts" "count" [.expr (lit 32 n)] none
private def control (name : String) (body : List Stmt) : Block :=
  { (default : Block) with
    name, kind := .control,
    params := [⟨"h", .struct "H", .inout⟩, ⟨"m", .struct "M", .inout⟩], body }

private def program : BlockAssembly :=
  { (default : BlockAssembly) with
    name := "six_stages", headers := "H", metadata := "M",
    errors := Validity.coreErrors,
    headerTypes := [⟨"Byte", [⟨"value", .bits 8⟩]⟩],
    structTypes := [⟨"H", [⟨"h", .header "Byte"⟩]⟩,
      ⟨"M", [⟨"ingress_port", .bits 9⟩, ⟨"parser_error", .error⟩,
        ⟨"egress_spec", .bits 9⟩, ⟨"egress_port", .bits 9⟩]⟩],
    externTypes := [⟨"counter", [⟨"size", .bits 32, .«in»⟩],
      [⟨"count", [⟨"index", .bits 32, .«in»⟩], none⟩]⟩],
    externInstances := [⟨"counts", "counter", [.bits 32 4]⟩],
    blocks := [
      { (default : Block) with
        name := "P", kind := .parser,
        params := [⟨"h", .struct "H", .out⟩, ⟨"m", .struct "M", .inout⟩],
        startState := "start", states := [⟨"start", [.extract (.member (.var "h") "h")], .direct .accept⟩] },
      control "V" [update .add 1],
      control "I" [update .mul 2, destination 2],
      control "E" [count 0, update .add 3, destination 3],
      control "C" [count 1, update .add 4],
      { (default : Block) with
        name := "D", kind := .deparser,
        params := [⟨"h", .struct "H", .«in»⟩], body := [count 2, .emit (.var "h")] }],
    exports := [⟨"parser", "P"⟩, ⟨"verify_checksum", "V"⟩, ⟨"ingress", "I"⟩,
      ⟨"egress", "E"⟩, ⟨"compute_checksum", "C"⟩, ⟨"deparser", "D"⟩] }

private def replaceBody (p : BlockAssembly) (name : String) (body : List Stmt) : BlockAssembly :=
  { p with blocks := p.blocks.map fun block => if block.name == name then { block with body } else block }

private def execute (p : BlockAssembly) (packet : ByteArray := ⟨#[1, 170]⟩) :
    Except String (V1ModelResult × Externs × List String) := do
  let index ← p.check.mapError toString
  let vm ← V1Model.load index p.toBlockBindings 4
  let externs ← P4bloArch.bind index
  let tags := (Coverage.run vm externs ⟨[]⟩ 0 packet).sorted
  let (result, externs) ← vm.run externs ⟨[]⟩ 0 packet
  pure (result, externs, tags)

private def cellCounts (externs : Externs) : Option (Array Nat) :=
  externs.instances["counts"]?.bind (·.counter?)

private def profile (p : BlockAssembly) : Except String Unit := do
  let index ← Index.build p
  V1ModelProfile.check index p.toBlockBindings

private def checkPacket (name : String) (result : Except String (V1ModelResult × Externs × List String))
    (predicate : V1ModelResult × Externs × List String → Bool) : T Unit :=
  checkOk name (result.map predicate) id

def tests : T Unit := do
  checkPacket "all six stages run in order, preserve payload and select before egress"
    (execute program) fun (result, externs, _) =>
      result.outputs.map (fun (port, bytes) => (port, bytesToHex bytes)) == [(2, "0baa")] &&
      cellCounts externs == some #[1, 1, 1, 0]
  let snapshot := replaceBody program "E" [
    .assign target (.cast (.bits 8) (.binary .add
      (.member (.var "m") "egress_port") (.member (.var "m") "egress_spec"))), destination 3]
  checkPacket "egress sees the selected port and reset egress_spec, and cannot redirect" (execute snapshot)
    fun (result, _, _) => result.outputs.map (fun (port, bytes) => (port, bytesToHex bytes)) == [(2, "06aa")]
  let noEgress := { (replaceBody program "C" [
      .assign target (.cast (.bits 8) (.member (.var "m") "egress_spec"))]) with
    exports := program.exports.filter (·.role != "egress") }
  checkPacket "egress_spec is reset even when egress is omitted" (execute noEgress)
    fun (result, _, _) => result.outputs.map (fun (port, bytes) => (port, bytesToHex bytes)) == [(2, "00aa")]
  let ingressDrop := replaceBody program "I" [destination 511]
  checkPacket "ingress drop suppresses every later effect and coverage" (execute ingressDrop)
    fun (result, externs, tags) => result.outputs.isEmpty && result.diagnostic.isNone &&
      cellCounts externs == some #[0, 0, 0, 0] && !tags.contains "stmt.callExtern" && !tags.contains "stmt.emit"
  let egressDrop := replaceBody program "E" [count 0, destination 511]
  checkPacket "egress drop preserves its effects and suppresses checksum/deparser effects" (execute egressDrop)
    fun (result, externs, tags) => result.outputs.isEmpty && result.diagnostic.isNone &&
      cellCounts externs == some #[1, 0, 0, 0] && !tags.contains "stmt.emit"
  checkPacket "a later assignment reverses drop in the same stage"
    (execute (replaceBody program "I" [destination 511, destination 2]))
    fun (result, _, _) => result.outputs.map (·.1) == [2]
  let parserError := replaceBody program "I" [
    .conditional (.binary .ne (.member (.var "m") "parser_error") (.literal (.error "NoError")))
      [destination 511] [destination 2]]
  checkPacket "parser rejection still reaches ingress with parser_error" (execute parserError ByteArray.empty)
    fun (result, externs, _) => result.outputs.isEmpty && cellCounts externs == some #[0, 0, 0, 0]
  checkError "verify stage cannot read parser_error"
    (profile (replaceBody program "V" [.conditional
      (.binary .eq (.member (.var "m") "parser_error") (.literal (.error "NoError"))) [] []]))
    "v1model stage 'verify_checksum' cannot read 'parser_error'"
  checkError "ingress cannot write egress_port"
    (profile (replaceBody program "I" [.assign (metadataField "egress_port") (lit 9 2)]))
    "v1model stage 'ingress' cannot write 'egress_port'"
  checkError "whole metadata replacement cannot hide readonly writes"
    (profile (replaceBody program "I" [.assign (.var "m") (.var "m")]))
    "v1model stage 'ingress' cannot write 'ingress_port'"
  let child : Block := { (default : Block) with
    name := "Child", kind := .control,
    params := [⟨"x", .bits 9, .inout⟩], body := [.assign (.var "x") (lit 9 1)] }
  let aliased := { (replaceBody program "I" [.callBlock "Child" [.lvalue (metadataField "egress_port")]]) with
    blocks := (replaceBody program "I" [.callBlock "Child" [.lvalue (metadataField "egress_port")]]).blocks ++ [child] }
  checkError "sub-block scalar aliases cannot write readonly metadata" (profile aliased)
    "v1model stage 'ingress' cannot write 'egress_port'"
  let safe := replaceBody aliased "I" [.callBlock "Child" [.lvalue (metadataField "egress_spec")]]
  checkOk "sub-block aliases may update egress_spec in ingress" (profile safe) (fun _ => true)
  let withLegacy := { program with structTypes := program.structTypes.map fun t =>
    if t.name == "M" then { t with fields := t.fields ++ [⟨"drop", .boolean⟩] } else t }
  checkError "legacy drop metadata is rejected" (profile withLegacy) "unsupported v1model metadata field 'drop'"
  let repeated := { program with exports := program.exports.map fun e =>
    if e.role == "egress" then { e with block := "I" } else e }
  checkError "stages cannot share a native block instantiation" (profile repeated)
    "v1model stages must use distinct blocks"
  let stageCall := replaceBody program "I" [.callBlock "E" [.lvalue (.var "h"), .lvalue (.var "m")]]
  checkError "native stage blocks cannot be nested calls" (profile stageCall)
    "v1model stage block 'E' cannot be called as a sub-block"
  for ports in [0, 512] do
    checkError s!"v1model rejects invalid port count {ports}"
      (do V1Model.load (← Index.build program) program.toBlockBindings ports)
      "v1model ports must be between 1 and 511"

end V1ModelTests
