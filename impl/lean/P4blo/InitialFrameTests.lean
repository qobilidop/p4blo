import P4blo.InitialFrames
import P4blo.FieldCommandExamples

namespace P4blo.InitialFrameTests
open Fields FieldCommandExamples

def actualIndex : P4bloIR.Index := (P4bloIR.Index.build program).toOption.getD default

set_option maxRecDepth 10000 in
theorem actualIndex_built : P4bloIR.Index.build program = .ok actualIndex := by
  cbv

def actualScope : P4bloIR.BlockScope := actualIndex.scopes["fields"]?.getD default

theorem actualScope_lookup : actualIndex.scopes[modes.scope.block.name]? = some actualScope := by
  cbv

theorem actual_modes : modes.Agrees actualScope := by
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

theorem actual_nominals : roots.IndexAgrees actualIndex := by
  have hh : actualIndex.headerTypes = index.headerTypes := by cbv
  have hs : actualIndex.structTypes = index.structTypes := by cbv
  simpa only [roots, headers, headerFields, ethernet, ethernetFields, ipv4, ipv4Fields,
    metadata, metaFields, route, routeFields, Layout.IndexAgrees, Shape.IndexAgrees,
    P4bloIR.FieldLaws.Declared, hh, hs] using indexAgrees

theorem actual_fuel : roots.zeroFuel ≤
    actualIndex.headerTypes.size + actualIndex.structTypes.size + 2 := by
  have hh : actualIndex.headerTypes = index.headerTypes := by cbv
  have hs : actualIndex.structTypes = index.structTypes := by cbv
  simp [hh, hs, index, Std.HashMap.size_insert, roots, headers, headerFields,
    ethernet, ethernetFields, ipv4, ipv4Fields, metadata, metaFields, route,
    routeFields, Layout.zeroFuel, Shape.zeroFuel]

theorem actual_coverage : roots.Covers actualScope := by
  intro name decl hd
  cbv at hd
  simp only [Std.HashMap.getElem?_insert] at hd
  split at hd
  next he => exact ⟨_, .there (.there (.there .here)), by simpa [Slot.name] using he⟩
  next _ =>
    split at hd
    next he => exact ⟨_, .there (.there .here), by simpa [Slot.name] using he⟩
    next _ =>
      split at hd
      next he => exact ⟨_, .there .here, by simpa [Slot.name] using he⟩
      next _ =>
        split at hd
        next he => exact ⟨_, .here, by simpa [Slot.name] using he⟩
        next _ => simp at hd

theorem forward_initialized : ∃ frame,
    P4bloIR.Frame.forBlock actualIndex modes.scope.block = .ok frame ∧
    frame.scope = actualScope ∧ P4bloIR.ScalarStatements.BlockFrame frame ∧
    FrameMatches roots.zero frame := by
  obtain ⟨frame, he, hs, hb, hm, _⟩ := roots.initialize actualIndex modes.scope.block actualScope
    actualScope_lookup (Modes.Agrees.declares actual_modes) actual_nominals actual_fuel
    (fun name decl hd hn => by
      obtain ⟨shape, root, hr⟩ := actual_coverage name decl hd
      exact False.elim (hn shape root hr))
  exact ⟨frame, he, hs, hb, hm⟩

-- Direct expected constructors do not call source/runtime zero functions.
def expectedHeaders : P4bloIR.Value := .struct "Headers"
  [.header "Ethernet" false [.bits ⟨48, 0, by decide⟩, .bits ⟨48, 0, by decide⟩,
    .bits ⟨16, 0, by decide⟩],
   .header "IPv4" false [.bits ⟨8, 0, by decide⟩, .bits ⟨8, 0, by decide⟩,
    .bits ⟨16, 0, by decide⟩]]
def expectedMetadata : P4bloIR.Value := .struct "Metadata"
  [.bits ⟨9, 0, by decide⟩, .bool false, .bits ⟨16, 0, by decide⟩]
def expectedRoute : P4bloIR.Value := .struct "Route"
  [.bool false, .bits ⟨48, 0, by decide⟩, .bits ⟨48, 0, by decide⟩, .bits ⟨9, 0, by decide⟩]
def expectedValues : List P4bloIR.Value :=
  [expectedHeaders, expectedMetadata, expectedRoute, .bits ⟨8, 0, by decide⟩]

example : roots.zero.toValues = expectedValues := rfl
example : roots.zero.validities = [false, false] := rfl

theorem forward_expected : ∃ frame,
    P4bloIR.Frame.forBlock actualIndex modes.scope.block = .ok frame ∧
    frame.read? "hdr" = some expectedHeaders ∧
    frame.read? "meta" = some expectedMetadata ∧
    frame.read? "route" = some expectedRoute ∧
    frame.read? "scratch" = some (.bits ⟨8, 0, by decide⟩) := by
  obtain ⟨frame, he, _, _, hm⟩ := forward_initialized
  exact ⟨frame, he, hm .here, hm (.there .here), hm (.there (.there .here)),
    hm (.there (.there (.there .here)))⟩

-- Extras extend the real-built scope. This is deliberately a local scope
-- extension, not a claim that the packet/call wrapper has been initialized.
def extraScope : P4bloIR.BlockScope :=
  { actualScope with
    vars := (actualScope.vars.insert "observer" (.param ⟨"observer", .bits 65, .inout⟩)).insert
      "unrelated" (.var ⟨"unrelated", .boolean⟩) }
def extraIndex : P4bloIR.Index :=
  { actualIndex with scopes := actualIndex.scopes.insert "fields" extraScope }

theorem extra_modes : modes.Agrees extraScope := by
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

theorem extra_success : ∀ (name : String) (decl : P4bloIR.VarDecl),
    extraScope.vars[name]? = some decl →
    (∀ shape (root : Slot roots shape), root.name ≠ name) →
    ∃ value, P4bloIR.Value.zero decl.type extraIndex = .ok value := by
  intro name decl hd hn
  simp only [extraScope, Std.HashMap.getElem?_insert] at hd
  split at hd
  next _ => cases hd; exact ⟨_, rfl⟩
  next _ =>
    split at hd
    next _ => cases hd; exact ⟨_, rfl⟩
    next _ =>
      obtain ⟨shape, root, hr⟩ := actual_coverage name decl hd
      exact False.elim (hn shape root hr)

theorem extras_initialized : ∃ frame,
    P4bloIR.Frame.forBlock extraIndex modes.scope.block = .ok frame ∧
    frame.scope = extraScope ∧ P4bloIR.ScalarStatements.BlockFrame frame ∧
    FrameMatches roots.zero frame ∧
    frame.read? "observer" = some (.bits ⟨65, 0, by decide⟩) ∧
    frame.read? "unrelated" = some (.bool false) := by
  obtain ⟨frame, he, hs, hb, hm, hv⟩ := roots.initialize extraIndex modes.scope.block extraScope
    (by simp [extraIndex, Modes.scope]) (Modes.Agrees.declares extra_modes)
    actual_nominals actual_fuel extra_success
  refine ⟨frame, he, hs, hb, hm, ?_, ?_⟩
  · simp [P4bloIR.Frame.read?, hb.2, hv, extraScope, P4bloIR.Value.zero,
      P4bloIR.Value.zeroWith, P4bloIR.VarDecl.type, Except.toOption, Std.HashMap.getElem_insert]
    rfl
  · simp [P4bloIR.Frame.read?, hb.2, hv, extraScope, P4bloIR.Value.zero,
      P4bloIR.Value.zeroWith, P4bloIR.VarDecl.type, Except.toOption]
    rfl

theorem observer_not_root : ∀ shape (root : Slot roots shape), root.name ≠ "observer" := by
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

example : ¬ roots.Covers extraScope := by
  intro h
  have hn := h.absent "observer" observer_not_root
  simp [extraScope] at hn

def failingScope : P4bloIR.BlockScope :=
  { extraScope with vars := extraScope.vars.insert "observer" (.param ⟨"observer", .header "Absent", .inout⟩) }
def failingIndex : P4bloIR.Index :=
  { extraIndex with scopes := extraIndex.scopes.insert "fields" failingScope }

example : ¬ (∀ (name : String) (decl : P4bloIR.VarDecl), failingScope.vars[name]? = some decl →
    (∀ shape (root : Slot roots shape), root.name ≠ name) →
    ∃ value, P4bloIR.Value.zero decl.type failingIndex = .ok value) := by
  intro h
  obtain ⟨value, hv⟩ := h "observer" (.param ⟨"observer", .header "Absent", .inout⟩)
    (by simp [failingScope]) observer_not_root
  have hh : failingIndex.headerTypes = index.headerTypes := by cbv
  simp [P4bloIR.Value.zero, P4bloIR.Value.zeroWith, P4bloIR.VarDecl.type,
    hh, index] at hv

example : ¬ roots.zeroFuel ≤ 2 := by decide
example : ¬ roots.IndexAgrees ({ program := default } : P4bloIR.Index) := by
  intro h
  have bad := h.1.1
  simp [P4bloIR.FieldLaws.Declared] at bad
example : ¬ RootDeclares roots ({ block := modes.scope.block } : P4bloIR.BlockScope) := by
  intro h
  obtain ⟨decl, hd, _, _⟩ := h .here
  simp [P4bloIR.BlockScope.var?, Slot.name] at hd

def directionRoots : Layout := .cons "wide" (.scalar (.bits 65))
  (.cons "flag" (.scalar .boolean) .nil)
def directionModes (mode : Scalar.Mode) : Modes directionRoots := .cons mode (.cons .local .nil)
def directionIndex (mode : Scalar.Mode) : P4bloIR.Index :=
  { program := default,
    scopes := ({} : Std.HashMap String P4bloIR.BlockScope).insert "fields" (directionModes mode).scope }

theorem all_directions_initialized (mode : Scalar.Mode) : ∃ frame,
    P4bloIR.Frame.forBlock (directionIndex mode) (directionModes mode).scope.block = .ok frame ∧
    frame.scope = (directionModes mode).scope ∧ P4bloIR.ScalarStatements.BlockFrame frame ∧
    FrameMatches directionRoots.zero frame := by
  obtain ⟨frame, he, hs, hb, hm, _⟩ := (directionModes mode).initialize (directionIndex mode)
    (directionModes mode).scope.block (by simp [directionIndex, Modes.scope])
    (by exact ⟨by decide, by decide, by simp [directionRoots, Layout.LocallyWellFormed,
      Shape.LocallyWellFormed]⟩)
    (by trivial) (by simp [directionRoots, directionIndex, Layout.zeroFuel, Shape.zeroFuel])
  exact ⟨frame, he, hs, hb, hm⟩

def run : IO Unit := do
  unless roots.zero.toValues == expectedValues && roots.zero.validities == [false, false] do
    throw (IO.userError "independent source zero store/validity")
  unless (match P4bloIR.Value.zeroWith actualIndex 2 headers.toIR with
      | .error message => message == "type nesting deeper than the number of declared types"
      | .ok _ => false) do
    throw (IO.userError "forwarding header fuel boundary")
  let frame ← IO.ofExcept (P4bloIR.Frame.forBlock actualIndex modes.scope.block)
  for (name, expected) in ["hdr", "meta", "route", "scratch"].zip expectedValues do
    unless frame.read? name == some expected do
      throw (IO.userError s!"real-built forward initial {name}")
  unless frame.vars.size == 4 && frame.read? "observer" == none &&
      frame.action.isNone && frame.actionVars.isNone do
    throw (IO.userError "fully modeled forward scope contents")
  let extra ← IO.ofExcept (P4bloIR.Frame.forBlock extraIndex modes.scope.block)
  for (name, expected) in ["hdr", "meta", "route", "scratch"].zip expectedValues do
    unless extra.read? name == some expected do
      throw (IO.userError s!"extra scope preserves modeled initial {name}")
  unless extra.vars.size == 6 && extra.read? "observer" == some (.bits ⟨65, 0, by decide⟩) &&
      extra.read? "unrelated" == some (.bool false) && extra.action.isNone && extra.actionVars.isNone do
    throw (IO.userError "explicit successful extras")
  unless (match P4bloIR.Frame.forBlock failingIndex modes.scope.block with
      | .error message => message == "unknown header type 'Absent'"
      | .ok _ => false) do
    throw (IO.userError "extra initializer failure is preserved")
  for mode in [Scalar.Mode.local, .param .none, .param .in, .param .out, .param .inout] do
    let initialized ← IO.ofExcept (P4bloIR.Frame.forBlock (directionIndex mode) (directionModes mode).scope.block)
    unless initialized.read? "wide" == some (.bits ⟨65, 0, by decide⟩) &&
        initialized.read? "flag" == some (.bool false) && initialized.vars.size == 2 &&
        initialized.action.isNone && initialized.actionVars.isNone do
      throw (IO.userError "all modes initialize independent zero values")
  IO.println "Actual-built forward source frames, exact modeled coverage, extras and all directions passed"

end P4blo.InitialFrameTests
