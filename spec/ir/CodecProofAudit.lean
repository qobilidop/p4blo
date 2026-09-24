import P4bloIR.CodecLaws
import Tests.CodecLaws
import P4bloIR.DeclarationCodecLaws
import Tests.DeclarationCodec
import P4bloIR.TableCodecLaws
import Tests.TableCodec
import P4bloIR.ParserCodecLaws
import Tests.ParserCodec
import P4bloIR.BlockCodecLaws
import Tests.BlockCodec

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

/-- info: 'P4bloIR.CodecLaws.field_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.field_roundtrip

/-- info: 'P4bloIR.CodecLaws.headerType_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.headerType_roundtrip

/-- info: 'P4bloIR.CodecLaws.structType_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.structType_roundtrip

/-- info: 'P4bloIR.CodecLaws.enumType_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.enumType_roundtrip

/-- info: 'P4bloIR.CodecLaws.var_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.var_roundtrip

/-- info: 'P4bloIR.CodecLaws.param_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.param_roundtrip

/-- info: 'P4bloIR.CodecLaws.method_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.method_roundtrip

/-- info: 'P4bloIR.CodecLaws.externType_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.externType_roundtrip

/-- info: 'P4bloIR.CodecLaws.externInstance_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.externInstance_roundtrip

/-- info: 'DeclarationCodecTests.declarations_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms DeclarationCodecTests.declarations_roundtrip

/-- info: 'P4bloIR.CodecLaws.key_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.key_roundtrip

/-- info: 'P4bloIR.CodecLaws.actionCall_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.actionCall_roundtrip

/-- info: 'P4bloIR.CodecLaws.entry_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.entry_roundtrip

/-- info: 'P4bloIR.CodecLaws.table_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.table_roundtrip

/-- info: 'TableCodecTests.tables_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms TableCodecTests.tables_roundtrip

/-- info: 'P4bloIR.CodecLaws.target_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.target_roundtrip

/-- info: 'P4bloIR.CodecLaws.keySet_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.keySet_roundtrip

/-- info: 'P4bloIR.CodecLaws.selectCase_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.selectCase_roundtrip

/-- info: 'P4bloIR.CodecLaws.transition_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.transition_roundtrip

/-- info: 'P4bloIR.CodecLaws.state_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.state_roundtrip

/-- info: 'ParserCodecTests.parserState_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms ParserCodecTests.parserState_roundtrip

/-- info: 'P4bloIR.CodecLaws.action_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.action_roundtrip

/-- info: 'P4bloIR.CodecLaws.block_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.CodecLaws.block_roundtrip

/-- info: 'BlockCodecTests.blocks_roundtrip' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms BlockCodecTests.blocks_roundtrip
