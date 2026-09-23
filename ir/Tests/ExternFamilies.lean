import Tests.Check

open P4bloIR

namespace ExternFamiliesTests

def bindChecksum (name : String) (width : Nat := 16) : Except String Nat := do
  let declaration : ExternType := {
    name
    constructorParams := []
    methods := [{ name := "compute"
                  params := [{ name := "data", type := .bits width, direction := .«in» }]
                  returns := some (.bits 16) }] }
  let index ← Index.build { (default : Program) with
    externTypes := [declaration]
    externInstances := [{ name := "sum", externType := name, args := [] }] }
  let externs ← Externs.bind index
  let (_, result) ← externs.call "sum" "compute" [.bits (Bits.wrap width 1)]
  match result.returns with
  | some (.bits value) => pure value.value
  | _ => throw "missing checksum"

def tests : T Unit := do
  for name in ["checksum16", "checksum16.16", "checksum16.multiple.dots"] do
    checkOk s!"suffixed family {name} dispatches and executes" (bindChecksum name) (· == 65534)
  for name in ["checksum16wrong", ".checksum16", "other.checksum16"] do
    checkError s!"family {name} is not a prefix match" (bindChecksum name) "no implementation"

end ExternFamiliesTests
