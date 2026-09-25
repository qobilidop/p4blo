import P4bloIR.Validity.Invariants

/-!
# Values of well-formed types

The pure facts the progress proof needs about values: a well-formed type
has a zero value of that type, a header of scalar fields has a width and
reads back from bits as a header of its type, a field of a typed header or
struct is found where its declaration says and can be replaced by a value
of its type, and a typed header's fields pack into bits.
-/

namespace P4bloIR.Validity

open Std (HashMap)

-- ---------------------------------------------------------------------------
-- Unfolding the typing of values
-- ---------------------------------------------------------------------------

@[simp] theorem valueHas_bits : ValueHas idx (.bits b) (.bits n) ↔ b.width = n := by
  simp [ValueHas]
@[simp] theorem valueHas_bool : ValueHas idx (.bool b) .boolean := by simp [ValueHas]
@[simp] theorem valueHas_enum : ValueHas idx (.enum t m) (.enumType n) ↔ t = n := by
  simp [ValueHas]
@[simp] theorem valueHas_error : ValueHas idx (.error e) .error := by simp [ValueHas]
theorem valueHas_header : ValueHas idx (.header t valid fs) (.header n) ↔
    t = n ∧ ∃ h, idx.headerTypes[n]? = some h ∧ FieldsHave idx h.fields fs := by
  simp [ValueHas]
theorem valueHas_struct : ValueHas idx (.struct t fs) (.struct n) ↔
    t = n ∧ ∃ s, idx.structTypes[n]? = some s ∧ FieldsHave idx s.fields fs := by
  simp [ValueHas]
theorem valueHas_stack : ValueHas idx (.stack t es next) (.stack h size) ↔
    t = h ∧ es.length = size ∧ ElemsHave idx h es := by
  simp [ValueHas]
@[simp] theorem fieldsHave_nil : FieldsHave idx [] [] := by simp [FieldsHave]
@[simp] theorem fieldsHave_cons : FieldsHave idx (f :: fs) (v :: vs) ↔
    ValueHas idx v f.type ∧ FieldsHave idx fs vs := by simp [FieldsHave]
@[simp] theorem elemsHave_nil : ElemsHave idx h [] := by simp [ElemsHave]
@[simp] theorem elemsHave_cons : ElemsHave idx h (v :: vs) ↔
    ValueHas idx v (.header h) ∧ ElemsHave idx h vs := by simp [ElemsHave]

theorem FieldsHave.length (h : FieldsHave idx fs vs) : vs.length = fs.length := by
  induction fs generalizing vs with
  | nil => cases vs <;> simp_all [FieldsHave]
  | cons f fs ih => cases vs <;> simp_all [FieldsHave]

theorem ElemsHave.get {i : Nat} (h : ElemsHave idx hd es) (hi : es[i]? = some v) :
    ValueHas idx v (.header hd) := by
  induction es generalizing i with
  | nil => simp at hi
  | cons e es ih =>
    cases i with
    | zero => simp at hi; subst hi; exact (elemsHave_cons.mp h).1
    | succ i => exact ih (elemsHave_cons.mp h).2 (by simpa using hi)

theorem ElemsHave.set (h : ElemsHave idx hd es) (hv : ValueHas idx v (.header hd)) :
    ElemsHave idx hd (es.set i v) := by
  induction es generalizing i with
  | nil => simp
  | cons e es ih =>
    cases i with
    | zero => simp_all
    | succ i => simp only [List.set_cons_succ, elemsHave_cons]; exact ⟨(elemsHave_cons.mp h).1,
        ih (elemsHave_cons.mp h).2⟩

theorem ElemsHave.replicate (hv : ValueHas idx v (.header hd)) :
    ElemsHave idx hd (List.replicate n v) := by
  induction n with
  | zero => simp
  | succ n ih => simp [List.replicate_succ, hv, ih]

theorem ElemsHave.append (h1 : ElemsHave idx hd a) (h2 : ElemsHave idx hd b) :
    ElemsHave idx hd (a ++ b) := by
  induction a with
  | nil => simpa using h2
  | cons x xs ih => simp only [List.cons_append, elemsHave_cons] at *; exact ⟨h1.1, ih h1.2⟩

theorem ElemsHave.take (h : ElemsHave idx hd es) : ElemsHave idx hd (es.take n) := by
  induction es generalizing n with
  | nil => simp
  | cons e es ih => cases n <;> simp_all

theorem ElemsHave.drop (h : ElemsHave idx hd es) : ElemsHave idx hd (es.drop n) := by
  induction es generalizing n with
  | nil => simp
  | cons e es ih => cases n <;> simp_all

-- ---------------------------------------------------------------------------
-- Types
-- ---------------------------------------------------------------------------

theorem tyDeep_succ (h : tyDeep idx f t = true) : tyDeep idx (f + 1) t = true := by
  induction f generalizing t with
  | zero => simp [tyDeep] at h
  | succ f ih =>
    cases t with
    | bits n => simpa [tyDeep] using h
    | boolean => rfl
    | error => rfl
    | enumType n => simpa [tyDeep] using h
    | header n =>
      unfold tyDeep at h ⊢
      split at h
      · simp only [List.all_eq_true, Bool.and_eq_true] at h ⊢
        exact fun x hx => ⟨(h x hx).1, ih (h x hx).2⟩
      · simp at h
    | struct n =>
      unfold tyDeep at h ⊢
      split at h
      · simp only [List.all_eq_true] at h ⊢
        exact fun x hx => ih (h x hx)
      · simp at h
    | stack hd size =>
      simp only [tyDeep, Bool.and_eq_true] at h ⊢
      exact ⟨h.1, ih h.2⟩

theorem tyDeep_le (hle : f ≤ g) (h : tyDeep idx f t = true) : tyDeep idx g t = true := by
  induction hle with
  | refl => exact h
  | step _ ih => exact tyDeep_succ ih

theorem fuel_pos (idx : Index) : 2 ≤ fuel idx := by unfold fuel; omega

/-- The type of a field of a well-formed header or struct type is well
formed. -/
theorem fieldType_tyOk (ht : TyOk idx bt) (hf : fieldType? idx bt f = some t) : TyOk idx t := by
  unfold TyOk at *
  obtain ⟨k, hk⟩ : ∃ k, fuel idx = k + 1 := ⟨fuel idx - 1, by have := fuel_pos idx; omega⟩
  rw [hk] at ht
  apply tyDeep_le (f := k) (by omega)
  cases bt with
  | header n =>
    simp only [fieldType?, Option.map_eq_some_iff, Option.bind_eq_some_iff] at hf
    obtain ⟨fl, ⟨h, hh, hfl⟩, rfl⟩ := hf
    simp only [tyDeep, hh, List.all_eq_true, Bool.and_eq_true] at ht
    exact (ht fl (List.mem_of_find?_eq_some hfl)).2
  | struct n =>
    simp only [fieldType?, Option.map_eq_some_iff, Option.bind_eq_some_iff] at hf
    obtain ⟨fl, ⟨s, hs, hfl⟩, rfl⟩ := hf
    simp only [tyDeep, hs, List.all_eq_true] at ht
    exact ht fl (List.mem_of_find?_eq_some hfl)
  | _ => simp [fieldType?] at hf

theorem stack_header_tyOk (ht : TyOk idx (.stack h n)) : TyOk idx (.header h) := by
  unfold TyOk at *
  obtain ⟨k, hk⟩ : ∃ k, fuel idx = k + 1 := ⟨fuel idx - 1, by have := fuel_pos idx; omega⟩
  rw [hk] at ht ⊢
  simp only [tyDeep, Bool.and_eq_true] at ht
  exact tyDeep_succ ht.2

theorem tyOk_bits_pos (h : TyOk idx (.bits n)) : 0 < n := by
  unfold TyOk at h
  obtain ⟨k, hk⟩ : ∃ k, fuel idx = k + 1 := ⟨fuel idx - 1, by have := fuel_pos idx; omega⟩
  rw [hk] at h
  simpa [tyDeep] using h

theorem tyOk_bits (h : 0 < n) : TyOk idx (.bits n) := by
  unfold TyOk
  obtain ⟨k, hk⟩ : ∃ k, fuel idx = k + 1 := ⟨fuel idx - 1, by have := fuel_pos idx; omega⟩
  rw [hk]; simpa [tyDeep] using h

theorem tyOk_boolean : TyOk idx .boolean := by
  unfold TyOk
  obtain ⟨k, hk⟩ : ∃ k, fuel idx = k + 1 := ⟨fuel idx - 1, by have := fuel_pos idx; omega⟩
  rw [hk]; rfl

theorem tyOk_error : TyOk idx .error := by
  unfold TyOk
  obtain ⟨k, hk⟩ : ∃ k, fuel idx = k + 1 := ⟨fuel idx - 1, by have := fuel_pos idx; omega⟩
  rw [hk]; rfl

-- ---------------------------------------------------------------------------
-- Zero values
-- ---------------------------------------------------------------------------

theorem mapM_fields {g : Field → Except String Value} {fs : List Field}
    (h : ∀ fl ∈ fs, ∃ v, g fl = .ok v ∧ ValueHas idx v fl.type) :
    ∃ vs, fs.mapM g = .ok vs ∧ FieldsHave idx fs vs := by
  induction fs with
  | nil => exact ⟨[], rfl, by simp⟩
  | cons fl fs ih =>
    obtain ⟨v, hv, ht⟩ := h fl (by simp)
    obtain ⟨vs, hvs, hts⟩ := ih fun x hx => h x (List.mem_cons_of_mem _ hx)
    refine ⟨v :: vs, ?_, by simp [ht, hts]⟩
    simp [List.mapM_cons, hv, hvs, bind, Except.bind, pure, Except.pure]

theorem zeroWith_ok (L : Build.IndexLaws p idx) (h : tyDeep idx f t = true) :
    ∃ v, Value.zeroWith idx f t = .ok v ∧ ValueHas idx v t := by
  induction f generalizing t with
  | zero => simp [tyDeep] at h
  | succ f ih =>
    cases t with
    | bits n => exact ⟨_, rfl, by simp [Bits.wrap]⟩
    | boolean => exact ⟨_, rfl, by simp⟩
    | error => exact ⟨_, rfl, by simp [Value.noError]⟩
    | enumType n =>
      simp only [tyDeep] at h
      split at h
      · rename_i e he
        cases hm : e.members with
        | nil => simp [hm] at h
        | cons m ms => exact ⟨.enum n m, by simp [Value.zeroWith, he, hm, pure, Except.pure], by simp⟩
      · simp at h
    | header n =>
      simp only [tyDeep] at h
      split at h
      · rename_i hd hh
        simp only [List.all_eq_true, Bool.and_eq_true] at h
        obtain ⟨vs, hvs, hts⟩ := mapM_fields (g := fun fl => Value.zeroWith idx f fl.type)
          (fs := hd.fields) fun fl hfl => ih (h fl hfl).2
        have hname := (L.header n hd hh).2
        refine ⟨.header hd.name false vs, ?_, ?_⟩
        · simp [Value.zeroWith, hh, hvs, bind, Except.bind, pure, Except.pure]
        · rw [valueHas_header]; exact ⟨hname, hd, hh, hts⟩
      · simp at h
    | struct n =>
      simp only [tyDeep] at h
      split at h
      · rename_i sd hs
        simp only [List.all_eq_true] at h
        obtain ⟨vs, hvs, hts⟩ := mapM_fields (g := fun fl => Value.zeroWith idx f fl.type)
          (fs := sd.fields) fun fl hfl => ih (h fl hfl)
        have hname := (L.struct_ n sd hs).2
        refine ⟨.struct sd.name vs, ?_, ?_⟩
        · simp [Value.zeroWith, hs, hvs, bind, Except.bind, pure, Except.pure]
        · rw [valueHas_struct]; exact ⟨hname, sd, hs, hts⟩
      · simp at h
    | stack hd size =>
      simp only [tyDeep, Bool.and_eq_true] at h
      obtain ⟨e, he, ht⟩ := ih h.2
      refine ⟨.stack hd (List.replicate size e) 0, ?_, ?_⟩
      · simp [Value.zeroWith, he, bind, Except.bind, pure, Except.pure]
      · rw [valueHas_stack]; exact ⟨rfl, by simp, ElemsHave.replicate ht⟩

theorem zero_ok (L : Build.IndexLaws p idx) (h : TyOk idx t) :
    ∃ v, Value.zero t idx = .ok v ∧ ValueHas idx v t :=
  zeroWith_ok L h

-- ---------------------------------------------------------------------------
-- Widths and packet representations
-- ---------------------------------------------------------------------------

/-- The width of a scalar field's type. -/
def scalarWidth : Ty → Nat
  | .bits n => n
  | _ => 1

theorem foldlM_sum {g : Nat → Field → Except String Nat} {w : Field → Nat} {fs : List Field}
    (h : ∀ n fl, fl ∈ fs → g n fl = .ok (n + w fl)) (acc : Nat) :
    fs.foldlM g acc = .ok (acc + (fs.map w).sum) := by
  induction fs generalizing acc with
  | nil => simp [pure, Except.pure]
  | cons fl fs ih =>
    rw [List.foldlM_cons, h acc fl (by simp)]
    simp only [bind, Except.bind]
    rw [ih fun n x hx => h n x (List.mem_cons_of_mem _ hx)]
    simp [Nat.add_assoc]

/-- A header whose fields are scalar has a width. -/
theorem widthOf_header (hh : idx.headerTypes[n]? = some hd)
    (hs : ∀ fl ∈ hd.fields, scalarField fl.type = true) :
    widthOf (.header n) idx = .ok (hd.fields.map fun fl => scalarWidth fl.type).sum := by
  unfold widthOf
  obtain ⟨k, hk⟩ : ∃ k, idx.headerTypes.size + idx.structTypes.size + 2 = k + 2 :=
    ⟨idx.headerTypes.size + idx.structTypes.size, rfl⟩
  rw [hk]
  simp only [widthOfWith, hh]
  rw [foldlM_sum (w := fun fl => scalarWidth fl.type)]
  · simp
  · intro acc fl hfl
    have := hs fl hfl
    cases hty : fl.type <;> simp_all [scalarField, scalarWidth, Functor.map, Except.map, pure,
      Except.pure]

theorem widthOf_scalar (h : scalarField t = true) : widthOf t idx = .ok (scalarWidth t) := by
  unfold widthOf
  obtain ⟨k, hk⟩ : ∃ k, idx.headerTypes.size + idx.structTypes.size + 2 = k + 1 :=
    ⟨idx.headerTypes.size + idx.structTypes.size + 1, rfl⟩
  rw [hk]
  cases t <;> simp_all [scalarField, widthOfWith, scalarWidth, pure, Except.pure]

theorem mapM_widths {fs : List Field} (h : ∀ fl ∈ fs, scalarField fl.type = true) :
    fs.mapM (fun fl => widthOf fl.type idx) = .ok (fs.map fun fl => scalarWidth fl.type) := by
  induction fs with
  | nil => rfl
  | cons fl fs ih =>
    rw [List.mapM_cons, widthOf_scalar (h fl (by simp)), ih fun x hx => h x (List.mem_cons_of_mem _ hx)]
    rfl

theorem unpackFields_length : (unpackFields ws raw).length = ws.length := by
  induction ws with
  | nil => rfl
  | cons w ws ih => simp [unpackFields, ih]

theorem fieldsFromBits {fs : List Field} {us : List Nat}
    (h : ∀ fl ∈ fs, scalarField fl.type = true)
    (hl : us.length = fs.length) :
    FieldsHave idx fs ((fs.zip ((fs.map fun fl => scalarWidth fl.type).zip us)).map
      fun p => fieldFromBits p.1 p.2.1 p.2.2) := by
  induction fs generalizing us with
  | nil => simp
  | cons fl fs ih =>
    cases us with
    | nil => simp at hl
    | cons u us =>
      simp only [List.map_cons, List.zip_cons_cons, fieldsHave_cons]
      refine ⟨?_, ih (fun x hx => h x (List.mem_cons_of_mem _ hx)) (by simpa using hl)⟩
      have hs := h fl (by simp)
      unfold fieldFromBits
      cases hty : fl.type with
      | boolean =>
        rw [show (Ty.boolean == Ty.boolean) = true from rfl]
        simp
      | bits n =>
        rw [show (Ty.bits n == Ty.boolean) = false from rfl]
        simp [scalarWidth, Bits.wrap]
      | _ => simp [scalarField, hty] at hs

theorem headerFromBits_ok (hh : idx.headerTypes[n]? = some hd)
    (hs : ∀ fl ∈ hd.fields, scalarField fl.type = true) :
    ∃ v, headerFromBits n raw idx = .ok v ∧ ValueHas idx v (.header n) := by
  let ws := hd.fields.map fun fl => scalarWidth fl.type
  refine ⟨.header n true ((hd.fields.zip (ws.zip (unpackFields ws raw))).map
    fun p => fieldFromBits p.1 p.2.1 p.2.2), ?_, ?_⟩
  · unfold headerFromBits
    rw [hh]
    simp only [mapM_widths hs, bind, Except.bind, pure, Except.pure]
    rfl
  · rw [valueHas_header]
    exact ⟨rfl, hd, hh, fieldsFromBits hs (by simp [unpackFields_length, ws])⟩

-- ---------------------------------------------------------------------------
-- Fields
-- ---------------------------------------------------------------------------

/-- A declared field is found at its position, holds a value of its type,
and can be replaced by another. -/
theorem FieldsHave.find (h : FieldsHave idx fs vs) (hf : fs.find? (·.name == f) = some fl) :
    ∃ i, fs.findIdx? (·.name == f) = some i ∧ (∃ v, vs[i]? = some v ∧ ValueHas idx v fl.type) ∧
      ∀ nv, ValueHas idx nv fl.type → FieldsHave idx fs (vs.set i nv) := by
  induction fs generalizing vs with
  | nil => simp at hf
  | cons g gs ih =>
    cases vs with
    | nil => simp [FieldsHave] at h
    | cons v vs =>
      rw [fieldsHave_cons] at h
      by_cases hg : (g.name == f) = true
      · simp only [List.find?_cons, hg] at hf
        cases hf
        refine ⟨0, by simp [List.findIdx?_cons, hg], ⟨v, rfl, h.1⟩, ?_⟩
        intro nv hnv
        simp [hnv, h.2]
      · simp only [List.find?_cons, hg] at hf
        obtain ⟨i, hi, hv, hset⟩ := ih h.2 hf
        refine ⟨i + 1, ?_, by simpa using hv, ?_⟩
        · simp [List.findIdx?_cons, hg, hi]
        · intro nv hnv
          simp only [List.set_cons_succ, fieldsHave_cons]
          exact ⟨h.1, hset nv hnv⟩

end P4bloIR.Validity
