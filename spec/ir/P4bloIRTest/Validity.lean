import P4bloIRTest.Check

/-!
Tests for `P4bloIR.Validity.check` on the forwarder fixture: it is
accepted, and each single break is rejected with the Python validator's
code. `tests/lean/test_lean_agrees_validity.py` compares the checker with the
Python validator on every corpus program and every validator test.
-/

namespace ValidityTests

open P4bloIR P4bloIR.Validity

/-- `check` that `p` is rejected with `code`. -/
def rejects (name : String) (p : Program) (code : Code) : T Unit :=
  match Validity.check p with
  | .ok _ => check s!"{name} (unexpectedly accepted)" false
  | .error d =>
    if d.code == code then check name true
    else do
      IO.println s!"     got: {d}"
      check name false

/-- Apply `f` to the block named `name`. -/
def onBlock (p : Program) (name : String) (f : Block → Block) : Program :=
  { p with blocks := p.blocks.map fun b => if b.name == name then f b else b }

def tests (p : Program) : T Unit := do
  check "forwarder is valid" (Validity.check p matches .ok _)
  rejects "core errors out of order" { p with errors := p.errors.reverse } .errorList
  let control := (p.blocks.find? (·.kind == .control)).get!
  let parser := (p.blocks.find? (·.kind == .parser)).get!
  let deparser := (p.blocks.find? (·.kind == .deparser)).get!
  rejects "extract in a control"
    (onBlock p control.name fun b => { b with body := b.body ++ [.extract (.var "x")] })
    .blockKindStmt
  rejects "a deparser calls a parser"
    (onBlock p deparser.name fun b => { b with body := b.body ++ [.callBlock parser.name []] })
    .callKind
  rejects "a control calls itself"
    (onBlock p control.name fun b => { b with body := b.body ++ [.callBlock control.name
      (b.params.map fun q => .lvalue (.var q.name))] })
    .callCycle
  rejects "a slice past the width"
    (onBlock p control.name fun b => { b with body := b.body ++
      [.conditional (.binary .eq (.slice (.literal (.bits 8 0)) 8 0) (.literal (.bits 9 0))) [] []] })
    .sliceRange
  rejects "a start state that does not exist"
    (onBlock p parser.name fun b => { b with startState := "nowhere" }) .parserStartState

end ValidityTests
