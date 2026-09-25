import P4blo.InitialFrames
import P4blo.FieldCommandExamples
import P4bloIR.PlainCallEntry

/-! Exact selected declarations of the tracked Python RewriteBody wrapper.
The body family is actually indexed; the original names specialize it to
an empty declaration-only program. Neither is a complete packet/caller wrapper. -/

namespace P4blo.CallEntry
open Fields

def resultWidths : List (String × Nat) :=
  [("dst", 48), ("src", 48), ("etherType", 16), ("ethernetValid", 8),
   ("ttl", 8), ("protocol", 8), ("checksum", 16), ("ipv4Valid", 8),
   ("port", 16), ("drop", 8), ("sentinel", 16), ("routeHit", 8),
   ("routeDst", 48), ("routeSrc", 48), ("routePort", 16), ("scratch", 8), ("unrelated", 8)]

def resultFields : Layout := resultWidths.foldr
  (fun (name, width) rest => .cons name (.scalar (.bits width)) rest) .nil
def resultShape : Shape := .aggregate .header "Result" resultFields
def observerFields : Layout := .cons "result" resultShape .nil
def observerShape : Shape := .aggregate .struct "H" observerFields

namespace WithBody

variable (body : List P4bloIR.Stmt)

def block : P4bloIR.Block :=
  { (default : P4bloIR.Block) with
    name := "RewriteBody", kind := .control,
    params := P4bloIR.PlainCallEntry.params,
    locals := [⟨"scratch", .bits 8⟩, ⟨"unrelated", .bits 8⟩], body }

def program : P4bloIR.BlockLibrary :=
  { (default : P4bloIR.BlockLibrary) with
    name := "plain-call-entry-declarations",
    headerTypes := FieldCommandExamples.program.headerTypes ++ [⟨"Result", resultFields.fields⟩],
    structTypes := FieldCommandExamples.program.structTypes ++ [⟨"H", observerFields.fields⟩],
    blocks := [block body] }

def index : P4bloIR.Index := (P4bloIR.Index.build (program body)).toOption.getD default
def scope : P4bloIR.BlockScope := (index body).scopes["RewriteBody"]?.getD default

theorem index_built : P4bloIR.Index.build (program body) = .ok (index body) := by cbv
theorem block_lookup : (index body).blocks["RewriteBody"]? = some (block body) := by cbv
theorem scope_lookup : (index body).scopes[(block body).name]? = some (scope body) := by cbv

/-- The selected scope retains the same actual body-bearing block. -/
theorem scope_block : (scope body).block = block body := by cbv

theorem block_body : (block body).body = body := rfl

/-- Changing executable statements does not change variable declarations. -/
theorem scope_vars : (scope body).vars = (scope []).vars := by cbv

theorem modes_agree : FieldCommandExamples.modes.Agrees (scope body) := by
  intro shape root
  cases root with
  | here => cbv
  | there root => cases root with
    | here => cbv
    | there root => cases root with
      | here => cbv
      | there root => cases root with
        | here => cbv
        | there root => cases root

private theorem type_maps :
    (index body).headerTypes = FieldCommandExamples.index.headerTypes.insert "Result" ⟨"Result", resultFields.fields⟩ ∧
    (index body).structTypes = FieldCommandExamples.index.structTypes.insert "H" ⟨"H", observerFields.fields⟩ := by
  constructor <;> cbv

theorem roots_agree : FieldCommandExamples.roots.IndexAgrees (index body) := by
  simp [FieldCommandExamples.roots, FieldCommandExamples.headers, FieldCommandExamples.headerFields,
    FieldCommandExamples.ethernet, FieldCommandExamples.ethernetFields, FieldCommandExamples.ipv4,
    FieldCommandExamples.ipv4Fields, FieldCommandExamples.metadata, FieldCommandExamples.metaFields,
    FieldCommandExamples.route, FieldCommandExamples.routeFields, Layout.IndexAgrees, Shape.IndexAgrees,
    P4bloIR.FieldLaws.Declared, P4bloIR.FieldLaws.NamesWellFormed, (type_maps body).1, (type_maps body).2,
    FieldCommandExamples.index, Layout.fields, Shape.toIR, Std.HashMap.getElem_insert]

theorem observer_agrees : observerShape.IndexAgrees (index body) := by
  simp [observerShape, observerFields, resultShape, resultFields, resultWidths, Layout.IndexAgrees,
    Shape.IndexAgrees, P4bloIR.FieldLaws.Declared, P4bloIR.FieldLaws.NamesWellFormed,
    (type_maps body).1, (type_maps body).2, FieldCommandExamples.index, Layout.fields, Shape.toIR]

theorem roots_fuel : FieldCommandExamples.roots.zeroFuel ≤ (index body).headerTypes.size + (index body).structTypes.size + 2 := by
  simp [(type_maps body).1, (type_maps body).2, FieldCommandExamples.index, Std.HashMap.size_insert,
    FieldCommandExamples.roots, FieldCommandExamples.headers, FieldCommandExamples.headerFields,
    FieldCommandExamples.ethernet, FieldCommandExamples.ethernetFields, FieldCommandExamples.ipv4,
    FieldCommandExamples.ipv4Fields, FieldCommandExamples.metadata, FieldCommandExamples.metaFields,
    FieldCommandExamples.route, FieldCommandExamples.routeFields, Layout.zeroFuel, Shape.zeroFuel]

theorem observer_zero : P4bloIR.Value.zero (.struct "H") (index body) = .ok observerShape.zero.toValue := by
  apply observerShape.zero_correct (index body) (observer_agrees body)
  simp [(type_maps body).1, (type_maps body).2, FieldCommandExamples.index, Std.HashMap.size_insert,
    observerShape, observerFields, resultShape, resultFields, resultWidths, Layout.zeroFuel, Shape.zeroFuel]

theorem extras_zero : ∀ (name : String) (decl : P4bloIR.VarDecl), (scope body).vars[name]? = some decl →
    (∀ shape (root : Slot FieldCommandExamples.roots shape), root.name ≠ name) →
    ∃ value, P4bloIR.Value.zero decl.type (index body) = .ok value := by
  intro name decl hd hn
  cbv at hd
  simp only [Std.HashMap.getElem?_insert] at hd
  split at hd
  next _ => cases hd; exact ⟨_, rfl⟩
  next he =>
    split at hd
    next h => exact False.elim (hn _ (.there (.there (.there .here))) (by simpa [Slot.name] using h))
    next _ =>
      split at hd
      next _ => cases hd; exact ⟨_, observer_zero body⟩
      next _ =>
        split at hd
        next h => exact False.elim (hn _ (.there (.there .here)) (by simpa [Slot.name] using h))
        next _ =>
          split at hd
          next h => exact False.elim (hn _ (.there .here) (by simpa [Slot.name] using h))
          next _ =>
            split at hd
            next h => exact False.elim (hn _ .here (by simpa [Slot.name] using h))
            next _ => simp at hd

theorem initialized : ∃ zero, P4bloIR.Frame.forBlock (index body) (block body) = .ok zero ∧ zero.scope = scope body ∧
    P4bloIR.ScalarStatements.BlockFrame zero ∧ FrameMatches FieldCommandExamples.roots.zero zero ∧
    ∀ (name : String), zero.vars[name]? =
      ((scope body).vars[name]?).bind (fun decl => (P4bloIR.Value.zero decl.type (index body)).toOption) :=
  FieldCommandExamples.roots.initialize (index body) (block body) (scope body) (scope_lookup body)
    (Modes.Agrees.declares (modes_agree body)) (roots_agree body) (roots_fuel body) (extras_zero body)


end WithBody

/-! Compatibility specializations: the old empty-body API is unchanged. -/
abbrev block := WithBody.block []
abbrev program := WithBody.program []
abbrev index := WithBody.index []
abbrev scope := WithBody.scope []
abbrev index_built := WithBody.index_built []
abbrev block_lookup := WithBody.block_lookup []
abbrev scope_lookup := WithBody.scope_lookup []
theorem modes_agree : FieldCommandExamples.modes.Agrees scope := WithBody.modes_agree []
abbrev roots_agree := WithBody.roots_agree []
abbrev observer_agrees := WithBody.observer_agrees []
abbrev roots_fuel := WithBody.roots_fuel []
abbrev observer_zero := WithBody.observer_zero []
abbrev extras_zero := WithBody.extras_zero []
abbrev initialized := WithBody.initialized []

/-- Index construction is not global type validation: this extra declaration
is accepted by the index, but cannot satisfy the initializer's extra premise. -/
def badExtraProgram : P4bloIR.BlockLibrary :=
  { program with blocks := [{ block with locals := block.locals ++ [⟨"extra", .struct "Missing"⟩] }] }
def badExtraIndex : P4bloIR.Index := (P4bloIR.Index.build badExtraProgram).toOption.getD default

theorem bad_extra_built : P4bloIR.Index.build badExtraProgram = .ok badExtraIndex := by cbv

theorem bad_extra_zero : ¬ ∃ value, P4bloIR.Value.zero (.struct "Missing") badExtraIndex = .ok value := by
  have h : P4bloIR.Value.zero (.struct "Missing") badExtraIndex = .error "unknown struct type 'Missing'" := by
    cbv
  simp [h]

theorem bad_extra_premise : ¬ (∀ (name : String) (decl : P4bloIR.VarDecl),
    (badExtraIndex.scopes["RewriteBody"]?.getD default).vars[name]? = some decl →
    (∀ shape (root : Slot FieldCommandExamples.roots shape), root.name ≠ name) →
    ∃ value, P4bloIR.Value.zero decl.type badExtraIndex = .ok value) := by
  intro h
  apply bad_extra_zero
  apply h "extra" (.var ⟨"extra", .struct "Missing"⟩) (by cbv)
  intro shape root
  cases root with
  | here => decide
  | there root => cases root with
    | here => decide
    | there root => cases root with
      | here => decide
      | there root => cases root with
        | here => decide
        | there root => cases root

end P4blo.CallEntry
