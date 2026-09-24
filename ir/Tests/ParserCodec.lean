import Tests.TableCodec
import P4bloIR.ParserCodecLaws

open Lean P4bloIR

namespace ParserCodecTests

def wireState : State := ⟨"", [.conditional (.literal (.boolean false))
  [.push (.var "missing") (2 ^ 32 - 1)] [.emit (.var "")]],
  .select [.lookahead (.stack "Missing" 0), .literal (.bits 0 (10 ^ 100))]
    [⟨[.exact (.boolean false), .masked (.bits 0 99) (.error ""),
       .range (.bits (2 ^ 32 - 1) 77) (.bits 0 2), .dontCare], .state ""⟩,
     ⟨[], .accept⟩, ⟨[.dontCare], .reject⟩]⟩

/-- Kernel nonvacuity: mixed arities/types, all sets/targets and a nested body. -/
theorem parserState_roundtrip (path : String) :
    State.decode path wireState.toJson = .ok wireState := by
  apply CodecLaws.state_roundtrip
  simp [wireState, CodecLaws.StateRepresentable, CodecLaws.TransitionRepresentable,
    CodecLaws.SelectCaseRepresentable, CodecLaws.KeySetRepresentable,
    CodecLaws.StmtRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.LValueRepresentable, CodecLaws.TypeRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]

example (target : Target) : CodecLaws.TransitionRepresentable (.direct target) := by trivial
example : ¬ CodecLaws.KeySetRepresentable (.exact (.bits (2 ^ 32) 0)) := by
  simp [CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeySetRepresentable (.masked (.bits (2 ^ 32) 0) (.boolean false)) := by
  simp [CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeySetRepresentable (.masked (.boolean false) (.bits (2 ^ 32) 0)) := by
  simp [CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeySetRepresentable (.range (.bits (2 ^ 32) 0) (.error "")) := by
  simp [CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.KeySetRepresentable (.range (.error "") (.bits (2 ^ 32) 0)) := by
  simp [CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.SelectCaseRepresentable ⟨[.exact (.bits (2 ^ 32) 0)], .accept⟩ := by
  simp [CodecLaws.SelectCaseRepresentable, CodecLaws.KeySetRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TransitionRepresentable
    (.select [.slice (.var "") (2 ^ 32) 0] []) := by
  simp [CodecLaws.TransitionRepresentable, CodecLaws.ExprRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TransitionRepresentable
    (.select [.slice (.var "") 0 (2 ^ 32)] []) := by
  simp [CodecLaws.TransitionRepresentable, CodecLaws.ExprRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TransitionRepresentable (.select [.lookahead (.bits (2 ^ 32))] []) := by
  simp [CodecLaws.TransitionRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TransitionRepresentable (.select [.lookahead (.stack "" (2 ^ 32))] []) := by
  simp [CodecLaws.TransitionRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.TransitionRepresentable
    (.select [] [⟨[.masked (.boolean false) (.bits (2 ^ 32) 0)], .reject⟩]) := by
  simp [CodecLaws.TransitionRepresentable, CodecLaws.SelectCaseRepresentable,
    CodecLaws.KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.StateRepresentable ⟨"", [.push (.var "") (2 ^ 32)], .direct .accept⟩ := by
  simp [CodecLaws.StateRepresentable, CodecLaws.StmtRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.StateRepresentable ⟨"", [.pop (.var "") (2 ^ 32)], .direct .reject⟩ := by
  simp [CodecLaws.StateRepresentable, CodecLaws.StmtRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.StateRepresentable
    ⟨"", [.conditional (.literal (.bits (2 ^ 32) 0)) [] []], .select [] []⟩ := by
  simp [CodecLaws.StateRepresentable, CodecLaws.StmtRepresentable,
    CodecLaws.ExprRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.StateRepresentable
    ⟨"", [], .select [] [⟨[.range (.error "") (.bits (2 ^ 32) 0)], .state ""⟩]⟩ := by
  simp [CodecLaws.StateRepresentable, CodecLaws.TransitionRepresentable,
    CodecLaws.SelectCaseRepresentable, CodecLaws.KeySetRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]

/-- Direct constructors, independent of production oneof labels and fixtures. -/
def targetValue : Target → Json
  | .state name => Json.mkObj [("tag", .str "state"), ("name", .str name)]
  | .accept => Json.mkObj [("tag", .str "accept")]
  | .reject => Json.mkObj [("tag", .str "reject")]
def keySetValue : KeySet → Json
  | .exact v => Json.mkObj [("tag", .str "exact"), ("value", CodecLawTests.literalValue v)]
  | .masked v m => Json.mkObj [("tag", .str "masked"),
      ("value", CodecLawTests.literalValue v), ("mask", CodecLawTests.literalValue m)]
  | .range lo hi => Json.mkObj [("tag", .str "range"),
      ("lo", CodecLawTests.literalValue lo), ("hi", CodecLawTests.literalValue hi)]
  | .dontCare => Json.mkObj [("tag", .str "dont_care")]
def caseValue (c : SelectCase) : Json := Json.mkObj
  [("sets", toJson (c.sets.map keySetValue)), ("target", targetValue c.target)]
def transitionValue : Transition → Json
  | .direct target => Json.mkObj [("tag", .str "direct"), ("target", targetValue target)]
  | .select keys cases => Json.mkObj [("tag", .str "select"),
      ("keys", toJson (keys.map CodecLawTests.exprValue)), ("cases", toJson (cases.map caseValue))]
def stateValue (s : State) : Json := Json.mkObj
  [("name", .str s.name), ("body", toJson (s.body.map CodecLawTests.stmtValue)),
   ("transition", transitionValue s.transition)]

/-- Only test dispatch grows; production codecs and old labels are unchanged. -/
def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  let observe := fun {α : Type} (dec : String → Json → Except String α)
      (value encoded : α → Json) => do
    let v ← dec "leaf" wire
    pure (Json.mkObj [("value", value v), ("encoded", encoded v)])
  match kind with
  | "target" => observe Target.decode targetValue Target.toJson
  | "key_set" => observe KeySet.decode keySetValue KeySet.toJson
  | "select_case" => observe SelectCase.decode caseValue SelectCase.toJson
  | "transition" => observe Transition.decode transitionValue Transition.toJson
  | "state" => observe State.decode stateValue State.toJson
  | _ => TableCodecTests.reply request

def tests : T Unit := do
  for (wire, target) in [(Json.mkObj [("state", .str "")], Target.state ""),
      (Json.mkObj [("accept", Json.mkObj [])], .accept),
      (Json.mkObj [("reject", Json.mkObj [])], .reject)] do
    checkOk "parser codec literal target constructor" (Target.decode "test" wire) (· == target)
  check "parser codec direct accept observer"
    (targetValue .accept == Json.mkObj [("tag", .str "accept")])
  check "parser codec direct reject observer"
    (targetValue .reject == Json.mkObj [("tag", .str "reject")])
  checkOk "parser codec exact permits Boolean false"
    (KeySet.decode "test" (Json.mkObj [("exact", Json.mkObj [("boolean", .bool false)])]))
    (· == .exact (.boolean false))
  checkOk "parser codec asymmetric masked operands"
    (KeySet.decode "test" (Json.mkObj [("masked", Json.mkObj
      [("value", Json.mkObj [("boolean", .bool false)]),
       ("mask", Json.mkObj [("error", .str "mask")])])]))
    (· == .masked (.boolean false) (.error "mask"))
  checkOk "parser codec descending range"
    (KeySet.decode "test" (Json.mkObj [("range", Json.mkObj
      [("lo", Json.mkObj [("bits", Json.mkObj [("value", .str "99")])]),
       ("hi", Json.mkObj [("bits", Json.mkObj [("value", .str "2")])])])]))
    (· == .range (.bits 0 99) (.bits 0 2))
  checkOk "parser codec wildcard"
    (KeySet.decode "test" (Json.mkObj [("dont_care", Json.mkObj [])])) (· == .dontCare)
  checkOk "parser codec empty select is present"
    (Transition.decode "test" (Json.mkObj [("select", Json.mkObj [])])) (· == .select [] [])
  check "parser codec empty direct is not empty select"
    (Transition.decode "test" (Json.mkObj [("direct", Json.mkObj [])]) matches
      .error "test.direct: no kind set")
  for absent in [Json.mkObj [], Json.mkObj [("target", .null)],
      Json.mkObj [("target", Json.mkObj [])]] do
    check "parser codec missing/null/empty target fails"
      (SelectCase.decode "test" absent matches .error "test.target: no kind set")
  for absent in [Json.mkObj [], Json.mkObj [("transition", .null)],
      Json.mkObj [("transition", Json.mkObj [])]] do
    check "parser codec missing/null/empty transition fails"
      (State.decode "test" absent matches .error "test.transition: no kind set")
  check "parser codec null oneof is absent"
    (Target.decode "test" (Json.mkObj [("accept", .null)]) matches .error "test: no kind set")
  checkOk "parser codec null alternative does not shadow reject"
    (Target.decode "test" (Json.mkObj [("accept", .null), ("reject", Json.mkObj [])]))
    (· == .reject)
  check "parser codec multiple kinds precede invalid payload"
    (Target.decode "test" (Json.mkObj [("reject", .bool false), ("state", .bool false)]) matches
      .error "test: more than one kind set: [state, reject]")
  check "parser codec value fails before mask"
    (KeySet.decode "test" (Json.mkObj [("masked", Json.mkObj [("mask", .bool false)])]) matches
      .error "test.masked.value: no kind set")
  check "parser codec keys fail before cases"
    (Transition.decode "test" (Json.mkObj [("select", Json.mkObj
      [("keys", toJson [Json.mkObj []]), ("cases", .bool false)])]) matches
      .error "test.select.keys[0]: no kind set")
  check "parser codec state name fails before body"
    (State.decode "test" (Json.mkObj [("name", .bool false), ("body", .bool false)]) matches
      .error "test.name: expected a string")
  check "parser codec state body fails before transition"
    (State.decode "test" (Json.mkObj [("body", .bool false), ("transition", .bool false)]) matches
      .error "test.body: expected an array")
  check "parser codec nested later case index"
    (Transition.decode "" (Json.mkObj [("select", Json.mkObj [("cases", toJson
      [Json.mkObj [("target", Json.mkObj [("accept", Json.mkObj [])])],
       Json.mkObj [("sets", toJson [Json.mkObj [("exact", Json.mkObj [])]])]])])]) matches
      .error "select.cases[1].sets[0].exact: no kind set")
  checkOk "parser codec asymmetric ordered cases"
    (Transition.decode "test" (Json.mkObj [("select", Json.mkObj [("cases", toJson
      [Json.mkObj [("target", Json.mkObj [("state", .str "missing")])],
       Json.mkObj [("target", Json.mkObj [("reject", Json.mkObj [])])],
       Json.mkObj [("target", Json.mkObj [("accept", Json.mkObj [])])]])])]))
    (· == .select [] [⟨[], .state "missing"⟩, ⟨[], .reject⟩, ⟨[], .accept⟩])
  checkOk "parser codec arbitrary body order"
    (State.decode "test" (Json.mkObj [("body", toJson
      [Json.mkObj [("apply", Json.mkObj [("table", .str "T")])],
       Json.mkObj [("call_block", Json.mkObj [("block", .str "B")])],
       Json.mkObj [("emit", Json.mkObj [("value", Json.mkObj [("var", .str "v")])])]]),
      ("transition", Json.mkObj [("select", Json.mkObj [])])]))
    (· == ⟨"", [.apply "T" none, .callBlock "B" [], .emit (.var "v")], .select [] []⟩)

end ParserCodecTests
