import P4blo.TutorialFirewallBloom

/-! Actual two-read boundary, independent of the later firewall decision. -/
namespace P4blo.TutorialFirewall.Readback
open P4bloIR P4bloIR.Execution

set_option maxRecDepth 8192

/-- Explicit action-first storage update, with existence proved separately. -/
def setRoot (frame : Frame) (name : String) (value : Value) : Frame :=
  match frame.actionVars with
  | some active => if active.contains name then
      { frame with actionVars := some (active.insert name value) }
    else { frame with vars := frame.vars.insert name value }
  | none => { frame with vars := frame.vars.insert name value }

theorem root_write (run : Run) (name : String) (old value : Value)
    (found : run.frame.read? name = some old) :
    (writeVar name value).run run =
      (.ok (), { run with frame := setRoot run.frame name value }) := by
  cases active : run.frame.actionVars with
  | none =>
    have absent : run.frame.actionVars.bind (·[name]?) = none := by simp [active]
    have block : run.frame.vars[name]? = some old := by simpa [Frame.read?, active] using found
    simpa [setRoot, active] using ScalarStatements.writeVar_block_unshadowed run absent block
  | some values =>
    cases lookup : values[name]? with
    | none =>
      have absent : run.frame.actionVars.bind (·[name]?) = none := by simp [active, lookup]
      have block : run.frame.vars[name]? = some old := by
        simpa [Frame.read?, active, lookup] using found
      have missing : name ∉ values := by simp [Std.HashMap.mem_iff_isSome_getElem?, lookup]
      simpa [setRoot, active, missing] using
        ScalarStatements.writeVar_block_unshadowed run absent block
    | some previous =>
      have present : name ∈ values := by
        simp [Std.HashMap.mem_iff_isSome_getElem?, lookup]
      simpa [setRoot, active, present] using ScalarStatements.writeVar_action run active lookup

def cellValue (cells : Array Nat) (position : Nat) : Value :=
  .bits (Bits.wrap 1 (cells[position]?.getD 0))

theorem cell_answer (cells : Array Nat) (position : Nat) :
    cellValue cells position =
      .bits ⟨1, (cells[position]?.getD 0) % 2, Nat.mod_lt _ (by decide)⟩ := rfl

theorem root_read_other (frame : Frame) (name query : String) (value : Value)
    (different : name ≠ query) :
    (setRoot frame name value).read? query = frame.read? query := by
  cases active : frame.actionVars with
  | none => simp [setRoot, Frame.read?, active, Std.HashMap.getElem?_insert, different]
  | some values =>
    by_cases present : name ∈ values <;>
      simp [setRoot, Frame.read?, active, present, Std.HashMap.getElem?_insert, different]

def resultOne (run : Run) (instanceName localName : String) (cells : Array Nat)
    (position : Nat) : Run :=
  { run with
    externs := ⟨run.externs.instances.insert instanceName (.register 1 cells)⟩
    frame := setRoot run.frame localName (cellValue cells position) }

private theorem get_run (r : Run) : (get : M Run).run r = (.ok r, r) := rfl
private theorem modify_run (f : Run → Run) (r : Run) :
    (modify f : M Unit).run r = (.ok (), f r) := rfl
private theorem type_register : index.externTypes["register"]? = some registerType := by cbv

theorem read_call (run : Run) (instanceName positionName resultName : String)
    (position : Fin (2 ^ 32)) (cells : Array Nat) (old : Value)
    (hi : run.index = index)
    (hn : index.externInstances[instanceName]? =
      some ⟨instanceName, "register", [.bits 32 4096]⟩)
    (hp : run.frame.read? positionName = some (.bits ⟨32, position.val, position.isLt⟩))
    (hd : run.frame.read? resultName = some old)
    (he : run.externs.instances[instanceName]? = some (.register 1 cells)) :
    (callExtern instanceName "read"
      [.lvalue (.var resultName), .expr (.var positionName)] none).run run =
      (.ok (), resultOne run instanceName resultName cells position.val) := by
  have readCell : (if h : position.val < cells.size then cells[position.val] else 0) =
      cells[position.val]?.getD 0 := by
    by_cases h : position.val < cells.size <;> simp [h]
  have out_ne_inout : (Direction.out == Direction.inout) = false := by decide
  have out_eq_out : (Direction.out == Direction.out) = true := by decide
  have in_ne_out : (Direction.in == Direction.out) = false := by decide
  have in_ne_inout : (Direction.in == Direction.inout) = false := by decide
  have zeroBits (idx : Index) : Value.zero (.bits 1) idx = .ok (.bits (Bits.wrap 1 0)) := rfl
  have callResult : run.externs.call instanceName "read"
      [.bits (Bits.wrap 1 0), .bits ⟨32, position.val, position.isLt⟩] =
      .ok (⟨run.externs.instances.insert instanceName (.register 1 cells)⟩,
        { outs := [cellValue cells position.val] }) := by
    simp [Externs.call, he, ExternState.call, readCell, cellValue]
    rfl
  simp [callExtern, ScalarTyping.run_bind, get_run, modify_run, getIndex,
    getFrame, hi, hn, type_register, registerType, argumentValue, out_ne_inout, out_eq_out,
    in_ne_out, in_ne_inout, zeroBits, evaluate, readVar, hp,
    callResult, P4bloIR.liftExcept, writeLValue]
  rw [← hi]
  exact root_write
    { run with externs := ⟨run.externs.instances.insert instanceName (.register 1 cells)⟩ }
    resultName old (cellValue cells position.val) hd

private theorem instance_one : index.externInstances["bloom_filter_1"]? =
    some ⟨"bloom_filter_1", "register", [.bits 32 4096]⟩ := by cbv
private theorem instance_two : index.externInstances["bloom_filter_2"]? =
    some ⟨"bloom_filter_2", "register", [.bits 32 4096]⟩ := by cbv

theorem first_call (run : Run) (p : Fin (2 ^ 32)) (one : Array Nat) (old : Value)
    (hi : run.index = index)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, p.val, p.isLt⟩))
    (hd : run.frame.read? "reg_val_one" = some old)
    (he : run.externs.instances["bloom_filter_1"]? = some (.register 1 one)) :
    (callExtern "bloom_filter_1" "read"
      [.lvalue regValOne.lvalue, .expr regPosOne.expr] none).run run =
      (.ok (), resultOne run "bloom_filter_1" "reg_val_one" one p.val) := by
  have resultPath : regValOne.lvalue = .var "reg_val_one" := by cbv
  have positionPath : regPosOne.expr = .var "reg_pos_one" := by cbv
  rw [resultPath, positionPath]
  exact read_call _ _ _ _ _ _ _ hi instance_one hp hd he

theorem second_call (run : Run) (q : Fin (2 ^ 32)) (two : Array Nat) (old : Value)
    (hi : run.index = index)
    (hp : run.frame.read? "reg_pos_two" = some (.bits ⟨32, q.val, q.isLt⟩))
    (hd : run.frame.read? "reg_val_two" = some old)
    (he : run.externs.instances["bloom_filter_2"]? = some (.register 1 two)) :
    (callExtern "bloom_filter_2" "read"
      [.lvalue regValTwo.lvalue, .expr regPosTwo.expr] none).run run =
      (.ok (), resultOne run "bloom_filter_2" "reg_val_two" two q.val) := by
  have resultPath : regValTwo.lvalue = .var "reg_val_two" := by cbv
  have positionPath : regPosTwo.expr = .var "reg_pos_two" := by cbv
  rw [resultPath, positionPath]
  exact read_call _ _ _ _ _ _ _ hi instance_two hp hd he

theorem body_identity : checkBloom = [
    .callExtern "bloom_filter_1" "read"
      [.lvalue (.var "reg_val_one"), .expr (.var "reg_pos_one")] none,
    .callExtern "bloom_filter_2" "read"
      [.lvalue (.var "reg_val_two"), .expr (.var "reg_pos_two")] none,
    .conditional (.binary .or
      (.binary .ne (.var "reg_val_one") (.literal (.bits 1 1)))
      (.binary .ne (.var "reg_val_two") (.literal (.bits 1 1))))
      [.callAction "drop" []] []] := by cbv

def result (run : Run) (one two : Array Nat) (p q : Nat) : Run :=
  resultOne (resultOne run "bloom_filter_1" "reg_val_one" one p)
    "bloom_filter_2" "reg_val_two" two q

theorem first_step (run : Run) (p : Fin (2 ^ 32)) (one : Array Nat)
    (old : Value) (rest : List Work) (hi : run.index = index)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, p.val, p.isLt⟩))
    (hd : run.frame.read? "reg_val_one" = some old)
    (he : run.externs.instances["bloom_filter_1"]? = some (.register 1 one)) :
    step { work := .statement checkBloom[0]! :: rest, run } =
      .inr { work := rest, run := resultOne run "bloom_filter_1" "reg_val_one" one p.val } := by
  have call : (dispatch (.statement checkBloom[0]!)).run run =
      (.ok [], resultOne run "bloom_filter_1" "reg_val_one" one p.val) := by
    change ((fun _ => ([] : List Work)) <$> callExtern "bloom_filter_1" "read"
      [.lvalue regValOne.lvalue, .expr regPosOne.expr] none).run run = _
    rw [ScalarTyping.run_map, first_call run p one old hi hp hd he]
  simp only [step, call, List.nil_append]
  rfl

theorem source_steps (run : Run) (one two : Array Nat) (p q : Fin (2 ^ 32))
    (oldOne oldTwo : Value) (rest : List Work)
    (hi : run.index = index)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, p.val, p.isLt⟩))
    (hq : run.frame.read? "reg_pos_two" = some (.bits ⟨32, q.val, q.isLt⟩))
    (hd1 : run.frame.read? "reg_val_one" = some oldOne)
    (hd2 : run.frame.read? "reg_val_two" = some oldTwo)
    (he1 : run.externs.instances["bloom_filter_1"]? = some (.register 1 one))
    (he2 : run.externs.instances["bloom_filter_2"]? = some (.register 1 two)) :
    Steps { work := .statements checkBloom :: rest, run }
      { work := .statements [checkBloom[2]!] :: rest, run := result run one two p.val q.val } := by
  let middle := resultOne run "bloom_filter_1" "reg_val_one" one p.val
  have nextPosition : middle.frame.read? "reg_pos_two" = some (.bits ⟨32, q.val, q.isLt⟩) := by
    simpa only [middle, resultOne,
      root_read_other _ "reg_val_one" "reg_pos_two" _ (by decide)] using hq
  have nextDestination : middle.frame.read? "reg_val_two" = some oldTwo := by
    simpa only [middle, resultOne,
      root_read_other _ "reg_val_one" "reg_val_two" _ (by decide)] using hd2
  have nextExtern : middle.externs.instances["bloom_filter_2"]? = some (.register 1 two) := by
    simpa [middle, resultOne, Std.HashMap.getElem?_insert] using he2
  have second := second_call middle q two oldTwo hi nextPosition nextDestination nextExtern
  have dispatchTwo : (dispatch (.statement checkBloom[1]!)).run middle =
      (.ok [], result run one two p.val q.val) := by
    change ((fun _ => ([] : List Work)) <$> callExtern "bloom_filter_2" "read"
      [.lvalue regValTwo.lvalue, .expr regPosTwo.expr] none).run middle = _
    rw [ScalarTyping.run_map, second]
    rfl
  have stepTwo : step
      { work := .statement checkBloom[1]! :: .statements [checkBloom[2]!] :: rest, run := middle } =
      .inr {
        work := .statements [checkBloom[2]!] :: rest
        run := result run one two p.val q.val } := by
    simp only [step, dispatchTwo, List.nil_append]
    rfl
  exact .next rfl (.next (first_step run p one oldOne _ hi hp hd1 he1)
    (.next rfl (.next stepTwo .refl)))

theorem root_stores_other (frame : Frame) (name query : String) (value : Value)
    (different : name ≠ query) :
    (setRoot frame name value).vars[query]? = frame.vars[query]? ∧
    (setRoot frame name value).actionVars.bind (·[query]?) =
      frame.actionVars.bind (·[query]?) := by
  cases active : frame.actionVars with
  | none => simp [setRoot, active, Std.HashMap.getElem?_insert, different]
  | some values =>
    by_cases present : name ∈ values <;>
      simp [setRoot, active, present, Std.HashMap.getElem?_insert, different]

theorem root_layer_preserved (frame : Frame) (name : String) (value : Value) :
    (setRoot frame name value).scope = frame.scope ∧
    (setRoot frame name value).action = frame.action ∧
    (setRoot frame name value).actionVars.isSome = frame.actionVars.isSome := by
  cases active : frame.actionVars with
  | none => simp [setRoot, active]
  | some values => by_cases present : name ∈ values <;> simp [setRoot, active, present]

theorem root_block_decoy (frame : Frame) (name : String) (old value : Value)
    (found : frame.actionVars.bind (·[name]?) = some old) :
    (setRoot frame name value).vars = frame.vars := by
  cases active : frame.actionVars with
  | none => simp [active] at found
  | some values =>
    have member : name ∈ values := by
      simp only [active, Option.bind_some] at found
      simp [Std.HashMap.mem_iff_isSome_getElem?, found]
    simp [setRoot, active, member]

theorem root_unshadowed_layer (frame : Frame) (name : String) (value : Value)
    (absent : frame.actionVars.bind (·[name]?) = none) :
    (setRoot frame name value).actionVars = frame.actionVars := by
  cases active : frame.actionVars with
  | none => simp [setRoot, active]
  | some values =>
    have missing : name ∉ values := by
      simp only [active, Option.bind_some] at absent
      simp [Std.HashMap.mem_iff_isSome_getElem?, absent]
    simp [setRoot, active, missing]

private theorem one_externs (run : Run) (inst localName : String) (cells : Array Nat)
    (position : Nat) (found : run.externs.instances[inst]? = some (.register 1 cells))
    (query : String) :
    (resultOne run inst localName cells position).externs.instances[query]? =
      run.externs.instances[query]? := by
  by_cases same : inst = query
  · subst query; simp [resultOne, found]
  · simp [resultOne, Std.HashMap.getElem?_insert, same]

theorem result_externs (run : Run) (one two : Array Nat) (p q : Nat)
    (h1 : run.externs.instances["bloom_filter_1"]? = some (.register 1 one))
    (h2 : run.externs.instances["bloom_filter_2"]? = some (.register 1 two))
    (query : String) :
    (result run one two p q).externs.instances[query]? = run.externs.instances[query]? := by
  have middle := one_externs run "bloom_filter_1" "reg_val_one" one p h1
  have next : (resultOne run "bloom_filter_1" "reg_val_one" one p).externs.instances[
      "bloom_filter_2"]? = some (.register 1 two) := by rw [middle]; exact h2
  exact (one_externs _ "bloom_filter_2" "reg_val_two" two q next query).trans (middle query)

theorem result_preserves (run : Run) (one two : Array Nat) (p q : Nat) :
    let final := result run one two p q
    final.index = run.index ∧ final.entries = run.entries ∧
    final.packet = run.packet ∧ final.emitter = run.emitter ∧ final.visits = run.visits ∧
    final.frame.scope = run.frame.scope ∧ final.frame.action = run.frame.action ∧
    final.frame.actionVars.isSome = run.frame.actionVars.isSome := by
  have first := root_layer_preserved run.frame "reg_val_one" (cellValue one p)
  have second := root_layer_preserved
    (setRoot run.frame "reg_val_one" (cellValue one p)) "reg_val_two" (cellValue two q)
  exact ⟨rfl, rfl, rfl, rfl, rfl, second.1.trans first.1,
    second.2.1.trans first.2.1, second.2.2.trans first.2.2⟩

theorem result_stores_other (run : Run) (one two : Array Nat) (p q : Nat) (query : String)
    (h1 : "reg_val_one" ≠ query) (h2 : "reg_val_two" ≠ query) :
    (result run one two p q).frame.vars[query]? = run.frame.vars[query]? ∧
    (result run one two p q).frame.actionVars.bind (·[query]?) =
      run.frame.actionVars.bind (·[query]?) := by
  have first := root_stores_other run.frame "reg_val_one" query (cellValue one p) h1
  have second := root_stores_other (setRoot run.frame "reg_val_one" (cellValue one p))
    "reg_val_two" query (cellValue two q) h2
  exact ⟨second.1.trans first.1, second.2.trans first.2⟩

theorem initialized_prefix (one two : Array Nat) (rest : List Work) :
    Steps { work := .statements checkBloom :: rest, run := Bloom.initializedRun one two }
      { work := .statements [checkBloom[2]!] :: rest,
        run := result (Bloom.initializedRun one two) one two 0 0 } := by
  apply source_steps _ one two ⟨0, by decide⟩ ⟨0, by decide⟩
    (.bits ⟨1, 0, by decide⟩) (.bits ⟨1, 0, by decide⟩) rest rfl
  · simpa [Bloom.initializedRun, Frame.read?, frame_no_action.2] using frame_locals_zero.1
  · simpa [Bloom.initializedRun, Frame.read?, frame_no_action.2] using frame_locals_zero.2.1
  · simpa [Bloom.initializedRun, Frame.read?, frame_no_action.2] using frame_locals_zero.2.2.1
  · simpa [Bloom.initializedRun, Frame.read?, frame_no_action.2] using frame_locals_zero.2.2.2.1
  · simp [Bloom.initializedRun, Std.HashMap.getElem_insert]
  · simp [Bloom.initializedRun]

end P4blo.TutorialFirewall.Readback
