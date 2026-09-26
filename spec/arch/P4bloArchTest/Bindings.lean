import P4bloArchTest.Check

namespace BindingTests
open P4bloIR P4bloArch

private def library : BlockLibrary :=
  { (default : BlockLibrary) with
    errors := Validity.coreErrors
    blocks := [parser "P", parser "P2", plain "C" .control, plain "C2" .control,
      plain "D" .deparser, plain "D2" .deparser] }
where
  parser (name : String) : Block :=
    { (default : Block) with
      name, kind := .parser, startState := "start",
      states := [⟨"start", [], .direct .accept⟩] }
  plain (name : String) (kind : BlockKind) : Block :=
    { (default : Block) with name, kind }

private def bindings : BlockBindings :=
  { headers := "H", metadata := "M", exports := [⟨"control", "C"⟩] }

def tests : T Unit := do
  check "a library has multiple blocks of each kind without roots or exports"
    (Validity.check library matches .ok _)
  let scalar := { library with
    blocks :=
    [{ (default : Block) with
       name := "C", kind := .control,
       params := [⟨"x", .bits 8, .inout⟩] }],
    structTypes := [⟨"H", []⟩, ⟨"M", []⟩] }
  check "core validity accepts a scalar control signature"
    (Validity.check scalar matches .ok _)
  check "architecture bindings reject a scalar entry signature"
    ((do
      let idx ← Validity.check scalar
      Bindings.check bindings idx
      pure ()) matches .error { code := .exportSignature, path := _, message := _ })
  check "v1model rejects scalar bindings before execution"
    ((do
      let idx ← Index.build scalar
      let _ ← V1Model.load idx bindings 4
      pure ()) matches .error _)
  let conventional := { scalar with blocks :=
    [{ (default : Block) with
       name := "C", kind := .control,
       params := [⟨"h", .struct "H", .inout⟩, ⟨"m", .struct "M", .inout⟩] }] }
  match Index.build conventional with
  | .error _ => check "binding fixture indexes" false
  | .ok idx =>
    check "correct bindings validate" (Bindings.check bindings idx matches .ok _)
    check "missing roots fail" (Bindings.check { bindings with headers := "Missing" } idx
      matches .error { code := .refUnresolved, path := _, message := _ })
    check "duplicate roles fail" (Bindings.check { bindings with exports := bindings.exports ++ bindings.exports } idx
      matches .error { code := .exportDuplicate, path := _, message := _ })
    check "unresolved exports fail" (Bindings.check { bindings with exports := [⟨"control", "Missing"⟩] } idx
      matches .error { code := .refUnresolved, path := _, message := _ })
    check "v1model rejects a valid signature bound to the wrong role kind"
      (V1Model.load idx { bindings with exports := [⟨"parser", "C"⟩] } 4 matches .error _)

end BindingTests
