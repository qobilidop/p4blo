import P4bloIR.FieldTyping
import Std.Data.HashMap.Lemmas

namespace FieldTypingTests

open P4bloIR FieldTyping

private def emptyIndex : Index := { program := default }
private def emptyScope : BlockScope := { block := default, vars := {} }

-- These are kernel-checked impossibility results for the specification
-- relation, independent of the typed source constructors.
example (ty : Ty) : ¬Path emptyIndex emptyScope (.var "missing") ty := by
  intro h
  cases h with
  | var name decl _ found _ => simp [emptyScope, BlockScope.var?] at found

example (index : Index) (scope : BlockScope) (ty : Ty) :
    ¬Path index scope (.var "") ty := by
  intro h
  cases h with
  | var _ _ nonempty _ _ => exact nonempty rfl

example (fields : List Field) : ¬FieldsOf emptyIndex (.header "missing") fields := by
  intro h
  cases h with
  | header declaration => simp [FieldLaws.Declared, emptyIndex] at declaration

example (fields : List Field) : ¬FieldsOf emptyIndex (.bits 8) fields := by
  intro h
  cases h

example (index : Index) (scope : BlockScope) :
    ¬Typed index scope (.literal (.bits 0 0)) (.bits 0) := by
  intro h
  cases h with
  | bits _ _ positive _ => omega
  | read path _ => cases path

example (index : Index) (scope : BlockScope) :
    ¬Typed index scope (.literal (.bits 8 256)) (.bits 8) := by
  intro h
  cases h with
  | bits _ _ _ fits => omega
  | read path _ => cases path

end FieldTypingTests
