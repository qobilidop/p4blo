import P4blo.InitialFrames
import P4blo.FieldCommandExamples
import P4bloIR.PlainCallEntry

/-! Exact selected declarations of the tracked Python RewriteBody wrapper.
This is a declaration-only program, not the complete packet/caller wrapper. -/

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

def block : P4bloIR.Block :=
  { (default : P4bloIR.Block) with
    name := "RewriteBody", kind := .control,
    params := P4bloIR.PlainCallEntry.params,
    locals := [⟨"scratch", .bits 8⟩, ⟨"unrelated", .bits 8⟩] }

def program : P4bloIR.Program :=
  { (default : P4bloIR.Program) with
    name := "plain-call-entry-declarations",
    headerTypes := FieldCommandExamples.program.headerTypes ++ [⟨"Result", resultFields.fields⟩],
    structTypes := FieldCommandExamples.program.structTypes ++ [⟨"H", observerFields.fields⟩],
    blocks := [block] }

def index : P4bloIR.Index := (P4bloIR.Index.build program).toOption.getD default
def scope : P4bloIR.BlockScope := index.scopes["RewriteBody"]?.getD default

theorem index_built : P4bloIR.Index.build program = .ok index := by cbv
theorem block_lookup : index.blocks["RewriteBody"]? = some block := by cbv
theorem scope_lookup : index.scopes[block.name]? = some scope := by cbv

theorem modes_agree : FieldCommandExamples.modes.Agrees scope := by
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
    index.headerTypes = FieldCommandExamples.index.headerTypes.insert "Result" ⟨"Result", resultFields.fields⟩ ∧
    index.structTypes = FieldCommandExamples.index.structTypes.insert "H" ⟨"H", observerFields.fields⟩ := by
  constructor <;> cbv

theorem roots_agree : FieldCommandExamples.roots.IndexAgrees index := by
  simp [FieldCommandExamples.roots, FieldCommandExamples.headers, FieldCommandExamples.headerFields,
    FieldCommandExamples.ethernet, FieldCommandExamples.ethernetFields, FieldCommandExamples.ipv4,
    FieldCommandExamples.ipv4Fields, FieldCommandExamples.metadata, FieldCommandExamples.metaFields,
    FieldCommandExamples.route, FieldCommandExamples.routeFields, Layout.IndexAgrees, Shape.IndexAgrees,
    P4bloIR.FieldLaws.Declared, P4bloIR.FieldLaws.NamesWellFormed, type_maps.1, type_maps.2,
    FieldCommandExamples.index, Layout.fields, Shape.toIR, Std.HashMap.getElem_insert]

theorem observer_agrees : observerShape.IndexAgrees index := by
  simp [observerShape, observerFields, resultShape, resultFields, resultWidths, Layout.IndexAgrees,
    Shape.IndexAgrees, P4bloIR.FieldLaws.Declared, P4bloIR.FieldLaws.NamesWellFormed,
    type_maps.1, type_maps.2, FieldCommandExamples.index, Layout.fields, Shape.toIR]

theorem roots_fuel : FieldCommandExamples.roots.zeroFuel ≤ index.headerTypes.size + index.structTypes.size + 2 := by
  simp [type_maps.1, type_maps.2, FieldCommandExamples.index, Std.HashMap.size_insert,
    FieldCommandExamples.roots, FieldCommandExamples.headers, FieldCommandExamples.headerFields,
    FieldCommandExamples.ethernet, FieldCommandExamples.ethernetFields, FieldCommandExamples.ipv4,
    FieldCommandExamples.ipv4Fields, FieldCommandExamples.metadata, FieldCommandExamples.metaFields,
    FieldCommandExamples.route, FieldCommandExamples.routeFields, Layout.zeroFuel, Shape.zeroFuel]

theorem observer_zero : P4bloIR.Value.zero (.struct "H") index = .ok observerShape.zero.toValue := by
  apply observerShape.zero_correct index observer_agrees
  simp [type_maps.1, type_maps.2, FieldCommandExamples.index, Std.HashMap.size_insert,
    observerShape, observerFields, resultShape, resultFields, resultWidths, Layout.zeroFuel, Shape.zeroFuel]

theorem extras_zero : ∀ (name : String) (decl : P4bloIR.VarDecl), scope.vars[name]? = some decl →
    (∀ shape (root : Slot FieldCommandExamples.roots shape), root.name ≠ name) →
    ∃ value, P4bloIR.Value.zero decl.type index = .ok value := by
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
      next _ => cases hd; exact ⟨_, observer_zero⟩
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

theorem initialized : ∃ zero, P4bloIR.Frame.forBlock index block = .ok zero ∧ zero.scope = scope ∧
    P4bloIR.ScalarStatements.BlockFrame zero ∧ FrameMatches FieldCommandExamples.roots.zero zero ∧
    ∀ (name : String), zero.vars[name]? =
      (scope.vars[name]?).bind (fun decl => (P4bloIR.Value.zero decl.type index).toOption) :=
  FieldCommandExamples.roots.initialize index block scope scope_lookup
    (Modes.Agrees.declares modes_agree) roots_agree roots_fuel extras_zero

/-- Index construction is not global type validation: this extra declaration
is accepted by the index, but cannot satisfy the initializer's extra premise. -/
def badExtraProgram : P4bloIR.Program :=
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
