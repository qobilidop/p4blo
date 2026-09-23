import Tests.Check
import P4bloIR.PlainCallReturn

namespace PlainCallReturnTests
open P4bloIR P4bloIR.PlainCallEntry

private def caller : Frame :=
  { scope := { block := { (default : Block) with name := "Caller" } }
    vars := ({} : Std.HashMap String Value).insert "source_hdr" (.bool false)
      |>.insert "source_meta" (.bits (Bits.wrap 8 5)) |>.insert "hdr" (.error "NoError")
      |>.insert "untouched" (.bits (Bits.wrap 9 303)) }
private def callee : Frame :=
  { scope := { block := { (default : Block) with name := "Callee" } }
    vars := ({} : Std.HashMap String Value).insert "hdr" (.bool true)
      |>.insert "meta" (.bits (Bits.wrap 8 29)) |>.insert "observer" (.error "Sentinel")
      |>.insert "scratch" (.bits (Bits.wrap 8 91)) }
private def run : Run := { index := default, frame := callee }

theorem missing_destination : ¬ ∃ old, caller.read? "source_route" = some old := by
  simp [caller, Frame.read?]

theorem action_frame_excluded : ¬ ScalarStatements.BlockFrame { caller with action := some "active" } := by
  simp [ScalarStatements.BlockFrame]

def tests : T Unit := do
  let result := (Execution.dispatch (.blockReturn caller params args)).run run
  check "normal return succeeds without any route binding" result.1.toOption.isSome
  check "return restores caller scope" (result.2.frame.scope.block.name == "Caller")
  check "return copies all three roots" (result.2.frame.read? "source_hdr" == some (.bool true) &&
    result.2.frame.read? "source_meta" == some (.bits (Bits.wrap 8 29)) &&
    result.2.frame.read? "hdr" == some (.error "Sentinel"))
  check "return preserves absence and unrelated caller" (result.2.frame.read? "source_route" == none &&
    result.2.frame.read? "scratch" == none && result.2.frame.read? "untouched" == some (.bits (Bits.wrap 9 303)))
  let missing := { caller with vars := caller.vars.erase "source_meta" }
  let noTarget := (Execution.dispatch (.blockReturn missing params args)).run run
  check "return requires existing caller destinations" (noTarget.1 matches .error (.interp "unknown variable 'source_meta' in block 'Caller'"))
  let noRead := (Execution.dispatch (.blockReturn caller params args)).run
    { run with frame := { callee with vars := callee.vars.erase "meta" } }
  check "return requires callee reads" (noRead.1 matches .error (.interp "unknown variable 'meta'"))

end PlainCallReturnTests
