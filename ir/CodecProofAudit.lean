import P4bloIR.CodecLaws
import Tests.CodecLaws

/-! Checked trust boundary for actual JSON-value syntax codec laws. -/

/-- info: 'P4bloIR.CodecLaws.decimal_toString' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.decimal_toString

/-- info: 'P4bloIR.CodecLaws.uint32_toJson' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.uint32_toJson

/-- info: 'P4bloIR.CodecLaws.uint32_toJson_reject' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.uint32_toJson_reject

/-- info: 'P4bloIR.CodecLaws.literal_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.literal_roundtrip

/-- info: 'P4bloIR.CodecLaws.type_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.type_roundtrip

/-- info: 'P4bloIR.CodecLaws.keyValue_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.keyValue_roundtrip

/-- info: 'P4bloIR.Decode.msgFieldBounded_erasure' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Decode.msgFieldBounded_erasure

/-- info: 'P4bloIR.Decode.oneofBounded_erasure' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Decode.oneofBounded_erasure

/-- info: 'P4bloIR.Expr.decode' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Expr.decode

/-- info: 'P4bloIR.Expr.decode_unfold' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Expr.decode_unfold

/-- info: 'P4bloIR.CodecLaws.expr_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.expr_roundtrip

/-- info: 'P4bloIR.LValue.decode' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.LValue.decode

/-- info: 'P4bloIR.LValue.decode_unfold' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.LValue.decode_unfold

/-- info: 'P4bloIR.Arg.decode' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Arg.decode

/-- info: 'P4bloIR.CodecLaws.lvalue_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.lvalue_roundtrip

/-- info: 'P4bloIR.CodecLaws.arg_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.arg_roundtrip

/-- info: 'P4bloIR.JsonBounds.array_mem_lt' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.JsonBounds.array_mem_lt

/-- info: 'P4bloIR.Decode.arrayBounded_erasure' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Decode.arrayBounded_erasure

/-- info: 'P4bloIR.Decode.listFieldBounded_erasure' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Decode.listFieldBounded_erasure

/-- info: 'P4bloIR.Stmt.decode' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Stmt.decode

/-- info: 'P4bloIR.Stmt.decode_unfold' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Stmt.decode_unfold

/-- info: 'P4bloIR.CodecLaws.array_encoded_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.array_encoded_roundtrip

/-- info: 'P4bloIR.CodecLaws.stmt_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.stmt_roundtrip

/-- info: 'CodecLawTests.nestedStatement_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms CodecLawTests.nestedStatement_roundtrip
