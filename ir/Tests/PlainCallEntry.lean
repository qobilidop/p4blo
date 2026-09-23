import Tests.Check
import P4bloIR.PlainCallEntry

namespace PlainCallEntryTests
open P4bloIR

private def run : Run :=
  { index := default
    frame := {
      scope := { block := default }
      vars := ({} : Std.HashMap String Value).insert "nonzero" (.bits (Bits.wrap 8 211)) } }

theorem out_bad_argument :
    (argumentValue ⟨"out", .bits 8, .out⟩ (.expr (.var "missing"))).run run =
      (.ok (.bits (Bits.wrap 8 0)), run) :=
  PlainCallEntry.argument_out run "out" (.bits 8) _ _ rfl

def tests : T Unit := do
  let out := (argumentValue ⟨"out", .bits 8, .out⟩ (.expr (.var "missing"))).run run
  check "out argument ignores unreadable expression" (out.1.toOption == some (.bits (Bits.wrap 8 0)))
  let nonzero := (argumentValue ⟨"out", .bits 8, .out⟩ (.lvalue (.var "nonzero"))).run run
  check "out argument ignores nonzero caller" (nonzero.1.toOption == some (.bits (Bits.wrap 8 0)))
  check "out does not overwrite caller" (nonzero.2.frame.read? "nonzero" == some (.bits (Bits.wrap 8 211)))
  let input := (argumentValue ⟨"in", .bits 8, .in⟩ (.expr (.var "missing"))).run run
  check "in argument evaluates unreadable expression" input.1.toOption.isNone
  let actionData := (argumentValue ⟨"data", .bits 8, .none⟩ (.expr (.var "nonzero"))).run run
  check "direction none still reads caller" (actionData.1.toOption == some (.bits (Bits.wrap 8 211)))
  let unknown := (Execution.dispatch (.block "missing" [])).run run
  check "missing block fails before initialization" (unknown.1 matches .error (.interp "unknown block 'missing'"))
  let block : Block := { (default : Block) with name := "four", params := PlainCallEntry.params }
  let r := { run with index := { run.index with blocks := run.index.blocks.insert "four" block } }
  let arity := (Execution.dispatch (.block "four" [])).run r
  check "wrong arity fails before missing scope" (arity.1 matches .error (.interp "block 'four' takes 4 arguments"))

end PlainCallEntryTests
