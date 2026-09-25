import P4bloIRTest.Check
import P4bloIR.FieldLaws
import Std.Data.HashMap.Lemmas

open P4bloIR P4bloIR.FieldLaws

namespace FieldLawTests

private def fields : List Field :=
  [⟨"left", .bits 8⟩, ⟨"right", .bits 9⟩, ⟨"flag", .boolean⟩]

private def values : List Value := [.bits (Bits.wrap 8 171), .bits (Bits.wrap 9 257), .bool true]

private def index : Index :=
  { program := default,
    headerTypes := ({} : Std.HashMap String HeaderType).insert "H" ⟨"H", fields⟩,
    structTypes := ({} : Std.HashMap String StructType).insert "M" ⟨"M", fields⟩ }

private def run : Run := { index, frame := default }

-- Concrete declarations establish that the public premises are inhabited.
private theorem header_declared : Declared index .header "H" fields := by
  simp [Declared, index, NamesWellFormed, fields]
example : Declared index .struct "M" fields := by
  simp [Declared, index, NamesWellFormed, fields]

example : (setField (.header "H" false values) "right" (.bits (Bits.wrap 9 7))).run run =
    (.ok (.header "H" false [.bits (Bits.wrap 8 171), .bits (Bits.wrap 9 7), .bool true]), run) := by
  exact (update_declared run (kind := .header) (valid := false)
    header_declared
    (by decide : fields.findIdx? (·.name == "right") = some 1)
    (by decide : values.length = fields.length) (.bits (Bits.wrap 9 7))).1

example : ¬Declared index .struct "H" fields := by simp [Declared, index]
example : ¬NamesWellFormed "H" [⟨"x", .bits 8⟩, ⟨"x", .bits 9⟩] := by decide
example : ¬([Value.bool true].length = fields.length) := by decide

private def isValue (result : Except Fault Value) (expected : Value) : Bool :=
  match result with
  | .ok value => value == expected
  | .error _ => false

private def isError (result : Except Fault Value) (expected : String) : Bool :=
  match result with
  | .error (.interp message) => message == expected
  | _ => false

def tests : T Unit := do
  for valid in [false, true] do
    let original := Value.header "H" valid values
    check s!"field reads stored invalid/valid header ({valid})"
      (isValue ((fieldOf original "right").run run).1 (.bits (Bits.wrap 9 257)))
    let changed := (setField original "right" (.bits (Bits.wrap 9 7))).run run
    check s!"field write preserves exact header/siblings/validity ({valid})"
      (isValue changed.1 (.header "H" valid
        [.bits (Bits.wrap 8 171), .bits (Bits.wrap 9 7), .bool true]))
  check "metadata field write preserves unequal siblings"
    (isValue ((setField (.struct "M" values) "flag" (.bool false)).run run).1
      (.struct "M" [.bits (Bits.wrap 8 171), .bits (Bits.wrap 9 257), .bool false]))
  check "field agreement accepts exact header declaration"
    (decide (Declared index .header "H" fields))
  check "field agreement accepts exact struct declaration"
    (decide (Declared index .struct "M" fields))
  check "field agreement rejects missing declaration"
    (!(decide (Declared index .header "absent" fields)))
  check "field agreement rejects wrong nominal kind"
    (!(decide (Declared index .struct "H" fields)))
  let shadow := { index with structTypes := index.structTypes.insert "H" ⟨"H", fields⟩ }
  check "field agreement rejects same-name header/struct shadow"
    (!(decide (Declared shadow .header "H" fields)))
  check "field agreement rejects shadowed struct despite matching positions"
    (!(decide (Declared shadow .struct "H" fields)))
  let wrongName := { index with headerTypes := index.headerTypes.insert "H" ⟨"other", fields⟩ }
  check "field agreement rejects declaration key/name disagreement"
    (!(decide (Declared wrongName .header "H" fields)))
  check "field agreement rejects reordered declarations"
    (!(decide (Declared index .header "H" fields.reverse)))
  check "field agreement rejects width mismatch"
    (!(decide (Declared index .header "H" [⟨"left", .bits 7⟩,
      ⟨"right", .bits 9⟩, ⟨"flag", .boolean⟩])))
  check "field names reject duplicate same-width names"
    (!(decide (NamesWellFormed "H" [⟨"x", .bits 8⟩, ⟨"x", .bits 8⟩])))
  check "field names reject empty field"
    (!(decide (NamesWellFormed "H" [⟨"", .bits 8⟩])))
  check "field names reject empty nominal name"
    (!(decide (NamesWellFormed "" fields)))
  check "exact field shape rejects short runtime list" ([Value.bool true].length != fields.length)
  check "raw short-list setter is a no-op, not a valid typed write"
    (isValue ((setField (.header "H" false [.bool true]) "right" (.bits (Bits.wrap 9 7))).run run).1
      (.header "H" false [.bool true]))
  check "raw short-list read is an interpreter error"
    (isError ((fieldOf (.header "H" false [.bool true]) "right").run run).1 "H.right")
  check "raw missing field is an interpreter error"
    (isError ((fieldOf (.header "H" false values) "absent").run run).1 "H.absent")
  -- Real name-index construction, not only a handcrafted index witness.
  match Index.build { (default : BlockLibrary) with
      headerTypes := [⟨"H", fields⟩], structTypes := [⟨"M", fields⟩] } with
  | .error _ => check "field Index.build witnesses" false
  | .ok actual =>
    check "field actual Index.build header agreement" (decide (Declared actual .header "H" fields))
    check "field actual Index.build struct agreement" (decide (Declared actual .struct "M" fields))

end FieldLawTests
