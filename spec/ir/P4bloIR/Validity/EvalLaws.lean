import P4bloIR.Validity.FrameLaws
import P4bloIR.FieldLaws

/-!
# Expressions and lvalues do not get stuck

On a well-formed run, evaluating a typed expression leaves the run as it
was and gives a value of the expression's type, or stops with
`PacketTooShort` when a `lookahead` runs past the packet. Reading a typed
lvalue does the same; writing a value of its type changes only the frame,
which stays well formed; resolving it gives an lvalue of the same type.
-/

namespace P4bloIR.Validity

open Std (HashMap)
open ScalarTyping (run_bind run_pure run_map)

/-- A fault that leaves the run as it was: running out of packet. -/
def Short (r : Run) (f : Fault) (r' : Run) : Prop := r' = r ∧ f = .parse "PacketTooShort"

theorem RunOk.frame (hr : RunOk G r) : RunOk G { r with frame := f } :=
  ⟨hr.index, hr.packet, hr.emitter, hr.entries, hr.externs⟩

theorem run_with_frame_self (r : Run) : { r with frame := r.frame } = r := rfl

-- ---------------------------------------------------------------------------
-- Primitive reads
-- ---------------------------------------------------------------------------

theorem readVar_run (h : r.frame.read? x = some v) : (readVar x).run r = (.ok v, r) := by
  simp [readVar, run_bind, h]

theorem fieldOf_run (G : Global) (hr : r.index = G.idx) (hv : ValueHas G.idx v bt)
    (hf : fieldType? G.idx bt f = some t) :
    ∃ fv, (fieldOf v f).run r = (.ok fv, r) ∧ ValueHas G.idx fv t ∧
      ∀ nv, ValueHas G.idx nv t → ∃ v', (setField v f nv).run r = (.ok v', r) ∧
        ValueHas G.idx v' bt := by
  cases bt with
  | header n =>
    cases v with
    | header tn valid fs => ?_
    | _ => simp [ValueHas] at hv
    obtain ⟨rfl, hd, hh, hfs⟩ := valueHas_header.mp hv
    simp only [fieldType?, hh, Option.bind_some, Option.map_eq_some_iff] at hf
    obtain ⟨fl, hfl, rfl⟩ := hf
    obtain ⟨i, hi, ⟨fv, hfv, hft⟩, hset⟩ := hfs.find hfl
    have hidx : r.index.fieldIndex? tn f = some i := by
      simp [Index.fieldIndex?, Index.fields?, hr, hh, hi]
    refine ⟨fv, FieldLaws.fieldOf_pack (kind := .header) (valid := valid) r hidx hfv, hft, ?_⟩
    intro nv hnv
    refine ⟨_, FieldLaws.setField_pack (kind := .header) (valid := valid) r hidx, ?_⟩
    show ValueHas G.idx (.header tn valid _) (.header tn)
    rw [valueHas_header]
    exact ⟨rfl, hd, hh, hset nv hnv⟩
  | struct n =>
    cases v with
    | struct tn fs => ?_
    | _ => simp [ValueHas] at hv
    obtain ⟨rfl, sd, hs, hfs⟩ := valueHas_struct.mp hv
    simp only [fieldType?, hs, Option.bind_some, Option.map_eq_some_iff] at hf
    obtain ⟨fl, hfl, rfl⟩ := hf
    obtain ⟨i, hi, ⟨fv, hfv, hft⟩, hset⟩ := hfs.find hfl
    have hidx : r.index.fieldIndex? tn f = some i := by
      simp [Index.fieldIndex?, Index.fields?, hr, hs, G.structNotHeader hs, hi]
    refine ⟨fv, FieldLaws.fieldOf_pack (kind := .struct) (valid := false) r hidx hfv, hft, ?_⟩
    intro nv hnv
    refine ⟨_, FieldLaws.setField_pack (kind := .struct) (valid := false) r hidx, ?_⟩
    show ValueHas G.idx (.struct tn _) (.struct tn)
    rw [valueHas_struct]
    exact ⟨rfl, sd, hs, hset nv hnv⟩
  | _ => simp [fieldType?] at hf

theorem elementOf_run (G : Global) (hr : r.index = G.idx) (hes : ElemsHave G.idx h es)
    (hh : TyOk G.idx (.header h)) :
    ∃ v, (elementOf h es i).run r = (.ok v, r) ∧ ValueHas G.idx v (.header h) := by
  cases he : es[i]? with
  | some v => exact ⟨v, by simp [elementOf, he], hes.get he⟩
  | none =>
    obtain ⟨v, hv, ht⟩ := zero_ok G.laws hh
    refine ⟨v, ?_, ht⟩
    simp [elementOf, he, run_bind, liftExcept, Value.zeroHeader, hr, hv]

-- ---------------------------------------------------------------------------
-- Expressions
-- ---------------------------------------------------------------------------

@[simp] theorem expectStack_stack : expectStack (.stack h es n) = pure (h, es, n) := rfl
@[simp] theorem expectBits_bits : expectBits (.bits b) = pure b := rfl
@[simp] theorem expectBool_bool : expectBool (.bool b) = pure b := rfl
@[simp] theorem expectHeader_header : expectHeader (.header t valid fs) = pure (t, valid, fs) := rfl

/-- The post-condition of an evaluation: the run unchanged, a value of the
type. -/
def EvalQ (G : Global) (r : Run) (t : Ty) (v : Value) (r' : Run) : Prop :=
  r' = r ∧ ValueHas G.idx v t

section
variable {G : Global} {c : Ctx} {r : Run}

theorem evaluate_binary (ihl : Triple (evaluate l) r (EvalQ G r a) (Short r))
    (ihr : Triple (evaluate rr) r (EvalQ G r b) (Short r)) (ht : binaryType op a b = some t) :
    Triple (evaluate (.binary op l rr)) r (EvalQ G r t) (Short r) := by
  cases op with
  | and =>
    cases a <;> cases b <;> simp [binaryType] at ht
    subst ht
    simp only [evaluate]
    refine Triple.bind ihl ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bool bv =>
      simp only [expectBool_bool, pure_bind]
      cases bv
      · exact Triple.of_run rfl ⟨rfl, by simp⟩
      · simp only [↓reduceIte]
        refine Triple.bind ihr ?_
        rintro w r' ⟨rfl, hw⟩
        cases w with
        | bool => exact Triple.of_run rfl ⟨rfl, by simp⟩
        | _ => simp [ValueHas] at hw
    | _ => simp [ValueHas] at hv
  | or =>
    cases a <;> cases b <;> simp [binaryType] at ht
    subst ht
    simp only [evaluate]
    refine Triple.bind ihl ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bool bv =>
      simp only [expectBool_bool, pure_bind]
      cases bv
      · simp only [Bool.false_eq_true, ↓reduceIte]
        refine Triple.bind ihr ?_
        rintro w r' ⟨rfl, hw⟩
        cases w with
        | bool => exact Triple.of_run rfl ⟨rfl, by simp⟩
        | _ => simp [ValueHas] at hw
      · exact Triple.of_run rfl ⟨rfl, by simp⟩
    | _ => simp [ValueHas] at hv
  | eq =>
    simp only [binaryType] at ht
    split at ht
    · cases ht
      simp only [evaluate]
      refine Triple.bind ihl ?_
      rintro v r' ⟨rfl, -⟩
      refine Triple.bind ihr ?_
      rintro w r' ⟨rfl, -⟩
      exact Triple.of_run rfl ⟨rfl, by simp⟩
    · cases ht
  | ne =>
    simp only [binaryType] at ht
    split at ht
    · cases ht
      simp only [evaluate]
      refine Triple.bind ihl ?_
      rintro v r' ⟨rfl, -⟩
      refine Triple.bind ihr ?_
      rintro w r' ⟨rfl, -⟩
      exact Triple.of_run rfl ⟨rfl, by simp⟩
    · cases ht
  | _ =>
    cases a <;> cases b <;> simp only [binaryType, reduceCtorEq] at ht
    all_goals
      rename_i n m
      simp only [evaluate]
      refine Triple.bind ihl ?_
      rintro v r' ⟨rfl, hv⟩
      refine Triple.bind ihr ?_
      rintro w r' ⟨rfl, hw⟩
      cases v with
      | bits x =>
        cases w with
        | bits y =>
          simp only [valueHas_bits] at hv hw
          subst hv hw
          simp only [expectBits_bits, pure_bind]
          (try split at ht) <;> (try simp only [Option.some.injEq, reduceCtorEq] at ht) <;>
            (try subst ht) <;> (try exact absurd ht (by simp)) <;>
            exact Triple.of_run rfl ⟨rfl, by (try split) <;> simp_all [Bits.wrap]⟩
        | _ => simp [ValueHas] at hw
      | _ => simp [ValueHas] at hv

theorem castOk_cases (h : castOk a to = true) :
    (∃ n m, a = .bits n ∧ to = .bits m) ∨ (a = .boolean ∧ to = .bits 1) ∨
      (a = .bits 1 ∧ to = .boolean) := by
  unfold castOk at h
  split at h
  · exact .inl ⟨_, _, rfl, rfl⟩
  · exact .inr (.inl ⟨rfl, rfl⟩)
  · exact .inr (.inr ⟨rfl, rfl⟩)
  · cases h

theorem evaluate_cast (ih : Triple (evaluate e) r (EvalQ G r a) (Short r))
    (hok : castOk a to = true) : Triple (evaluate (.cast to e)) r (EvalQ G r to) (Short r) := by
  simp only [evaluate]
  refine Triple.bind ih ?_
  rintro v r' ⟨rfl, hv⟩
  rcases castOk_cases hok with ⟨n, m, rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩
  · cases v with
    | bits b => exact Triple.pure' ⟨rfl, valueHas_bits.mpr rfl⟩
    | _ => simp [ValueHas] at hv
  · cases v with
    | bool b => exact Triple.pure' ⟨rfl, valueHas_bits.mpr rfl⟩
    | _ => simp [ValueHas] at hv
  · cases v with
    | bits b => exact Triple.pure' ⟨rfl, by simp⟩
    | _ => simp [ValueHas] at hv

@[simp] theorem run_get : (get : M Run).run r = (.ok r, r) := rfl

theorem requirePacket_run (h : r.packet = some p) : requirePacket.run r = (.ok p, r) := by
  simp [requirePacket, run_bind, h]

theorem lookahead_ok (hr : RunOk G r) (hk : G.kind = .parser) (hty : TyOk G.idx ty)
    (hkind : readable ty = true) :
    Triple (lookaheadValue ty) r (EvalQ G r ty) (Short r) := by
  obtain ⟨p, hp⟩ := Option.isSome_iff_exists.mp (hr.packet hk)
  have hw : ∃ w, widthOf ty G.idx = .ok w ∧ ∀ raw, ∃ v, valueFromBits ty raw G.idx = .ok v ∧
      ValueHas G.idx v ty := by
    cases ty with
    | bits n =>
      exact ⟨n, widthOf_scalar (by simpa [scalarField] using tyOk_bits_pos hty),
        fun raw => ⟨_, rfl, valueHas_bits.mpr rfl⟩⟩
    | boolean => exact ⟨1, widthOf_scalar rfl, fun raw => ⟨_, rfl, by simp⟩⟩
    | header n =>
      unfold TyOk at hty
      obtain ⟨k, hk⟩ : ∃ k, fuel G.idx = k + 1 := ⟨fuel G.idx - 1, by have := fuel_pos G.idx; omega⟩
      rw [hk] at hty
      simp only [tyDeep] at hty
      split at hty
      · rename_i hd hh
        exact ⟨_, widthOf_header hh (G.headerScalar hh), fun raw => headerFromBits_ok hh (G.headerScalar hh)⟩
      · simp at hty
    | _ => simp [readable] at hkind
  obtain ⟨w, hwidth, hval⟩ := hw
  cases hpk : p.peek? w with
  | none =>
    refine Triple.of_run_error (f := .parse "PacketTooShort") (r' := r) ?_ ⟨rfl, rfl⟩
    simp [lookaheadValue, run_bind, requirePacket_run hp, hr.index, hwidth, hpk, liftExcept,
      throwParse]
    rfl
  | some raw =>
    obtain ⟨v, hv, ht⟩ := hval raw
    refine Triple.of_run (a := v) (r' := r) ?_ ⟨rfl, ht⟩
    simp [lookaheadValue, run_bind, requirePacket_run hp, hr.index, hwidth, hpk, liftExcept, hv]

theorem evaluate_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (he : ExprTyped c e t) : Triple (evaluate e) r (EvalQ G r t) (Short r) := by
  have hidx := hc.index
  induction he with
  | literal hl =>
    exact Triple.pure' ⟨rfl, hidx ▸ hl.value⟩
  | var hd =>
    obtain ⟨v, hv, ht⟩ := hf.read hd
    exact Triple.of_run (readVar_run hv) ⟨rfl, hidx ▸ ht⟩
  | member _ hfield ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    obtain ⟨fv, hfv, ht, -⟩ := fieldOf_run G hr.index hv (hidx ▸ hfield)
    exact Triple.of_run hfv ⟨rfl, ht⟩
  | index hb _ ihb ihi =>
    have hty := stack_header_tyOk (hc.exprTy hb)
    simp only [evaluate]
    refine Triple.bind ihb ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | stack h es next =>
      obtain ⟨rfl, -, hes⟩ := valueHas_stack.mp hv
      simp only [expectStack_stack, pure_bind]
      refine Triple.bind ihi ?_
      rintro iv r' ⟨rfl, hiv⟩
      cases iv with
      | bits ib =>
        simp only [expectBits_bits, pure_bind]
        obtain ⟨ev, hev, ht⟩ := elementOf_run G hr.index hes hty
        exact Triple.of_run hev ⟨rfl, ht⟩
      | _ => simp [ValueHas] at hiv
    | _ => simp [ValueHas] at hv
  | lastIndex _ _ ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | stack =>
      simp only [expectStack_stack, pure_bind]
      exact Triple.pure' ⟨rfl, valueHas_bits.mpr rfl⟩
    | _ => simp [ValueHas] at hv
  | not _ ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bool => exact Triple.of_run rfl ⟨rfl, by simp⟩
    | _ => simp [ValueHas] at hv
  | complement _ ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bits => exact Triple.of_run rfl ⟨rfl, by simp_all [Bits.wrap]⟩
    | _ => simp [ValueHas] at hv
  | negate _ ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bits => exact Triple.of_run rfl ⟨rfl, by simp_all [Bits.wrap]⟩
    | _ => simp [ValueHas] at hv
  | binary _ _ ht ihl ihr => exact evaluate_binary ihl ihr ht
  | cast _ _ hok ih => exact evaluate_cast ih hok
  | slice _ hlo hhi ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bits b =>
      simp only [expectBits_bits, pure_bind]
      refine Triple.of_run (a := .bits (Bits.wrap _ (b.value >>> _))) (r' := r')
        (by simp [Nat.not_lt_of_ge hlo]; rfl) ⟨rfl, by simp [Bits.wrap]⟩
    | _ => simp [ValueHas] at hv
  | isValid _ ih =>
    simp only [evaluate]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | header => exact Triple.of_run rfl ⟨rfl, by simp⟩
    | _ => simp [ValueHas] at hv
  | mux _ _ _ ihc iha ihb =>
    simp only [evaluate]
    refine Triple.bind ihc ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bool bv =>
      simp only [expectBool_bool, pure_bind]
      cases bv
      · exact ihb
      · exact iha
    | _ => simp [ValueHas] at hv
  | lookahead hk hty hkind =>
    exact lookahead_ok hr (hc.kind ▸ hk) (hc.index ▸ hty) hkind

/-- An index evaluates to bits, or runs out of packet. -/
theorem idx_eval (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r) (hi : IdxOk c i) :
    Triple (evaluate i) r (fun v r' => r' = r ∧ ∃ b, v = .bits b) (Short r) := by
  rcases hi with ⟨w, he⟩ | ⟨w, v, rfl⟩
  · refine Triple.mono (evaluate_ok hc hf hr he) ?_ (fun _ _ h => h)
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bits b => exact ⟨rfl, b, rfl⟩
    | _ => simp [ValueHas] at hv
  · exact Triple.pure' ⟨rfl, _, rfl⟩

theorem readLValue_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hl : LvOk c lv t) : Triple (readLValue lv) r (EvalQ G r t) (Short r) := by
  have hidx := hc.index
  induction hl with
  | var hd =>
    obtain ⟨v, hv, ht⟩ := hf.read hd
    exact Triple.of_run (readVar_run hv) ⟨rfl, hidx ▸ ht⟩
  | member _ hfield ih =>
    simp only [readLValue]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    obtain ⟨fv, hfv, ht, -⟩ := fieldOf_run G hr.index hv (hidx ▸ hfield)
    exact Triple.of_run hfv ⟨rfl, ht⟩
  | index hb hi ih =>
    have hty := stack_header_tyOk (hc.lvTy hb)
    simp only [readLValue]
    refine Triple.bind ih ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | stack h es next =>
      obtain ⟨rfl, -, hes⟩ := valueHas_stack.mp hv
      simp only [expectStack_stack, pure_bind]
      refine Triple.bind (idx_eval hc hf hr hi) ?_
      rintro iv r' ⟨rfl, b, rfl⟩
      simp only [expectBits_bits, pure_bind]
      obtain ⟨ev, hev, ht⟩ := elementOf_run G hr.index hes hty
      exact Triple.of_run hev ⟨rfl, ht⟩
    | _ => simp [ValueHas] at hv

/-- What a write leaves: the run with a new frame of the same context. -/
def WriteQ (c : Ctx) (r : Run) (_ : Unit) (r' : Run) : Prop :=
  ∃ f', r' = { r with frame := f' } ∧ FrameOk c f'

theorem writeVar_run (h : r.frame.write? x v = some f') :
    (writeVar x v).run r = (.ok (), { r with frame := f' }) := by
  simp [writeVar, run_bind, h, setFrame]
  rfl

theorem writeLValue_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hl : LvOk c lv t) (hv : ValueHas G.idx v t) :
    Triple (writeLValue lv v) r (WriteQ c r) (Short r) := by
  have hidx := hc.index
  induction hl generalizing v with
  | var hd =>
    obtain ⟨f', hw, hf'⟩ := hf.write hd (hidx ▸ hv)
    exact Triple.of_run (writeVar_run hw) ⟨f', rfl, hf'⟩
  | member _ hfield ih =>
    simp only [writeLValue]
    refine Triple.bind (readLValue_ok hc hf hr (by assumption)) ?_
    rintro cv r' ⟨rfl, hcv⟩
    obtain ⟨-, -, -, hset⟩ := fieldOf_run G hr.index hcv (hidx ▸ hfield)
    obtain ⟨cv', hcv', ht'⟩ := hset v hv
    refine Triple.bind (Triple.of_run hcv' (Q := fun a r'' => r'' = r' ∧ a = cv') ⟨rfl, rfl⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    exact ih ht'
  | index hb hi ih =>
    rename_i base h n i
    simp only [writeLValue]
    refine Triple.bind (readLValue_ok hc hf hr hb) ?_
    rintro sv r' ⟨rfl, hsv⟩
    cases sv with
    | stack h' es next =>
      obtain ⟨rfl, hlen, hes⟩ := valueHas_stack.mp hsv
      simp only [expectStack_stack, pure_bind]
      refine Triple.bind (idx_eval hc hf hr hi) ?_
      rintro iv r' ⟨rfl, b, rfl⟩
      simp only [expectBits_bits, pure_bind]
      split
      · cases v with
        | header ht valid fs =>
          simp only [expectHeader_header, pure_bind]
          apply ih
          rw [valueHas_stack]
          exact ⟨rfl, by simp [hlen], hes.set hv⟩
        | _ => simp [ValueHas] at hv
      · exact Triple.pure' ⟨_, rfl, hf⟩
    | _ => simp [ValueHas] at hsv

theorem resolveLValue_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hl : LvOk c lv t) :
    Triple (resolveLValue lv) r (fun lv' r' => r' = r ∧ LvOk c lv' t) (Short r) := by
  induction hl with
  | var hd => exact Triple.pure' ⟨rfl, .var hd⟩
  | member _ hfield ih =>
    simp only [resolveLValue]
    refine Triple.bind ih ?_
    rintro lv' r' ⟨rfl, hl'⟩
    exact Triple.pure' ⟨rfl, .member hl' hfield⟩
  | index _ hi ih =>
    simp only [resolveLValue]
    refine Triple.bind ih ?_
    rintro lv' r' ⟨rfl, hl'⟩
    refine Triple.bind (idx_eval hc hf hr hi) ?_
    rintro iv r' ⟨rfl, b, rfl⟩
    simp only [expectBits_bits, pure_bind]
    exact Triple.pure' ⟨rfl, .index hl' (.inr ⟨_, _, rfl⟩)⟩

end

end P4bloIR.Validity
