import P4bloIRTest.DeclarationCodec
import P4bloIR.TableCodecLaws

open Lean P4bloIR

namespace TableCodecTests

def wireCall : ActionCall := ⟨"Missing", [.bits 0 (10 ^ 100 + 7), .boolean false,
  .enumMember "" "", .error "", .bits (2 ^ 32 - 1) 0]⟩
def wireKey : Key := ⟨.slice (.lookahead (.stack "Missing" 0)) 0 (2 ^ 32 - 1), .lpm, ""⟩
def wireEntry : Entry := ⟨[.exact (10 ^ 100), .lpm 99 (2 ^ 32 - 1), .ternary 73 2],
  wireCall, 2 ^ 32 - 1⟩
def wireTable (flag : Bool) (default : Option ActionCall) : Table := ⟨"",
  [wireKey, ⟨.literal (.bits 0 77), .exact, "same"⟩, ⟨.var "missing", .ternary, "same"⟩],
  ["", "same", "same", "Missing"], default, flag,
  [wireEntry, ⟨[], ⟨"", []⟩, 0⟩, ⟨[.ternary (10 ^ 100) 0], ⟨"same", [.boolean true]⟩, 2⟩], 0⟩

/-- All four laws have constructive, kernel-checked wire-only instances. -/
theorem tables_roundtrip (path : String) (flag : Bool) :
    Key.decode path wireKey.toJson = .ok wireKey ∧
    ActionCall.decode path wireCall.toJson = .ok wireCall ∧
    Entry.decode path wireEntry.toJson = .ok wireEntry ∧
    Table.decode path (wireTable flag none).toJson = .ok (wireTable flag none) ∧
    Table.decode path (wireTable flag (some ⟨"", []⟩)).toJson =
      .ok (wireTable flag (some ⟨"", []⟩)) ∧
    Table.decode path (wireTable flag (some wireCall)).toJson =
      .ok (wireTable flag (some wireCall)) := by
  refine ⟨CodecLaws.key_roundtrip _ _ ?_, CodecLaws.actionCall_roundtrip _ _ ?_,
    CodecLaws.entry_roundtrip _ _ ?_, CodecLaws.table_roundtrip _ _ ?_,
    CodecLaws.table_roundtrip _ _ ?_, CodecLaws.table_roundtrip _ _ ?_⟩
  all_goals simp [wireKey, wireCall, wireEntry, wireTable, CodecLaws.KeyRepresentable,
    CodecLaws.ActionCallRepresentable, CodecLaws.EntryRepresentable,
    CodecLaws.TableRepresentable, CodecLaws.ExprRepresentable, CodecLaws.TypeRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.KeyValueRepresentable, CodecLaws.UInt32]

-- An absent default adds no premise; neither names nor const flags impose validation.
example (name : String) (actions : List String) (flag : Bool) (size : Nat) :
    CodecLaws.TableRepresentable ⟨name, [], actions, none, flag, [], size⟩ ↔
      CodecLaws.UInt32 size := by simp [CodecLaws.TableRepresentable]

-- Every embedded numeric wire bound remains necessary, including through Table.
example : ¬ CodecLaws.KeyRepresentable ⟨.literal (.bits (2 ^ 32) 0), .exact, ""⟩ := by
  simp [CodecLaws.KeyRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeyRepresentable ⟨.lookahead (.bits (2 ^ 32)), .lpm, ""⟩ := by
  simp [CodecLaws.KeyRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeyRepresentable ⟨.lookahead (.stack "" (2 ^ 32)), .ternary, ""⟩ := by
  simp [CodecLaws.KeyRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeyRepresentable ⟨.slice (.var "") (2 ^ 32) 0, .exact, ""⟩ := by
  simp [CodecLaws.KeyRepresentable, CodecLaws.ExprRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeyRepresentable ⟨.slice (.var "") 0 (2 ^ 32), .exact, ""⟩ := by
  simp [CodecLaws.KeyRepresentable, CodecLaws.ExprRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ActionCallRepresentable ⟨"", [.bits (2 ^ 32) 0]⟩ := by
  simp [CodecLaws.ActionCallRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.EntryRepresentable ⟨[.lpm 0 (2 ^ 32)], ⟨"", []⟩, 0⟩ := by
  simp [CodecLaws.EntryRepresentable, CodecLaws.KeyValueRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.EntryRepresentable ⟨[], ⟨"", [.bits (2 ^ 32) 0]⟩, 0⟩ := by
  simp [CodecLaws.EntryRepresentable, CodecLaws.ActionCallRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.EntryRepresentable ⟨[], ⟨"", []⟩, 2 ^ 32⟩ := by
  simp [CodecLaws.EntryRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TableRepresentable ⟨"", [], [], none, false, [], 2 ^ 32⟩ := by
  simp [CodecLaws.TableRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TableRepresentable
    ⟨"", [⟨.lookahead (.bits (2 ^ 32)), .exact, ""⟩], [], none, false, [], 0⟩ := by
  simp [CodecLaws.TableRepresentable, CodecLaws.KeyRepresentable,
    CodecLaws.ExprRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TableRepresentable
    ⟨"", [], [], some ⟨"", [.bits (2 ^ 32) 0]⟩, false, [], 0⟩ := by
  simp [CodecLaws.TableRepresentable, CodecLaws.ActionCallRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TableRepresentable
    ⟨"", [], [], none, false, [⟨[.lpm 0 (2 ^ 32)], ⟨"", []⟩, 0⟩], 0⟩ := by
  simp [CodecLaws.TableRepresentable, CodecLaws.EntryRepresentable,
    CodecLaws.KeyValueRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TableRepresentable
    ⟨"", [], [], none, false, [⟨[], ⟨"", [.bits (2 ^ 32) 0]⟩, 0⟩], 0⟩ := by
  simp [CodecLaws.TableRepresentable, CodecLaws.EntryRepresentable,
    CodecLaws.ActionCallRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TableRepresentable
    ⟨"", [], [], none, false, [⟨[], ⟨"", []⟩, 2 ^ 32⟩], 0⟩ := by
  simp [CodecLaws.TableRepresentable, CodecLaws.EntryRepresentable, CodecLaws.UInt32]

/-- Direct constructor observation, independent of the shared wire table. -/
def matchKindValue : MatchKind → String
  | .exact => "MATCH_KIND_EXACT"
  | .lpm => "MATCH_KIND_LPM"
  | .ternary => "MATCH_KIND_TERNARY"

def keyValue (v : Key) : Json := Json.mkObj
  [("expr", CodecLawTests.exprValue v.expr), ("match_kind", .str (matchKindValue v.matchKind)),
   ("name", .str v.name)]
def actionValue (v : ActionCall) : Json := Json.mkObj
  [("action", .str v.action), ("args", toJson (v.args.map CodecLawTests.literalValue))]
def entryValue (v : Entry) : Json := Json.mkObj
  [("keys", toJson (v.keys.map CodecLawTests.keyValue)), ("action", actionValue v.action),
   ("priority", toJson v.priority)]
def tableValue (v : Table) : Json := Json.mkObj
  [("name", .str v.name), ("keys", toJson (v.keys.map keyValue)), ("actions", toJson v.actions),
   ("default_action", v.defaultAction.map actionValue |>.getD .null),
   ("const_default_action", .bool v.constDefaultAction),
   ("const_entries", toJson (v.constEntries.map entryValue)), ("size", toJson v.size)]

/-- Extend only the test endpoint; old `key` means KeyValue, never Key. -/
def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  let observe := fun {α : Type} (dec : String → Json → Except String α)
      (value encoded : α → Json) => do
    let v ← dec "leaf" wire
    pure (Json.mkObj [("value", value v), ("encoded", encoded v)])
  match kind with
  | "table_key" => observe Key.decode keyValue Key.toJson
  | "action_call" => observe ActionCall.decode actionValue ActionCall.toJson
  | "entry" => observe Entry.decode entryValue Entry.toJson
  | "table" => observe Table.decode tableValue Table.toJson
  | _ => DeclarationCodecTests.reply request

def tests : T Unit := do
  for (wire, kind) in [("MATCH_KIND_EXACT", MatchKind.exact),
      ("MATCH_KIND_LPM", .lpm), ("MATCH_KIND_TERNARY", .ternary)] do
    checkOk s!"table codec literal match kind {wire}"
      (Key.decode "test" (Json.mkObj [("expr", Json.mkObj [("var", .str "x")]),
        ("match_kind", .str wire)])) (· == ⟨.var "x", kind, ""⟩)
    check s!"table codec independent match observer {wire}" (matchKindValue kind == wire)
  for wire in [Json.mkObj [], Json.mkObj [("action", .null)],
      Json.mkObj [("action", Json.mkObj [])]] do
    checkOk "table codec Entry absent/null/empty action is an empty call"
      (Entry.decode "test" wire) (· == ⟨[], ⟨"", []⟩, 0⟩)
  for wire in [Json.mkObj [], Json.mkObj [("default_action", .null)]] do
    checkOk "table codec Table absent/null default is none"
      (Table.decode "test" wire) (· == ⟨"", [], [], none, false, [], 0⟩)
  checkOk "table codec Table present empty default remains some"
    (Table.decode "test" (Json.mkObj [("default_action", Json.mkObj [])]))
    (· == ⟨"", [], [], some ⟨"", []⟩, false, [], 0⟩)
  for flag in [false, true] do
    checkOk s!"table codec const flag has independent meaning {flag}"
      (Table.decode "test" (Json.mkObj [("const_default_action", .bool flag)]))
      (· == ⟨"", [], [], none, flag, [], 0⟩)
  checkOk "table codec action argument order"
    (ActionCall.decode "test" (Json.mkObj [("action", .str "Missing"), ("args", toJson
      [Json.mkObj [("boolean", .bool false)], Json.mkObj [("error", .str "E")],
       Json.mkObj [("bits", Json.mkObj [("value", .str "99")])]])]))
    (· == ⟨"Missing", [.boolean false, .error "E", .bits 0 99]⟩)
  checkOk "table codec independent string and entry order"
    (Table.decode "test" (Json.mkObj [("actions", toJson (["last", "", "last", "first"] : List String)),
      ("const_entries", toJson [Json.mkObj [("priority", toJson (9 : Nat))], Json.mkObj [],
        Json.mkObj [("priority", toJson (2 : Nat))]])]))
    (· == ⟨"", [], ["last", "", "last", "first"], none, false,
      [⟨[], ⟨"", []⟩, 9⟩, ⟨[], ⟨"", []⟩, 0⟩, ⟨[], ⟨"", []⟩, 2⟩], 0⟩)
  check "table codec expression failure precedes match kind and name"
    (match Key.decode "test" (Json.mkObj [("match_kind", .str "BAD"), ("name", .bool false)]) with
     | .error e => e == "test.expr: no kind set"
     | .ok _ => false)
  check "table codec keys fail before bad name list"
    (match Table.decode "test" (Json.mkObj [("keys", toJson [Json.mkObj []]), ("actions", .bool false)]) with
     | .error e => e == "test.keys[0].expr: no kind set"
     | .ok _ => false)
  check "table codec default failure before const flag"
    (match Table.decode "test" (Json.mkObj [("default_action", .bool false),
      ("const_default_action", .str "true")]) with
     | .error e => e == "test.default_action: expected an object"
     | .ok _ => false)
  check "table codec later entry index"
    (match Table.decode "test" (Json.mkObj [("const_entries", toJson [Json.mkObj [],
      Json.mkObj [("action", Json.mkObj [("args", toJson [Json.mkObj []])])]])]) with
     | .error e => e == "test.const_entries[1].action.args[0]: no kind set"
     | .ok _ => false)

end TableCodecTests
