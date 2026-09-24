import P4blo.TutorialFirewallProof

/-! Unregistered feasibility only: the actual first extern call and elementary
cell observations. This is not yet the two-statement execution theorem. -/

namespace FirewallBloomProbe
open P4bloIR P4bloIR.Execution
open P4blo.TutorialFirewall

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

private theorem get_run (r : Run) : (get : M Run).run r = (.ok r, r) := rfl
private theorem modify_run (f : Run → Run) (r : Run) :
    (modify f : M Unit).run r = (.ok (), f r) := rfl

private theorem instance_one : index.externInstances["bloom_filter_1"]? =
    some ⟨"bloom_filter_1", "register", [.bits 32 4096]⟩ := by cbv
private theorem type_register : index.externTypes["register"]? = some registerType := by cbv

def afterOne (run : Run) (cells : Array Nat) (position : Nat) : Run :=
  { run with externs := ⟨run.externs.instances.insert "bloom_filter_1"
    (.register 1 (cellsAfter cells position))⟩ }

theorem first_call (run : Run) (position : Fin (2 ^ 32)) (cells : Array Nat)
    (hi : run.index = index)
    (hp : run.frame.read? "reg_pos_one" = some (.bits ⟨32, position.val, position.isLt⟩))
    (he : run.externs.instances["bloom_filter_1"]? = some (.register 1 cells)) :
    (callExtern "bloom_filter_1" "write"
      [.expr regPosOne.expr, .expr (.literal (.bits 1 1))] none).run run =
      (.ok (), afterOne run cells position.val) := by
  have path : regPosOne.expr = .var "reg_pos_one" := by cbv
  have din : (Direction.in == Direction.out) = false := by decide
  have dinout : (Direction.in == Direction.inout) = false := by decide
  simp [callExtern, ScalarTyping.run_bind,
    get_run, modify_run, getIndex, getFrame, hi, instance_one, type_register,
    registerType, argumentValue, path, din, dinout,
    evaluate, readVar, hp, literalValue, Literal.toValue, Bits.wrap,
    Externs.call, ExternState.call, he, P4bloIR.liftExcept, afterOne, cellsAfter]
  rw [← hi]
  rfl

#print axioms first_call
#print axioms cell_answer
#print axioms size_preserved
#print axioms membership_preserved

end FirewallBloomProbe
