import P4blo.Fields

/-! Independent source initial values and correspondence with the actual
fuel-bounded IR initializer. This does not initialize frames or prove global
declaration validity; nominal agreement and sufficient fuel are explicit. -/

namespace P4blo.Fields

mutual
def Shape.zero : (shape : Shape) → Data shape
  | .scalar (.bits _) => .scalar 0
  | .scalar .boolean => .scalar false
  | .aggregate .header _ fields => .aggregate false fields.zero
  | .aggregate .struct _ fields => .aggregate () fields.zero
def Layout.zero : (fields : Layout) → Record fields
  | .nil => .nil
  | .cons _ shape rest => .cons shape.zero rest.zero
end

mutual
/-- Scalars consume one unit; aggregate fields share the remaining budget. -/
def Shape.zeroFuel : Shape → Nat
  | .scalar _ => 1
  | .aggregate _ _ fields => fields.zeroFuel + 1
def Layout.zeroFuel : Layout → Nat
  | .nil => 0
  | .cons _ shape rest => max shape.zeroFuel rest.zeroFuel
end

mutual
theorem Shape.zeroWith_correct (shape : Shape) (index : P4bloIR.Index)
    (hi : shape.IndexAgrees index) (fuel : Nat) (hf : shape.zeroFuel ≤ fuel) :
    P4bloIR.Value.zeroWith index fuel shape.toIR = .ok shape.zero.toValue := by
  cases fuel with
  | zero => cases shape <;> simp [Shape.zeroFuel] at hf
  | succ fuel =>
    cases shape with
    | scalar type =>
      cases type <;> simp [Shape.toIR, Scalar.Ty.toIR, Shape.zero,
        Data.toValue, Scalar.toValue, P4bloIR.Value.zeroWith, P4bloIR.Bits.wrap] <;> rfl
    | aggregate kind name fields =>
      have bound : fields.zeroFuel ≤ fuel := by simpa [Shape.zeroFuel] using hf
      have children := Layout.zeroWith_correct fields index hi.2 fuel bound
      cases kind <;>
        simp [Shape.toIR, Shape.zero, Data.toValue, Validity.toBool,
          P4bloIR.FieldLaws.pack, P4bloIR.Value.zeroWith, hi.1.2.1, children] <;> rfl
termination_by sizeOf shape

theorem Layout.zeroWith_correct (fields : Layout) (index : P4bloIR.Index)
    (hi : fields.IndexAgrees index) (fuel : Nat) (hf : fields.zeroFuel ≤ fuel) :
    fields.fields.mapM (fun field => P4bloIR.Value.zeroWith index fuel field.type) =
      .ok fields.zero.toValues := by
  cases fields with
  | nil => rfl
  | cons name shape rest =>
    have hb : shape.zeroFuel ≤ fuel ∧ rest.zeroFuel ≤ fuel := by
      exact Nat.max_le.mp hf
    simp [Layout.fields, Layout.zero, Record.toValues,
      Shape.zeroWith_correct shape index hi.1 fuel hb.1,
      Layout.zeroWith_correct rest index hi.2 fuel hb.2] <;> rfl
termination_by sizeOf fields
end

/-- The concrete runtime budget remains a premise, not an inferred
acyclicity theorem about arbitrary nominal declarations. -/
theorem Shape.zero_correct (shape : Shape) (index : P4bloIR.Index)
    (hi : shape.IndexAgrees index)
    (hf : shape.zeroFuel ≤ index.headerTypes.size + index.structTypes.size + 2) :
    P4bloIR.Value.zero shape.toIR index = .ok shape.zero.toValue :=
  shape.zeroWith_correct index hi _ hf

end P4blo.Fields
