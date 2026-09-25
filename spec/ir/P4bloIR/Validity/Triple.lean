import P4bloIR.ScalarTyping

/-!
# Triples over the interpreter monad

`Triple m r Q E`: running `m` from the run `r`, a success satisfies `Q`
and a fault satisfies `E`, each with the run after it. The progress proof
states what every interpreter function does on well-typed input as a
triple whose `E` admits only parser errors, so an `InterpError` is
excluded by the post-condition, not by a separate argument.

The combinators below follow the monad's structure; they are proved from
`ScalarTyping.run_bind` and the definitions, and introduce no evaluator.
-/

namespace P4bloIR.Validity

open ScalarTyping (run_bind run_pure run_map)

/-- `m` from `r`: a result satisfies `Q`, a fault `E`. -/
def Triple (m : M α) (r : Run) (Q : α → Run → Prop) (E : Fault → Run → Prop) : Prop :=
  match m.run r with
  | (.ok a, r') => Q a r'
  | (.error f, r') => E f r'

/-- Two lists related pointwise. -/
inductive Forall2 (R : α → β → Prop) : List α → List β → Prop
  | nil : Forall2 R [] []
  | cons : R a b → Forall2 R as bs → Forall2 R (a :: as) (b :: bs)

namespace Triple

variable {α β : Type} {m : M α} {r r' : Run} {Q P : α → Run → Prop} {E E' : Fault → Run → Prop}

theorem of_run (h : m.run r = (.ok a, r')) (hq : Q a r') : Triple m r Q E := by
  unfold Triple; rw [h]; exact hq

theorem of_run_error (h : m.run r = (.error f, r')) (he : E f r') : Triple m r Q E := by
  unfold Triple; rw [h]; exact he

theorem pure' (h : Q a r) : Triple (pure a : M α) r Q E := of_run rfl h

theorem bind {Q : β → Run → Prop} {f : α → M β} (hm : Triple m r P E)
    (hf : ∀ a r', P a r' → Triple (f a) r' Q E) : Triple (m >>= f) r Q E := by
  unfold Triple at *
  rw [run_bind]
  revert hm
  cases m.run r with
  | mk res r' =>
    cases res with
    | ok a => exact fun hm => hf a r' hm
    | error e => exact fun hm => hm

theorem mono (h : Triple m r P E) (hq : ∀ a r', P a r' → Q a r')
    (he : ∀ f r', E f r' → E' f r') : Triple m r Q E' := by
  unfold Triple at *
  revert h
  cases m.run r with
  | mk res r' => cases res <;> simp_all

theorem map {Q : β → Run → Prop} {f : α → β} (h : Triple m r P E)
    (hq : ∀ a r', P a r' → Q (f a) r') : Triple (f <$> m) r Q E := by
  unfold Triple at *
  rw [run_map]
  revert h
  cases m.run r with
  | mk res r' => cases res <;> simp_all

theorem throw' (h : E f r) : Triple (throw f : M α) r Q E := of_run_error rfl h

theorem throwParse' (h : E (.parse e) r) : Triple (throwParse e : M α) r Q E :=
  of_run_error rfl h

theorem get' {Q : Run → Run → Prop} (h : Q r r) : Triple (get : M Run) r Q E := of_run rfl h

theorem getFrame' {Q : Frame → Run → Prop} (h : Q r.frame r) : Triple getFrame r Q E := of_run rfl h

theorem getIndex' {Q : Index → Run → Prop} (h : Q r.index r) : Triple getIndex r Q E := of_run rfl h

theorem setFrame' {Q : Unit → Run → Prop} (h : Q () { r with frame := f }) : Triple (setFrame f) r Q E := of_run rfl h

theorem modify' {Q : Unit → Run → Prop} (h : Q () (g r)) : Triple (modify g : M Unit) r Q E := of_run rfl h

theorem liftExcept' (hx : x = .ok a) (h : Q a r) : Triple (liftExcept x) r Q E := by
  subst hx; exact of_run rfl h

theorem ite' {c : Prop} [Decidable c] {t e : M α} (ht : c → Triple t r Q E)
    (he : ¬c → Triple e r Q E) : Triple (if c then t else e) r Q E := by
  by_cases h : c
  · simp only [h, ↓reduceIte]; exact ht h
  · simp only [h, ↓reduceIte]; exact he h

/-- A loop over a list: an invariant on the remaining elements and the
accumulator, kept by every pass that yields. -/
theorem forIn' {Q : β → Run → Prop} {l : List α} {b : β} {f : α → β → M (ForInStep β)}
    (I : List α → β → Run → Prop) (h0 : I l b r)
    (step : ∀ x xs b r, I (x :: xs) b r →
      Triple (f x b) r (fun s r' => match s with
        | .yield b' => I xs b' r'
        | .done b' => Q b' r') E)
    (done : ∀ b r, I [] b r → Q b r) :
    Triple (forIn l b f) r Q E := by
  induction l generalizing b r with
  | nil => exact pure' (done b r h0)
  | cons x xs ih =>
    rw [List.forIn_cons]
    refine bind (step x xs b r h0) ?_
    intro s r' hs
    cases s with
    | done b' => exact pure' hs
    | yield b' => exact ih hs

/-- `mapM` with a per-element triple whose post relates input and output. -/
theorem mapM' {l : List α} {f : α → M β} (R : α → β → Prop) (I : Run → Prop) (h0 : I r)
    (step : ∀ x ∈ l, ∀ r, I r → Triple (f x) r (fun y r' => R x y ∧ I r') E) :
    Triple (l.mapM f) r (fun ys r' => Forall2 R l ys ∧ I r') E := by
  induction l generalizing r with
  | nil => exact pure' ⟨.nil, h0⟩
  | cons x xs ih =>
    rw [List.mapM_cons]
    refine bind (step x (by simp) r h0) ?_
    intro y r' ⟨hy, hi⟩
    refine bind (ih hi (fun z hz => step z (List.mem_cons_of_mem _ hz))) ?_
    intro ys r'' ⟨hys, hi'⟩
    exact pure' ⟨.cons hy hys, hi'⟩

end Triple

end P4bloIR.Validity
