import P4blo.ScalarContext
import P4bloIR.FieldLaws
import P4bloIR.FieldTyping
import P4bloIR.ScalarStatements

/-!
# Independent finite aggregate values

Schemas carry nominal declarations; values carry every field and header
validity bit. Scalar paths update this source data without invoking the IR
evaluator. Conversion and explicit index agreement are separate bridges.
-/

namespace P4blo.Fields

abbrev Kind := P4bloIR.FieldLaws.Kind

mutual
inductive Shape where
  | scalar : Scalar.Ty → Shape
  | aggregate : Kind → String → Layout → Shape
inductive Layout where
  | nil
  | cons : String → Shape → Layout → Layout
end

def Shape.toIR : Shape → P4bloIR.Ty
  | .scalar t => t.toIR
  | .aggregate .header name _ => .header name
  | .aggregate .struct name _ => .struct name

def Layout.fields : Layout → List P4bloIR.Field
  | .nil => []
  | .cons name shape rest => ⟨name, shape.toIR⟩ :: rest.fields

def Layout.Scalars : Layout → Prop
  | .nil => True
  | .cons _ (.scalar _) rest => rest.Scalars
  | .cons _ (.aggregate ..) _ => False

mutual
/-- Local names, widths and header restrictions only. Repeated nominal
names across the tree additionally require one coherent `IndexAgrees`.
This predicate alone need not admit any agreeing index. -/
def Shape.LocallyWellFormed : Shape → Prop
  | .scalar (.bits width) => 0 < width
  | .scalar .boolean => True
  | .aggregate kind name fields =>
    P4bloIR.FieldLaws.NamesWellFormed name fields.fields ∧ fields.LocallyWellFormed ∧
      (kind = .header → fields.Scalars)
def Layout.LocallyWellFormed : Layout → Prop
  | .nil => True
  | .cons _ shape rest => shape.LocallyWellFormed ∧ rest.LocallyWellFormed
end

mutual
def Shape.IndexAgrees (index : P4bloIR.Index) : Shape → Prop
  | .scalar _ => True
  | .aggregate kind name fields =>
    P4bloIR.FieldLaws.Declared index kind name fields.fields ∧ fields.IndexAgrees index
def Layout.IndexAgrees (index : P4bloIR.Index) : Layout → Prop
  | .nil => True
  | .cons _ shape rest => shape.IndexAgrees index ∧ rest.IndexAgrees index
end

/-- All occurrences of one nominal kind/name share the same ordered
declaration when an agreeing index exists. Local well-formedness alone
does not establish this cross-tree constraint. -/
theorem nominal_fields_unique
    (ha : P4bloIR.FieldLaws.Declared index kind name first)
    (hb : P4bloIR.FieldLaws.Declared index kind name second) : first = second := by
  have h := ha.fields_eq.symm.trans hb.fields_eq
  exact Option.some.inj h

theorem nominal_kind_unique
    (ha : P4bloIR.FieldLaws.Declared index firstKind name first)
    (hb : P4bloIR.FieldLaws.Declared index secondKind name second) : firstKind = secondKind := by
  cases firstKind <;> cases secondKind
  · rfl
  · have h := ha.2.1.symm.trans hb.2.2
    contradiction
  · have h := hb.2.1.symm.trans ha.2.2
    contradiction
  · rfl

def Validity : Kind → Type
  | .header => Bool
  | .struct => Unit

def Validity.toBool : {kind : Kind} → Validity kind → Bool
  | .header, valid => valid
  | .struct, _ => false

mutual
inductive Data : Shape → Type
  | scalar : Scalar.Meaning t → Data (.scalar t)
  | aggregate : Validity kind → Record fields → Data (.aggregate kind name fields)
inductive Record : Layout → Type
  | nil : Record .nil
  | cons : Data shape → Record rest → Record (.cons name shape rest)
end

mutual
def Data.toValue : Data shape → P4bloIR.Value
  | .scalar value => Scalar.toValue value
  | .aggregate (kind := kind) (name := name) valid fields =>
    P4bloIR.FieldLaws.pack kind name valid.toBool fields.toValues
def Record.toValues : Record fields → List P4bloIR.Value
  | .nil => []
  | .cons value rest => value.toValue :: rest.toValues
end

mutual
/-- Every stored header-validity bit, including headers not on a path. -/
def Data.validities : Data shape → List Bool
  | .scalar _ => []
  | .aggregate (kind := .header) valid fields => valid :: fields.validities
  | .aggregate (kind := .struct) _ fields => fields.validities
def Record.validities : Record fields → List Bool
  | .nil => []
  | .cons value rest => value.validities ++ rest.validities
end

inductive Slot : Layout → Shape → Type
  | here : Slot (.cons name shape rest) shape
  | there : Slot rest shape → Slot (.cons name other rest) shape

def Slot.name : Slot fields shape → String
  | .here (name := name) => name
  | .there slot => slot.name

def Slot.index : Slot fields shape → Nat
  | .here => 0
  | .there slot => slot.index + 1

theorem Slot.mem (slot : Slot fields shape) :
    (⟨slot.name, shape.toIR⟩ : P4bloIR.Field) ∈ fields.fields := by
  induction slot with
  | here => simp [Slot.name, Layout.fields]
  | there slot ih => exact List.mem_cons_of_mem _ ih

theorem Slot.position (slot : Slot fields shape)
    (hw : (fields.fields.map P4bloIR.Field.name).Nodup) :
    fields.fields.findIdx? (·.name == slot.name) = some slot.index := by
  induction slot with
  | here => simp [Layout.fields, Slot.name, Slot.index, List.findIdx?_cons]
  | @there rest shape name other slot ih =>
    have hn : slot.name ≠ name := by
      intro h
      have hm : slot.name ∈ rest.fields.map P4bloIR.Field.name :=
        List.mem_map.mpr ⟨_, slot.mem, rfl⟩
      exact (List.nodup_cons.mp hw).1 (h ▸ hm)
    simp [Layout.fields, Slot.name, Slot.index, List.findIdx?_cons, Ne.symm hn,
      ih (List.nodup_cons.mp hw).2]

theorem Slot.indexAgrees {index : P4bloIR.Index} (slot : Slot fields shape) (hi : fields.IndexAgrees index) :
    shape.IndexAgrees index := by
  induction slot with
  | here => exact hi.1
  | there slot ih => exact ih hi.2

def Record.get : Record fields → Slot fields shape → Data shape
  | .cons value _, .here => value
  | .cons _ rest, .there slot => rest.get slot

def Record.set : Record fields → Slot fields shape → Data shape → Record fields
  | .cons _ rest, .here, value => .cons value rest
  | .cons head rest, .there slot, value => .cons head (rest.set slot value)

theorem Record.get_set (record : Record fields) (slot : Slot fields shape) (value : Data shape) :
    (record.set slot value).get slot = value := by
  induction slot with
  | here => cases record; rfl
  | there slot ih => cases record; exact ih _ value

theorem Record.validities_set (record : Record fields) (slot : Slot fields shape)
    (value : Data shape) (hv : value.validities = (record.get slot).validities) :
    (record.set slot value).validities = record.validities := by
  induction slot with
  | here => cases record; simpa [Record.set, Record.validities, Record.get] using hv
  | there slot ih =>
    cases record
    simp only [Record.set, Record.validities]
    rw [ih _ value hv]

theorem Record.length_toValues (record : Record fields) :
    record.toValues.length = fields.fields.length := by
  cases record with
  | nil => rfl
  | cons value rest => simpa [Record.toValues, Layout.fields] using rest.length_toValues

theorem Record.toValues_get (record : Record fields) (slot : Slot fields shape) :
    record.toValues[slot.index]? = some (record.get slot).toValue := by
  induction slot with
  | here => cases record; rfl
  | there slot ih => cases record; simpa [Record.toValues, Slot.index, Record.get] using ih _

theorem Record.toValues_set (record : Record fields) (slot : Slot fields shape)
    (value : Data shape) :
    (record.set slot value).toValues = record.toValues.set slot.index value.toValue := by
  induction slot with
  | here => cases record; rfl
  | there slot ih => cases record; simp [Record.set, Record.toValues, Slot.index, ih]

theorem Record.get_set_value (record : Record fields) (slot : Slot fields shape)
    (value : Data shape) (other : Slot fields otherShape)
    (hw : (fields.fields.map P4bloIR.Field.name).Nodup) :
    ((record.set slot value).get other).toValue =
      if other.name = slot.name then value.toValue else (record.get other).toValue := by
  induction slot with
  | @here name shape rest =>
    cases record with
    | cons head tail =>
      cases other with
      | here => simp [Record.set, Record.get]
      | there other =>
        have hn : other.name ≠ name := by
          intro h
          exact (List.nodup_cons.mp hw).1
            (h ▸ List.mem_map.mpr ⟨_, other.mem, rfl⟩)
        simp [Record.set, Record.get, Slot.name, hn]
  | @there rest shape name headShape slot ih =>
    have hn : slot.name ≠ name := by
      intro h
      exact (List.nodup_cons.mp hw).1
        (h ▸ List.mem_map.mpr ⟨_, slot.mem, rfl⟩)
    cases record with
    | cons head tail =>
      cases other with
      | here => simp [Record.set, Record.get, Slot.name, Ne.symm hn]
      | there other =>
        simpa [Record.set, Record.get, Slot.name] using
          ih tail value other (List.nodup_cons.mp hw).2

theorem Record.fieldOf (record : Record fields) (slot : Slot fields shape)
    (valid : Validity kind) (run : P4bloIR.Run)
    (hd : P4bloIR.FieldLaws.Declared run.index kind name fields.fields) :
    (P4bloIR.fieldOf (Data.aggregate (name := name) valid record).toValue slot.name).run run =
      (.ok (record.get slot).toValue, run) := by
  exact P4bloIR.FieldLaws.fieldOf_pack run
    (hd.position (slot.position hd.1.2.1)) (record.toValues_get slot)

theorem Record.setField (record : Record fields) (slot : Slot fields shape)
    (valid : Validity kind) (value : Data shape) (run : P4bloIR.Run)
    (hd : P4bloIR.FieldLaws.Declared run.index kind name fields.fields) :
    (P4bloIR.setField (Data.aggregate (name := name) valid record).toValue slot.name value.toValue).run run =
      (.ok (Data.aggregate (name := name) valid (record.set slot value)).toValue, run) := by
  simpa only [Data.toValue, record.toValues_set slot value] using
    P4bloIR.FieldLaws.setField_pack (values := record.toValues) (valid := valid.toBool)
      run (hd.position (slot.position hd.1.2.1))

/-- Only scalar leaves are accessible; there is no aggregate assignment. -/
inductive Path : Shape → Scalar.Ty → Type
  | scalar : Path (.scalar t) t
  | field : Slot fields child → Path child t → Path (.aggregate kind name fields) t

def Path.get : Path shape t → Data shape → Scalar.Meaning t
  | .scalar, .scalar value => value
  | .field slot path, .aggregate _ fields => path.get (fields.get slot)

def Path.set : Path shape t → Data shape → Scalar.Meaning t → Data shape
  | .scalar, .scalar _, value => .scalar value
  | .field slot path, .aggregate valid fields, value =>
    .aggregate valid (fields.set slot (path.set (fields.get slot) value))

theorem Path.get_set (path : Path shape t) (data : Data shape) (value : Scalar.Meaning t) :
    path.get (path.set data value) = value := by
  induction path with
  | scalar => cases data; rfl
  | field slot path ih =>
    cases data
    simp only [Path.get, Path.set, Record.get_set]
    exact ih _ value

theorem Path.validities_set (path : Path shape t) (data : Data shape)
    (value : Scalar.Meaning t) : (path.set data value).validities = data.validities := by
  induction path with
  | scalar => cases data; rfl
  | @field fields child t kind name slot path ih =>
    cases data with
    | aggregate valid record =>
      have h := record.validities_set slot (path.set (record.get slot) value) (ih _ value)
      cases kind <;> simp only [Path.set, Data.validities, h]

def Path.expr : Path shape t → P4bloIR.Expr → P4bloIR.Expr
  | .scalar, base => base
  | .field slot path, base => path.expr (.member base slot.name)

def Path.lvalue : Path shape t → P4bloIR.LValue → P4bloIR.LValue
  | .scalar, base => base
  | .field slot path, base => path.lvalue (.member base slot.name)

theorem Path.evaluate (path : Path shape t) (data : Data shape) (run : P4bloIR.Run)
    (hi : shape.IndexAgrees run.index)
    (hb : (P4bloIR.evaluate base).run run = (.ok data.toValue, run)) :
    (P4bloIR.evaluate (path.expr base)).run run = (.ok (Scalar.toValue (path.get data)), run) := by
  induction path generalizing base with
  | scalar => cases data; exact hb
  | field slot path ih =>
    cases data with
    | aggregate valid fields =>
      apply ih (fields.get slot) (slot.indexAgrees hi.2)
      simpa [P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind, hb] using
        fields.fieldOf slot valid run hi.1

theorem Path.readLValue (path : Path shape t) (data : Data shape) (run : P4bloIR.Run)
    (hi : shape.IndexAgrees run.index)
    (hb : (P4bloIR.readLValue base).run run = (.ok data.toValue, run)) :
    (P4bloIR.readLValue (path.lvalue base)).run run = (.ok (Scalar.toValue (path.get data)), run) := by
  induction path generalizing base with
  | scalar => cases data; exact hb
  | field slot path ih =>
    cases data with
    | aggregate valid fields =>
      apply ih (fields.get slot) (slot.indexAgrees hi.2)
      simpa [P4bloIR.readLValue, P4bloIR.ScalarTyping.run_bind, hb] using
        fields.fieldOf slot valid run hi.1

/-- Actual recursive lvalue reconstruction reduces to one root write. This
does not assume a callback that already states write correctness. -/
theorem Path.writeLValue (path : Path shape t) (data : Data shape) (value : Scalar.Meaning t)
    (run : P4bloIR.Run) (hi : shape.IndexAgrees run.index)
    (hb : (P4bloIR.readLValue base).run run = (.ok data.toValue, run)) :
    (P4bloIR.writeLValue (path.lvalue base) (Scalar.toValue value)).run run =
      (P4bloIR.writeLValue base (path.set data value).toValue).run run := by
  induction path generalizing base with
  | scalar => cases data; rfl
  | field slot path ih =>
    cases data with
    | aggregate valid fields =>
      have hr : (P4bloIR.readLValue (.member base slot.name)).run run =
          (.ok (fields.get slot).toValue, run) := by
        simpa [P4bloIR.readLValue, P4bloIR.ScalarTyping.run_bind, hb] using
          fields.fieldOf slot valid run hi.1
      rw [Path.lvalue, ih (fields.get slot) value (slot.indexAgrees hi.2) hr]
      simp [P4bloIR.writeLValue, P4bloIR.ScalarTyping.run_bind, hb,
        fields.setField slot valid (path.set (fields.get slot) value) run hi.1, Path.set]

/-- A root store is the same heterogeneous record representation. Root
names denote variables, while nested layouts denote nominal fields. -/
abbrev Store := Record

def Record.bindings : Record roots → Std.HashMap String P4bloIR.Value
  | .nil => {}
  | .cons (name := name) value rest => rest.bindings.insert name value.toValue

theorem Record.bindings_get (store : Record roots) (slot : Slot roots shape)
    (hw : (roots.fields.map P4bloIR.Field.name).Nodup) :
    store.bindings[slot.name]? = some (store.get slot).toValue := by
  induction slot with
  | here => cases store; simp [Record.bindings, Record.get, Slot.name]
  | @there rest shape name headShape slot ih =>
    have hn : slot.name ≠ name := by
      intro h
      exact (List.nodup_cons.mp hw).1
        (h ▸ List.mem_map.mpr ⟨_, slot.mem, rfl⟩)
    cases store with
    | cons head tail =>
      simpa [Record.bindings, Record.get, Slot.name, Std.HashMap.getElem?_insert,
        hn, Ne.symm hn] using ih tail (List.nodup_cons.mp hw).2

def FrameMatches (store : Store roots) (frame : P4bloIR.Frame) : Prop :=
  ∀ {shape} (root : Slot roots shape), frame.read? root.name = some (store.get root).toValue

def Record.frame (store : Store roots) : P4bloIR.Frame :=
  { scope := default, vars := store.bindings }

theorem Record.frame_matches (store : Store roots)
    (hw : (roots.fields.map P4bloIR.Field.name).Nodup) : FrameMatches store store.frame := by
  intro shape root
  simpa [Record.frame, P4bloIR.Frame.read?] using store.bindings_get root hw

theorem FrameMatches.set {store : Store roots} (hf : FrameMatches store frame)
    (hw : (roots.fields.map P4bloIR.Field.name).Nodup)
    (hb : P4bloIR.ScalarStatements.BlockFrame frame) (root : Slot roots shape) (value : Data shape) :
    FrameMatches (store.set root value)
      { frame with vars := frame.vars.insert root.name value.toValue } := by
  intro otherShape other
  rw [Record.get_set_value store root value other hw]
  have h := hf other
  simp only [P4bloIR.Frame.read?, hb.2, Option.bind_none] at h ⊢
  simp only [Std.HashMap.getElem?_insert]
  by_cases he : other.name = root.name
  · simp [he]
  · simp [he, Ne.symm he, h]

inductive Ref (roots : Layout) (t : Scalar.Ty)
  | mk {shape : Shape} : Slot roots shape → Path shape t → Ref roots t

def Ref.get : Ref roots t → Store roots → Scalar.Meaning t
  | .mk root path, store => path.get (store.get root)

def Ref.set : Ref roots t → Store roots → Scalar.Meaning t → Store roots
  | .mk root path, store, value => store.set root (path.set (store.get root) value)

theorem Ref.get_set (ref : Ref roots t) (store : Store roots) (value : Scalar.Meaning t) :
    ref.get (ref.set store value) = value := by
  cases ref with
  | mk root path => simp [Ref.get, Ref.set, Record.get_set, Path.get_set]

theorem Ref.validities_set (ref : Ref roots t) (store : Store roots) (value : Scalar.Meaning t) :
    (ref.set store value).validities = store.validities := by
  cases ref with
  | mk root path => exact store.validities_set root _ (path.validities_set _ value)

def Ref.rootName : Ref roots t → String
  | .mk root _ => root.name

def Ref.expr : Ref roots t → P4bloIR.Expr
  | .mk root path => path.expr (.var root.name)

def Ref.lvalue : Ref roots t → P4bloIR.LValue
  | .mk root path => path.lvalue (.var root.name)

theorem Ref.evaluate (ref : Ref roots t) (store : Store roots) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame) :
    (P4bloIR.evaluate ref.expr).run run = (.ok (Scalar.toValue (ref.get store)), run) := by
  cases ref with
  | mk root path =>
    apply path.evaluate (store.get root) run (root.indexAgrees hi)
    simp [P4bloIR.evaluate, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind, hf root]

/-- One actual frame update containing the complete independent source root.
Permission/declaration checks are separate; the runtime itself does not
enforce source writability. -/
theorem Ref.write (root : Slot roots shape) (path : Path shape t)
    (store : Store roots) (value : Scalar.Meaning t) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame)
    (hb : P4bloIR.ScalarStatements.BlockFrame run.frame) :
    (P4bloIR.writeLValue (Ref.mk root path).lvalue (Scalar.toValue value)).run run =
      (.ok (), { run with frame := { run.frame with vars := (run.frame.vars.insert root.name
        (path.set (store.get root) value).toValue) } }) := by
  have hr : (P4bloIR.readLValue (.var root.name)).run run =
      (.ok (store.get root).toValue, run) := by
    simp [P4bloIR.readLValue, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind, hf root]
  rw [Ref.lvalue, path.writeLValue (store.get root) value run (root.indexAgrees hi) hr]
  apply P4bloIR.ScalarStatements.writeVar_block run hb
  simpa [P4bloIR.Frame.read?, hb.2] using hf root

/-- Exact updated source store and unrelated runtime state. Source write
permissions are not claimed here; they must be supplied by writable places. -/
theorem Ref.write_matches (ref : Ref roots t) (store : Store roots) (value : Scalar.Meaning t)
    (run : P4bloIR.Run) (hi : roots.IndexAgrees run.index)
    (hf : FrameMatches store run.frame) (hw : (roots.fields.map P4bloIR.Field.name).Nodup)
    (hb : P4bloIR.ScalarStatements.BlockFrame run.frame) :
    ∃ final, (P4bloIR.writeLValue ref.lvalue (Scalar.toValue value)).run run = (.ok (), final) ∧
      FrameMatches (ref.set store value) final.frame ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars run final ∧
      P4bloIR.ScalarStatements.PreservesOutside [ref.rootName] run final := by
  cases ref with
  | mk root path =>
    refine ⟨_, Ref.write root path store value run hi hf hb, hf.set hw hb root _, ⟨_, rfl⟩, ?_⟩
    intro name hn
    simp only [Ref.rootName, List.mem_singleton] at hn
    simp [Std.HashMap.getElem?_insert, Ne.symm hn]

/-- Root names and local shape restrictions; nominal consistency remains
the additional `IndexAgrees` premise. -/
def RootWellFormed (roots : Layout) : Prop :=
  (roots.fields.map P4bloIR.Field.name).Nodup ∧
  (∀ field ∈ roots.fields, field.name ≠ "") ∧ roots.LocallyWellFormed

/-- Exact actual block variable declarations, separate from runtime values. -/
def RootDeclares (roots : Layout) (scope : P4bloIR.BlockScope) : Prop :=
  ∀ {shape} (root : Slot roots shape), ∃ decl,
    scope.var? root.name = some decl ∧ decl.name = root.name ∧ decl.type = shape.toIR

theorem Slot.locallyWellFormed (slot : Slot fields shape) (hw : fields.LocallyWellFormed) :
    shape.LocallyWellFormed := by
  induction slot with
  | here => exact hw.1
  | there slot ih => exact ih hw.2

theorem Path.leaf_valid (path : Path shape t) (hw : shape.LocallyWellFormed) : t.Valid := by
  induction path with
  | @scalar scalarType => cases scalarType <;> exact hw
  | field slot path ih => exact ih (slot.locallyWellFormed hw.2.1)

theorem Path.typed (path : Path shape t) (hi : shape.IndexAgrees index)
    (hb : P4bloIR.FieldTyping.Path index scope base shape.toIR) :
    P4bloIR.FieldTyping.Path index scope (path.expr base) (Scalar.Ty.toIR t) := by
  induction path generalizing base with
  | scalar => exact hb
  | @field fields child t kind name slot path ih =>
    have hfields : P4bloIR.FieldTyping.FieldsOf index
        (Shape.aggregate kind name fields).toIR fields.fields := by
      cases kind with
      | header => exact .header hi.1
      | struct => exact .struct hi.1
    exact ih (slot.indexAgrees hi.2) (.member ⟨slot.name, child.toIR⟩ hb hfields slot.mem)

theorem Ref.typed (ref : Ref roots t) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : RootDeclares roots scope) :
    P4bloIR.FieldTyping.Typed index scope ref.expr t := by
  cases ref with
  | mk root path =>
    obtain ⟨decl, hfind, hname, htype⟩ := hd root
    have hn := hw.2.1 _ root.mem
    have hpath : P4bloIR.FieldTyping.Path index scope (.var root.name) _ :=
      .var root.name decl hn hfind hname
    rw [htype] at hpath
    apply P4bloIR.FieldTyping.Typed.read
    · have ht : Scalar.Ty.toIR t = P4bloIR.ScalarStatements.irType t := by cases t <;> rfl
      rw [← ht]
      exact path.typed (root.indexAgrees hi) hpath
    · exact path.leaf_valid (root.locallyWellFormed hw.2.2)

end P4blo.Fields
