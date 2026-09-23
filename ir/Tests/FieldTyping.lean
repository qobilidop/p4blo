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

private def parameterScope (direction : Direction) : BlockScope :=
  { block := default, vars := ({} : Std.HashMap String VarDecl).insert
      "hdr" (.param ⟨"hdr", .header "Header", direction⟩) }

private def headerIndex : Index :=
  { program := default, headerTypes := ({} : Std.HashMap String HeaderType).insert
      "Header" ⟨"Header", [⟨"byte", .bits 8⟩]⟩ }

private theorem headerFields : FieldsOf headerIndex (.header "Header") [⟨"byte", .bits 8⟩] := by
  apply FieldsOf.header
  simp [FieldLaws.Declared, FieldLaws.NamesWellFormed, headerIndex]

private theorem readonlyRoot (direction : Direction)
    (readonly : direction = .«in» ∨ direction = .none) (ty : Ty) :
    ¬WritablePath headerIndex (parameterScope direction) (.var "hdr") ty := by
  intro h
  cases h with
  | var _ decl _ found _ permission =>
    have hd : decl = .param ⟨"hdr", .header "Header", direction⟩ := by
      simpa [parameterScope, BlockScope.var?] using found.symm
    subst decl
    rcases readonly with rfl | rfl <;> contradiction

-- A mutable header's nested field remains read-only through either kind
-- of non-writable parameter. These tests inspect the specification relation,
-- not failure of a user constructor to elaborate.
example (ty : Ty) (fieldName : String) :
    ¬WritablePath headerIndex (parameterScope .«in») (.member (.var "hdr") fieldName) ty := by
  intro h
  cases h with
  | member _ root _ _ => exact readonlyRoot .«in» (Or.inl rfl) _ root

example (ty : Ty) (fieldName : String) :
    ¬WritablePath headerIndex (parameterScope .none) (.member (.var "hdr") fieldName) ty := by
  intro h
  cases h with
  | member _ root _ _ => exact readonlyRoot .none (Or.inr rfl) _ root

example (ty : Ty) : ¬WritablePath headerIndex emptyScope (.var "missing") ty := by
  intro h
  cases h with
  | var _ _ _ found _ _ => simp [emptyScope, BlockScope.var?] at found

example (index : Index) (scope : BlockScope) (ty : Ty) :
    ¬WritablePath index scope (.var "") ty := by
  intro h
  cases h with
  | var _ _ nonempty _ _ _ => exact nonempty rfl

private theorem writableHeader (direction : Direction)
    (allowed : direction = .out ∨ direction = .inout) :
    WritablePath headerIndex (parameterScope direction) (.member (.var "hdr") "byte") (.bits 8) := by
  apply WritablePath.member ⟨"byte", .bits 8⟩ _ headerFields (by simp)
  apply WritablePath.var "hdr" (.param ⟨"hdr", .header "Header", direction⟩) (by decide)
    (by simp [parameterScope, BlockScope.var?]) rfl
  rcases allowed with rfl | rfl <;> rfl

example : StatementTyped headerIndex (parameterScope .out)
    (.assign (.member (.var "hdr") "byte") (.literal (.bits 8 255))) :=
  .assign (t := .bits 8) (writableHeader .out (Or.inl rfl)) (.bits 8 255 (by decide) (by decide))

example : StatementTyped headerIndex (parameterScope .inout)
    (.assign (.member (.var "hdr") "byte") (.literal (.bits 8 0))) :=
  .assign (t := .bits 8) (writableHeader .inout (Or.inr rfl)) (.bits 8 0 (by decide) (by decide))

private def localScope : BlockScope :=
  { block := default, vars := ({} : Std.HashMap String VarDecl).insert
      "hdr" (.var ⟨"hdr", .header "Header"⟩) }

example : WritablePath headerIndex localScope
    (.member (.var "hdr") "byte") (.bits 8) := by
  apply WritablePath.member ⟨"byte", .bits 8⟩ _ headerFields (by simp)
  exact .var "hdr" (.var ⟨"hdr", .header "Header"⟩) (by decide)
    (by simp [localScope, BlockScope.var?]) rfl rfl

-- A declaration with the correct nominal name but the wrong kind cannot
-- provide the member path, and an eight-bit field cannot receive nine bits.
example (fields : List Field) : ¬FieldsOf headerIndex (.struct "Header") fields := by
  intro h
  cases h with
  | struct declared => simp [FieldLaws.Declared, headerIndex] at declared

private theorem member_width (fieldName : String) (ty : Ty)
    (target : WritablePath headerIndex (parameterScope .out) (.member (.var "hdr") fieldName) ty) :
    ty = .bits 8 := by
  cases target with
  | member field root fields member =>
    cases root with
    | var _ decl _ found _ _ =>
      have hd : decl = .param ⟨"hdr", .header "Header", .out⟩ := by
        simpa [parameterScope, BlockScope.var?] using found.symm
      subst decl
      cases fields with
      | header declared =>
        have hs := declared.fields_eq
        simp [headerIndex, Index.fields?] at hs
        subst_vars
        exact congrArg Field.type (List.mem_singleton.mp member)

example (fieldName : String) : ¬StatementTyped headerIndex (parameterScope .out)
    (.assign (.member (.var "hdr") fieldName) (.literal (.bits 9 255))) := by
  intro h
  cases h with
  | assign target value =>
    cases value with
    | read path _ => cases path
    | bits _ _ _ _ => have impossible := member_width _ _ target; contradiction

end FieldTypingTests
