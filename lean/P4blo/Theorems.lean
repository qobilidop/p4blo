import P4blo.Eval

/-!
# The one theorem: extract after emit is the identity

docs/design.md, "Open questions", picks the extract-then-emit roundtrip as
the theorem of claim 4. This module proves it about the definitions the
interpreter runs, in three layers.

1. **Bit strings.** `packFields` (the core of `emit`) and `unpackFields`
   (the core of `extract` and `lookahead`; both in `Eval.lean`) are
   inverse. `unpackFields_packFields` (A): unpacking a packed list of
   fields at its widths gives the fields back, when each field fits its
   width; `unpackFields_packFields_zip` says the same with the widths and
   values as two lists indexed side by side. `packFields_unpackFields`
   (B): packing the fields unpacked from a number below `2 ^ (sum of the
   widths)` gives the number back.
2. **Header values.** `headerFromBits_headerToBits` lifts (A) to the
   functions `emitValue` and `extract` call: a valid header whose fields
   fit its type's declaration goes through `headerToBits` to some
   `(width, value)`, `width` is what `extract` reads for that type
   (`widthOf`), `value` fits in `width` bits, and `headerFromBits` at
   `value` rebuilds the header.
3. **Bytes.** `extract_emit` adds the buffer and the packet: write the
   header into an empty `Emitter`, take its `toBytes` as the packet, read
   `width` bits at cursor 0 (`Packet.read?`, what `extract` does through
   `packetRead`): the bits read are `value`, the cursor stops at `width`,
   and `headerFromBits` rebuilds the header. This is the roundtrip of one
   header through the deparser's bytes and back through the parser.

Not covered, and why: the `M`-monad plumbing around these calls
(`readLValue`/`writeLValue` on the target, `hs.next`, the
`PacketTooShort` fault) is state threading with no bit arithmetic in it;
`emit` of a struct or a stack is `emitValue` on each header in order; and
several headers in one packet are `Emitter.write` chained, which is
`packFields` with one pair per header. `extract` and `emitValue` are not
`partial`, but they run in `M` over hash-map stores, and a theorem about
`M.run` would be about the store, not the roundtrip.

Lean core only; `#print axioms` on every theorem here lists nothing beyond
`propext`, `Classical.choice` and `Quot.sound`.
-/

namespace P4blo

-- ---------------------------------------------------------------------------
-- Arithmetic
-- ---------------------------------------------------------------------------

/-- `v <<< s ||| p` is `v * 2 ^ s + p` when `p` fits in `s` bits: the two
halves do not overlap. -/
theorem shiftLeft_or_eq (v s p : Nat) (hp : p < 2 ^ s) : v <<< s ||| p = v * 2 ^ s + p := by
  rw [← Nat.shiftLeft_add_eq_or_of_lt hp, Nat.shiftLeft_eq]

theorem Except.ok_bind {ε α β : Type} (a : α) (f : α → Except ε β) :
    (Except.ok a >>= f : Except ε β) = f a := rfl

theorem Except.map_ok {ε α β : Type} (f : α → β) (a : α) :
    (f <$> Except.ok a : Except ε β) = Except.ok (f a) := rfl

theorem Except.pure_eq {ε α : Type} (a : α) : (pure a : Except ε α) = Except.ok a := rfl

/-- `v` is a value of the header field type `ty`: `bit<n>` holds bits of
width `n` and `bool` holds a boolean. A `HeaderType` admits no other field
type (IR.lean), so this is what "the fields fit the declaration" means for
a header. -/
def FieldFits : Value → Ty → Prop
  | .bits b, .bits n => b.width = n
  | .bool _, .boolean => True
  | _, _ => False

-- ---------------------------------------------------------------------------
-- (A) and (B): packFields and unpackFields are inverse
-- ---------------------------------------------------------------------------

/-- Packed fields that each fit their width fit the total width. -/
theorem packFields_lt (fs : List (Nat × Nat)) (h : ∀ f ∈ fs, f.2 < 2 ^ f.1) :
    packFields fs < 2 ^ (fs.map Prod.fst).sum := by
  induction fs with
  | nil => simp [packFields]
  | cons f fs ih =>
    obtain ⟨w, v⟩ := f
    have hv : v < 2 ^ w := h (w, v) (by simp)
    have hp := ih (fun g hg => h g (by simp [hg]))
    simp only [packFields, List.map_cons, List.sum_cons]
    rw [shiftLeft_or_eq _ _ _ hp, Nat.pow_add]
    generalize (fs.map Prod.fst).sum = s at hp ⊢
    calc v * 2 ^ s + packFields fs < v * 2 ^ s + 2 ^ s := Nat.add_lt_add_left hp _
      _ = (v + 1) * 2 ^ s := by rw [Nat.succ_mul]
      _ ≤ 2 ^ w * 2 ^ s := Nat.mul_le_mul_right _ hv

/-- Unpacking looks only at the low `ws.sum` bits. -/
theorem unpackFields_mod (ws : List Nat) (n : Nat) :
    unpackFields ws (n % 2 ^ ws.sum) = unpackFields ws n := by
  induction ws generalizing n with
  | nil => rfl
  | cons w ws ih =>
    simp only [unpackFields, List.sum_cons, Nat.shiftRight_eq_div_pow]
    congr 1
    · rw [Nat.pow_add', Nat.mod_mul_right_div_self, Nat.mod_mod]
    · rw [← ih (n % 2 ^ (w + ws.sum)), Nat.mod_mod_of_dvd _ (Nat.pow_dvd_pow 2 (by omega)), ih]

/-- Bits above the total width do not change what is unpacked. -/
theorem unpackFields_shiftLeft_or (ws : List Nat) (v p : Nat) (hp : p < 2 ^ ws.sum) :
    unpackFields ws (v <<< ws.sum ||| p) = unpackFields ws p := by
  rw [shiftLeft_or_eq _ _ _ hp, ← unpackFields_mod ws (v * 2 ^ ws.sum + p), Nat.mul_comm,
    Nat.mul_add_mod, unpackFields_mod]

theorem length_unpackFields (ws : List Nat) (n : Nat) :
    (unpackFields ws n).length = ws.length := by
  induction ws with
  | nil => rfl
  | cons w ws ih => simp [unpackFields, ih]

/-- **(A) unpack after pack.** For any list of `(width, value)` fields in
which every value fits its width, unpacking the packed bit string at those
widths gives the values back. -/
theorem unpackFields_packFields (fs : List (Nat × Nat)) (h : ∀ f ∈ fs, f.2 < 2 ^ f.1) :
    unpackFields (fs.map Prod.fst) (packFields fs) = fs.map Prod.snd := by
  induction fs with
  | nil => rfl
  | cons f fs ih =>
    obtain ⟨w, v⟩ := f
    have hv : v < 2 ^ w := h (w, v) (by simp)
    have hrest : ∀ g ∈ fs, g.2 < 2 ^ g.1 := fun g hg => h g (by simp [hg])
    have hp := packFields_lt fs hrest
    simp only [packFields, List.map_cons, unpackFields]
    rw [unpackFields_shiftLeft_or _ _ _ hp, ih hrest]
    congr 1
    rw [shiftLeft_or_eq _ _ _ hp, Nat.shiftRight_eq_div_pow, Nat.mul_comm,
      Nat.mul_add_div (Nat.two_pow_pos _), Nat.div_eq_of_lt hp, Nat.add_zero, Nat.mod_eq_of_lt hv]

/-- The index form of "every value fits its width", as membership in the
zip. -/
theorem forall_mem_zip_of_lt (ws vs : List Nat) (hlen : vs.length = ws.length)
    (h : ∀ i (h₁ : i < ws.length) (h₂ : i < vs.length), vs[i] < 2 ^ ws[i]) :
    ∀ f ∈ ws.zip vs, f.2 < 2 ^ f.1 := by
  induction ws generalizing vs with
  | nil => simp
  | cons w ws ih =>
    cases vs with
    | nil => simp at hlen
    | cons v vs =>
      intro f hf
      simp only [List.zip_cons_cons, List.mem_cons] at hf
      rcases hf with rfl | hf
      · exact h 0 (by simp) (by simp)
      · exact ih vs (by simpa using hlen)
          (fun i h₁ h₂ => h (i + 1) (by simp; omega) (by simp; omega)) f hf

/-- **(A), with widths and values as two lists.** For field widths `ws` and
values `vs` of the same length with `vs[i] < 2 ^ ws[i]` at every `i`,
unpacking at `ws` the packed bit string of `ws` zipped with `vs` gives
`vs` back. -/
theorem unpackFields_packFields_zip (ws vs : List Nat) (hlen : vs.length = ws.length)
    (h : ∀ i (h₁ : i < ws.length) (h₂ : i < vs.length), vs[i] < 2 ^ ws[i]) :
    unpackFields ws (packFields (ws.zip vs)) = vs := by
  have := unpackFields_packFields (ws.zip vs) (forall_mem_zip_of_lt ws vs hlen h)
  rwa [List.map_fst_zip (by omega), List.map_snd_zip (by omega)] at this

/-- **(B) pack after unpack.** For any widths `ws` and any `n < 2 ^ ws.sum`,
packing the fields unpacked from `n` at `ws` (paired with their widths)
gives `n` back. -/
theorem packFields_unpackFields (ws : List Nat) (n : Nat) (hn : n < 2 ^ ws.sum) :
    packFields (ws.zip (unpackFields ws n)) = n := by
  induction ws generalizing n with
  | nil =>
    simp only [List.sum_nil, Nat.pow_zero] at hn
    simp only [unpackFields, List.zip_nil_left, packFields]
    omega
  | cons w ws ih =>
    simp only [List.sum_cons] at hn
    have hmod : n % 2 ^ ws.sum < 2 ^ ws.sum := Nat.mod_lt _ (Nat.two_pow_pos _)
    simp only [unpackFields, List.zip_cons_cons, packFields]
    rw [List.map_fst_zip (by rw [length_unpackFields]; exact Nat.le_refl _),
      ← unpackFields_mod ws n, ih _ hmod,
      shiftLeft_or_eq _ _ _ hmod, Nat.shiftRight_eq_div_pow]
    have hdiv : n / 2 ^ ws.sum < 2 ^ w :=
      (Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _)).2 (Nat.pow_add 2 w ws.sum ▸ hn)
    rw [Nat.mod_eq_of_lt hdiv, Nat.div_add_mod']

-- ---------------------------------------------------------------------------
-- Header values: headerToBits and headerFromBits
-- ---------------------------------------------------------------------------

/-- One field that fits its declared type: `fieldBits` gives it a width and
a value, `widthOfWith` at any positive fuel agrees on the width, the value
fits, and `fieldFromBits` rebuilds the field. -/
theorem field_roundtrip (index : Index) (f : Field) (v : Value) (hfit : FieldFits v f.type) :
    ∃ w x, fieldBits v = .ok (w, x) ∧ (∀ k, widthOfWith index (k + 1) f.type = .ok w) ∧
      x < 2 ^ w ∧ fieldFromBits f w x = v := by
  obtain ⟨name, ty⟩ := f
  cases ty <;> cases v <;> simp only [FieldFits] at hfit
  · rename_i n b
    obtain ⟨w, x, hx⟩ := b
    subst hfit
    have hne : (Ty.bits w == Ty.boolean) = false := rfl
    exact ⟨w, x, rfl, fun _ => rfl, hx, by simp [fieldFromBits, hne, Bits.wrap, Nat.mod_eq_of_lt hx]⟩
  · rename_i b
    exact ⟨1, if b then 1 else 0, rfl, fun _ => rfl, by cases b <;> decide, by cases b <;> rfl⟩

/-- `field_roundtrip` along two lists: the fields of a header value
against the fields of its declaration. -/
theorem fields_roundtrip (index : Index) (decls : List Field) (fields : List Value)
    (hlen : fields.length = decls.length)
    (hfit : ∀ p ∈ fields.zip decls, FieldFits p.1 p.2.type) :
    ∃ fs : List (Nat × Nat), fields.mapM fieldBits = .ok fs ∧
      decls.mapM (fun f => widthOf f.type index) = .ok (fs.map Prod.fst) ∧
      (∀ k acc, decls.foldlM (fun n f => (n + ·) <$> widthOfWith index (k + 1) f.type) acc =
        .ok (acc + (fs.map Prod.fst).sum)) ∧
      (∀ f ∈ fs, f.2 < 2 ^ f.1) ∧
      (decls.zip ((fs.map Prod.fst).zip (fs.map Prod.snd))).map
        (fun p => fieldFromBits p.1 p.2.1 p.2.2) = fields := by
  induction decls generalizing fields with
  | nil =>
    cases fields with
    | nil => exact ⟨[], rfl, rfl, fun _ _ => rfl, by simp, rfl⟩
    | cons _ _ => simp at hlen
  | cons d decls ih =>
    cases fields with
    | nil => simp at hlen
    | cons v fields =>
      obtain ⟨w, x, hfb, hw, hx, hv⟩ := field_roundtrip index d v (hfit (v, d) (by simp))
      obtain ⟨fs, hfs, hws, hfold, hlt, hre⟩ :=
        ih fields (by simpa using hlen) (fun p hp => hfit p (by simp [hp]))
      refine ⟨(w, x) :: fs, ?_, ?_, ?_, ?_, ?_⟩
      · rw [List.mapM_cons, hfb, Except.ok_bind, hfs]; rfl
      · have hw' : widthOf d.type index = .ok w := hw _
        rw [List.mapM_cons, hw', Except.ok_bind, hws]; rfl
      · intro k acc
        rw [List.foldlM_cons, hw k, Except.map_ok, Except.ok_bind, hfold k, List.map_cons,
          List.sum_cons, Nat.add_assoc]
      · intro f hf
        simp only [List.mem_cons] at hf
        rcases hf with rfl | hf
        · exact hx
        · exact hlt f hf
      · simp only [List.map_cons, List.zip_cons_cons]
        rw [hre]
        exact congrArg (· :: fields) hv

/-- The index form of "every field fits its declared type", as membership
in the zip. -/
theorem forall_mem_zip_of_fits (fields : List Value) (decls : List Field)
    (hlen : fields.length = decls.length)
    (h : ∀ i (h₁ : i < fields.length) (h₂ : i < decls.length), FieldFits fields[i] decls[i].type) :
    ∀ p ∈ fields.zip decls, FieldFits p.1 p.2.type := by
  induction fields generalizing decls with
  | nil => simp
  | cons v fields ih =>
    cases decls with
    | nil => simp at hlen
    | cons d decls =>
      intro p hp
      simp only [List.zip_cons_cons, List.mem_cons] at hp
      rcases hp with rfl | hp
      · exact h 0 (by simp) (by simp)
      · exact ih decls (by simpa using hlen)
          (fun i h₁ h₂ => h (i + 1) (by simp; omega) (by simp; omega)) p hp

/-- **Roundtrip of a header value.** Let `decl` be the declaration of
header type `typeName` in `index`, and `fields` a list of values, one per
declared field, each fitting its field's type (`FieldFits`: `bit<n>` holds
`n`-bit bits, `bool` holds a boolean). Then `headerToBits fields`, the
number `emit` writes, is some `.ok (width, value)`; `value` fits in
`width` bits; `width` is what `extract` reads for the type,
`widthOf (.header typeName)`; and `headerFromBits` at `value`, what
`extract` stores, is the valid header of `typeName` with exactly these
`fields`. -/
theorem headerFromBits_headerToBits {index : Index} {typeName : String} {decl : HeaderType}
    (hdecl : index.headerTypes[typeName]? = some decl) (fields : List Value)
    (hlen : fields.length = decl.fields.length)
    (hfit : ∀ i (h₁ : i < fields.length) (h₂ : i < decl.fields.length),
      FieldFits fields[i] decl.fields[i].type) :
    ∃ width value, headerToBits fields = .ok (width, value) ∧ value < 2 ^ width ∧
      widthOf (.header typeName) index = .ok width ∧
      headerFromBits typeName value index = .ok (.header typeName true fields) := by
  obtain ⟨fs, hfs, hws, hfold, hlt, hre⟩ :=
    fields_roundtrip index decl.fields fields hlen (forall_mem_zip_of_fits fields decl.fields hlen hfit)
  refine ⟨(fs.map Prod.fst).sum, packFields fs, ?_, packFields_lt fs hlt, ?_, ?_⟩
  · unfold headerToBits
    rw [hfs, Except.ok_bind, Except.pure_eq]
  · show widthOfWith index (index.headerTypes.size + index.structTypes.size + 1 + 1) _ = _
    rw [widthOfWith]
    simp only [hdecl]
    rw [hfold, Nat.zero_add]
  · unfold headerFromBits
    rw [hdecl]
    simp only [hws, Except.ok_bind, unpackFields_packFields fs hlt, hre, Except.pure_eq]

-- ---------------------------------------------------------------------------
-- Bytes: the emitter's buffer read back as a packet
-- ---------------------------------------------------------------------------

theorem natToBytes_go_length (k m : Nat) (acc : List UInt8) :
    (natToBytes.go k m acc).length = k + acc.length := by
  induction k generalizing m acc with
  | zero => simp [natToBytes.go]
  | succ k ih => simp [natToBytes.go, ih]; omega

theorem natToBytes_go_foldl (k m : Nat) (acc : List UInt8) (a : Nat) :
    (natToBytes.go k m acc).foldl (fun n b => n * 256 + b.toNat) a =
      acc.foldl (fun n b => n * 256 + b.toNat) (a * 256 ^ k + m % 256 ^ k) := by
  induction k generalizing m acc a with
  | zero => simp [natToBytes.go, Nat.mod_one]
  | succ k ih =>
    rw [natToBytes.go, ih, List.foldl_cons]
    congr 1
    have h1 : (UInt8.ofNat (m % 256)).toNat = m % 256 := by simp
    have h2 : m % 256 ^ (k + 1) = m % 256 + 256 * (m / 256 % 256 ^ k) := by
      rw [Nat.pow_succ', Nat.mod_mul]
    have h3 : a * 256 ^ (k + 1) = a * 256 ^ k * 256 := by rw [Nat.pow_succ, Nat.mul_assoc]
    rw [h1, h2, h3]
    generalize a * 256 ^ k = A
    generalize m / 256 % 256 ^ k = Q
    omega

theorem size_natToBytes (n size : Nat) : (natToBytes n size).size = size := by
  simp [natToBytes, ByteArray.size, natToBytes_go_length]

/-- The bytes of `n`, read back, are `n` modulo the bytes' capacity. -/
theorem bytesToNat_natToBytes (n size : Nat) : bytesToNat (natToBytes n size) = n % 256 ^ size := by
  simp only [bytesToNat, natToBytes, List.foldl_toArray']
  rw [natToBytes_go_foldl]
  simp

/-- `width` bits written into an empty emitter, padded to bytes and read
back as a packet at cursor 0, are the same bits, and the cursor stops at
`width`. -/
theorem read_write (width value : Nat) (hv : value < 2 ^ width) :
    (Packet.ofBytes (Emitter.write {} width value).toBytes).read? width =
      some (value, { Packet.ofBytes (Emitter.write {} width value).toBytes with cursor := width }) := by
  have h8 : (width + (8 - width % 8) % 8) % 8 = 0 := by omega
  simp only [Emitter.write, Emitter.toBytes, Nat.zero_shiftLeft, Nat.zero_or, Nat.zero_add]
  generalize (8 - width % 8) % 8 = padding at h8 ⊢
  have hsize : (width + padding) / 8 * 8 = width + padding := by omega
  have hgt : ¬ width > width + padding := by omega
  have hlt : value <<< padding < 256 ^ ((width + padding) / 8) := by
    rw [Nat.shiftLeft_eq]
    calc value * 2 ^ padding < 2 ^ width * 2 ^ padding :=
          (Nat.mul_lt_mul_right (Nat.two_pow_pos _)).2 hv
      _ = 2 ^ (width + padding) := (Nat.pow_add _ _ _).symm
      _ = 2 ^ (8 * ((width + padding) / 8)) := by
          rw [show 8 * ((width + padding) / 8) = width + padding by omega]
      _ = 256 ^ ((width + padding) / 8) := by simp [Nat.pow_mul]
  simp [Packet.ofBytes, Packet.read?, Packet.peek?, Packet.remainingBits, Packet.totalBits,
    size_natToBytes, bytesToNat_natToBytes, Nat.mod_eq_of_lt hlt, hsize, hgt, Nat.mod_eq_of_lt hv]

/-- **Extract after emit.** Under the hypotheses of
`headerFromBits_headerToBits`: emit the header into an empty deparser
buffer (`headerToBits`, then `Emitter.write`), take the buffer's bytes
(`Emitter.toBytes`, zero-padded to a byte boundary) as a packet
(`Packet.ofBytes`, cursor 0), and read the header's width
(`Packet.read?`, what `extract` does through `packetRead`): the read
succeeds, returns the emitted `value`, leaves the cursor at `width`, and
`headerFromBits` at `value` is the valid header with the same `fields`. -/
theorem extract_emit {index : Index} {typeName : String} {decl : HeaderType}
    (hdecl : index.headerTypes[typeName]? = some decl) (fields : List Value)
    (hlen : fields.length = decl.fields.length)
    (hfit : ∀ i (h₁ : i < fields.length) (h₂ : i < decl.fields.length),
      FieldFits fields[i] decl.fields[i].type) :
    ∃ width value, headerToBits fields = .ok (width, value) ∧
      widthOf (.header typeName) index = .ok width ∧
      (∃ rest, (Packet.ofBytes (Emitter.write {} width value).toBytes).read? width =
        some (value, rest) ∧ rest.cursor = width) ∧
      headerFromBits typeName value index = .ok (.header typeName true fields) := by
  obtain ⟨width, value, hto, hlt, hwidth, hfrom⟩ := headerFromBits_headerToBits hdecl fields hlen hfit
  exact ⟨width, value, hto, hwidth, ⟨_, read_write width value hlt, rfl⟩, hfrom⟩

end P4blo
