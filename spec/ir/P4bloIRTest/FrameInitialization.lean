import P4bloIRTest.Check
import P4bloIR.FrameInitialization

namespace FrameInitializationTests
open P4bloIR

private def block : Block := { (default : Block) with name := "requested", kind := .control }
private def storedBlock : Block := { (default : Block) with name := "stored", kind := .parser }
private def scope : BlockScope :=
  { block := storedBlock
    vars := ({} : Std.HashMap String VarDecl)
      |>.insert "packet" (.param ⟨"packet", .struct "Nested", .inout⟩)
      |>.insert "input" (.param ⟨"input", .bits 8, .in⟩)
      |>.insert "output" (.param ⟨"output", .bits 9, .out⟩)
      |>.insert "data" (.param ⟨"data", .boolean, .none⟩)
      |>.insert "observer" (.var ⟨"observer", .bits 65⟩)
      |>.insert "unrelated" (.var ⟨"differentDeclarationName", .boolean⟩) }
private def index : Index :=
  { program := default
    headerTypes := ({} : Std.HashMap String HeaderType)
      |>.insert "Mixed" ⟨"Mixed", [⟨"octet", .bits 8⟩, ⟨"wide", .bits 65⟩, ⟨"flag", .boolean⟩]⟩
      |>.insert "Empty" ⟨"Empty", []⟩
    structTypes := ({} : Std.HashMap String StructType).insert "Nested"
      ⟨"Nested", [⟨"header", .header "Mixed"⟩, ⟨"empty", .header "Empty"⟩, ⟨"port", .bits 9⟩]⟩
    scopes := ({} : Std.HashMap String BlockScope).insert "requested" scope }

-- These answers are built directly, without invoking any zero initializer.
private def expectedPacket : Value := .struct "Nested"
  [.header "Mixed" false [.bits ⟨8, 0, by decide⟩, .bits ⟨65, 0, by decide⟩, .bool false],
   .header "Empty" false [], .bits ⟨9, 0, by decide⟩]
private def expected : List (String × Value) :=
  [("packet", expectedPacket), ("input", .bits ⟨8, 0, by decide⟩),
   ("output", .bits ⟨9, 0, by decide⟩), ("data", .bool false),
   ("observer", .bits ⟨65, 0, by decide⟩), ("unrelated", .bool false)]

private theorem scope_lookup : index.scopes[block.name]? = some scope := by
  simp [index, block]

private theorem packet_zero : Value.zero (.struct "Nested") index = .ok expectedPacket := by
  simp [Value.zero, Value.zeroWith, index, Std.HashMap.size_insert,
    Std.HashMap.getElem?_insert, expectedPacket, Bits.wrap]
  rfl

private theorem all_zero : ∀ (name : String) (decl : VarDecl),
    scope.vars[name]? = some decl → ∃ value, Value.zero decl.type index = .ok value := by
  intro name decl hd
  simp only [scope, Std.HashMap.getElem?_insert, Std.HashMap.getElem?_empty] at hd
  repeat first
    | split at hd
    | contradiction
    | cases hd
    | exact ⟨expectedPacket, packet_zero⟩
    | exact ⟨_, rfl⟩

-- The theorem has an inhabited premise covering every actual declaration.
example : ∃ frame, Frame.forBlock index block = .ok frame ∧ frame.scope = scope ∧
    frame.action = none ∧ frame.actionVars = none ∧
    ∀ (name : String), frame.vars[name]? =
      (scope.vars[name]?).bind (fun decl => (Value.zero decl.type index).toOption) :=
  Frame.forBlock_initialized index block scope scope_lookup all_zero

-- Independently expected values also follow through the actual frame loop;
-- this is a kernel witness, distinct from the compiled observations below.
example : ∃ frame, Frame.forBlock index block = .ok frame ∧
    frame.read? "packet" = some expectedPacket ∧
    frame.read? "unrelated" = some (.bool false) ∧
    frame.read? "differentDeclarationName" = none ∧ frame.block = storedBlock := by
  obtain ⟨frame, hf, hs, _, ha, hv⟩ :=
    Frame.forBlock_initialized index block scope scope_lookup all_zero
  refine ⟨frame, hf, ?_, ?_, ?_, ?_⟩
  · simp [Frame.read?, ha, hv, scope, Std.HashMap.getElem_insert,
      packet_zero, VarDecl.type, Except.toOption]
  · simp [Frame.read?, ha, hv, scope, Value.zero, Value.zeroWith, VarDecl.type, Except.toOption]
    rfl
  · simp [Frame.read?, ha, hv, scope]
  · exact congrArg BlockScope.block hs

-- The scope's stored block and declaration names are deliberately inconsistent.
-- Production initialization uses the scope-map key and each variable-map key.
example : scope.block ≠ block := by
  intro h
  have hn := congrArg Block.name h
  contradiction
example : scope.vars["unrelated"]? = some (.var ⟨"differentDeclarationName", .boolean⟩) := by
  simp [scope]

private def failedScope : BlockScope :=
  { scope with vars := scope.vars.insert "extra" (.var ⟨"extra", .header "Absent"⟩) }
private def failedIndex : Index :=
  { index with scopes := index.scopes.insert "requested" failedScope }

example : ¬ (∀ (name : String) (decl : VarDecl), failedScope.vars[name]? = some decl →
    ∃ value, Value.zero decl.type failedIndex = .ok value) := by
  intro h
  obtain ⟨value, hv⟩ := h "extra" (.var ⟨"extra", .header "Absent"⟩) (by simp [failedScope])
  simp [Value.zero, Value.zeroWith, failedIndex, index, VarDecl.type] at hv

private def checkFrame (label : String) (actual : Except String Frame) : T Unit := do
  match actual with
  | .error e =>
    IO.println s!"     got: {e}"
    check label false
  | .ok frame =>
    for (name, value) in expected do
      check s!"{label}: exact {name}" (frame.vars[name]? == some value && frame.read? name == some value)
    check s!"{label}: no extra storage" (frame.vars.size == 6 && frame.vars["absent"]?.isNone &&
      frame.vars["differentDeclarationName"]?.isNone)
    check s!"{label}: no action layer" (frame.action.isNone && frame.actionVars.isNone)

def tests : T Unit := do
  checkFrame "frame mixed scope/all directions" (Frame.forBlock index block)
  match Frame.forBlock index block with
  | .ok frame =>
    check "frame returns the looked-up scope's different block"
      (frame.block.name == "stored" && frame.block.kind == .parser)
    check "frame preserves the looked-up declaration map"
      (frame.scope.vars["unrelated"]? == some (.var ⟨"differentDeclarationName", .boolean⟩))
  | .error _ => check "frame returns looked-up scope" false
  check "frame extra declaration zero failure"
    (match Frame.forBlock failedIndex block with
      | .error e => e == "unknown header type 'Absent'"
      | .ok _ => false)
  check "frame missing scope exact error"
    (match Frame.forBlock index { block with name := "missing" } with
      | .error e => e == "unknown block 'missing'"
      | .ok _ => false)
  let emptyScope : BlockScope := { block }
  let emptyIndex := { index with scopes := index.scopes.insert "requested" emptyScope }
  check "frame empty scope succeeds without bindings"
    (match Frame.forBlock emptyIndex block with
      | .ok frame => frame.vars.isEmpty && frame.action.isNone && frame.actionVars.isNone
      | .error _ => false)
  -- Exercise real Index.build too, keeping native evidence distinct from the
  -- kernel witness above (which intentionally permits an inconsistent scope).
  let actualBlock : Block := { block with
    params := [⟨"packet", .struct "Nested", .inout⟩, ⟨"input", .bits 8, .in⟩,
      ⟨"output", .bits 9, .out⟩, ⟨"data", .boolean, .none⟩]
    locals := [⟨"observer", .bits 65⟩, ⟨"unrelated", .boolean⟩] }
  match Index.build { (default : Program) with
      headerTypes := index.headerTypes.toList.map Prod.snd
      structTypes := index.structTypes.toList.map Prod.snd
      blocks := [actualBlock] } with
  | .error _ => check "frame real Index.build" false
  | .ok actual => checkFrame "frame real Index.build" (Frame.forBlock actual actualBlock)

end FrameInitializationTests
