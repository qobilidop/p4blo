import Tests.Check
import P4bloIR.DeviationLaws
import Std.Data.HashMap.Lemmas

/-!
An instance of every public theorem of `P4bloIR.DeviationLaws`, in the
order of that module: each is applied to concrete values, runs, tables and
machine configurations that meet all of its premises, so no premise set is
empty. A theorem without premises is applied to concrete arguments too.
A few executable checks of the same cases follow.

The instances show only that the premises can be met together. What each
theorem says about the definitions is in its own statement.
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
private def stack1 : Value := .stack "H" [valid, x] 1

private def frame : Frame :=
  { scope := default,
    vars := ({} : Std.HashMap String Value)
      |>.insert "x" x |>.insert "y" y |>.insert "v" valid |>.insert "hs" stack
      |>.insert "hs1" stack1 }

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
  read "hs" stack (by simp [frame, Std.HashMap.getElem_insert])
private theorem read_hs1 : (evaluate (.var "hs1")).run run = (.ok stack1, run) :=
  read "hs1" stack1 (by simp [frame])
private theorem readL_hs : (readLValue (.var "hs")).run run = (.ok stack, run) := by
  have h : frame.vars["hs"]? = some stack := by simp [frame, Std.HashMap.getElem_insert]
  simp [readLValue, readVar, ScalarTyping.run_getFrame, run, Frame.read?, h, ScalarTyping.run_bind]
  rfl
private theorem lit (w v : Nat) :
    (evaluate (.literal (.bits w v))).run run = (.ok (literalValue (.bits w v)), run) := rfl
private theorem header_declared : run.index.headerTypes["H"]? = some ⟨"H", fields⟩ := by
  simp [run, index]
private theorem header_fields : ∀ f ∈ (⟨"H", fields⟩ : HeaderType).fields, HeaderFieldTy f.type := by
  simp [fields, HeaderFieldTy]

-- ---------------------------------------------------------------------------
-- Header equality, `==` and `!=`
-- ---------------------------------------------------------------------------

example := header_equal_invalid "H" "G" [.bool true] []
example := header_equal_valid_invalid "H" "H" [.bool true] [.bool true]
example := header_equal_invalid_valid "H" "H" [.bool true] [.bool true]
example := header_equal_valid "H" "H" [.bool true] [.bool false]

-- `==` through the evaluator, on two variables.
example := evaluate_eq (.var "x") (.var "y") run run run x y read_x read_y

-- Two invalid headers with different stored fields compare equal.
example : (evaluate (.binary .eq (.var "x") (.var "y"))).run run = (.ok (.bool true), run) :=
  evaluate_eq_invalid_headers _ _ run run run "H" "H" _ _ read_x read_y

-- A valid and an invalid header with the same stored fields compare unequal.
example : (evaluate (.binary .eq (.var "v") (.var "x"))).run run = (.ok (.bool false), run) :=
  evaluate_eq_valid_invalid _ _ run run run "H" "H" _ _ read_v read_x

example := evaluate_ne (.var "v") (.var "x") run run run valid x read_v read_x

-- `!=` on two invalid headers is `false`, the negation of their `==`.
example : (evaluate (.binary .ne (.var "x") (.var "y"))).run run = (.ok (.bool false), run) :=
  evaluate_ne_eq _ _ run run true
    (evaluate_eq_invalid_headers _ _ run run run "H" "H" _ _ read_x read_y)

-- `!=` fails as `==` does when an operand names no variable.
private theorem read_nope : ∃ f, (readVar "nope").run run = (.error f, run) := by
  have h : frame.vars["nope"]? = none := by simp [frame]
  refine ⟨.interp "unknown variable 'nope' in block ''", ?_⟩
  simp [readVar, ScalarTyping.run_getFrame, run, Frame.read?, h, ScalarTyping.run_bind]
  rfl

example : ∃ f, (evaluate (.binary .ne (.var "nope") (.var "x"))).run run = (.error f, run) := by
  obtain ⟨f, h⟩ := read_nope
  exact ⟨f, evaluate_ne_eq_error _ _ run run f (by simp [evaluate, ScalarTyping.run_bind, h])⟩

example := (equal_bits_iff (Bits.wrap 8 1) (Bits.wrap 8 1)).mpr rfl
example := (equal_bool_iff true true).mpr rfl
example := equalList_cons (.bool true) (.bool false) [] []

private theorem kinds :
    SameScalarKinds [.bits (Bits.wrap 8 1), .bool true] [.bits (Bits.wrap 8 2), .bool true] :=
  .cons trivial (.cons trivial .nil)

example := equalList_scalar_iff _ _ kinds
example := header_equal_valid_iff "H" "H" _ _ kinds

-- ---------------------------------------------------------------------------
-- Zero values
-- ---------------------------------------------------------------------------

private theorem hz : Value.zeroHeader "H" index = .ok zeroH :=
  zeroHeader_eq index "H" ⟨"H", fields⟩ (by simp [index]) header_fields

example := zero_bits index 8
example := zero_boolean index
example := zero_error index

-- ---------------------------------------------------------------------------
-- Index out of range
-- ---------------------------------------------------------------------------

example := elementOf_out_of_range run "H" [valid, x] 5 ⟨"H", fields⟩ (by decide) header_declared
  header_fields

-- `hs[5]` on a two-element stack is the zero invalid header.
example : (evaluate (.index (.var "hs") (.literal (.bits 32 5)))).run run = (.ok zeroH, run) :=
  evaluate_index_out_of_range _ _ run run run "H" _ 0 (Bits.wrap 32 5) ⟨"H", fields⟩ read_hs rfl
    (by decide) header_declared header_fields

example := readLValue_index_out_of_range (.var "hs") (.literal (.bits 32 5)) run run run "H" _ 0
  _ ⟨"H", fields⟩ readL_hs (lit 32 5) (by decide) header_declared header_fields

example := writeLValue_index_out_of_range (.var "hs") (.literal (.bits 32 5)) (.bool true)
  run run run "H" _ 0 _ readL_hs (lit 32 5) (by decide)

private theorem field_a : run.index.fieldIndex? "H" "a" = some 0 := by
  simp [run, index, Index.fieldIndex?, Index.fields?, fields]; rfl

example := writeLValue_member_out_of_range (.var "hs") (.literal (.bits 32 5)) "a"
  (.bits (Bits.wrap 8 7)) run "H" _ 0 _ ⟨"H", fields⟩ 0 readL_hs (lit 32 5) (by decide)
  header_declared header_fields field_a

-- ---------------------------------------------------------------------------
-- hs.lastIndex and hs.last
-- ---------------------------------------------------------------------------

example := evaluate_lastIndex (.var "hs") run run "H" _ 0 read_hs
example := lastIndex_empty
example := lastIndex_nonempty 1 (by decide)

-- `hs.last` on an empty stack is the zero invalid header.
example : (evaluate (.index (.var "hs") (.lastIndex (.var "hs")))).run run = (.ok zeroH, run) :=
  evaluate_last_empty _ run "H" _ ⟨"H", fields⟩ read_hs (by decide) header_declared header_fields

-- `hs1.last` with `nextIndex = 1` of two elements is element 0.
example := evaluate_last_nonempty (.var "hs1") run "H" _ 1 read_hs1 (by decide) (by decide)
  (by decide)

-- ---------------------------------------------------------------------------
-- push_front and pop_front
-- ---------------------------------------------------------------------------

example := pushFront_eq "H" [valid, x] 1 1 index zeroH hz
example := pushFront_spec "H" [valid, x] 1 1 index zeroH hz
example := pushFront_clamp "H" [valid, x] 1 5 index zeroH hz (by decide)
example := popFront_eq "H" [valid, x] 1 1 index zeroH hz
example := popFront_spec "H" [valid, x] 1 1 index zeroH hz (by decide)
example := popFront_clamp "H" [valid, x] 1 5 index zeroH hz (by decide) (by decide)

-- ---------------------------------------------------------------------------
-- Shifts by the width or more
-- ---------------------------------------------------------------------------

example := evaluate_shl_large (.literal (.bits 8 3)) (.literal (.bits 32 9)) run run run
  (Bits.wrap 8 3) (Bits.wrap 32 9) (lit 8 3) (lit 32 9) (by decide)
example := evaluate_shr_large (.literal (.bits 8 3)) (.literal (.bits 32 3000)) run run run
  (Bits.wrap 8 3) (Bits.wrap 32 3000) (lit 8 3) (lit 32 3000) (by decide)
example := wrap_zero_value 8

-- ---------------------------------------------------------------------------
-- Bit alignment
-- ---------------------------------------------------------------------------

example := write_fits {} 12 0xabc (by decide) (by decide)
example := toBytes_padded (({} : Emitter).write 12 0xabc)
  (write_fits {} 12 0xabc (by decide) (by decide)).2.2

-- ---------------------------------------------------------------------------
-- Parser loop bound
-- ---------------------------------------------------------------------------

private def loop : State := ⟨"loop", [], .direct (.state "loop")⟩
private def other : State := ⟨"other", [], .direct .accept⟩
private def scope : BlockScope :=
  { block := default, states := ({} : Std.HashMap String State).insert "loop" loop }

-- A run whose record is empty, and one where `loop` was entered at cursor 0.
private def run0 : Run := { run with visits := {} }
private def runAt0 : Run :=
  { run with visits := ({} : Std.HashMap (String × String) Nat).insert ("", "loop") 0 }

private theorem block_name (r : Run) (h : r.frame = frame) : r.frame.block.name = "" := by
  rw [h]; rfl

-- Entering `loop` again at the recorded cursor 8 is a timeout.
example : (enterState loop).run run = (.error (.parse "ParserTimeout"), run) :=
  enterState_revisit _ run packet rfl (by rw [block_name run rfl]; simp [run, loop]; rfl)

private theorem fresh0 : run0.visits[(run0.frame.block.name, loop.name)]? ≠ some packet.cursor := by
  simp [run0]

private def run1 : Run :=
  { run0 with visits := run0.visits.insert (run0.frame.block.name, loop.name) packet.cursor }

private theorem enter0 : (enterState loop).run run0 = (.ok (), run1) :=
  enterState_first loop run0 packet rfl fresh0
example := enterState_again loop run0 _ enter0

-- Entering `loop`, then `other`, then `loop` at one cursor: the third entry times out.
example : ∃ r1 r2, (enterState loop).run run0 = (.ok (), r1) ∧
    (enterState other).run r1 = (.ok (), r2) ∧
    (enterState loop).run r2 = (.error (.parse "ParserTimeout"), r2) := by
  refine ⟨_, _, enter0, enterState_first other _ packet rfl ?_, ?_⟩
  · rw [block_name run1 rfl]; simp [run1, run0, loop, other]
  · apply enterState_revisit loop _ packet rfl
    rw [block_name _ rfl]; simp [run1, run0, loop, other, Std.HashMap.getElem?_insert]; rfl

example := step_state_revisit scope loop [] run packet rfl
  (by rw [block_name run rfl]; simp [run, loop]; rfl)

-- One step of the machine on an empty statement list.
private theorem step_nil :
    Execution.step ⟨[.statements []], run0, none⟩ = .inr ⟨[], run0, none⟩ := rfl
private theorem reach_nil : Reaches ⟨[.statements []], run0, none⟩ ⟨[], run0, none⟩ :=
  .step step_nil (.refl _)

example := step_advances _ _ step_nil
example := reaches_advances reach_nil
example := reaches_cursor_le reach_nil packet rfl
example := recorded_empty run0 rfl
example := recorded_of_advances (recorded_empty run0 rfl) (step_advances _ _ step_nil)
example := reaches_recorded reach_nil (recorded_empty run0 rfl)

-- `loop` last entered at cursor 0 is entered again at cursor 8: the cursor advanced.
private theorem recordedAt0 : Recorded runAt0 := by
  intro p hp k c hc
  simp only [runAt0, run] at hp
  cases hp
  simp only [runAt0, Std.HashMap.getElem?_insert] at hc
  split at hc
  · cases hc; decide
  · simp at hc

example : 0 < packet.cursor := by
  have hv : runAt0.visits[(runAt0.frame.block.name, loop.name)]? = some 0 := by
    rw [block_name runAt0 rfl]; simp [runAt0, loop]
  exact enterState_advanced loop runAt0 _ packet 0 recordedAt0 rfl hv
    (enterState_first loop runAt0 packet rfl (by rw [hv]; decide))

-- Entering `loop` and, with nothing consumed, entering it again times out.
example := enterState_no_consumption loop loop run0 _ _ packet packet rfl enter0
  (reaches_advances (.refl ⟨[], _, none⟩)) rfl rfl rfl rfl

-- On the machine: enter `loop`, run its empty body and its transition back to
-- `loop`, and the second entry at the same cursor starts unwinding.
private theorem step_enter :
    Execution.step ⟨[.state scope loop], run0, none⟩ =
      .inr ⟨[.statements [], .transition scope loop.transition], run1, none⟩ := by
  simp only [Execution.step, Option.isSome_none, Bool.false_and, Bool.false_eq_true, ite_false,
    Execution.dispatch, ScalarTyping.run_bind, enter0, ScalarTyping.run_pure]
  rfl

private theorem reach_again :
    Reaches ⟨[.statements [], .transition scope loop.transition], run1, none⟩
      ⟨[.state scope loop], run1, none⟩ := by
  refine .step rfl (.step ?_ (.refl _))
  have hs : scope.states["loop"]? = some loop := by simp [scope]
  simp only [Execution.step, Option.isSome_none, Bool.false_and, Bool.false_eq_true, ite_false,
    Execution.dispatch, loop, P4bloIR.transition, ScalarTyping.run_bind, ScalarTyping.run_pure, hs,
    List.nil_append]
  rfl

example := reaches_state_revisit scope scope loop loop [] [] _ _ ⟨[.state scope loop], run1, none⟩
  packet packet rfl rfl rfl step_enter rfl reach_again rfl rfl rfl rfl rfl rfl

-- ---------------------------------------------------------------------------
-- LPM and priority
-- ---------------------------------------------------------------------------

private def tbl : Table :=
  { name := "t", keys := [⟨.var "k", .lpm, "k"⟩], actions := ["a"],
    defaultAction := none, constDefaultAction := false, constEntries := [], size := 0 }
private def tscope : BlockScope :=
  { block := default, tables := ({} : Std.HashMap String Table).insert "t" tbl }
private def tindex : Index :=
  { program := default, scopes := ({} : Std.HashMap String BlockScope).insert "c" tscope }
private def short : Entry := ⟨[.lpm 0x0A000000 8], ⟨"short", []⟩, 0⟩
private def long : Entry := ⟨[.lpm 0x0A010000 16], ⟨"long", []⟩, 0⟩
private def inst : Installed :=
  { index := tindex,
    entries := ({} : Std.HashMap TableRef (Array Entry)).insert ("c", "t") #[short, long] }
private def key : List Bits := [Bits.wrap 32 0x0A010203]
private def keyMiss : List Bits := [Bits.wrap 32 0x0B000000]

private theorem ht : inst.table? ("c", "t") = .ok tbl := by
  simp [inst, tindex, tscope, Installed.table?]; rfl
private theorem he : inst.entries.getD ("c", "t") #[] = #[short, long] := by simp [inst]
private theorem hd : inst.defaults.getD ("c", "t") none = none := by simp [inst]

-- `10.1.2.3` matches both `10/8` and `10.1/16`; the lookup picks `10.1/16`.
private theorem hit :
    inst.lookup ("c", "t") key = .ok { action := some ⟨"long", []⟩, hit := true } := by
  simp only [Installed.lookup, ht, he, hd]
  rfl
private theorem miss : inst.lookup ("c", "t") keyMiss = .ok { action := none, hit := false } := by
  simp only [Installed.lookup, ht, he, hd]
  rfl

example := prefixLength_eq long
example := prefixLength_single [] [] 0x0A010000 16 ⟨"long", []⟩ 0 (by simp)
example := rank_lpm long
example := keyValueMatches_exact 7 (Bits.wrap 8 7)
example := keyValueMatches_lpm 0x0A010000 16 (Bits.wrap 32 0x0A010203) (by decide)
example := keyValueMatches_ternary 0x0A000000 0xFF000000 (Bits.wrap 32 0x0A010203)
example := lookup_hit inst ("c", "t") key tbl _ ht rfl hit rfl
example := lookup_miss inst ("c", "t") keyMiss tbl _ ht rfl miss rfl
example := lookup_longest_prefix inst ("c", "t") key tbl _ ht rfl rfl hit rfl
example := lookup_longest_lpm inst ("c", "t") key tbl _ ht rfl rfl hit rfl

-- ---------------------------------------------------------------------------
-- Executable checks
-- ---------------------------------------------------------------------------

private def isValue (result : Except Fault Value) (expected : Value) : Bool :=
  match result with
  | .ok value => value == expected
  | .error _ => false

def tests : T Unit := do
  check "invalid headers with different fields are equal"
    (isValue ((evaluate (.binary .eq (.var "x") (.var "y"))).run run).1 (.bool true))
  check "valid and invalid headers with equal fields are unequal"
    (isValue ((evaluate (.binary .eq (.var "v") (.var "x"))).run run).1 (.bool false))
  check "!= on two invalid headers is false"
    (isValue ((evaluate (.binary .ne (.var "x") (.var "y"))).run run).1 (.bool false))
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
