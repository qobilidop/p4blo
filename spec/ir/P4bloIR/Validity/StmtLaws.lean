import P4bloIR.Validity.CallLaws

/-!
# Statements do not get stuck

The statement primitives of `P4bloIR.Exec` on typed input: validity bits,
push and pop, extract, advance, verify, emit, select and the revisit
rule. Each keeps the run and the frame well formed, and each fault is a
parser error the program declares.
-/

namespace P4bloIR.Validity

open Std (HashMap)
open ScalarTyping (run_bind run_pure run_map)

section
variable {G : Global} {c : Ctx} {r : Run}

theorem Triple.shortErr (hr : RunOk G r) (hf : FrameOk c r.frame) (h : Triple m r Q (Short r)) :
    Triple m r Q (ErrQ G c) := Triple.mono h (fun _ _ h => h) (fun _ _ h => Short.errQ hr hf h)

theorem Triple.evalErr (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (he : ExprTyped c e t) : Triple (evaluate e) r (EvalQ G r t) (ErrQ G c) :=
  Triple.shortErr hr hf (evaluate_ok hc hf hr he)

theorem documented (G : Global) (h : e ∈ coreErrors) : Documented G (.parse e) := ⟨e, rfl, G.core h⟩

-- ---------------------------------------------------------------------------
-- Validity bits, push and pop
-- ---------------------------------------------------------------------------

theorem setValidity_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hl : LValueTyped c lv (.header n)) :
    Triple (setValidity lv valid) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  unfold setValidity
  refine Triple.bind (Triple.shortErr hr hf (readLValue_ok hc hf hr hl.lvOk)) ?_
  rintro v r' ⟨rfl, hv⟩
  cases v with
  | header t vd fs =>
    simp only [expectHeader_header, pure_bind]
    refine Triple.mono (writeLValue_ok hc hf hr hl.lvOk ?_) (fun _ _ h => h.okQ hr)
      (fun _ _ h => Short.errQ hr hf h)
    rw [valueHas_header] at hv ⊢
    exact hv
  | _ => simp [ValueHas] at hv

theorem pushFront_ok (L : Build.IndexLaws p idx) (hv : ValueHas idx v (.stack h size))
    (hh : TyOk idx (.header h)) :
    ∃ v', pushFront v n idx = .ok v' ∧ ValueHas idx v' (.stack h size) := by
  cases v with
  | stack t es next =>
    obtain ⟨rfl, hlen, hes⟩ := valueHas_stack.mp hv
    obtain ⟨z, hz, hzt⟩ := zero_ok L hh
    refine ⟨_, by simp [pushFront, Value.expectStack, Value.zeroHeader, hz, bind, Except.bind,
      pure, Except.pure]; rfl, ?_⟩
    rw [valueHas_stack]
    refine ⟨rfl, ?_, (ElemsHave.replicate hzt).append hes.take⟩
    simp [List.length_take]; omega
  | _ => simp [ValueHas] at hv

theorem popFront_ok (L : Build.IndexLaws p idx) (hv : ValueHas idx v (.stack h size))
    (hh : TyOk idx (.header h)) :
    ∃ v', popFront v n idx = .ok v' ∧ ValueHas idx v' (.stack h size) := by
  cases v with
  | stack t es next =>
    obtain ⟨rfl, hlen, hes⟩ := valueHas_stack.mp hv
    obtain ⟨z, hz, hzt⟩ := zero_ok L hh
    refine ⟨_, by simp [popFront, Value.expectStack, Value.zeroHeader, hz, bind, Except.bind,
      pure, Except.pure]; rfl, ?_⟩
    rw [valueHas_stack]
    refine ⟨rfl, ?_, hes.drop.append (ElemsHave.replicate hzt)⟩
    simp [List.length_drop]; omega
  | _ => simp [ValueHas] at hv

-- ---------------------------------------------------------------------------
-- The packet
-- ---------------------------------------------------------------------------

theorem RunOk.packet' (hr : RunOk G r) : RunOk G { r with packet := some p } :=
  ⟨hr.index, fun _ => rfl, hr.emitter, hr.entries, hr.externs⟩

theorem packetRead_ok (hr : RunOk G r) (hk : G.kind = .parser) :
    Triple (packetRead n) r (fun _ r' => ∃ p', r' = { r with packet := some p' }) (Short r) := by
  obtain ⟨p, hp⟩ := Option.isSome_iff_exists.mp (hr.packet hk)
  unfold packetRead
  refine Triple.bind (Triple.of_run (requirePacket_run hp) (Q := fun a r' => r' = r ∧ a = p)
    ⟨rfl, rfl⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  split
  · rename_i raw p' _
    exact Triple.of_run rfl ⟨p', rfl⟩
  · exact Triple.throwParse' ⟨rfl, rfl⟩

/-- The header an lvalue of header type is filled from the packet. -/
theorem extractInto_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hk : G.kind = .parser) (hl : LValueTyped c lv (.header n)) :
    Triple (do
      let v ← readLValue lv
      let x ← expectHeader v
      match x with
      | (typeName, _, _) => do
        let w ← liftExcept (widthOf (.header typeName) G.idx)
        let raw ← packetRead w
        let h ← liftExcept (headerFromBits typeName raw G.idx)
        writeLValue lv h : M Unit) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  have hty := hc.lvTy hl.lvOk
  unfold TyOk at hty
  obtain ⟨k, hk'⟩ : ∃ k, fuel G.idx = k + 1 := ⟨fuel G.idx - 1, by have := fuel_pos G.idx; omega⟩
  rw [hk'] at hty
  simp only [tyDeep] at hty
  split at hty
  case h_2 => simp at hty
  rename_i hd hh
  refine Triple.bind (Triple.shortErr hr hf (readLValue_ok hc hf hr hl.lvOk)) ?_
  rintro v r' ⟨rfl, hv⟩
  cases v with
  | header t vd fs =>
    obtain ⟨rfl, -⟩ := valueHas_header.mp hv
    simp only [expectHeader_header, pure_bind]
    refine Triple.bind (Triple.liftExcept' (widthOf_header hh (G.headerScalar hh))
      (Q := fun a r'' => r'' = _ ∧ a = _) ⟨rfl, rfl⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    refine Triple.bind (Triple.shortErr hr hf (packetRead_ok hr hk)) ?_
    rintro raw _ ⟨p', rfl⟩
    obtain ⟨hv', hhv, hht⟩ := headerFromBits_ok (raw := raw) hh (G.headerScalar hh)
    refine Triple.bind (Triple.liftExcept' hhv (Q := fun a r'' => r'' = _ ∧ a = hv') ⟨rfl, rfl⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    exact Triple.mono (writeLValue_ok hc hf hr.packet' hl.lvOk hht) (fun _ _ h => h.okQ hr.packet')
      (fun _ _ h => Short.errQ hr.packet' hf h)
  | _ => simp [ValueHas] at hv

theorem extract_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StmtTyped c (.extract target)) :
    Triple (extract target) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  have hk : G.kind = .parser := by
    cases hs with
    | extractNext hk _ => exact hc.kind ▸ hk
    | extract hk _ _ => exact hc.kind ▸ hk
  obtain ⟨p, hp⟩ := Option.isSome_iff_exists.mp (hr.packet hk)
  unfold extract
  refine Triple.bind (Triple.of_run (requirePacket_run hp) (Q := fun a r' => r' = r ∧ a = p)
    ⟨rfl, rfl⟩) ?_
  rintro _ r' ⟨hr', rfl⟩
  subst hr'
  refine Triple.bind (Triple.getIndex' (Q := fun a r'' => r'' = _ ∧ a = G.idx) ⟨rfl, hr.index⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  cases hs with
  | extractNext _ hl =>
    have hty := stack_header_tyOk (hc.lvTy hl.lvOk)
    unfold TyOk at hty
    obtain ⟨k, hk'⟩ : ∃ k, fuel G.idx = k + 1 := ⟨fuel G.idx - 1, by have := fuel_pos G.idx; omega⟩
    rw [hk'] at hty
    simp only [tyDeep] at hty
    split at hty
    case h_2 => simp at hty
    rename_i hd hh
    simp only
    refine Triple.bind (Triple.shortErr hr hf (readLValue_ok hc hf hr hl.lvOk)) ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | stack t es next =>
      obtain ⟨rfl, hlen, hes⟩ := valueHas_stack.mp hv
      simp only [expectStack_stack, pure_bind]
      split
      · exact Triple.bind (P := fun _ _ => False)
          (Triple.throwParse' ⟨documented G (by simp [coreErrors]), hr, hf⟩) (fun _ _ h => h.elim)
      · refine Triple.bind (Triple.liftExcept' (widthOf_header hh (G.headerScalar hh))
          (Q := fun a r'' => r'' = _ ∧ a = _) ⟨rfl, rfl⟩) ?_
        rintro _ _ ⟨rfl, rfl⟩
        refine Triple.bind (Triple.shortErr hr hf (packetRead_ok hr hk)) ?_
        rintro raw _ ⟨p', rfl⟩
        obtain ⟨hv', hhv, hht⟩ := headerFromBits_ok (raw := raw) hh (G.headerScalar hh)
        refine Triple.bind (Triple.liftExcept' hhv (Q := fun a r'' => r'' = _ ∧ a = hv')
          ⟨rfl, rfl⟩) ?_
        rintro _ _ ⟨rfl, rfl⟩
        refine Triple.mono (writeLValue_ok hc hf hr.packet' hl.lvOk ?_)
          (fun _ _ h => h.okQ hr.packet') (fun _ _ h => Short.errQ hr.packet' hf h)
        rw [valueHas_stack]
        exact ⟨rfl, by simp [hlen], hes.set hht⟩
    | _ => simp [ValueHas] at hv
  | extract _ hnot hl =>
    cases target with
    | next s => exact absurd rfl (hnot s)
    | var x => exact extractInto_ok hc hf hr hk hl
    | member b f => exact extractInto_ok hc hf hr hk hl
    | index b i => exact extractInto_ok hc hf hr hk hl

theorem advance_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hk : G.kind = .parser) (he : ExprTyped c e (.bits 32)) :
    Triple (advance e) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  obtain ⟨p, hp⟩ := Option.isSome_iff_exists.mp (hr.packet hk)
  unfold advance
  refine Triple.bind (Triple.evalErr hc hf hr he) ?_
  rintro v r' ⟨rfl, hv⟩
  cases v with
  | bits b =>
    simp only [expectBits_bits, pure_bind]
    refine Triple.bind (Triple.of_run (requirePacket_run hp) (Q := fun a r'' => r'' = _ ∧ a = p)
      ⟨rfl, rfl⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    split
    · rename_i p' _
      exact Triple.of_run rfl ⟨hr.packet', hf⟩
    · exact Triple.throwParse' ⟨documented G (by simp [coreErrors]), hr, hf⟩
  | _ => simp [ValueHas] at hv

theorem verify_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (he : ExprTyped c e .boolean) (herr : err ∈ c.index.program.errors) :
    Triple (verify e err) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  have hdoc : Documented G (.parse err) := by
    refine ⟨err, rfl, ?_⟩
    rw [hc.index, G.laws.program] at herr
    exact herr
  unfold verify
  refine Triple.bind (Triple.evalErr hc hf hr he) ?_
  rintro v r' ⟨rfl, hv⟩
  cases v with
  | bool b =>
    simp only [expectBool_bool, pure_bind]
    cases b
    · exact Triple.throwParse' ⟨hdoc, hr, hf⟩
    · exact Triple.pure' ⟨hr, hf⟩
  | _ => simp [ValueHas] at hv

-- ---------------------------------------------------------------------------
-- Emit
-- ---------------------------------------------------------------------------

theorem RunOk.emitter' (hr : RunOk G r) : RunOk G { r with emitter := some e } :=
  ⟨hr.index, hr.packet, fun _ => rfl, hr.entries, hr.externs⟩

theorem requireEmitter_run (h : r.emitter = some e) : requireEmitter.run r = (.ok e, r) := by
  simp [requireEmitter, run_bind, h]

theorem headerToBits_ok (hs : ∀ fl ∈ fds, scalarField fl.type = true) (hfs : FieldsHave idx fds fs) :
    ∃ w v, headerToBits fs = .ok (w, v) := by
  suffices h : ∃ ws, fs.mapM fieldBits = .ok ws by
    obtain ⟨ws, hws⟩ := h
    exact ⟨(ws.map Prod.fst).sum, packFields ws,
      by simp [headerToBits, hws, bind, Except.bind, pure, Except.pure]⟩
  induction fds generalizing fs with
  | nil =>
    cases fs with
    | nil => exact ⟨[], rfl⟩
    | cons _ _ => simp [FieldsHave] at hfs
  | cons fl fds ih =>
    cases fs with
    | nil => simp [FieldsHave] at hfs
    | cons v vs =>
      rw [fieldsHave_cons] at hfs
      obtain ⟨ws, hws⟩ := ih (fun x hx => hs x (List.mem_cons_of_mem _ hx)) hfs.2
      have hsc := hs fl (by simp)
      have : ∃ wv, fieldBits v = .ok wv := by
        cases hty : fl.type <;> simp [scalarField, hty] at hsc <;> rw [hty] at hfs <;>
          cases v <;> simp [ValueHas] at hfs <;> exact ⟨_, rfl⟩
      obtain ⟨wv, hwv⟩ := this
      exact ⟨wv :: ws, by simp [List.mapM_cons, hwv, hws, bind, Except.bind, pure, Except.pure]⟩

/-- Emitting a typed header: its fields pack, and only the emitter changes. -/
theorem emitHeader_ok (hr : RunOk G r) (hk : G.kind = .deparser)
    (hv : ValueHas G.idx v (.header n)) :
    Triple (emitValue v) r (fun _ r' => RunOk G r' ∧ r'.frame = r.frame) (ErrQ G c) := by
  obtain ⟨e, he⟩ := Option.isSome_iff_exists.mp (hr.emitter hk)
  cases v with
  | header t valid fs =>
    obtain ⟨rfl, hd, hh, hfs⟩ := valueHas_header.mp hv
    simp only [emitValue]
    cases valid
    · exact Triple.pure' ⟨hr, rfl⟩
    · obtain ⟨w, val, hb⟩ := headerToBits_ok (G.headerScalar hh) hfs
      simp only [↓reduceIte]
      refine Triple.bind (Triple.liftExcept' hb (Q := fun a r' => r' = _ ∧ a = (w, val)) ⟨rfl, rfl⟩) ?_
      rintro _ _ ⟨rfl, rfl⟩
      simp only
      refine Triple.bind (Triple.of_run (requireEmitter_run he) (Q := fun a r' => r' = _ ∧ a = e)
        ⟨rfl, rfl⟩) ?_
      rintro _ _ ⟨rfl, rfl⟩
      exact Triple.of_run rfl ⟨hr.emitter', rfl⟩
  | _ => simp [ValueHas] at hv

theorem emitList_headers (hr : RunOk G r) (hk : G.kind = .deparser) (hes : ElemsHave G.idx h es) :
    Triple (emitList es) r (fun _ r' => RunOk G r' ∧ r'.frame = r.frame) (ErrQ G c) := by
  induction es generalizing r with
  | nil => exact Triple.pure' ⟨hr, rfl⟩
  | cons v vs ih =>
    rw [elemsHave_cons] at hes
    simp only [emitList]
    refine Triple.bind (emitHeader_ok hr hk hes.1) ?_
    rintro _ r' ⟨hr', hfr⟩
    exact Triple.mono (ih hr' hes.2) (fun _ _ h => ⟨h.1, h.2.trans hfr⟩) (fun _ _ h => h)

theorem emitValue_ok (hk : G.kind = .deparser) :
    ∀ (f : Nat) {v : Value} {t : Ty} {r : Run}, emittable G.idx f t = true → ValueHas G.idx v t →
      RunOk G r → Triple (emitValue v) r (fun _ r' => RunOk G r' ∧ r'.frame = r.frame) (ErrQ G c)
  | 0, _, _, _, he, _, _ => by simp [emittable] at he
  | f + 1, v, t, r, he, hv, hr => by
    cases t with
    | header n => exact emitHeader_ok hr hk hv
    | stack h size =>
      cases v with
      | stack t es next =>
        obtain ⟨rfl, -, hes⟩ := valueHas_stack.mp hv
        simp only [emitValue]
        exact emitList_headers hr hk hes
      | _ => simp [ValueHas] at hv
    | struct n =>
      cases v with
      | struct t fs =>
        obtain ⟨rfl, sd, hs, hfs⟩ := valueHas_struct.mp hv
        simp only [emittable, hs, List.all_eq_true] at he
        simp only [emitValue]
        have key : ∀ (fls : List Field) (fs : List Value) (r : Run),
            (∀ x ∈ fls, emittable G.idx f x.type = true) → FieldsHave G.idx fls fs → RunOk G r →
            Triple (emitList fs) r (fun _ r' => RunOk G r' ∧ r'.frame = r.frame) (ErrQ G c) := by
          intro fls
          induction fls with
          | nil =>
            intro fs r _ hfs hr
            cases fs with
            | nil => exact Triple.pure' ⟨hr, rfl⟩
            | cons _ _ => simp [FieldsHave] at hfs
          | cons fl fls ih =>
            intro fs r he hfs hr
            cases fs with
            | nil => simp [FieldsHave] at hfs
            | cons x xs =>
              rw [fieldsHave_cons] at hfs
              simp only [emitList]
              refine Triple.bind (emitValue_ok hk f (he fl (by simp)) hfs.1 hr) ?_
              rintro _ r' ⟨hr', hfr⟩
              exact Triple.mono (ih xs r' (fun y hy => he y (List.mem_cons_of_mem _ hy)) hfs.2 hr')
                (fun _ _ h => ⟨h.1, h.2.trans hfr⟩) (fun _ _ h => h)
        exact key sd.fields fs r he hfs hr
      | _ => simp [ValueHas] at hv
    | _ => simp [emittable] at he

-- ---------------------------------------------------------------------------
-- Select and the revisit rule
-- ---------------------------------------------------------------------------

theorem selectKeys_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hk : SelectKeysTyped c keys tys) :
    Triple (keys.mapM evaluate) r (fun vs r' => r' = r ∧ ValuesHave G.idx vs tys) (Short r) := by
  induction hk with
  | nil => exact Triple.pure' ⟨rfl, .nil⟩
  | cons he _ _ ih =>
    rw [List.mapM_cons]
    refine Triple.bind (evaluate_ok hc hf hr he) ?_
    rintro v r' ⟨rfl, hv⟩
    refine Triple.bind ih ?_
    rintro vs r' ⟨rfl, hvs⟩
    exact Triple.pure' ⟨rfl, .cons hv hvs⟩

theorem keySetMatches_ok (hks : KeySetTyped idx kt ks) (hv : ValueHas idx v kt) :
    ∃ b, (keySetMatches ks v).run r = (.ok b, r) := by
  cases hks with
  | exact _ => exact ⟨_, rfl⟩
  | masked hb hlv hlm =>
    cases kt <;> simp at hb
    cases v <;> simp [ValueHas] at hv
    cases hlv; cases hlm
    exact ⟨_, rfl⟩
  | range hb hlo hhi =>
    cases kt <;> simp at hb
    cases v <;> simp [ValueHas] at hv
    cases hlo; cases hhi
    exact ⟨_, rfl⟩
  | dontCare => exact ⟨_, rfl⟩

theorem allM_matches (hks : KeySetsTyped idx tys sets) (hvs : ValuesHave idx vs tys) :
    ∃ b, ((sets.zip vs).allM fun x => match x with | (ks, k) => keySetMatches ks k).run r =
      (.ok b, r) := by
  induction hks generalizing vs with
  | nil => exact ⟨true, by cases vs <;> rfl⟩
  | cons hks _ ih =>
    cases hvs with
    | cons hv hvs =>
      obtain ⟨b, hb⟩ := keySetMatches_ok (r := r) hks hv
      obtain ⟨b', hb'⟩ := ih hvs
      simp only [List.zip_cons_cons, List.allM]
      cases b
      · exact ⟨false, by simp [run_bind, hb]⟩
      · exact ⟨b', by simp [run_bind, hb, hb']⟩

theorem KeySetsTyped.length (h : KeySetsTyped idx tys sets) : sets.length = tys.length := by
  induction h with
  | nil => rfl
  | cons _ _ ih => simp [ih]

theorem select_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hk : SelectKeysTyped c keys tys)
    (hcases : ∀ cs ∈ cases, KeySetsTyped c.index tys cs.sets ∧ TargetOk c cs.target) :
    Triple (select keys cases) r (fun t r' => OkQ G c r' ∧ TargetOk c t) (ErrQ G c) := by
  unfold select
  refine Triple.bind (Triple.shortErr hr hf (selectKeys_ok hc hf hr hk)) ?_
  rintro vs r' ⟨hr', hvs⟩
  subst hr'
  have hvl := hvs.length
  refine Triple.bind (Triple.forIn'
    (I := fun rem acc r'' => OkQ G c r'' ∧ acc.1 = none ∧ ∀ cs ∈ rem, cs ∈ cases)
    (Q := fun acc r'' => OkQ G c r'' ∧ ∀ t, acc.1 = some t → TargetOk c t)
    ⟨⟨hr, hf⟩, rfl, fun _ h => h⟩ ?_ ?_) ?_
  · rintro cs css acc r'' ⟨hok, hacc, hin⟩
    obtain ⟨hsets, htarget⟩ := hcases cs (hin cs (by simp))
    have hlen : (cs.sets.length != vs.length) = false := by
      simp [hsets.length, hvl]
    simp only [hlen, Bool.false_eq_true, ↓reduceIte]
    obtain ⟨b, hb⟩ := allM_matches (r := r'') (hc.index ▸ hsets) hvs
    refine Triple.bind (Triple.of_run hb (Q := fun a r3 => OkQ G c r3 ∧ a = b) ⟨hok, rfl⟩) ?_
    rintro bb r3 ⟨hok3, -⟩
    cases bb
    · exact Triple.pure' ⟨hok3, rfl, fun x hx => hin x (List.mem_cons_of_mem _ hx)⟩
    · exact Triple.pure' ⟨hok3, fun t ht => by cases ht; exact htarget⟩
  · rintro acc r'' ⟨hok, hacc, -⟩
    exact ⟨hok, fun t ht => by rw [hacc] at ht; cases ht⟩
  · rintro acc r'' ⟨hok, hq⟩
    simp only
    split
    · rename_i t ht
      exact Triple.pure' ⟨hok, hq t ht⟩
    · exact Triple.throwParse' ⟨documented G (by simp [coreErrors]), hok⟩

theorem enterState_ok (hr : RunOk G r) (hf : FrameOk c r.frame) (hk : G.kind = .parser) :
    Triple (enterState st) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  obtain ⟨p, hp⟩ := Option.isSome_iff_exists.mp (hr.packet hk)
  unfold enterState
  refine Triple.bind (Triple.of_run (a := r.frame.block) rfl (Q := fun a r' => r' = r ∧ True)
    ⟨rfl, trivial⟩) ?_
  rintro _ _ ⟨rfl, -⟩
  refine Triple.bind (Triple.of_run (requirePacket_run hp) (Q := fun a r' => r' = _ ∧ a = p)
    ⟨rfl, rfl⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  refine Triple.bind (Triple.get' (Q := fun a r' => r' = _ ∧ a = r') ⟨rfl, rfl⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  split
  · exact Triple.bind (P := fun _ _ => False)
      (Triple.throwParse' ⟨documented G (by simp [coreErrors]), hr, hf⟩) (fun _ _ h => h.elim)
  · exact Triple.of_run rfl ⟨⟨hr.index, hr.packet, hr.emitter, hr.entries, hr.externs⟩, hf⟩

end

end P4bloIR.Validity
