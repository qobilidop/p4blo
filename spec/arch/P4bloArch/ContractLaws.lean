import P4bloArch.Externs
import P4bloIR.Validity.Invariants
import P4bloIR.Validity.IndexLaws

/-!
# The reference extern families meet the contract of progress

`P4bloIR.Validity.progress` assumes an `ExternContract`: under some
invariant of the extern state, a call on a program instance with typed
arguments succeeds, keeps the invariant and returns values of the declared
types. This module proves one for the reference architecture's binding
(`P4bloArch.bind`, the five families of `P4bloArch.Externs`), so that the
premise is discharged whenever binding succeeds.

The invariant `Inv` says the model is the reference `model` and every
program instance holds a state its extern type's declaration fits
(`StateFits`): a register's cells have the width of the declared `T`, a
CRC's data width is the declared `D`, and each declared method has the
directions and types of its family's shape. `bind_inv` reads that back
from `Externs.bind`: `matchShape` checked each method against the shape
(`matchShape_ok`), `make` built the state from the same width bindings
(`stateFits_of`), and the extern-type rule makes method names distinct.
`call_ok` then runs each family's call on typed arguments.

What is not established: that binding succeeds. A valid program may declare
an extern type no family implements, or with a shape or constructor
arguments that do not fit; `bind` rejects it at load, before any packet
runs.
-/

namespace P4bloArch.Contract

open P4bloIR P4bloIR.Validity

-- ---------------------------------------------------------------------------
-- Loops
-- ---------------------------------------------------------------------------

/-- A loop whose every pass yields keeps a relation `R` from start to end,
and every element's fact `Q`, when later passes preserve it. -/
theorem forIn_ok {α β ε : Type} {l : List α} {f : α → β → Except ε (ForInStep β)} {b0 r : β}
    (R : β → β → Prop) (Q : α → β → Prop) (refl : ∀ b, R b b)
    (trans : ∀ a b c, R a b → R b c → R a c) (mono : ∀ x b b', Q x b → R b b' → Q x b')
    (step : ∀ x ∈ l, ∀ b s, f x b = .ok s → ∃ b', s = .yield b' ∧ R b b' ∧ Q x b')
    (h : forIn l b0 f = .ok r) : R b0 r ∧ ∀ x ∈ l, Q x r := by
  induction l generalizing b0 with
  | nil =>
    simp only [List.forIn_nil, pure, Except.pure, Except.ok.injEq] at h
    subst h
    exact ⟨refl _, by simp⟩
  | cons a as ih =>
    rw [List.forIn_cons] at h
    cases hf : f a b0 with
    | error e => rw [hf] at h; cases h
    | ok s =>
      obtain ⟨b1, rfl, hR, hQ⟩ := step a (by simp) b0 s hf
      rw [hf] at h
      obtain ⟨hR', hQ'⟩ := ih (fun x hx => step x (by simp [hx])) h
      refine ⟨trans _ _ _ hR hR', fun x hx => ?_⟩
      rcases List.mem_cons.mp hx with rfl | hx
      · exact mono _ _ _ hQ hR'
      · exact hQ' x hx

theorem bind_ok {ε α β : Type} {x : Except ε α} {f : α → Except ε β} {b : β}
    (h : (x >>= f) = .ok b) : ∃ a, x = .ok a ∧ f a = .ok b := by
  cases x with
  | error e => cases h
  | ok a => exact ⟨a, rfl, h⟩

theorem mem_zipIdx_of_mem {l : List α} {x : α} (h : x ∈ l) : ∃ i, (x, i) ∈ l.zipIdx := by
  obtain ⟨i, hi, rfl⟩ := List.getElem_of_mem h
  exact ⟨i, by simp [List.mem_zipIdx_iff_getElem?, List.getElem?_eq_getElem hi]⟩

-- ---------------------------------------------------------------------------
-- Width bindings
-- ---------------------------------------------------------------------------

/-- `b'` extends `b`: every bound width stays bound to the same value. -/
def Ext (b b' : Bindings) : Prop := ∀ (k : String) (v : Nat), b[k]? = some v → b'[k]? = some v

theorem Ext.refl (b : Bindings) : Ext b b := fun _ _ h => h
theorem Ext.trans {a b c : Bindings} (h1 : Ext a b) (h2 : Ext b c) : Ext a c :=
  fun k v h => h2 k v (h1 k v h)

/-- Width `w` stands for `n` under bindings `b`. -/
def WidthIs (b : Bindings) : Width → Nat → Prop
  | .fixed k, n => n = k
  | .var x, n => b[x]? = some n

theorem WidthIs.ext {b b' : Bindings} (h : WidthIs b w n) (e : Ext b b') : WidthIs b' w n := by
  cases w with
  | fixed k => exact h
  | var x => exact e x n h

theorem unify_ok {b b' : Bindings} (h : b.unify w ty where_ = .ok b') :
    Ext b b' ∧ ∃ n, ty = .bits n ∧ WidthIs b' w n := by
  unfold Bindings.unify at h
  cases ty with
  | bits n =>
    cases w with
    | fixed k =>
      simp only [Bind.bind, Except.bind] at h
      by_cases hk : n = k
      · subst hk; simp [pure, Except.pure] at h; subst h
        exact ⟨Ext.refl _, n, rfl, rfl⟩
      · simp [hk, throw, throwThe, MonadExceptOf.throw] at h
    | var x =>
      simp only at h
      cases hx : b[x]? with
      | none =>
        simp [hx, pure, Except.pure] at h; subst h
        refine ⟨fun k v hk => ?_, n, rfl, by simp [WidthIs]⟩
        rw [Std.HashMap.getElem?_insert]
        split
        · rename_i he; simp at he; subst he; rw [hx] at hk; cases hk
        · exact hk
      | some m =>
        by_cases hm : m = n
        · subst hm; simp [hx, pure, Except.pure] at h; subst h
          exact ⟨Ext.refl _, m, rfl, hx⟩
        · simp [hx, hm, throw, throwThe, MonadExceptOf.throw, Functor.map, Except.map] at h
  | _ => simp [throw, throwThe, MonadExceptOf.throw] at h

-- ---------------------------------------------------------------------------
-- Shape matching
-- ---------------------------------------------------------------------------

/-- A declared parameter fits its shape under `b`: same direction, bits of
the width the shape names. -/
def ParamFits (b : Bindings) (y : Param × ParamShape) : Prop :=
  y.1.direction = y.2.direction ∧ ∃ n, y.1.type = .bits n ∧ WidthIs b y.2.width n

/-- A declared return type fits its shape under `b`. -/
def RetFits (b : Bindings) : Option Width → Option Ty → Prop
  | none, none => True
  | some w, some t => ∃ n, t = .bits n ∧ WidthIs b w n
  | _, _ => False

/-- The method the shape names is declared and fits it under `b`. -/
def MethodFits (decl : ExternType) (b : Bindings) (x : String × MethodShape) : Prop :=
  ∃ m, decl.methods.find? (·.name == x.1) = some m ∧ m.params.length = x.2.params.length ∧
    (∀ y ∈ m.params.zip x.2.params, ParamFits b y) ∧ RetFits b x.2.returns m.returns

theorem ParamFits.ext (h : ParamFits b y) (e : Ext b b') : ParamFits b' y :=
  ⟨h.1, let ⟨n, hn, hw⟩ := h.2; ⟨n, hn, hw.ext e⟩⟩

theorem RetFits.ext (h : RetFits b w t) (e : Ext b b') : RetFits b' w t := by
  cases w <;> cases t <;> simp only [RetFits] at h ⊢
  obtain ⟨n, hn, hw⟩ := h
  exact ⟨n, hn, hw.ext e⟩

theorem MethodFits.ext (h : MethodFits decl b x) (e : Ext b b') : MethodFits decl b' x :=
  let ⟨m, hf, hl, hp, hr⟩ := h
  ⟨m, hf, hl, fun y hy => (hp y hy).ext e, hr.ext e⟩

theorem matchShape_ok (h : matchShape decl shape = .ok b) :
    (∀ m ∈ decl.methods, m.name ∈ shape.methods.map (·.1)) ∧
      ∀ x ∈ shape.methods, MethodFits decl b x := by
  unfold matchShape at h
  simp only at h
  split at h
  · cases h
  · obtain ⟨b1, h1, h⟩ := bind_ok h
    split at h
    · cases h
    rename_i hall
    obtain ⟨b2, h2, h⟩ := bind_ok h
    cases h
    refine ⟨?_, (forIn_ok Ext (fun x b => MethodFits decl b x) Ext.refl (fun _ _ _ => Ext.trans)
      (fun _ _ _ h e => MethodFits.ext h e) ?_ h2).2⟩
    · simp only [Bool.not_eq_true', Bool.and_eq_false_iff, List.all_eq_false, List.contains_iff_mem,
        ] at hall
      intro m hm
      by_cases hn : m.name ∈ shape.methods.map (·.1)
      · exact hn
      · exact absurd (Or.inl ⟨m.name, List.mem_map_of_mem (f := fun x => x.name) hm, hn⟩) hall
    · intro x _ b s hs
      obtain ⟨mn, ms⟩ := x
      simp only at hs
      split at hs
      · rename_i m hm
        split at hs
        · cases hs
        rename_i hlen
        obtain ⟨b3, h3, hs⟩ := bind_ok hs
        have L := forIn_ok Ext (fun y b => ParamFits b y.1) Ext.refl (fun _ _ _ => Ext.trans)
          (fun _ _ _ h e => ParamFits.ext h e) ?_ h3
        · have fits : ∀ b', Ext b3 b' → RetFits b' ms.returns m.returns →
              MethodFits decl b' (mn, ms) := fun b' e hr =>
            ⟨m, hm, by simpa using hlen, fun y hy => by
              obtain ⟨i, hi⟩ := mem_zipIdx_of_mem hy
              exact (L.2 _ hi).ext e, hr⟩
          split at hs
          · rename_i hr hr'
            cases hs
            exact ⟨b3, rfl, L.1, fits b3 (Ext.refl _) (by rw [hr, hr']; trivial)⟩
          · rename_i w ty hr hr'
            obtain ⟨b4, hu, hs⟩ := bind_ok hs
            cases hs
            obtain ⟨e, n, hn, hw⟩ := unify_ok hu
            exact ⟨b4, rfl, L.1.trans e, fits b4 e (by rw [hr, hr']; exact ⟨n, hn, hw⟩)⟩
          · cases hs
        · intro y _ b s hs
          split at hs
          · cases hs
          · rename_i hdir
            obtain ⟨b', hu, hs⟩ := bind_ok hs
            cases hs
            obtain ⟨e, n, hn, hw⟩ := unify_ok hu
            exact ⟨b', rfl, e, by simpa using hdir, n, hn, hw⟩
      · cases hs

theorem find_of_nodup {l : List Method} (hnd : (l.map (·.name)).Nodup) (hm : m ∈ l) :
    l.find? (·.name == m.name) = some m := by
  induction l with
  | nil => cases hm
  | cons a as ih =>
    simp only [List.map_cons, List.nodup_cons] at hnd
    rcases List.mem_cons.mp hm with rfl | hm
    · simp
    · have : (a.name == m.name) = false := by
        simp only [beq_eq_false_iff_ne]
        intro he; exact hnd.1 (he ▸ List.mem_map_of_mem hm)
      simp [this, ih hnd.2 hm]

/-- What a one-parameter method shape tells about a declared method. -/
theorem fits1 (h : MethodFits decl b (mn, ⟨[p0], r⟩)) (hnd : (decl.methods.map (·.name)).Nodup)
    (hm : m ∈ decl.methods) (hn : m.name = mn) :
    ∃ q0, m.params = [q0] ∧ ParamFits b (q0, p0) ∧ RetFits b r m.returns := by
  obtain ⟨m', hf, hl, hp, hr⟩ := h
  rw [← hn, find_of_nodup hnd hm] at hf
  cases hf
  match hq : m.params, hl with
  | [q0], _ => exact ⟨q0, rfl, hp _ (by simp [hq]), hr⟩

/-- What a two-parameter method shape tells about a declared method. -/
theorem fits2 (h : MethodFits decl b (mn, ⟨[p0, p1], r⟩)) (hnd : (decl.methods.map (·.name)).Nodup)
    (hm : m ∈ decl.methods) (hn : m.name = mn) :
    ∃ q0 q1, m.params = [q0, q1] ∧ ParamFits b (q0, p0) ∧ ParamFits b (q1, p1) ∧
      RetFits b r m.returns := by
  obtain ⟨m', hf, hl, hp, hr⟩ := h
  rw [← hn, find_of_nodup hnd hm] at hf
  cases hf
  match hq : m.params, hl with
  | [q0, q1], _ => exact ⟨q0, q1, rfl, hp _ (by simp [hq]), hp _ (by simp [hq]), hr⟩

-- ---------------------------------------------------------------------------
-- The families' states
-- ---------------------------------------------------------------------------

/-- A method's parameter directions and types, in order. -/
def sig (m : Method) : List (Direction × Ty) := m.params.map fun q => (q.direction, q.type)

/-- A method of a `register` of `bit<w>` cells. -/
def RegisterOk (w : Nat) (m : Method) : Prop :=
  (m.name = "read" ∧ sig m = [(.out, .bits w), (.in, .bits 32)] ∧ m.returns = none) ∨
    (m.name = "write" ∧ sig m = [(.in, .bits 32), (.in, .bits w)] ∧ m.returns = none)

/-- The method of a `counter`. -/
def CounterOk (m : Method) : Prop :=
  m.name = "count" ∧ sig m = [(.in, .bits 32)] ∧ m.returns = none

/-- The method of a stateless digest over `bit<w>` to `bit<out>`. -/
def ComputeOk (out w : Nat) (m : Method) : Prop :=
  m.name = "compute" ∧ sig m = [(.in, .bits w)] ∧ m.returns = some (.bits out)

/-- The state of an instance of `et` is one the reference model accepts
every declared method call on. -/
def StateFits (et : ExternType) (s : ExternState) : Prop :=
  (∃ w cells, s = .register w cells ∧ ∀ m ∈ et.methods, RegisterOk w m) ∨
    (∃ counts, s = .counter counts ∧ ∀ m ∈ et.methods, CounterOk m) ∨
    (s = .checksum16 ∧ ∀ m ∈ et.methods, ∃ w, ComputeOk 16 w m) ∨
    (∃ w, s = .crc16 w ∧ ∀ m ∈ et.methods, ComputeOk 16 w m) ∨
    (∃ w, s = .crc32 w ∧ ∀ m ∈ et.methods, ComputeOk 32 w m)

theorem stateFits_of {fam : String} {shape : Shape} {b : Bindings} {args : List Value}
    {st : ExternState} (hfam : (decl.name.splitOn ".").head! = fam)
    (hshape : shapeOf fam = some shape) (hm : matchShape decl shape = .ok b)
    (hmake : make decl b args = .ok st) (hnd : (decl.methods.map (·.name)).Nodup) :
    StateFits decl st := by
  obtain ⟨hA, hB⟩ := matchShape_ok hm
  unfold make at hmake
  rw [hfam] at hmake
  unfold shapeOf at hshape
  split at hshape <;> cases hshape
  · -- register
    have hread : MethodFits decl b ("read", { params := [⟨.out, .var "T"⟩, ⟨.in, .fixed 32⟩] }) :=
      hB _ (by simp [registerShape])
    have hwrite : MethodFits decl b ("write", { params := [⟨.in, .fixed 32⟩, ⟨.in, .var "T"⟩] }) :=
      hB _ (by simp [registerShape])
    split at hmake
    case h_1 size _ =>
      cases hT : b["T"]? with
      | none => rw [hT] at hmake; cases hmake
      | some w =>
        rw [hT] at hmake; cases hmake
        refine .inl ⟨w, _, rfl, fun m hm => ?_⟩
        have hn := hA m hm
        simp only [registerShape, List.map_cons, List.map_nil, List.mem_cons,
          List.not_mem_nil, or_false] at hn
        rcases hn with hn | hn
        · obtain ⟨q0, q1, hq, ⟨d0, n0, t0, w0⟩, ⟨d1, n1, t1, w1⟩, hr⟩ := fits2 hread hnd hm hn
          simp only [WidthIs] at w0 w1
          simp only at d0 d1 t0 t1
          rw [hT] at w0; cases w0; subst w1
          refine .inl ⟨hn, by simp [sig, hq, d0, t0, d1, t1], ?_⟩
          cases hret : m.returns <;> simp_all [RetFits]
        · obtain ⟨q0, q1, hq, ⟨d0, n0, t0, w0⟩, ⟨d1, n1, t1, w1⟩, hr⟩ := fits2 hwrite hnd hm hn
          simp only [WidthIs] at w0 w1
          simp only at d0 d1 t0 t1
          rw [hT] at w1; cases w1; subst w0
          refine .inr ⟨hn, by simp [sig, hq, d0, t0, d1, t1], ?_⟩
          cases hret : m.returns <;> simp_all [RetFits]
    all_goals first | (cases hmake; done) | (rename_i heq; exact absurd heq (by decide))
  · -- counter
    have hcount : MethodFits decl b ("count", { params := [⟨.in, .fixed 32⟩] }) :=
      hB _ (by simp [counterShape])
    split at hmake
    case h_2 size _ =>
      cases hmake
      refine .inr (.inl ⟨_, rfl, fun m hm => ?_⟩)
      have hn := hA m hm
      simp only [counterShape, List.map_cons, List.map_nil, List.mem_cons,
        List.not_mem_nil, or_false] at hn
      obtain ⟨q0, hq, ⟨d0, n0, t0, w0⟩, hr⟩ := fits1 hcount hnd hm hn
      simp only [WidthIs] at w0
      simp only at d0 t0
      subst w0
      refine ⟨hn, by simp [sig, hq, d0, t0], ?_⟩
      cases hret : m.returns <;> simp_all [RetFits]
    all_goals first | (cases hmake; done) | (rename_i heq; exact absurd heq (by decide))
  · -- checksum16
    have hc : MethodFits decl b ("compute", { params := [⟨.in, .var "D"⟩], returns := some (.fixed 16) }) :=
      hB _ (by simp [checksum16Shape])
    split at hmake
    case h_3 _ =>
      cases hmake
      refine .inr (.inr (.inl ⟨rfl, fun m hm => ?_⟩))
      have hn := hA m hm
      simp only [checksum16Shape, List.map_cons, List.map_nil, List.mem_cons,
        List.not_mem_nil, or_false] at hn
      obtain ⟨q0, hq, ⟨d0, n0, t0, w0⟩, hr⟩ := fits1 hc hnd hm hn
      simp only at d0 t0
      refine ⟨n0, hn, by simp [sig, hq, d0, t0], ?_⟩
      cases hret : m.returns <;> simp_all [RetFits, WidthIs]
    all_goals first | (cases hmake; done) | (rename_i heq; exact absurd heq (by decide))
  · -- crc16
    have hc : MethodFits decl b ("compute", { params := [⟨.in, .var "D"⟩], returns := some (.fixed 16) }) :=
      hB _ (by simp [crcShape])
    split at hmake
    case h_4 =>
      simp only at hmake
      cases hD : b["D"]? with
      | none => rw [hD] at hmake; cases hmake
      | some w =>
        simp only [hD] at hmake
        split at hmake
        · cases hmake
        simp only [pure, Except.pure, Except.ok.injEq] at hmake
        subst hmake
        refine .inr (.inr (.inr (.inl ⟨w, by simp, fun m hm => ?_⟩)))
        have hn := hA m hm
        simp only [crcShape, List.map_cons, List.map_nil, List.mem_cons,
          List.not_mem_nil, or_false] at hn
        obtain ⟨q0, hq, ⟨d0, n0, t0, w0⟩, hr⟩ := fits1 hc hnd hm hn
        simp only [WidthIs] at w0
        simp only at d0 t0
        rw [hD] at w0; cases w0
        refine ⟨hn, by simp [sig, hq, d0, t0], ?_⟩
        cases hret : m.returns <;> simp_all [RetFits, WidthIs]
    all_goals first | (cases hmake; done) | (rename_i heq; exact absurd heq (by decide))
  · -- crc32
    have hc : MethodFits decl b ("compute", { params := [⟨.in, .var "D"⟩], returns := some (.fixed 32) }) :=
      hB _ (by simp [crcShape])
    split at hmake
    case h_5 =>
      simp only at hmake
      cases hD : b["D"]? with
      | none => rw [hD] at hmake; cases hmake
      | some w =>
        simp only [hD] at hmake
        split at hmake
        · cases hmake
        simp only [pure, Except.pure, Except.ok.injEq] at hmake
        subst hmake
        refine .inr (.inr (.inr (.inr ⟨w, by simp, fun m hm => ?_⟩)))
        have hn := hA m hm
        simp only [crcShape, List.map_cons, List.map_nil, List.mem_cons,
          List.not_mem_nil, or_false] at hn
        obtain ⟨q0, hq, ⟨d0, n0, t0, w0⟩, hr⟩ := fits1 hc hnd hm hn
        simp only [WidthIs] at w0
        simp only at d0 t0
        rw [hD] at w0; cases w0
        refine ⟨hn, by simp [sig, hq, d0, t0], ?_⟩
        cases hret : m.returns <;> simp_all [RetFits, WidthIs]
    all_goals first | (cases hmake; done) | (rename_i heq; exact absurd heq (by decide))

-- ---------------------------------------------------------------------------
-- Binding
-- ---------------------------------------------------------------------------

/-- Extern instance names are distinct in a program `Index.build` accepts. -/
theorem instanceNames_nodup (h : Index.build p = .ok idx) :
    (p.externInstances.map (·.name)).Nodup := by
  rw [Build.index_eq] at h
  unfold Build.index at h
  simp only [Bind.bind, Except.bind] at h
  split at h
  · cases h
  rename_i r1 h1
  obtain ⟨hs, top1⟩ := r1
  simp only at h
  split at h
  · cases h
  rename_i r2 h2
  obtain ⟨ss, top2⟩ := r2
  simp only at h
  split at h
  · cases h
  rename_i r3 h3
  obtain ⟨es, top3⟩ := r3
  simp only at h
  split at h
  · cases h
  rename_i r4 h4
  obtain ⟨xts, top4⟩ := r4
  simp only at h
  split at h
  · cases h
  rename_i r5 h5
  obtain ⟨xis, top5⟩ := r5
  exact (Build.addAll_ok h5).nodup

/-- Binding left instance `inst` a state that fits its type's declaration. -/
def Bound (idx : Index) (inst : ExternInstance) (s : ExternState) : Prop :=
  ∃ decl, idx.externTypes[inst.externType]? = some decl ∧ StateFits decl s

theorem bindLoop {idx : Index} {l : List ExternInstance}
    {f : ExternInstance → Std.HashMap String ExternState →
      Except String (ForInStep (Std.HashMap String ExternState))}
    {m0 r : Std.HashMap String ExternState}
    (step : ∀ a ∈ l, ∀ m s, f a m = .ok s → ∃ st, s = .yield (m.insert a.name st) ∧ Bound idx a st)
    (nd : (l.map (·.name)).Nodup) (h : forIn l m0 f = .ok r) :
    (∀ k, k ∉ l.map (·.name) → r[k]? = m0[k]?) ∧
      ∀ a ∈ l, ∃ st, r[a.name]? = some st ∧ Bound idx a st := by
  induction l generalizing m0 with
  | nil =>
    simp only [List.forIn_nil, pure, Except.pure, Except.ok.injEq] at h
    subst h
    exact ⟨fun _ _ => rfl, by simp⟩
  | cons a as ih =>
    rw [List.forIn_cons] at h
    simp only [List.map_cons, List.nodup_cons] at nd
    cases hf : f a m0 with
    | error e => rw [hf] at h; cases h
    | ok s =>
      obtain ⟨st, rfl, hb⟩ := step a (by simp) m0 s hf
      rw [hf] at h
      obtain ⟨hk, ha⟩ := ih (fun x hx => step x (by simp [hx])) nd.2 h
      refine ⟨fun k hkn => ?_, fun x hx => ?_⟩
      · simp only [List.map_cons, List.mem_cons, not_or] at hkn
        rw [hk k hkn.2, Std.HashMap.getElem?_insert]
        have : (a.name == k) = false := by simp only [beq_eq_false_iff_ne]; exact fun h => hkn.1 h.symm
        simp [this]
      · rcases List.mem_cons.mp hx with rfl | hx
        · refine ⟨st, ?_, hb⟩
          rw [hk _ nd.1]
          simp
        · exact ha x hx

/-- The invariant of the reference extern state for program index `idx`:
the reference model, and every instance of the program bound to a state
its type's declaration fits. -/
def Inv (idx : Index) (e : Externs) : Prop :=
  e.model = model ∧ ∀ (n : String) (inst : ExternInstance) (et : ExternType),
    idx.externInstances[n]? = some inst → idx.externTypes[inst.externType]? = some et →
    ∃ s, e.instances[n]? = some s ∧ StateFits et s

/-- A successful binding of a valid program's instances satisfies `Inv`.

Premises: `Valid p idx` and `P4bloArch.bind idx = .ok e`. -/
theorem bind_inv {p : BlockLibrary} {idx : Index} {e : Externs} (hv : Valid p idx)
    (h : P4bloArch.bind idx = .ok e) : Inv idx e := by
  have L := Build.build_ok hv.index
  unfold P4bloArch.bind Externs.bind at h
  simp only at h
  obtain ⟨r, hr, h⟩ := bind_ok h
  cases h
  have nd := instanceNames_nodup hv.index
  rw [← L.program] at nd
  obtain ⟨-, hall⟩ := bindLoop (idx := idx) (by
    intro a _ m s hs
    split at hs
    · rename_i decl hdecl
      split at hs
      · rename_i shape hshape
        obtain ⟨b, hb, hs⟩ := bind_ok hs
        split at hs
        · cases hs
        obtain ⟨_, _, hs⟩ := bind_ok hs
        obtain ⟨st, hmk, hs⟩ := bind_ok hs
        cases hs
        have hnd : (decl.methods.map (·.name)).Nodup :=
          (hv.externTypes decl (L.externType _ decl hdecl).1).2.2.1.2
        exact ⟨st, rfl, decl, hdecl, stateFits_of rfl hshape hb hmk hnd⟩
      · cases hs
    · cases hs) nd hr
  refine ⟨rfl, fun n inst et hi het => ?_⟩
  obtain ⟨hmem, rfl⟩ := L.externInstance n inst hi
  rw [← L.program] at hmem
  obtain ⟨st, hst, decl, hdecl, hfit⟩ := hall inst hmem
  rw [het] at hdecl
  cases hdecl
  exact ⟨st, hst, hfit⟩

-- ---------------------------------------------------------------------------
-- Calls
-- ---------------------------------------------------------------------------

theorem sig1 (h : sig m = [(d0, t0)]) : ∃ q0 : Param, m.params = [q0] ∧ q0.direction = d0 ∧ q0.type = t0 := by
  unfold sig at h
  match hq : m.params, h with
  | [q0], h => simp at h; exact ⟨q0, rfl, h.1, h.2⟩

theorem sig2 (h : sig m = [(d0, t0), (d1, t1)]) :
    ∃ q0 q1 : Param, m.params = [q0, q1] ∧ q0.direction = d0 ∧ q0.type = t0 ∧
      q1.direction = d1 ∧ q1.type = t1 := by
  unfold sig at h
  match hq : m.params, h with
  | [q0, q1], h => simp at h; exact ⟨q0, q1, rfl, h.1.1, h.1.2, h.2.1, h.2.2⟩

theorem values1 (h : ValuesHave idx args [.bits w0]) : ∃ b0 : Bits, args = [.bits b0] ∧ b0.width = w0 := by
  match args, h with
  | [.bits b0], .cons h0 .nil => exact ⟨b0, rfl, h0⟩

theorem values2 (h : ValuesHave idx args [.bits w0, .bits w1]) :
    ∃ b0 b1 : Bits, args = [.bits b0, .bits b1] ∧ b0.width = w0 ∧ b1.width = w1 := by
  match args, h with
  | [.bits b0, .bits b1], .cons h0 (.cons h1 .nil) => exact ⟨b0, b1, rfl, h0, h1⟩

theorem Inv.update (h : Inv idx e) (hi : idx.externInstances[name]? = some inst)
    (het : idx.externTypes[inst.externType]? = some et) (hfit : StateFits et s') :
    Inv idx { e with instances := e.instances.insert name s' } := by
  refine ⟨h.1, fun n inst' et' hi' het' => ?_⟩
  by_cases hn : name = n
  · subst hn
    rw [hi] at hi'; cases hi'
    rw [het] at het'; cases het'
    exact ⟨s', by simp, hfit⟩
  · obtain ⟨s, hs, hf⟩ := h.2 n inst' et' hi' het'
    exact ⟨s, by simp [Std.HashMap.getElem?_insert, hn, hs], hf⟩

/-- A typed call on an instance whose state fits its type succeeds under the
reference model, keeps the state fitting, and returns typed values.

Premises: `Inv idx e`, the instance and its type indexed, the method
declared, and arguments of the parameters' types. This is exactly the
`call` obligation of `ExternContract`.

It does not say which values a call returns; the families' arithmetic is
pinned by vectors, not here. -/
theorem call_ok {idx : Index} (e : Externs) (name : String) (inst : ExternInstance) (et : ExternType)
    (meth : Method) (args : List Value) (hinv : Inv idx e)
    (hi : idx.externInstances[name]? = some inst) (het : idx.externTypes[inst.externType]? = some et)
    (hm : meth ∈ et.methods) (hargs : ValuesHave idx args (meth.params.map (·.type))) :
    ∃ e' res, e.call name meth.name args = .ok (e', res) ∧ Inv idx e' ∧
      ValuesHave idx res.outs ((meth.params.filter (isOut ·.direction)).map (·.type)) ∧
      ∀ t, meth.returns = some t → ∃ v, res.returns = some v ∧ ValueHas idx v t := by
  obtain ⟨s, hs, hfit⟩ := hinv.2 name inst et hi het
  have hmod := hinv.1
  have up := fun s' (h : StateFits et s') => hinv.update hi het h
  rcases hfit with ⟨w, cells, rfl, hms⟩ | ⟨counts, rfl, hms⟩ | ⟨rfl, hms⟩ | ⟨w, rfl, hms⟩ |
    ⟨w, rfl, hms⟩
  · rcases hms meth hm with ⟨hn, hsig, hret⟩ | ⟨hn, hsig, hret⟩
    · obtain ⟨q0, q1, hq, d0, t0, d1, t1⟩ := sig2 hsig
      rw [hq, List.map_cons, List.map_cons, List.map_nil, t0, t1] at hargs
      obtain ⟨b0, b1, rfl, -, -⟩ := values2 hargs
      refine ⟨_, { outs := [.bits (Bits.wrap w
          (if h : b1.value < cells.size then cells[b1.value] else 0))] }, ?_,
        up _ (.inl ⟨w, cells, rfl, hms⟩), ?_, by simp [hret]⟩
      · simp [Externs.call, hs, hmod, hn, model, call, Bind.bind, Except.bind, pure, Except.pure, ExternState.register]
      · simp only [hq, List.filter_cons, d0, d1, isOut, List.filter_nil]
        refine Forall2.cons ?_ .nil
        show ValueHas idx (.bits _) q0.type
        rw [t0]; exact rfl
    · obtain ⟨q0, q1, hq, d0, t0, d1, t1⟩ := sig2 hsig
      rw [hq, List.map_cons, List.map_cons, List.map_nil, t0, t1] at hargs
      obtain ⟨b0, b1, rfl, -, -⟩ := values2 hargs
      refine ⟨_, {}, ?_, up (.register w (if b0.value < cells.size then cells.set! b0.value b1.value
        else cells)) (.inl ⟨w, _, rfl, hms⟩), ?_, by simp [hret]⟩
      · simp [Externs.call, hs, hmod, hn, model, call, Bind.bind, Except.bind, pure, Except.pure, ExternState.register]
      · simp only [hq, List.filter_cons, d0, d1, isOut, List.filter_nil]
        exact .nil
  · obtain ⟨hn, hsig, hret⟩ := hms meth hm
    obtain ⟨q0, hq, d0, t0⟩ := sig1 hsig
    rw [hq, List.map_cons, List.map_nil, t0] at hargs
    obtain ⟨b0, rfl, -⟩ := values1 hargs
    refine ⟨_, {}, ?_, up (.counter (if h : b0.value < counts.size then
      counts.set b0.value (counts[b0.value] + 1) else counts)) (.inr (.inl ⟨_, rfl, hms⟩)), ?_,
      by simp [hret]⟩
    · simp [Externs.call, hs, hmod, hn, model, call, Bind.bind, Except.bind, pure, Except.pure, ExternState.counter]
    · simp only [hq, List.filter_cons, d0, isOut, List.filter_nil]
      exact .nil
  · obtain ⟨w, hn, hsig, hret⟩ := hms meth hm
    obtain ⟨q0, hq, d0, t0⟩ := sig1 hsig
    rw [hq, List.map_cons, List.map_nil, t0] at hargs
    obtain ⟨b0, rfl, -⟩ := values1 hargs
    refine ⟨_, { returns := some (.bits (Bits.wrap 16 (internetChecksum b0.width b0.value))) }, ?_,
      up .checksum16 (.inr (.inr (.inl ⟨rfl, hms⟩))), ?_, ?_⟩
    · simp [Externs.call, hs, hmod, hn, model, call, Bind.bind, Except.bind, pure, Except.pure, ExternState.checksum16]
    · simp only [hq, List.filter_cons, d0, isOut, List.filter_nil]
      exact .nil
    · intro t ht; rw [hret] at ht; cases ht; exact ⟨_, rfl, by simp [ValueHas, Bits.wrap]⟩
  · obtain ⟨hn, hsig, hret⟩ := hms meth hm
    obtain ⟨q0, hq, d0, t0⟩ := sig1 hsig
    rw [hq, List.map_cons, List.map_nil, t0] at hargs
    obtain ⟨b0, rfl, hw⟩ := values1 hargs
    refine ⟨_, { returns := some (.bits (Bits.wrap 16 (crc16 w b0.value))) }, ?_,
      up (.crc16 w) (.inr (.inr (.inr (.inl ⟨w, rfl, hms⟩)))), ?_, ?_⟩
    · simp [Externs.call, hs, hmod, hn, model, call, Bind.bind, Except.bind, pure, Except.pure, ExternState.crc16, hw]
    · simp only [hq, List.filter_cons, d0, isOut, List.filter_nil]
      exact .nil
    · intro t ht; rw [hret] at ht; cases ht; exact ⟨_, rfl, by simp [ValueHas, Bits.wrap]⟩
  · obtain ⟨hn, hsig, hret⟩ := hms meth hm
    obtain ⟨q0, hq, d0, t0⟩ := sig1 hsig
    rw [hq, List.map_cons, List.map_nil, t0] at hargs
    obtain ⟨b0, rfl, hw⟩ := values1 hargs
    refine ⟨_, { returns := some (.bits (Bits.wrap 32 (crc32 w b0.value))) }, ?_,
      up (.crc32 w) (.inr (.inr (.inr (.inr ⟨w, rfl, hms⟩)))), ?_, ?_⟩
    · simp [Externs.call, hs, hmod, hn, model, call, Bind.bind, Except.bind, pure, Except.pure, ExternState.crc32, hw]
    · simp only [hq, List.filter_cons, d0, isOut, List.filter_nil]
      exact .nil
    · intro t ht; rw [hret] at ht; cases ht; exact ⟨_, rfl, by simp [ValueHas, Bits.wrap]⟩

-- ---------------------------------------------------------------------------
-- The contract
-- ---------------------------------------------------------------------------

/-- The reference architecture's extern binding, as the contract the
progress proof assumes: its invariant is `Inv`, and `call_ok` discharges
the call obligation for all five families. -/
def contract (idx : Index) : ExternContract idx where
  inv := Inv idx
  call := call_ok

/-- A successful `P4bloArch.bind` of a valid program meets the extern
contract of progress.

Premises: `Valid p idx`, for instance from `check_sound`, and
`P4bloArch.bind idx = .ok e`.

Conclusion: `e` satisfies the invariant of `contract idx`, so `contract idx`
is an `ExternContract` whose invariant the run's externs satisfy, which is
the `externs` field of `RunOk`. Every call with typed arguments on an
instance of the program then succeeds, keeps the invariant and returns
values of the declared types.

It does not establish that `bind` succeeds: a program whose extern types
no family implements, or whose shapes or constructor arguments do not fit,
is valid but fails at load, before any packet runs. -/
theorem bind_contract {p : BlockLibrary} {idx : Index} {e : Externs} (hv : Valid p idx)
    (h : P4bloArch.bind idx = .ok e) : (contract idx).inv e :=
  bind_inv hv h

/-- The same as an existential over contracts: a bound reference extern
state satisfies some extern contract.

Premises and limits: those of `bind_contract`. -/
theorem bind_exists_contract {p : BlockLibrary} {idx : Index} {e : Externs} (hv : Valid p idx)
    (h : P4bloArch.bind idx = .ok e) : ∃ C : ExternContract idx, C.inv e :=
  ⟨contract idx, bind_contract hv h⟩

end P4bloArch.Contract
