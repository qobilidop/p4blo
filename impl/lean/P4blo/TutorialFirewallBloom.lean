import P4blo.TutorialFirewallProof
import P4bloArch.Externs

/-! Exact actual Bloom insertion, not hash computation or the full firewall.
One-valued membership is monotone; arbitrary natural cell values are not. -/
namespace P4blo.TutorialFirewall.Bloom
open P4bloIR P4bloIR.Execution

set_option maxRecDepth 8192

def cellsAfter (cells : Array Nat) (position : Nat) : Array Nat :=
  if position < cells.size then cells.set! position 1 else cells

theorem cell_answer (cells : Array Nat) (position query : Nat) :
    (cellsAfter cells position)[query]? =
      if position = query ∧ position < cells.size then some 1 else cells[query]? := by
  by_cases h : position < cells.size
  · simp [cellsAfter, h, Array.getElem?_setIfInBounds]
  · simp [cellsAfter, h]

theorem size_preserved (cells : Array Nat) (position : Nat) :
    (cellsAfter cells position).size = cells.size := by
  by_cases h : position < cells.size <;> simp [cellsAfter, h]

theorem membership_preserved (cells : Array Nat) (position query : Nat)
    (h : cells[query]? = some 1) : (cellsAfter cells position)[query]? = some 1 := by
  rw [cell_answer]
  split <;> simp_all

theorem selected_cell (cells : Array Nat) (position : Nat) (h : position < cells.size) :
    (cellsAfter cells position)[position]? = some 1 := by simp [cell_answer, h]

def writeResult (run : Run) (name : String) (cells : Array Nat) (position : Nat) : Run :=
  { run with externs := { run.externs with
      instances := run.externs.instances.insert name (.register 1 (cellsAfter cells position)) } }

def result (run : Run) (one two : Array Nat) (p q : Nat) : Run :=
  writeResult (writeResult run "bloom_filter_1" one p) "bloom_filter_2" two q

private theorem get_run (r : Run) : (get : M Run).run r = (.ok r, r) := rfl
private theorem modify_run (f : Run → Run) (r : Run) :
    (modify f : M Unit).run r = (.ok (), f r) := rfl
private theorem instance_one : index.externInstances["bloom_filter_1"]? =
    some ⟨"bloom_filter_1", "register", [.bits 32 4096]⟩ := by cbv
private theorem instance_two : index.externInstances["bloom_filter_2"]? =
    some ⟨"bloom_filter_2", "register", [.bits 32 4096]⟩ := by cbv
private theorem type_register : index.externTypes["register"]? = some registerType := by cbv

private theorem write_call (run : Run) (name localName : String)
    (position : Fin (2 ^ 32)) (cells : Array Nat)
    (hi : run.index = index) (hm : run.externs.model = P4bloArch.model)
    (hn : index.externInstances[name]? = some ⟨name, "register", [.bits 32 4096]⟩)
    (hp : run.frame.read? localName = some (.bits ⟨32, position.val, position.isLt⟩))
    (he : run.externs.instances[name]? = some (.register 1 cells)) :
    (callExtern name "write"
      [.expr (.var localName), .expr (.literal (.bits 1 1))] none).run run =
      (.ok (), writeResult run name cells position.val) := by
  simp [callExtern, ScalarTyping.run_bind, get_run, modify_run, getIndex,
    getFrame, hi, hn, type_register, registerType, copyIn, resolveArg, argumentValue,
    evaluate, readVar, hp, literalValue, Literal.toValue, Bits.wrap,
    Externs.call, hm, P4bloArch.model, P4bloArch.call, ExternState.register, he,
    P4bloIR.liftExcept, writeResult, cellsAfter]
  rw [← hi]
  rfl

theorem first_call (run : Run) (position : Fin (2 ^ 32)) (cells : Array Nat)
    (hi : run.index = index) (hm : run.externs.model = P4bloArch.model)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, position.val, position.isLt⟩))
    (he : run.externs.instances["bloom_filter_1"]? = some (.register 1 cells)) :
    (callExtern "bloom_filter_1" "write"
      [.expr regPosOne.expr, .expr (.literal (.bits 1 1))] none).run run =
      (.ok (), writeResult run "bloom_filter_1" cells position.val) := by
  have path : regPosOne.expr = .var "reg_pos_one" := by cbv
  rw [path]
  exact write_call _ _ _ _ _ hi hm instance_one hp he

theorem second_call (run : Run) (position : Fin (2 ^ 32)) (cells : Array Nat)
    (hi : run.index = index) (hm : run.externs.model = P4bloArch.model)
    (hp : run.frame.read? "reg_pos_two" = some (.bits ⟨32, position.val, position.isLt⟩))
    (he : run.externs.instances["bloom_filter_2"]? = some (.register 1 cells)) :
    (callExtern "bloom_filter_2" "write"
      [.expr regPosTwo.expr, .expr (.literal (.bits 1 1))] none).run run =
      (.ok (), writeResult run "bloom_filter_2" cells position.val) := by
  have path : regPosTwo.expr = .var "reg_pos_two" := by cbv
  rw [path]
  exact write_call _ _ _ _ _ hi hm instance_two hp he

/-- The actual body, including both distinct targets and write order. -/
theorem body_identity : insertBloom = [
    .callExtern "bloom_filter_1" "write" [.expr (.var "reg_pos_one"),
      .expr (.literal (.bits 1 1))] none,
    .callExtern "bloom_filter_2" "write" [.expr (.var "reg_pos_two"),
      .expr (.literal (.bits 1 1))] none] := by cbv

/-- The first actual statement leaves arbitrary subsequent work pending. -/
theorem first_step (run : Run) (p : Fin (2 ^ 32)) (one : Array Nat) (rest : List Work)
    (hi : run.index = index) (hm : run.externs.model = P4bloArch.model)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, p.val, p.isLt⟩))
    (h1 : run.externs.instances["bloom_filter_1"]? = some (.register 1 one)) :
    step { work := .statement insertBloom[0]! :: rest, run } =
      .inr { work := rest, run := writeResult run "bloom_filter_1" one p.val } := by
  have dispatchOne : (dispatch (.statement insertBloom[0]!)).run run =
      (.ok [], writeResult run "bloom_filter_1" one p.val) := by
    change ((fun _ => ([] : List Work)) <$> callExtern "bloom_filter_1" "write"
      [.expr regPosOne.expr, .expr (.literal (.bits 1 1))] none).run run = _
    rw [ScalarTyping.run_map, first_call run p one hi hm hp h1]
  simp only [step, dispatchOne, List.nil_append]
  rfl

/-- Exact pointwise extern observations, including all absent/unrelated keys. -/
theorem result_externs (run : Run) (one two : Array Nat) (p q : Nat) (name : String) :
    (result run one two p q).externs.instances[name]? =
      if name = "bloom_filter_2" then some (.register 1 (cellsAfter two q))
      else if name = "bloom_filter_1" then some (.register 1 (cellsAfter one p))
      else run.externs.instances[name]? := by
  by_cases h2 : name = "bloom_filter_2"
  · subst name; simp [result, writeResult]
  · by_cases h1 : name = "bloom_filter_1"
    · subst name; simp [result, writeResult, Std.HashMap.getElem_insert]
    · simp [result, writeResult, Std.HashMap.getElem?_insert, h1, h2,
        Ne.symm h1, Ne.symm h2]

theorem result_preserves (run : Run) (one two : Array Nat) (p q : Nat) :
    let final := result run one two p q
    final.index = run.index ∧ final.frame = run.frame ∧ final.entries = run.entries ∧
    final.packet = run.packet ∧ final.emitter = run.emitter ∧ final.visits = run.visits := by
  exact ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩

/-- The concrete array-size profile still needs explicit bounds: bit<32>
positions alone are insufficient. Hash computation is not assumed proved. -/
theorem profile_cells (one two : Array Nat) (p q : Fin 4096)
    (h1 : one.size = 4096) (h2 : two.size = 4096) :
    (cellsAfter one p.val)[p.val]? = some 1 ∧
    (cellsAfter two q.val)[q.val]? = some 1 ∧
    (cellsAfter one p.val).size = 4096 ∧ (cellsAfter two q.val).size = 4096 := by
  exact ⟨selected_cell _ _ (by rw [h1]; exact p.isLt),
    selected_cell _ _ (by rw [h2]; exact q.isLt),
    (size_preserved _ _).trans h1, (size_preserved _ _).trans h2⟩

/-- Entire actual two-statement execution. The read premises permit action
shadowing and arbitrary unused frame/shared state, not only fresh frames. -/
theorem insertion (run : Run) (p q : Fin (2 ^ 32)) (one two : Array Nat)
    (hi : run.index = index) (hm : run.externs.model = P4bloArch.model)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, p.val, p.isLt⟩))
    (hq : run.frame.read? "reg_pos_two" = some (.bits ⟨32, q.val, q.isLt⟩))
    (h1 : run.externs.instances["bloom_filter_1"]? = some (.register 1 one))
    (h2 : run.externs.instances["bloom_filter_2"]? = some (.register 1 two)) :
    (execute insertBloom).run run = (.ok (), result run one two p.val q.val) := by
  let middle := writeResult run "bloom_filter_1" one p.val
  have nextRegister : middle.externs.instances["bloom_filter_2"]? =
      some (.register 1 two) := by
    simpa [middle, writeResult, Std.HashMap.getElem?_insert] using h2
  have middleModel : middle.externs.model = P4bloArch.model := hm
  have second := second_call middle q two hi middleModel hq nextRegister
  have dispatchTwo : (dispatch (.statement insertBloom[1]!)).run middle =
      (.ok [], result run one two p.val q.val) := by
    change ((fun _ => ([] : List Work)) <$> callExtern "bloom_filter_2" "write"
      [.expr regPosTwo.expr, .expr (.literal (.bits 1 1))] none).run middle = _
    rw [ScalarTyping.run_map, second]
    rfl
  have stepOne := first_step run p one [.statements [insertBloom[1]!]] hi hm hp h1
  have stepTwo : step { work := [.statement insertBloom[1]!, .statements []], run := middle } =
      .inr { work := [.statements []], run := result run one two p.val q.val } := by
    simp only [step, dispatchTwo, List.nil_append]
    rfl
  have trace : Finishes { work := [.statements insertBloom], run }
      (.ok (), result run one two p.val q.val) := by
    exact .next rfl (.next stepOne (.next rfl (.next stepTwo (.next rfl (.done rfl)))))
  exact trace.sound

def initializedRun (one two : Array Nat) : Run :=
  { index, frame := initialFrame, externs := P4bloArch.externs (
    (({} : Std.HashMap String ExternState).insert "bloom_filter_1" (.register 1 one)).insert
      "bloom_filter_2" (.register 1 two)) }

/-- Constructive nonvacuity from the actual initialized frame. The register
arrays are caller-supplied state, not a claim about startup sizes or validity. -/
theorem initialized_insertion (one two : Array Nat) :
    (execute insertBloom).run (initializedRun one two) =
      (.ok (), result (initializedRun one two) one two 0 0) := by
  apply insertion _ ⟨0, by decide⟩ ⟨0, by decide⟩ _ _ rfl rfl
  · simpa [initializedRun, Frame.read?, frame_no_action.2] using frame_locals_zero.1
  · simpa [initializedRun, Frame.read?, frame_no_action.2] using frame_locals_zero.2.1
  · simp [initializedRun, P4bloArch.externs, Std.HashMap.getElem_insert]
  · simp [initializedRun, P4bloArch.externs]

end P4blo.TutorialFirewall.Bloom
