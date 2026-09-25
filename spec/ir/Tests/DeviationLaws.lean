import Tests.Check
import P4bloIR.DeviationLaws
import Std.Data.HashMap.Lemmas

/-!
Concrete runs that meet the premises of the deviation laws, so that none of
them is vacuous, and a few executable checks of the same cases.
-/

namespace DeviationLawTests
open P4bloIR P4bloIR.DeviationLaws

private def fields : List Field := [⟨"a", .bits 8⟩, ⟨"f", .boolean⟩]

private def index : Index :=
  { program := default,
    headerTypes := ({} : Std.HashMap String HeaderType).insert "H" ⟨"H", fields⟩ }

private def zeroH : Value := .header "H" false [.bits (Bits.wrap 8 0), .bool false]
private def x : Value := .header "H" false [.bits (Bits.wrap 8 1), .bool true]
private def y : Value := .header "H" false [.bits (Bits.wrap 8 2), .bool false]
private def valid : Value := .header "H" true [.bits (Bits.wrap 8 1), .bool true]
private def stack : Value := .stack "H" [valid, x] 0

private def frame : Frame :=
  { scope := default,
    vars := ({} : Std.HashMap String Value)
      |>.insert "x" x |>.insert "y" y |>.insert "v" valid |>.insert "hs" stack }

private def packet : Packet := { Packet.ofBytes (ByteArray.mk #[1, 2]) with cursor := 8 }

private def run : Run :=
  { index, frame, packet := some packet,
    visits := ({} : Std.HashMap (String × String) Nat).insert ("", "loop") 8 }

private theorem read (name : String) (v : Value) (h : frame.vars[name]? = some v) :
    (evaluate (.var name)).run run = (.ok v, run) := by
  simp [evaluate, readVar, ScalarTyping.run_getFrame, run, Frame.read?, h, ScalarTyping.run_bind]
  rfl

private theorem read_x : (evaluate (.var "x")).run run = (.ok x, run) :=
  read "x" x (by simp [frame, Std.HashMap.getElem_insert])
private theorem read_y : (evaluate (.var "y")).run run = (.ok y, run) :=
  read "y" y (by simp [frame, Std.HashMap.getElem_insert])
private theorem read_v : (evaluate (.var "v")).run run = (.ok valid, run) :=
  read "v" valid (by simp [frame, Std.HashMap.getElem_insert])
private theorem read_hs : (evaluate (.var "hs")).run run = (.ok stack, run) :=
  read "hs" stack (by simp [frame])
private theorem header_declared : run.index.headerTypes["H"]? = some ⟨"H", fields⟩ := by
  simp [run, index]
private theorem header_fields : ∀ f ∈ (⟨"H", fields⟩ : HeaderType).fields, HeaderFieldTy f.type := by
  simp [fields, HeaderFieldTy]

-- Two invalid headers with different stored fields compare equal.
example : (evaluate (.binary .eq (.var "x") (.var "y"))).run run = (.ok (.bool true), run) :=
  evaluate_eq_invalid_headers _ _ run run run "H" "H" _ _ read_x read_y

-- A valid and an invalid header with the same stored fields compare unequal.
example : (evaluate (.binary .eq (.var "v") (.var "x"))).run run = (.ok (.bool false), run) :=
  evaluate_eq_valid_invalid _ _ run run run "H" "H" _ _ read_v read_x

-- `hs[5]` on a two-element stack is the zero invalid header.
example : (evaluate (.index (.var "hs") (.literal (.bits 32 5)))).run run = (.ok zeroH, run) :=
  evaluate_index_out_of_range _ _ run run run "H" _ 0 (Bits.wrap 32 5) ⟨"H", fields⟩ read_hs rfl
    (by decide) header_declared header_fields

-- `hs.last` on an empty stack is the zero invalid header.
example : (evaluate (.index (.var "hs") (.lastIndex (.var "hs")))).run run = (.ok zeroH, run) :=
  evaluate_last_empty _ run "H" _ ⟨"H", fields⟩ read_hs (by decide) header_declared header_fields

-- Entering `loop` again at the recorded cursor 8 is a timeout.
example : (enterState ⟨"loop", [], .direct .accept⟩).run run =
    (.error (.parse "ParserTimeout"), run) :=
  enterState_revisit _ run packet rfl (by
    have : run.frame.block.name = "" := rfl
    rw [this]; simp [run]; rfl)

private def isValue (result : Except Fault Value) (expected : Value) : Bool :=
  match result with
  | .ok value => value == expected
  | .error _ => false

def tests : T Unit := do
  check "invalid headers with different fields are equal"
    (isValue ((evaluate (.binary .eq (.var "x") (.var "y"))).run run).1 (.bool true))
  check "valid and invalid headers with equal fields are unequal"
    (isValue ((evaluate (.binary .eq (.var "v") (.var "x"))).run run).1 (.bool false))
  check "out-of-range read is the zero invalid header"
    (isValue ((evaluate (.index (.var "hs") (.literal (.bits 32 5)))).run run).1 zeroH)
  check "lastIndex at nextIndex 0 is 2^32 - 1"
    (isValue ((evaluate (.lastIndex (.var "hs"))).run run).1 (.bits (Bits.wrap 32 (2 ^ 32 - 1))))
  check "push_front past the size clears every element"
    (match pushFront stack 5 index with
     | .ok v => v == .stack "H" [zeroH, zeroH] 2
     | .error _ => false)
  check "pop_front past the size clears every element and nextIndex"
    (match popFront (.stack "H" [valid, x] 1) 5 index with
     | .ok v => v == .stack "H" [zeroH, zeroH] 0
     | .error _ => false)
  check "twelve emitted bits pad to two bytes with four zero bits"
    ((({} : Emitter).write 12 0xabc).toBytes.data == #[0xab, 0xc0])

end DeviationLawTests
