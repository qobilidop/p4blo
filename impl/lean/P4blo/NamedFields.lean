import P4blo.FieldPlaces

/-! Checked names resolve to the existing typed Slot/Path/Ref/Place values.
Only visited names and the selected scalar leaf are checked; this is not
global schema, nominal index, declaration or runtime-frame validation. -/

namespace P4blo.Fields

inductive ResolutionError
  | emptyPath
  | emptySegment
  | missing (name : String)
  | ambiguous (name : String)
  | notAggregate (next : String)
  | aggregateEndpoint
  | typeMismatch (actual expected : Scalar.Ty)
  | invalidScalar (type : Scalar.Ty)
  | readonly (root : String)
  deriving Repr, DecidableEq

def Layout.countName : Layout → String → Nat
  | .nil, _ => 0
  | .cons name _ rest, query => (if name = query then 1 else 0) + rest.countName query

def Path.segments : Path shape t → List String
  | .scalar => []
  | .field slot path => slot.name :: path.segments

/-- Structural spelling of the actual selected reference, not its request. -/
def Ref.segments : Ref roots t → List String
  | .mk root path => root.name :: path.segments

def Path.WellNamed : {shape : Shape} → {t : Scalar.Ty} → Path shape t → Prop
  | _, t, .scalar => t.Valid
  | .aggregate _ _ fields, _, .field slot path =>
    slot.name ≠ "" ∧ fields.countName slot.name = 1 ∧ path.WellNamed

/-- Every selected name is nonempty and unique in its own layout; the
scalar endpoint is valid. Unvisited names/types are deliberately unchecked. -/
def Ref.WellNamed : Ref roots t → Prop
  | .mk root path => root.name ≠ "" ∧ roots.countName root.name = 1 ∧ path.WellNamed

def expressionOfSegments : List String → Option P4bloIR.Expr
  | [] => none
  | root :: rest => some (rest.foldl P4bloIR.Expr.member (.var root))

def lvalueOfSegments : List String → Option P4bloIR.LValue
  | [] => none
  | root :: rest => some (rest.foldl P4bloIR.LValue.member (.var root))

theorem Path.expr_spelling (path : Path shape t) (base : P4bloIR.Expr) :
    path.expr base = path.segments.foldl P4bloIR.Expr.member base := by
  induction path generalizing base with
  | scalar => rfl
  | field slot path ih => exact ih _

theorem Path.lvalue_spelling (path : Path shape t) (base : P4bloIR.LValue) :
    path.lvalue base = path.segments.foldl P4bloIR.LValue.member base := by
  induction path generalizing base with
  | scalar => rfl
  | field slot path ih => exact ih _

theorem Ref.expr_spelling (ref : Ref roots t) :
    some ref.expr = expressionOfSegments ref.segments := by
  cases ref with
  | mk root path => exact congrArg some (path.expr_spelling _)

theorem Ref.lvalue_spelling (ref : Ref roots t) :
    some ref.lvalue = lvalueOfSegments ref.segments := by
  cases ref with
  | mk root path => exact congrArg some (path.lvalue_spelling _)

private structure NamedSlot (fields : Layout) (query : String) where
  shape : Shape
  slot : Slot fields shape
  spelling : slot.name = query
  nonempty : query ≠ ""
  unique : fields.countName query = 1

private def resolveSlot (fields : Layout) (query : String) : Except ResolutionError (NamedSlot fields query) :=
  if empty : query = "" then .error .emptySegment
  else match fields with
  | .nil => .error (.missing query)
  | .cons name shape rest =>
    if equal : name = query then
      if absent : rest.countName query = 0 then
        .ok ⟨shape, .here, equal, empty, by simp [Layout.countName, equal, absent]⟩
      else .error (.ambiguous query)
    else do
      let selected ← resolveSlot rest query
      pure ⟨selected.shape, .there selected.slot, selected.spelling, empty,
        by simp [Layout.countName, equal, selected.unique]⟩

private def resolvePath (shape : Shape) (t : Scalar.Ty) (segments : List String) :
    Except ResolutionError {path : Path shape t // path.segments = segments ∧ path.WellNamed} :=
  match segments with
  | [] => match shape with
    | .aggregate .. => .error .aggregateEndpoint
    | .scalar actual =>
      if same : actual = t then
        if valid : t.Valid then
          .ok ⟨same ▸ Path.scalar, by subst actual; exact ⟨rfl, valid⟩⟩
        else .error (.invalidScalar t)
      else .error (.typeMismatch actual t)
  | name :: rest =>
    if name = "" then .error .emptySegment
    else match shape with
    | .scalar _ => .error (.notAggregate name)
    | .aggregate kind nominal fields => do
      let selected ← resolveSlot fields name
      let child ← resolvePath selected.shape t rest
      pure ⟨.field (kind := kind) (name := nominal) selected.slot child.val,
        by
          constructor
          · simp [Path.segments, selected.spelling, child.property.1]
          · refine ⟨?_, ?_, child.property.2⟩
            · simpa only [selected.spelling] using selected.nonempty
            · simpa only [selected.spelling] using selected.unique⟩
termination_by segments.length

private def resolveRef (roots : Layout) (t : Scalar.Ty) (segments : List String) :
    Except ResolutionError {ref : Ref roots t // ref.segments = segments ∧ ref.WellNamed} :=
  match segments with
  | [] => .error .emptyPath
  | name :: rest => do
    let selected ← resolveSlot roots name
    let child ← resolvePath selected.shape t rest
    pure ⟨.mk selected.slot child.val, by
      constructor
      · simp [Ref.segments, selected.spelling, child.property.1]
      · refine ⟨?_, ?_, child.property.2⟩
        · simpa only [selected.spelling] using selected.nonempty
        · simpa only [selected.spelling] using selected.unique⟩

/-- Total typed resolution. Errors distinguish name, traversal, type and
permission failures; no unchecked casts or interpreter calls are involved. -/
def Ref.resolve (roots : Layout) (t : Scalar.Ty) (segments : List String) :
    Except ResolutionError (Ref roots t) := (resolveRef roots t segments).map Subtype.val

theorem Ref.resolve_sound {segments : List String} (h : Ref.resolve roots t segments = .ok ref) :
    ref.segments = segments ∧ ref.WellNamed := by
  unfold Ref.resolve at h
  cases result : resolveRef roots t segments with
  | error error => simp [result, Except.map] at h
  | ok selected =>
    simp [result, Except.map] at h
    subst ref
    exact selected.property

private def checked (result : Except ResolutionError α) (success : result.isOk = true) : α :=
  match result with
  | .ok value => value
  | .error _ => False.elim (by contradiction)

private theorem checked_ok (result : Except ResolutionError α) (success : result.isOk = true) :
    result = .ok (checked result success) := by
  cases result with
  | ok value => rfl
  | error error => contradiction

/-- Expected type supplies roots and leaf type. Concrete names discharge
the success proof in the kernel; dynamic callers use `Ref.resolve`. -/
def Ref.named {roots : Layout} {t : Scalar.Ty} (segments : List String)
    (success : (Ref.resolve roots t segments).isOk = true := by decide +kernel) : Ref roots t :=
  checked (Ref.resolve roots t segments) success

theorem Ref.named_sound (segments : List String)
    (success : (Ref.resolve roots t segments).isOk = true) :
    (Ref.named segments success).segments = segments ∧ (Ref.named segments success).WellNamed := by
  exact Ref.resolve_sound (checked_ok _ success)

theorem Ref.named_expr (segments : List String)
    (success : (Ref.resolve roots t segments).isOk = true) :
    some (Ref.named segments success).expr = expressionOfSegments segments := by
  rw [Ref.expr_spelling, (Ref.named_sound segments success).1]

private def resolvePlace (modes : Modes roots) (t : Scalar.Ty) (segments : List String) :
    Except ResolutionError {place : Place modes t // place.ref.segments = segments ∧ place.ref.WellNamed} := do
  let selected ← resolveRef roots t segments
  if writable : (modes.getRef selected.val).writable = true then
    pure ⟨⟨selected.val, writable⟩, selected.property⟩
  else .error (.readonly selected.val.rootName)

def Place.resolve (modes : Modes roots) (t : Scalar.Ty) (segments : List String) :
    Except ResolutionError (Place modes t) := (resolvePlace modes t segments).map Subtype.val

theorem Place.resolve_sound (h : Place.resolve modes t segments = .ok place) :
    place.ref.segments = segments ∧ place.ref.WellNamed := by
  unfold Place.resolve at h
  cases result : resolvePlace modes t segments with
  | error error => simp [result, Except.map] at h
  | ok selected =>
    simp [result, Except.map] at h
    subst place
    exact selected.property

def Place.named {roots : Layout} {modes : Modes roots} {t : Scalar.Ty} (segments : List String)
    (success : (Place.resolve modes t segments).isOk = true := by decide +kernel) : Place modes t :=
  checked (Place.resolve modes t segments) success

theorem Place.named_sound (segments : List String)
    (success : (Place.resolve modes t segments).isOk = true) :
    (Place.named segments success).ref.segments = segments ∧ (Place.named segments success).ref.WellNamed := by
  exact Place.resolve_sound (checked_ok _ success)

theorem Place.named_lvalue (segments : List String)
    (success : (Place.resolve modes t segments).isOk = true) :
    some (Place.named segments success).ref.lvalue = lvalueOfSegments segments := by
  rw [Ref.lvalue_spelling, (Place.named_sound segments success).1]

end P4blo.Fields
