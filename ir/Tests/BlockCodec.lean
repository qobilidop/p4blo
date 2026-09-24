import Tests.ParserCodec
import P4bloIR.BlockCodecLaws

open Lean P4bloIR

namespace BlockCodecTests

def wireAction : Action := ⟨"",
  [⟨"same", .bits 0, .none⟩, ⟨"same", .struct "Missing", .«in»⟩,
   ⟨"", .stack "Missing" (2 ^ 32 - 1), .out⟩, ⟨"", .boolean, .inout⟩],
  [.conditional (.literal (.boolean false)) [.push (.var "Missing") (2 ^ 32 - 1)]
    [.pop (.var "Missing") 0], .callBlock "" []]⟩
def wireBlock (kind : BlockKind) : Block := ⟨"block", kind, wireAction.params.reverse,
  [⟨"", .bits (2 ^ 32 - 1)⟩, ⟨"same", .stack "" 0⟩, ⟨"same", .error⟩],
  [wireAction, ⟨"", [], []⟩, ⟨"", [], [.emit (.var "Missing")]⟩],
  [TableCodecTests.wireTable false none,
   TableCodecTests.wireTable true (some ⟨"", []⟩),
   TableCodecTests.wireTable false (some TableCodecTests.wireCall)],
  [ParserCodecTests.wireState, ⟨"", [], .direct .accept⟩, ⟨"", [], .direct .reject⟩],
  "Unresolved", [.apply "Missing" none, .emit (.var ""), .advance (.literal (.bits 0 (10 ^ 100)))]⟩

/-- Kernel nonvacuity for every kind, including semantically invalid field combinations. -/
theorem blocks_roundtrip (path : String) (kind : BlockKind) :
    Action.decode path wireAction.toJson = .ok wireAction ∧
    Block.decode path (wireBlock kind).toJson = .ok (wireBlock kind) := by
  refine ⟨CodecLaws.action_roundtrip _ _ ?_, CodecLaws.block_roundtrip _ _ ?_⟩
  all_goals simp [wireAction, wireBlock, TableCodecTests.wireTable,
    TableCodecTests.wireEntry, TableCodecTests.wireKey, TableCodecTests.wireCall,
    ParserCodecTests.wireState, CodecLaws.BlockRepresentable, CodecLaws.ActionRepresentable,
    CodecLaws.ParamRepresentable, CodecLaws.VarRepresentable,
    CodecLaws.TableRepresentable, CodecLaws.KeyRepresentable,
    CodecLaws.EntryRepresentable, CodecLaws.ActionCallRepresentable,
    CodecLaws.KeyValueRepresentable, CodecLaws.StateRepresentable,
    CodecLaws.TransitionRepresentable, CodecLaws.SelectCaseRepresentable,
    CodecLaws.KeySetRepresentable, CodecLaws.StmtRepresentable,
    CodecLaws.ExprRepresentable, CodecLaws.LValueRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]

private def emptyBlock : Block := ⟨"", .control, [], [], [], [], [], "", []⟩
example : ¬ CodecLaws.ActionRepresentable ⟨"", [⟨"", .bits (2 ^ 32), .none⟩], []⟩ := by
  simp [CodecLaws.ActionRepresentable, CodecLaws.ParamRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ActionRepresentable ⟨"", [⟨"", .stack "" (2 ^ 32), .inout⟩], []⟩ := by
  simp [CodecLaws.ActionRepresentable, CodecLaws.ParamRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ActionRepresentable ⟨"", [], [.push (.var "") (2 ^ 32)]⟩ := by
  simp [CodecLaws.ActionRepresentable, CodecLaws.StmtRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ActionRepresentable
    ⟨"", [], [.conditional (.literal (.bits (2 ^ 32) 0)) [] []]⟩ := by
  simp [CodecLaws.ActionRepresentable, CodecLaws.StmtRepresentable,
    CodecLaws.ExprRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with params := [⟨"", .bits (2 ^ 32), .out⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.ParamRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with locals := [⟨"", .stack "Missing" (2 ^ 32)⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.VarRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with actions := [⟨"", [⟨"", .bits (2 ^ 32), .«in»⟩], []⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.ActionRepresentable,
    CodecLaws.ParamRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with actions := [⟨"", [], [.pop (.var "") (2 ^ 32)]⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.ActionRepresentable,
    CodecLaws.StmtRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with tables := [⟨"", [], [], none, false, [], 2 ^ 32⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.TableRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with tables := [⟨"", [⟨.slice (.var "") (2 ^ 32) 0, .exact, ""⟩],
      [], none, false, [], 0⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.TableRepresentable,
    CodecLaws.KeyRepresentable, CodecLaws.ExprRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with tables := [⟨"", [], [], some ⟨"", [.bits (2 ^ 32) 0]⟩, false, [], 0⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.TableRepresentable,
    CodecLaws.ActionCallRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with tables := [⟨"", [], [], none, false,
      [⟨[.lpm 0 (2 ^ 32)], ⟨"", []⟩, 0⟩], 0⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.TableRepresentable,
    CodecLaws.EntryRepresentable, CodecLaws.KeyValueRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with tables := [⟨"", [], [], none, false,
      [⟨[], ⟨"", [.bits (2 ^ 32) 0]⟩, 0⟩], 0⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.TableRepresentable,
    CodecLaws.EntryRepresentable, CodecLaws.ActionCallRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with tables := [⟨"", [], [], none, false, [⟨[], ⟨"", []⟩, 2 ^ 32⟩], 0⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.TableRepresentable,
    CodecLaws.EntryRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with states := [⟨"", [], .select [.slice (.var "") 0 (2 ^ 32)] []⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.StateRepresentable,
    CodecLaws.TransitionRepresentable, CodecLaws.ExprRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with states := [⟨"", [], .select []
      [⟨[.masked (.boolean false) (.bits (2 ^ 32) 0)], .accept⟩]⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.StateRepresentable,
    CodecLaws.TransitionRepresentable, CodecLaws.SelectCaseRepresentable,
    CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with states := [⟨"", [.push (.var "") (2 ^ 32)], .direct .reject⟩] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.StateRepresentable,
    CodecLaws.StmtRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with body := [.emit (.lookahead (.bits (2 ^ 32)))] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.StmtRepresentable,
    CodecLaws.ExprRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with body := [.emit (.lookahead (.stack "" (2 ^ 32)))] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.StmtRepresentable,
    CodecLaws.ExprRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.BlockRepresentable
    { emptyBlock with body := [.pop (.var "") (2 ^ 32)] } := by
  simp [emptyBlock, CodecLaws.BlockRepresentable, CodecLaws.StmtRepresentable, CodecLaws.UInt32]

/-- Direct constructors, independent of BlockKind.names and protoName. -/
def kindValue : BlockKind → String
  | .parser => "BLOCK_KIND_PARSER"
  | .control => "BLOCK_KIND_CONTROL"
  | .deparser => "BLOCK_KIND_DEPARSER"

def actionValue (a : Action) : Json := Json.mkObj
  [("name", .str a.name), ("params", toJson (a.params.map DeclarationCodecTests.paramValue)),
   ("body", toJson (a.body.map CodecLawTests.stmtValue))]
def blockValue (b : Block) : Json := Json.mkObj
  [("name", .str b.name), ("kind", .str (kindValue b.kind)),
   ("params", toJson (b.params.map DeclarationCodecTests.paramValue)),
   ("locals", toJson (b.locals.map DeclarationCodecTests.varValue)),
   ("actions", toJson (b.actions.map actionValue)),
   ("tables", toJson (b.tables.map TableCodecTests.tableValue)),
   ("states", toJson (b.states.map ParserCodecTests.stateValue)),
   ("start_state", .str b.startState), ("body", toJson (b.body.map CodecLawTests.stmtValue))]

def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  let observe := fun {α : Type} (dec : String → Json → Except String α)
      (value encoded : α → Json) => do
    let v ← dec "leaf" wire
    pure (Json.mkObj [("value", value v), ("encoded", encoded v)])
  match kind with
  | "action" => observe Action.decode actionValue Action.toJson
  | "block" => observe Block.decode blockValue Block.toJson
  | _ => ParserCodecTests.reply request

private def object := Json.mkObj
private def empty := object []
private def paramsWire : List Json :=
  [("", "DIRECTION_NONE"), ("same", "DIRECTION_IN"),
   ("same", "DIRECTION_OUT"), ("", "DIRECTION_INOUT")].map fun (name, direction) =>
    object [("name", .str name), ("type", object [("bits", toJson (0 : Nat))]),
      ("direction", .str direction)]
private def params : List Param :=
  [⟨"", .bits 0, .none⟩, ⟨"same", .bits 0, .«in»⟩,
   ⟨"same", .bits 0, .out⟩, ⟨"", .bits 0, .inout⟩]
private def mixedWire (kind : String) : Json := object
  [("name", .str "block-name"), ("kind", .str kind), ("params", toJson paramsWire),
   ("locals", toJson [object [("type", object [("bits", toJson (0 : Nat))])],
     object [("name", .str "same"), ("type", object [("stack", object [("header", .str "Missing")])])],
     object [("name", .str "same"), ("type", object [("boolean", empty)])]]),
   ("actions", toJson [empty, object [("name", .str "same"), ("params", toJson paramsWire)],
     object [("name", .str "same"), ("body", toJson [object [("apply", empty)]])]]),
   ("tables", toJson [empty, object [("name", .str "same"), ("default_action", empty),
     ("const_default_action", .bool true), ("const_entries", toJson [empty])],
     object [("name", .str "same"), ("size", toJson (2 : Nat))]]),
   ("states", toJson [object [("transition", object [("direct", object [("reject", empty)])])],
     object [("name", .str "same"), ("transition", object [("select", empty)])],
     object [("name", .str "same"), ("transition", object [("direct", object [("state", .str "Missing")])])]]),
   ("start_state", .str "different-start"),
   ("body", toJson [object [("call_action", empty)],
     object [("emit", object [("value", object [("var", .str "Missing")])])],
     object [("push", object [("stack", object [("var", .str "")])])]])]
private def mixedBlock (kind : BlockKind) : Block :=
  ⟨"block-name", kind, params,
   [⟨"", .bits 0⟩, ⟨"same", .stack "Missing" 0⟩, ⟨"same", .boolean⟩],
   [⟨"", [], []⟩, ⟨"same", params, []⟩, ⟨"same", [], [.apply "" none]⟩],
   [⟨"", [], [], none, false, [], 0⟩,
    ⟨"same", [], [], some ⟨"", []⟩, true, [⟨[], ⟨"", []⟩, 0⟩], 0⟩,
    ⟨"same", [], [], none, false, [], 2⟩],
   [⟨"", [], .direct .reject⟩, ⟨"same", [], .select [] []⟩, ⟨"same", [], .direct (.state "Missing")⟩],
   "different-start", [.callAction "" [], .emit (.var "Missing"), .push (.var "") 0]⟩

def tests : T Unit := do
  for (wire, kind) in [("BLOCK_KIND_PARSER", BlockKind.parser),
      ("BLOCK_KIND_CONTROL", .control), ("BLOCK_KIND_DEPARSER", .deparser)] do
    checkOk "block codec literal kind constructor"
      (Block.decode "test" (object [("kind", .str wire)]))
      (· == ⟨"", kind, [], [], [], [], [], "", []⟩)
    check "block codec direct kind observer" (kindValue kind == wire)
    checkOk "block codec all fields regardless of kind"
      (Block.decode "test" (mixedWire wire)) (· == mixedBlock kind)
  checkOk "action codec empty action defaults" (Action.decode "test" empty) (· == ⟨"", [], []⟩)
  checkOk "action codec all directions and null body"
    (Action.decode "test" (object [("params", toJson paramsWire), ("body", .null)]))
    (· == ⟨"", params, []⟩)
  for wire in [empty, object [("kind", .null)], object [("kind", .str "BLOCK_KIND_UNSPECIFIED")],
      object [("kind", .str "OTHER_UNSPECIFIED")]] do
    check "block codec unspecified is not parser"
      (Block.decode "test" wire matches .error "test.kind: unspecified")
  check "block codec numeric kind rejected"
    (Block.decode "test" (object [("kind", toJson (1 : Nat))]) matches
      .error "test.kind: expected a string")
  check "block codec unknown kind rejected"
    (Block.decode "test" (object [("kind", .str "BAD")]) matches
      .error "test.kind: unknown value \"BAD\"")
  check "action codec name precedes params"
    (Action.decode "test" (object [("name", .bool false), ("params", .bool false)]) matches
      .error "test.name: expected a string")
  check "action codec params precede body"
    (Action.decode "test" (object [("params", .bool false), ("body", .bool false)]) matches
      .error "test.params: expected an array")
  for ((first, bad, message), (second, bad2)) in
      [(("name", .bool false, "expected a string"), ("kind", .str "BAD")),
       (("kind", .str "BAD", "unknown value \"BAD\""), ("params", .bool false)),
       (("params", .bool false, "expected an array"), ("locals", .bool false)),
       (("locals", .bool false, "expected an array"), ("actions", .bool false)),
       (("actions", .bool false, "expected an array"), ("tables", .bool false)),
       (("tables", .bool false, "expected an array"), ("states", .bool false)),
       (("states", .bool false, "expected an array"), ("start_state", .bool false)),
       (("start_state", .bool false, "expected a string"), ("body", .bool false))] do
    check "block codec adjacent field error precedence"
      (match Block.decode "test" (object [("kind", .str "BLOCK_KIND_CONTROL"),
        (first, bad), (second, bad2)]) with
       | .error error => error == s!"test.{first}: {message}"
       | .ok _ => false)
  check "block codec nested later root index"
    (Block.decode "" (object [("kind", .str "BLOCK_KIND_DEPARSER"),
      ("actions", toJson [empty, object [("params", toJson
        [object [("type", object [("bits", toJson (0 : Nat))]),
          ("direction", .str "DIRECTION_NONE")], .null])]])]) matches
      .error "actions[1].params[1]: expected an object")

end BlockCodecTests
