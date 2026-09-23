import P4bloIR.ScalarTyping

/-!
# Exact field primitive laws

These laws expose the existing `fieldOf` and `setField`, not another
evaluator. Declaration agreement includes nominal kind and prevents the
header-first index lookup from accepting a same-named struct. Exact list
shape rules out the silent no-op of an out-of-range `List.set`.

This is not value typing or program validity: callers must separately
justify field types, nested shapes, permissions and initialization.
-/

namespace P4bloIR.FieldLaws

inductive Kind where
  | header | struct
  deriving DecidableEq, BEq, Repr

def pack : Kind → String → Bool → List Value → Value
  | .header, name, valid, values => .header name valid values
  | .struct, name, _, values => .struct name values

/-- A well-named field list, without a claim about the field types. -/
def NamesWellFormed (name : String) (fields : List Field) : Prop :=
  name ≠ "" ∧ (fields.map Field.name).Nodup ∧ ∀ field ∈ fields, field.name ≠ ""

instance : Decidable (NamesWellFormed name fields) := by
  unfold NamesWellFormed
  infer_instance

/-- Exact reachable nominal declaration; unrelated index entries are allowed.
The opposite kind must be absent even though runtime lookup prefers headers. -/
def Declared (index : Index) (kind : Kind) (name : String) (fields : List Field) : Prop :=
  NamesWellFormed name fields ∧ match kind with
  | .header => index.headerTypes[name]? = some ⟨name, fields⟩ ∧
      index.structTypes[name]? = none
  | .struct => index.structTypes[name]? = some ⟨name, fields⟩ ∧
      index.headerTypes[name]? = none

instance : Decidable (Declared index kind name fields) := by
  unfold Declared
  cases kind <;> infer_instance

variable {fields : List Field} {values : List Value}

theorem Declared.fields_eq (h : Declared index kind name fields) :
    index.fields? name = some fields := by
  cases kind <;> simp_all [Declared, Index.fields?]

theorem Declared.position (h : Declared index kind name fields)
    (hp : fields.findIdx? (·.name == field) = some i) :
    index.fieldIndex? name field = some i := by
  simp [Index.fieldIndex?, h.fields_eq, hp]

@[simp] theorem run_getIndex (run : Run) : getIndex.run run = (.ok run.index, run) := rfl

/-- Raw read equation: validity is intentionally irrelevant. -/
theorem fieldOf_pack (run : Run)
    (hi : run.index.fieldIndex? name field = some i)
    (hv : values[i]? = some value) :
    (fieldOf (pack kind name valid values) field).run run = (.ok value, run) := by
  cases kind <;> simp [pack, fieldOf, ScalarTyping.run_bind, hi, hv]

/-- Raw setter equation. Bounds are deliberately not assumed here: the
runtime silently leaves a too-short list unchanged. Use `update_declared`
to establish that the selected value actually changes. -/
theorem setField_pack (run : Run)
    (hi : run.index.fieldIndex? name field = some i) :
    (setField (pack kind name valid values) field value).run run =
      (.ok (pack kind name valid (values.set i value)), run) := by
  cases kind <;> simp [pack, setField, ScalarTyping.run_bind, hi]

/-- Exact shape plus a declared position gives an existing runtime cell. -/
theorem position_lt (hp : fields.findIdx? (·.name == field) = some i)
    (hs : values.length = fields.length) : i < values.length := by
  have h := (List.findIdx?_eq_some_iff_getElem.mp hp).choose
  omega

theorem read_declared (run : Run) (hd : Declared run.index kind name fields)
    (hp : fields.findIdx? (·.name == field) = some i)
    (hs : values.length = fields.length) :
    (fieldOf (pack kind name valid values) field).run run =
      (.ok (values[i]'(position_lt hp hs)), run) := by
  exact fieldOf_pack run (hd.position hp) (List.getElem?_eq_getElem (position_lt hp hs))

/-- One update, with exact reconstructed container, successful readback,
unchanged length and every sibling position preserved. The exact container
equation includes nominal name and header validity, including `false`. -/
theorem update_declared (run : Run) (hd : Declared run.index kind name fields)
    (hp : fields.findIdx? (·.name == field) = some i)
    (hs : values.length = fields.length) (value : Value) :
    (setField (pack kind name valid values) field value).run run =
        (.ok (pack kind name valid (values.set i value)), run) ∧
    (fieldOf (pack kind name valid (values.set i value)) field).run run =
        (.ok value, run) ∧
    (values.set i value).length = fields.length ∧
    (∀ j, j ≠ i → (values.set i value)[j]? = values[j]?) := by
  refine ⟨setField_pack run (hd.position hp), ?_, by simpa using hs, ?_⟩
  · exact fieldOf_pack run (hd.position hp) (List.getElem?_set_self (position_lt hp hs))
  · intro j hj
    exact List.getElem?_set_ne (Ne.symm hj)

end P4bloIR.FieldLaws
