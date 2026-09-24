import P4blo.SourceZero
import P4blo.FieldCommandExamples

namespace P4blo.SourceZeroTests
open Fields

private instance : BEq (Except String P4bloIR.Value) where
  beq
    | .ok actual, .ok expected => actual == expected
    | .error actual, .error expected => actual == expected
    | _, _ => false

def leaves : Layout := .cons "octet" (.scalar (.bits 8))
  (.cons "wide" (.scalar (.bits 65)) (.cons "flag" (.scalar .boolean) .nil))
def header : Shape := .aggregate .header "Mixed" leaves
def empty : Shape := .aggregate .header "Empty" .nil
def children : Layout := .cons "packet" header
  (.cons "empty" empty (.cons "port" (.scalar (.bits 9)) .nil))
def nested : Shape := .aggregate .struct "Nested" children

def index : P4bloIR.Index :=
  { program := default,
    headerTypes := (({} : Std.HashMap String P4bloIR.HeaderType).insert
      "Mixed" ⟨"Mixed", leaves.fields⟩).insert "Empty" ⟨"Empty", []⟩,
    structTypes := ({} : Std.HashMap String P4bloIR.StructType).insert
      "Nested" ⟨"Nested", children.fields⟩ }

theorem indexAgrees : nested.IndexAgrees index := by
  simp [nested, children, header, leaves, empty, Shape.IndexAgrees,
    Layout.IndexAgrees, P4bloIR.FieldLaws.Declared,
    P4bloIR.FieldLaws.NamesWellFormed, index, Layout.fields, Shape.toIR,
    Std.HashMap.getElem_insert]

-- Independent constructor answers: no call to either source/runtime zero.
def expectedHeader : P4bloIR.Value :=
  .header "Mixed" false [.bits ⟨8, 0, by decide⟩,
    .bits ⟨65, 0, by decide⟩, .bool false]
def expected : P4bloIR.Value :=
  .struct "Nested" [expectedHeader, .header "Empty" false [],
    .bits ⟨9, 0, by decide⟩]

example : nested.zero.toValue = expected := rfl
example : nested.zeroFuel = 3 := rfl
example : empty.zeroFuel = 1 := rfl
example : nested.zero.validities = [false, false] := rfl

theorem actualZero : P4bloIR.Value.zero nested.toIR index = .ok expected := by
  apply nested.zero_correct index indexAgrees
  simp [nested, children, header, leaves, empty, Shape.zeroFuel, Layout.zeroFuel,
    index, Std.HashMap.size_insert]

-- A real mixed forwarding layout discharges the runtime budget premise.
theorem forwardZero :
    FieldCommandExamples.roots.fields.mapM
      (fun field => P4bloIR.Value.zero field.type FieldCommandExamples.index) =
    .ok FieldCommandExamples.roots.zero.toValues := by
  exact FieldCommandExamples.roots.zeroWith_correct FieldCommandExamples.index
    FieldCommandExamples.indexAgrees _ (by
      simp [FieldCommandExamples.roots, FieldCommandExamples.headers,
        FieldCommandExamples.headerFields, FieldCommandExamples.ethernet,
        FieldCommandExamples.ethernetFields, FieldCommandExamples.ipv4,
        FieldCommandExamples.ipv4Fields, FieldCommandExamples.metadata,
        FieldCommandExamples.metaFields, FieldCommandExamples.route,
        FieldCommandExamples.routeFields, FieldCommandExamples.index,
        Shape.zeroFuel, Layout.zeroFuel, Std.HashMap.size_insert])

def run : IO Unit := do
  unless nested.zero.toValue == expected do
    throw (IO.userError "independent source aggregate zero")
  unless nested.zero.validities == [false, false] do
    throw (IO.userError "every source header starts invalid")
  for fuel in [3, 4, 9] do
    unless P4bloIR.Value.zeroWith index fuel nested.toIR == .ok expected do
      throw (IO.userError s!"actual aggregate zero fuel {fuel}")
  for fuel in [0, 1, 2] do
    unless P4bloIR.Value.zeroWith index fuel nested.toIR ==
        .error "type nesting deeper than the number of declared types" do
      throw (IO.userError s!"insufficient aggregate zero fuel {fuel}")
  unless P4bloIR.Value.zero nested.toIR index == .ok expected do
    throw (IO.userError "actual production zero budget")
  unless P4bloIR.Value.zeroWith index 1 empty.toIR == .ok (.header "Empty" false []) do
    throw (IO.userError "empty header consumes one fuel and starts invalid")
  for width in [0, 1, 8, 9, 65] do
    let source : Shape := .scalar (.bits width)
    let expected : P4bloIR.Value := .bits ⟨width, 0, Nat.two_pow_pos width⟩
    unless source.zero.toValue == expected &&
        P4bloIR.Value.zeroWith index 1 source.toIR == .ok expected do
      throw (IO.userError s!"scalar zero width {width}")
  unless P4bloIR.Value.zeroWith index 1 .boolean == .ok (.bool false) do
    throw (IO.userError "Boolean zero")
  unless P4bloIR.Value.zeroWith index 1 (.header "Absent") ==
      .error "unknown header type 'Absent'" do
    throw (IO.userError "missing declaration is not nominal agreement")
  -- Runtime initialization does not validate nominal name consistency.
  -- The correspondence premise must not conceal this boundary.
  let wrong := { index with
    headerTypes := index.headerTypes.insert "Empty" ⟨"Different", []⟩ }
  unless P4bloIR.Value.zeroWith wrong 1 empty.toIR == .ok (.header "Different" false []) do
    throw (IO.userError "actual stored declaration name boundary")
  IO.println "Independent source/actual zero values, fuel limits and nominal boundaries passed"

end P4blo.SourceZeroTests
