import P4bloIR.Validity.Check

/-!
# The checker is sound

`check_sound`: a program `Validity.check` accepts is `Valid`, with the index
the checker returns. The proof follows the checker function by function;
each lemma reads one function's success as the rule it decides.

Completeness is not proved: a program that is `Valid` might, in principle,
be rejected. The conformance test compares the checker with the Python
validator instead, which is what the checker has to agree with.
-/

namespace P4bloIR.Validity

open Std (HashMap)

-- ---------------------------------------------------------------------------
-- The check monad
-- ---------------------------------------------------------------------------

theorem bind_ok {x : Except ε α} {f : α → Except ε β} :
    x >>= f = .ok b ↔ ∃ a, x = .ok a ∧ f a = .ok b := by
  cases x <;> simp [bind, Except.bind]

theorem pure_ok : (pure a : Except ε α) = .ok b ↔ a = b := by
  simp [pure, Except.pure]

theorem ensure_ok : ensure b c path msg = .ok u ↔ b = true := by
  cases b
  · exact ⟨fun h => (nomatch h), fun h => (nomatch h)⟩
  · exact ⟨fun _ => rfl, fun _ => rfl⟩

theorem need_ok : need o c path msg = .ok a ↔ o = some a := by
  cases o
  · exact ⟨fun h => (nomatch h), fun h => (nomatch h)⟩
  · simp [need, pure, Except.pure]

@[simp] theorem fail_ok : fail c path msg = (.ok a : Chk α) ↔ False :=
  ⟨fun h => (nomatch h), fun h => h.elim⟩

theorem expect_ok : expect t ok w path = .ok t' ↔ ok t = true ∧ t' = t := by
  simp only [expect, bind_ok, ensure_ok, pure_ok]
  constructor
  · rintro ⟨_, h, rfl⟩; exact ⟨h, rfl⟩
  · rintro ⟨h, rfl⟩; exact ⟨(), h, rfl⟩

theorem each_go_ok {f : Nat → α → Chk Unit} :
    each.go f i l = .ok u → ∀ x ∈ l, ∃ j, f j x = .ok () := by
  induction l generalizing i with
  | nil => simp
  | cons y ys ih =>
    intro h x hx
    simp only [each.go, bind_ok] at h
    obtain ⟨_, hy, hr⟩ := h
    rcases List.mem_cons.mp hx with rfl | hx
    · exact ⟨i, hy⟩
    · exact ih hr x hx

theorem each_ok {f : Nat → α → Chk Unit} (h : each l f = .ok u) :
    ∀ x ∈ l, ∃ j, f j x = .ok () := each_go_ok h

theorem resolve_ok (h : resolve idx found n w path = .ok a) : found = some a := by
  unfold resolve at h
  split at h
  · simpa [pure_ok] using h
  · exfalso
    repeat' split at h
    all_goals simp at h

theorem resolveLocal_ok (h : resolveLocal c found el n w path = .ok a) : found = some a := by
  unfold resolveLocal at h
  split at h
  · simpa [pure_ok] using h
  · exfalso
    simp only at h
    repeat' split at h
    all_goals simp at h

theorem resolveVar_ok (h : resolveVar c x path = .ok d) : c.var? x = some d := by
  unfold resolveVar at h
  split at h
  · rename_i hd; simpa [pure_ok, hd] using h
  · exfalso
    simp only at h
    repeat' split at h
    all_goals simp at h

-- ---------------------------------------------------------------------------
-- Types and literals
-- ---------------------------------------------------------------------------

theorem checkType_ok (h : checkType idx path ty = .ok u) : TyOk idx ty := by
  simp only [checkType, bind_ok, ensure_ok] at h
  obtain ⟨_, _, h⟩ := h
  exact h

theorem checkLiteral_ok (h : checkLiteral idx path lit = .ok t) : LitTyped idx lit t := by
  cases lit with
  | bits w v =>
    simp only [checkLiteral, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, hw, _, hv, rfl⟩ := h
    exact .bits (by simpa using hw) (by simpa using hv)
  | boolean b =>
    simp only [checkLiteral, pure_ok] at h
    subst h; exact .boolean
  | enumMember t m =>
    simp only [checkLiteral, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨e, he, _, hm, rfl⟩ := h
    exact .enumMember (resolve_ok he) (by simpa using hm)
  | error n =>
    simp only [checkLiteral, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, hn, rfl⟩ := h
    exact .error (by simpa using hn)

theorem checkLiteralArgs_ok (h : checkLiteralArgs idx args params path code = .ok u) :
    LitArgsTyped idx args params := by
  simp only [checkLiteralArgs, bind_ok, ensure_ok] at h
  obtain ⟨_, hlen, h⟩ := h
  replace hlen : args.length = params.length := by simpa using hlen
  have hall := each_ok h
  clear h
  induction args generalizing params with
  | nil =>
    cases params with
    | nil => exact .nil
    | cons _ _ => simp at hlen
  | cons a as ih =>
    cases params with
    | nil => simp at hlen
    | cons q qs =>
      have ha := hall (a, q) (by simp)
      obtain ⟨j, ha⟩ := ha
      simp only [bind_ok, ensure_ok] at ha
      obtain ⟨t, ht, heq⟩ := ha
      have heq : t = q.type := of_decide_eq_true heq
      exact .cons (heq ▸ checkLiteral_ok ht)
        (ih (by simpa using hlen) fun x hx => hall x (List.mem_cons_of_mem _ hx))

-- ---------------------------------------------------------------------------
-- Expressions and lvalues
-- ---------------------------------------------------------------------------

theorem checkField_ok (h : checkField idx bt f path = .ok t) : fieldType? idx bt f = some t := by
  unfold checkField at h
  split at h
  · rename_i ht; simpa [pure_ok, ht] using h
  · split at h <;> simp at h

theorem checkExpr_ok (h : checkExpr c path e = .ok t) : ExprTyped c e t := by
  induction e generalizing path t with
  | literal lit =>
    simp only [checkExpr] at h
    exact .literal (checkLiteral_ok h)
  | var x =>
    simp only [checkExpr, bind_ok, pure_ok] at h
    obtain ⟨d, hd, rfl⟩ := h
    exact .var (resolveVar_ok hd)
  | member base f ih =>
    simp only [checkExpr, bind_ok] at h
    obtain ⟨bt, hb, hf⟩ := h
    exact .member (ih hb) (checkField_ok hf)
  | index base i ihb ihi =>
    simp only [checkExpr, bind_ok, expect_ok] at h
    obtain ⟨bt, hb, _, ⟨hs, -⟩, it, hi, _, ⟨hbits, -⟩, h⟩ := h
    cases bt <;> simp [isStack] at hs
    cases it <;> simp [isBits] at hbits
    simp only [pure_ok] at h
    subst h
    exact .index (ihb hb) (ihi hi)
  | lastIndex s ih =>
    simp only [checkExpr, bind_ok, ensure_ok, expect_ok, pure_ok] at h
    obtain ⟨_, hk, st, hs, _, ⟨hst, -⟩, rfl⟩ := h
    cases st <;> simp [isStack] at hst
    exact .lastIndex (by simpa using hk) (ih hs)
  | unary op e ih =>
    simp only [checkExpr, bind_ok] at h
    obtain ⟨a, ha, h⟩ := h
    cases op <;> simp only [expect_ok] at h <;> obtain ⟨hk, ht⟩ := h <;> subst ht
    · cases t <;> simp [isBoolean] at hk; exact .not (ih ha)
    · cases t <;> simp [isBits] at hk; exact .complement (ih ha)
    · cases t <;> simp [isBits] at hk; exact .negate (ih ha)
  | binary op l r ihl ihr =>
    simp only [checkExpr, bind_ok, need_ok] at h
    obtain ⟨a, ha, b, hb, h⟩ := h
    exact .binary (ihl ha) (ihr hb) h
  | cast to e ih =>
    simp only [checkExpr, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, hto, a, ha, _, hc, rfl⟩ := h
    exact .cast (ih ha) (checkType_ok hto) hc
  | slice e hi lo ih =>
    simp only [checkExpr, bind_ok, expect_ok] at h
    obtain ⟨a, ha, _, ⟨hb, -⟩, h⟩ := h
    cases a <;> simp [isBits] at hb
    simp only [bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, hr, rfl⟩ := h
    simp only [Bool.and_eq_true, decide_eq_true_eq] at hr
    exact .slice (ih ha) hr.1 hr.2
  | isValid e ih =>
    simp only [checkExpr, bind_ok, expect_ok, pure_ok] at h
    obtain ⟨a, ha, _, ⟨hh, -⟩, rfl⟩ := h
    cases a <;> simp [isHeader] at hh
    exact .isValid (ih ha)
  | mux cnd a b ihc iha ihb =>
    simp only [checkExpr, bind_ok, expect_ok, ensure_ok, pure_ok] at h
    obtain ⟨ct, hc, _, ⟨hct, -⟩, ta, ha, tb, hb, _, heq, rfl⟩ := h
    cases ct <;> simp [isBoolean] at hct
    have heq : ta = tb := of_decide_eq_true heq
    subst heq
    exact .mux (ihc hc) (iha ha) (ihb hb)
  | lookahead ty =>
    simp only [checkExpr, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, hk, _, hty, _, hkind, rfl⟩ := h
    refine .lookahead (by simpa using hk) (checkType_ok hty) ?_
    cases ty <;> simp_all [isBits, isBoolean, isHeader, readable]

theorem checkLValue_ok (h : checkLValue c path lv = .ok t) : LValueTyped c lv t := by
  induction lv generalizing path t with
  | var x =>
    simp only [checkLValue, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨d, hd, _, hw, rfl⟩ := h
    exact .var (resolveVar_ok hd) hw
  | member base f ih =>
    simp only [checkLValue, bind_ok] at h
    obtain ⟨bt, hb, hf⟩ := h
    exact .member (ih hb) (checkField_ok hf)
  | index base i ih =>
    simp only [checkLValue, bind_ok, expect_ok] at h
    obtain ⟨bt, hb, _, ⟨hs, -⟩, it, hi, _, ⟨hbits, -⟩, h⟩ := h
    cases bt <;> simp [isStack] at hs
    cases it <;> simp [isBits] at hbits
    simp only [pure_ok] at h
    subst h
    exact .index (ih hb) (checkExpr_ok hi)
  | next s _ => simp [checkLValue] at h

-- ---------------------------------------------------------------------------
-- Small namespaces and lists
-- ---------------------------------------------------------------------------

theorem contains_ne {m : HashMap String α} (h : m.contains k = true) : m[k]? ≠ none := by
  rw [Std.HashMap.contains_eq_isSome_getElem?] at h
  exact Option.isSome_iff_ne_none.mp h

theorem checkNames_go_ok (h : checkNames.go path what seen i names = .ok u) :
    (∀ n ∈ names, n ≠ "") ∧ names.Nodup ∧ ∀ n ∈ names, n ∉ seen := by
  induction names generalizing seen i with
  | nil => simp
  | cons n ns ih =>
    simp only [checkNames.go, bind_ok, ensure_ok] at h
    obtain ⟨_, he, _, hs, hr⟩ := h
    obtain ⟨h1, h2, h3⟩ := ih hr
    have hne : n ≠ "" := by
      intro hn; subst hn; simp at he
    have hns : n ∉ seen := by simpa using hs
    refine ⟨?_, ?_, ?_⟩
    · intro x hx
      rcases List.mem_cons.mp hx with rfl | hx
      · exact hne
      · exact h1 x hx
    · refine List.nodup_cons.mpr ⟨fun hm => h3 n hm (by simp), h2⟩
    · intro x hx
      rcases List.mem_cons.mp hx with rfl | hx
      · exact hns
      · exact fun hm => h3 x hx (by simp [hm])

theorem checkNames_ok (h : checkNames names path what = .ok u) : NamesOk names := by
  obtain ⟨h1, h2, _⟩ := checkNames_go_ok h
  exact ⟨h1, h2⟩

-- ---------------------------------------------------------------------------
-- Arguments
-- ---------------------------------------------------------------------------

theorem checkArgs_ok (h : checkArgs c args params path = .ok u) :
    ArgsTyped c args params ∧ noAlias args = true := by
  simp only [checkArgs, bind_ok, ensure_ok] at h
  obtain ⟨_, hlen, _, heach, hna⟩ := h
  replace hlen : args.length = params.length := by simpa using hlen
  refine ⟨?_, hna⟩
  have hall := each_ok heach
  clear heach hna
  induction args generalizing params with
  | nil =>
    cases params with
    | nil => exact .nil
    | cons _ _ => simp at hlen
  | cons a as ih =>
    cases params with
    | nil => simp at hlen
    | cons q qs =>
      obtain ⟨j, hj⟩ := hall (a, q) (by simp)
      refine .cons ?_ (ih (by simpa using hlen) fun x hx => hall x (List.mem_cons_of_mem _ hx))
      simp only at hj
      split at hj
      · rename_i hout
        simp only [bind_ok, ensure_ok] at hj
        obtain ⟨t, ht, heq⟩ := hj
        have heq := of_decide_eq_true heq
        subst heq
        exact .output hout (checkLValue_ok ht)
      · rename_i hout
        simp only [bind_ok, ensure_ok] at hj
        obtain ⟨t, ht, heq⟩ := hj
        have heq := of_decide_eq_true heq
        subst heq
        exact .input hout (checkExpr_ok ht)
      · simp at hj
      · simp at hj

-- ---------------------------------------------------------------------------
-- Statements
-- ---------------------------------------------------------------------------

theorem checkHit_ok (h : checkHit c path hit = .ok u) :
    ∀ lv, hit = some lv → LValueTyped c lv .boolean := by
  intro lv hlv
  subst hlv
  simp only [checkHit, bind_ok, expect_ok] at h
  obtain ⟨t, ht, _, ⟨hb, -⟩, -⟩ := h
  cases t <;> simp [isBoolean] at hb
  exact checkLValue_ok ht

theorem checkResult_ok (h : checkResult c path rt result = .ok u) : ResultTyped c rt result := by
  cases rt <;> cases result
  · exact .none
  · simp [checkResult] at h
  · simp [checkResult] at h
  · simp only [checkResult, bind_ok, ensure_ok] at h
    obtain ⟨t, ht, heq⟩ := h
    have heq := of_decide_eq_true heq
    subst heq
    exact .some (checkLValue_ok ht)

theorem allowed_extract (h : allowed k (.extract t) = true) : k = .parser := by
  cases k <;> simp_all [allowed]

mutual
theorem checkStmt_ok {c : Ctx} {path : String} : (s : Stmt) → checkStmt c path s = .ok u →
    StmtTyped c s
  | .assign target value, h => by
    simp only [checkStmt, bind_ok, ensure_ok] at h
    obtain ⟨_, _, tt, ht, vt, hv, heq⟩ := h
    have heq := of_decide_eq_true heq
    subst heq
    exact .assign (checkLValue_ok ht) (checkExpr_ok hv)
  | .conditional cnd yes no, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, _, ct, hc, _, ⟨hb, -⟩, _, hy, hn⟩ := h
    cases ct <;> simp [isBoolean] at hb
    exact .conditional (checkExpr_ok hc) (checkStmts_ok yes hy) (checkStmts_ok no hn)
  | .apply t hit, h => by
    simp only [checkStmt, bind_ok, ensure_ok] at h
    obtain ⟨_, hk, _, ha, tbl, htbl, hh⟩ := h
    exact .apply (by simpa [allowed] using hk) (by simpa using ha) (resolveLocal_ok htbl)
      (checkHit_ok hh)
  | .callAction a args, h => by
    simp only [checkStmt, bind_ok, ensure_ok] at h
    obtain ⟨_, hk, act, hact, hargs⟩ := h
    obtain ⟨ht, hna⟩ := checkArgs_ok hargs
    exact .callAction (by simpa [allowed] using hk) (resolveLocal_ok hact) ht hna
  | .callBlock b args, h => by
    simp only [checkStmt, bind_ok, ensure_ok] at h
    obtain ⟨_, _, _, ha, blk, hblk, _, hkind, hargs⟩ := h
    obtain ⟨ht, hna⟩ := checkArgs_ok hargs
    exact .callBlock (by simpa using ha) (resolve_ok hblk) (by simpa using hkind) ht hna
  | .callExtern inst m args result, h => by
    simp only [checkStmt, bind_ok, ensure_ok, need_ok] at h
    obtain ⟨_, _, i, hi, et, het, meth, hmeth, _, hargs, hres⟩ := h
    obtain ⟨ht, hna⟩ := checkArgs_ok hargs
    exact .callExtern (resolve_ok hi) (resolve_ok het) hmeth ht hna (checkResult_ok hres)
  | .setValid lv, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, _, t, ht, _, ⟨hh, -⟩, -⟩ := h
    cases t <;> simp [isHeader] at hh
    exact .setValid (checkLValue_ok ht)
  | .setInvalid lv, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, _, t, ht, _, ⟨hh, -⟩, -⟩ := h
    cases t <;> simp [isHeader] at hh
    exact .setInvalid (checkLValue_ok ht)
  | .push lv count, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, _, t, ht, _, ⟨hs, -⟩, hc⟩ := h
    cases t <;> simp [isStack] at hs
    exact .push (checkLValue_ok ht) (by simpa using hc)
  | .pop lv count, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, _, t, ht, _, ⟨hs, -⟩, hc⟩ := h
    cases t <;> simp [isStack] at hs
    exact .pop (checkLValue_ok ht) (by simpa using hc)
  | .extract target, h => by
    simp only [checkStmt, bind_ok, ensure_ok] at h
    obtain ⟨_, hk, ht⟩ := h
    have hpar : c.kind = .parser := allowed_extract hk
    clear hk
    cases target with
    | next st =>
      simp only [checkExtractTarget, bind_ok, expect_ok] at ht
      obtain ⟨t, ht, _, ⟨hs, -⟩, -⟩ := ht
      cases t <;> simp [isStack] at hs
      exact .extractNext hpar (checkLValue_ok ht)
    | var x =>
      simp only [checkExtractTarget, bind_ok, expect_ok] at ht
      obtain ⟨t, ht, _, ⟨hh, -⟩, -⟩ := ht
      cases t <;> simp [isHeader] at hh
      exact .extract hpar (by simp) (checkLValue_ok ht)
    | member b f =>
      simp only [checkExtractTarget, bind_ok, expect_ok] at ht
      obtain ⟨t, ht, _, ⟨hh, -⟩, -⟩ := ht
      cases t <;> simp [isHeader] at hh
      exact .extract hpar (by simp) (checkLValue_ok ht)
    | index b i =>
      simp only [checkExtractTarget, bind_ok, expect_ok] at ht
      obtain ⟨t, ht, _, ⟨hh, -⟩, -⟩ := ht
      cases t <;> simp [isHeader] at hh
      exact .extract hpar (by simp) (checkLValue_ok ht)
  | .advance e, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, hk, t, ht, _, ⟨hb, -⟩, -⟩ := h
    have hb := of_decide_eq_true hb
    subst hb
    exact .advance (by simpa [allowed] using hk) (checkExpr_ok ht)
  | .verify cnd err, h => by
    simp only [checkStmt, bind_ok, ensure_ok, expect_ok] at h
    obtain ⟨_, hk, t, ht, _, ⟨hb, -⟩, he⟩ := h
    cases t <;> simp [isBoolean] at hb
    exact .verify (by simpa [allowed] using hk) (checkExpr_ok ht) (by simpa using he)
  | .emit e, h => by
    simp only [checkStmt, bind_ok, ensure_ok] at h
    obtain ⟨_, hk, t, ht, he⟩ := h
    exact .emit (by simpa [allowed] using hk) (checkExpr_ok ht) he

theorem checkStmts_ok {c : Ctx} {path : String} {i : Nat} : (ss : List Stmt) →
    checkStmts c path i ss = .ok u → StmtsTyped c ss
  | [], _ => .nil
  | s :: ss, h => by
    simp only [checkStmts, bind_ok] at h
    obtain ⟨_, hs, hr⟩ := h
    exact .cons (checkStmt_ok s hs) (checkStmts_ok ss hr)
end

-- ---------------------------------------------------------------------------
-- Parser states
-- ---------------------------------------------------------------------------

theorem checkTarget_ok (h : checkTarget c path t = .ok u) : TargetOk c t := by
  cases t with
  | state n =>
    simp only [checkTarget, bind_ok] at h
    obtain ⟨_, hs, -⟩ := h
    simp [TargetOk, resolveLocal_ok hs]
  | accept => trivial
  | reject => trivial

theorem checkKeySet_ok (h : checkKeySet idx key path ks = .ok u) : KeySetTyped idx key ks := by
  cases ks with
  | exact lit =>
    simp only [checkKeySet, bind_ok, ensure_ok] at h
    obtain ⟨t, ht, heq⟩ := h
    have heq := of_decide_eq_true heq
    subst heq
    exact .exact (checkLiteral_ok ht)
  | masked v m =>
    simp only [checkKeySet, bind_ok, ensure_ok] at h
    obtain ⟨_, hb, t1, h1, _, e1, t2, h2, e2⟩ := h
    refine .masked ?_ (of_decide_eq_true e1 ▸ checkLiteral_ok h1)
      (of_decide_eq_true e2 ▸ checkLiteral_ok h2)
    cases key <;> simp_all [isBits]
  | range lo hi =>
    simp only [checkKeySet, bind_ok, ensure_ok] at h
    obtain ⟨_, hb, t1, h1, _, e1, t2, h2, e2⟩ := h
    refine .range ?_ (of_decide_eq_true e1 ▸ checkLiteral_ok h1)
      (of_decide_eq_true e2 ▸ checkLiteral_ok h2)
    cases key <;> simp_all [isBits]
  | dontCare => exact .dontCare

theorem checkSelectKeys_ok (h : checkSelectKeys c path i keys = .ok tys) :
    SelectKeysTyped c keys tys := by
  induction keys generalizing i tys with
  | nil =>
    simp only [checkSelectKeys, pure_ok] at h
    subst h; exact .nil
  | cons e es ih =>
    simp only [checkSelectKeys, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨t, ht, _, hs, rest, hr, rfl⟩ := h
    exact .cons (checkExpr_ok ht) hs (ih hr)

theorem SelectKeysTyped.length (h : SelectKeysTyped c keys tys) : tys.length = keys.length := by
  induction h with
  | nil => rfl
  | cons _ _ _ ih => simp [ih]

theorem keySets_ok (hlen : tys.length = sets.length)
    (h : ∀ t k, (t, k) ∈ tys.zip sets → ∃ path, checkKeySet idx t path k = .ok ()) :
    KeySetsTyped idx tys sets := by
  induction tys generalizing sets with
  | nil =>
    cases sets with
    | nil => exact .nil
    | cons _ _ => simp at hlen
  | cons t ts ih =>
    cases sets with
    | nil => simp at hlen
    | cons k ks =>
      obtain ⟨j, hj⟩ := h t k (by simp)
      exact .cons (checkKeySet_ok hj)
        (ih (by simpa using hlen) fun x y hx => h x y (List.mem_cons_of_mem _ hx))

theorem checkState_ok (h : checkState c path st = .ok u) : StateTyped c st := by
  unfold checkState at h
  simp only [bind_ok] at h
  obtain ⟨_, hb, ht⟩ := h
  refine ⟨checkStmts_ok _ hb, ?_⟩
  cases htr : st.transition with
  | direct t =>
    rw [htr] at ht
    exact .direct (checkTarget_ok ht)
  | select keys cases =>
    rw [htr] at ht
    simp only [bind_ok, ensure_ok] at ht
    obtain ⟨_, hne, tys, htys, hcases⟩ := ht
    have hk := checkSelectKeys_ok htys
    refine .select (by simpa using hne) hk ?_
    intro cs hcs
    obtain ⟨j, hj⟩ := each_ok hcases cs hcs
    simp only [bind_ok, ensure_ok] at hj
    obtain ⟨_, hlen, _, hsets, htarget⟩ := hj
    have hlen : cs.sets.length = keys.length := by simpa using hlen
    refine ⟨keySets_ok (by rw [hk.length, hlen]) ?_, checkTarget_ok htarget⟩
    intro x y hx
    obtain ⟨j, hj⟩ := each_ok hsets (x, y) hx
    exact ⟨_, hj⟩

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

theorem checkCall_ok (h : checkCall c t path call = .ok u) : CallTyped c t call := by
  simp only [checkCall, bind_ok, ensure_ok] at h
  obtain ⟨act, hact, _, hin, hargs⟩ := h
  exact ⟨by simpa using hin, act, resolveLocal_ok hact, checkLiteralArgs_ok hargs⟩

theorem checkKeys_ok (h : checkKeys c path seen i keys = .ok ws) :
    KeysTyped c keys ws ∧ (keys.filterMap keyName).Nodup ∧
      ∀ n ∈ keys.filterMap keyName, n ∉ seen := by
  induction keys generalizing seen i ws with
  | nil =>
    simp only [checkKeys, pure_ok] at h
    subst h; exact ⟨.nil, by simp, by simp⟩
  | cons k ks ih =>
    simp only [checkKeys, bind_ok] at h
    obtain ⟨_, hname, t, ht, h⟩ := h
    have hname' : ∀ n, keyName k = some n → n ∉ seen := by
      intro n hn
      unfold checkKeyName at hname
      rw [hn] at hname
      simpa [ensure_ok] using hname
    split at h
    · simp only [bind_ok, pure_ok] at h
      obtain ⟨rest, hr, rfl⟩ := h
      obtain ⟨h1, h2, h3⟩ := ih hr
      refine ⟨.cons (checkExpr_ok ht) h1, ?_, ?_⟩
      · cases hk : keyName k with
        | none => simpa [List.filterMap_cons, hk] using h2
        | some n =>
          simp only [List.filterMap_cons, hk, List.nodup_cons]
          exact ⟨fun hm => h3 n hm (by simp [hk]), h2⟩
      · intro n hn hs
        cases hk : keyName k with
        | none =>
          simp only [List.filterMap_cons, hk] at hn
          exact h3 n hn (by simp [hk, hs])
        | some m =>
          simp only [List.filterMap_cons, hk, List.mem_cons] at hn
          rcases hn with rfl | hn
          · exact hname' n hk hs
          · exact h3 n hn (by simp [hk, hs])
    · simp at h

theorem KeysTyped.length (h : KeysTyped c keys ws) : ws.length = keys.length := by
  induction h with
  | nil => rfl
  | cons _ _ ih => simp [ih]

theorem checkKeyValue_ok (h : checkKeyValue k w path v = .ok pat) : pattern? k w v = some pat := by
  cases v with
  | exact x =>
    simp only [checkKeyValue, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, h1, _, h2, rfl⟩ := h
    simp [pattern?, h1, h2]
  | lpm x q =>
    simp only [checkKeyValue, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, h1, _, h2, _, h3, _, h4, rfl⟩ := h
    simp_all [pattern?]
  | ternary x m =>
    simp only [checkKeyValue, bind_ok, ensure_ok, pure_ok] at h
    obtain ⟨_, h1, _, h2, _, h3, _, h4, rfl⟩ := h
    simp_all [pattern?]

theorem mapM_isSome {l : List α} {f : α → Option β} (h : ∀ x ∈ l, (f x).isSome) : (l.mapM f).isSome := by
  induction l with
  | nil => simp
  | cons x xs ih =>
    obtain ⟨y, hy⟩ := Option.isSome_iff_exists.mp (h x (by simp))
    obtain ⟨ys, hys⟩ := Option.isSome_iff_exists.mp
      (ih fun z hz => h z (List.mem_cons_of_mem _ hz))
    simp [List.mapM_cons, hy, hys]

theorem checkEntry_ok (hws : ws.length = t.keys.length) (h : checkEntry c t ws path e = .ok u) :
    EntryTyped c t ws e := by
  simp only [checkEntry, bind_ok, ensure_ok] at h
  obtain ⟨_, hcall, _, hpr, _, hlen, hvals⟩ := h
  have hlen : e.keys.length = t.keys.length := by simpa using hlen
  refine ⟨checkCall_ok hcall, ?_, ?_⟩
  · intro ht
    simpa [ht] using hpr
  · have hall := each_ok hvals
    unfold patterns?
    split
    · apply mapM_isSome
      intro x hx
      obtain ⟨j, hj⟩ := hall x hx
      simp only [bind_ok] at hj
      obtain ⟨pat, hp, -⟩ := hj
      simp [checkKeyValue_ok hp]
    · rename_i hn
      exfalso
      apply hn
      simp [hlen, hws]

theorem checkTableActions_ok (h : checkTableActions c path seen i as = .ok u) :
    as.Nodup ∧ (∀ a ∈ as, a ∉ seen) ∧ ∀ a ∈ as, ∃ act, c.scope.actions[a]? = some act ∧
      ∀ q ∈ act.params, q.direction = .none := by
  induction as generalizing seen i with
  | nil => simp
  | cons a as ih =>
    simp only [checkTableActions, bind_ok, ensure_ok] at h
    obtain ⟨_, hs, act, hact, _, hdir, hr⟩ := h
    obtain ⟨h1, h2, h3⟩ := ih hr
    have hs : a ∉ seen := by simpa using hs
    refine ⟨List.nodup_cons.mpr ⟨fun hm => h2 a hm (by simp), h1⟩, ?_, ?_⟩
    · intro x hx
      rcases List.mem_cons.mp hx with rfl | hx
      · exact hs
      · exact fun hm => h2 x hx (by simp [hm])
    · intro x hx
      rcases List.mem_cons.mp hx with rfl | hx
      · refine ⟨act, resolveLocal_ok hact, ?_⟩
        intro q hq
        have := List.all_eq_true.mp hdir q hq
        simpa using this
      · exact h3 x hx

theorem checkTable_ok (h : checkTable c path t = .ok u) : TableTyped c t := by
  simp only [checkTable, bind_ok, ensure_ok] at h
  obtain ⟨ws, hws, _, hlpm, _, hmix, _, hne, _, hacts, _, hdef, _, hentries, hdist⟩ := h
  obtain ⟨hk, hnames, -⟩ := checkKeys_ok hws
  obtain ⟨hnodup, -, hexist⟩ := checkTableActions_ok hacts
  refine ⟨⟨ws, hk, ?_, hdist⟩, hnames, by simpa using hlpm, hmix,
    ⟨by simpa using hne, hnodup⟩, hexist, ?_⟩
  · intro e he
    obtain ⟨j, hj⟩ := each_ok hentries e he
    exact checkEntry_ok hk.length hj
  · intro call hcall
    rw [hcall] at hdef
    exact checkCall_ok (show checkCall c t _ call = _ from hdef)

-- ---------------------------------------------------------------------------
-- Blocks
-- ---------------------------------------------------------------------------

theorem checkParams_ok (h : checkParams idx params ok path what = .ok u) :
    ∀ q ∈ params, ok q.direction = true ∧ TyOk idx q.type := by
  intro q hq
  obtain ⟨j, hj⟩ := each_ok h q hq
  simp only [bind_ok, ensure_ok] at hj
  obtain ⟨_, hd, ht⟩ := hj
  exact ⟨hd, checkType_ok ht⟩

theorem checkAction_ok (h : checkAction c path a = .ok u) : ActionTyped c a := by
  simp only [checkAction, bind_ok, ensure_ok] at h
  obtain ⟨_, hna, _, hps, hbody⟩ := h
  refine ⟨?_, fun q hq => (checkParams_ok hps q hq).2, checkStmts_ok _ hbody⟩
  intro hn
  simp only [hn, bne_self_eq_false, Bool.false_or, Bool.and_eq_true, List.isEmpty_iff] at hna
  exact hna

theorem checkShape_ok (h : checkShape sc b path = .ok u) : ShapeOk sc b := by
  unfold checkShape at h
  unfold ShapeOk
  split at h <;> rename_i hk <;> rw [hk]
  · simp only [bind_ok, ensure_ok] at h
    obtain ⟨_, hs, _, hst, _, hb, _, ha, ht⟩ := h
    simp only [List.isEmpty_iff, Bool.not_eq_true', List.isEmpty_eq_false_iff] at hs hb ha ht
    exact ⟨hs, contains_ne hst, hb, ha, ht⟩
  · simp only [bind_ok, ensure_ok] at h
    obtain ⟨_, hs, hst⟩ := h
    simp only [List.isEmpty_iff, String.isEmpty_iff] at hs hst
    exact ⟨hs, hst⟩
  · simp only [bind_ok, ensure_ok] at h
    obtain ⟨_, hs, hst⟩ := h
    simp only [List.isEmpty_iff, String.isEmpty_iff] at hs hst
    exact ⟨hs, hst⟩

theorem checkBlock_ok (h : checkBlock idx path b = .ok u) :
    ∃ sc, idx.scopes[b.name]? = some sc ∧ BlockTyped idx sc b := by
  simp only [checkBlock, bind_ok, ensure_ok, need_ok] at h
  obtain ⟨_, hps, _, hls, sc, hsc, _, hshape, _, hacts, _, hacyc, _, htabs, _, hsts, hbody⟩ := h
  refine ⟨sc, hsc, ?_, ?_, checkShape_ok hshape, ?_, hacyc, ?_, ?_, checkStmts_ok _ hbody⟩
  · intro q hq
    obtain ⟨hd, ht⟩ := checkParams_ok hps q hq
    exact ⟨by simpa using hd, ht⟩
  · intro v hv
    obtain ⟨j, hj⟩ := each_ok hls v hv
    exact checkType_ok hj
  · intro a ha
    obtain ⟨j, hj⟩ := each_ok hacts a ha
    exact checkAction_ok hj
  · intro t ht
    obtain ⟨j, hj⟩ := each_ok htabs t ht
    exact checkTable_ok hj
  · intro s hs
    obtain ⟨j, hj⟩ := each_ok hsts s hs
    exact checkState_ok hj

-- ---------------------------------------------------------------------------
-- The program
-- ---------------------------------------------------------------------------

theorem checkExternType_ok (h : checkExternType idx path et = .ok u) : ExternTypeOk idx et := by
  simp only [checkExternType, bind_ok] at h
  obtain ⟨_, hcn, _, hcp, _, hmn, hms⟩ := h
  refine ⟨checkNames_ok hcn, ?_, checkNames_ok hmn, ?_⟩
  · intro q hq
    obtain ⟨hd, ht⟩ := checkParams_ok hcp q hq
    exact ⟨by simpa using hd, ht⟩
  · intro m hm
    obtain ⟨j, hj⟩ := each_ok hms m hm
    simp only [bind_ok] at hj
    obtain ⟨_, hpn, _, hpp, hret⟩ := hj
    refine ⟨checkNames_ok hpn, ?_, ?_⟩
    · intro q hq
      obtain ⟨hd, ht⟩ := checkParams_ok hpp q hq
      exact ⟨by simpa using hd, ht⟩
    · intro t hrt
      rw [hrt] at hret
      exact checkType_ok hret

theorem mapError_ok {x : Except ε α} {f : ε → ε'} : x.mapError f = .ok a ↔ x = .ok a := by
  cases x <;> simp [Except.mapError]

/-- A program the checker accepts is valid, and the index it returns is
the program's.

Premise: `check p` returned `idx`.

It does not establish that `check` accepts every `Valid` program, nor
anything about programs that fail to decode, which never reach it. -/
theorem check_sound (h : check p = .ok idx) : Valid p idx := by
  simp only [check, bind_ok, ensure_ok, pure_ok] at h
  obtain ⟨idx', hidx, _, herr, _, hhs, _, hss, _, hes, _, hcyc, _, hext,
    _, hinst, _, hblocks, _, hacyc, rfl⟩ := h
  have hidx := mapError_ok.mp hidx
  refine ⟨hidx, herr, ?_, ?_, ?_, ?_, ?_, ?_, hacyc⟩
  · intro hd hmem
    obtain ⟨j, hj⟩ := each_ok hhs hd hmem
    simp only [bind_ok] at hj
    obtain ⟨_, hn, hf⟩ := hj
    refine ⟨checkNames_ok hn, fun f hf' => ?_⟩
    obtain ⟨k, hk⟩ := each_ok hf f hf'
    simp only [bind_ok, ensure_ok] at hk
    obtain ⟨_, _, hk⟩ := hk
    exact hk
  · intro s hs
    obtain ⟨j, hj⟩ := each_ok hss s hs
    simp only [bind_ok] at hj
    obtain ⟨_, hn, -⟩ := hj
    obtain ⟨k, hk⟩ := each_ok hcyc s hs
    exact ⟨checkNames_ok hn, ensure_ok.mp hk⟩
  · intro e he
    obtain ⟨j, hj⟩ := each_ok hes e he
    simp only [bind_ok, ensure_ok] at hj
    obtain ⟨_, hn, hne⟩ := hj
    exact ⟨checkNames_ok hn, by simpa using hne⟩
  · intro et het
    obtain ⟨j, hj⟩ := each_ok hext et het
    exact checkExternType_ok hj
  · intro i hi
    obtain ⟨j, hj⟩ := each_ok hinst i hi
    simp only [bind_ok] at hj
    obtain ⟨et, het, hargs⟩ := hj
    exact ⟨et, resolve_ok het, checkLiteralArgs_ok hargs⟩
  · intro b hb
    obtain ⟨j, hj⟩ := each_ok hblocks b hb
    exact checkBlock_ok hj

end P4bloIR.Validity
