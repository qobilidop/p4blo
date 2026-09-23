import Tests.Check
import P4bloIR.CodecLaws

open P4bloIR Lean

namespace CodecLawTests

-- Kernel-checked witnesses include semantically invalid but representable
-- leaves. None of these claims invokes the whole-program validator.
example : CodecLaws.LiteralRepresentable (.bits 0 (10 ^ 100)) := by
  unfold CodecLaws.LiteralRepresentable CodecLaws.UInt32
  decide
example : CodecLaws.TypeRepresentable (.stack "" 0) := by
  unfold CodecLaws.TypeRepresentable CodecLaws.UInt32
  decide
example : ¬ CodecLaws.TypeRepresentable (.bits (2 ^ 32)) := by
  unfold CodecLaws.TypeRepresentable CodecLaws.UInt32
  decide
example : Literal.decode "" (Literal.bits 0 (10 ^ 100)).toJson =
    .ok (.bits 0 (10 ^ 100)) := CodecLaws.literal_roundtrip _ _ (by
      unfold CodecLaws.LiteralRepresentable CodecLaws.UInt32
      decide)
example : Ty.decode "" (Ty.stack "" 0).toJson = .ok (.stack "" 0) :=
  CodecLaws.type_roundtrip _ _ (by
    unfold CodecLaws.TypeRepresentable CodecLaws.UInt32
    decide)
example : Decode.uint32 "width" (toJson (2 ^ 32 : Nat)) =
    .error "width: 4294967296 does not fit in uint32" :=
  CodecLaws.uint32_toJson_reject _ _ (by unfold CodecLaws.UInt32; decide)

example : CodecLaws.KeyValueRepresentable (.lpm (10 ^ 100) 0) := by
  unfold CodecLaws.KeyValueRepresentable CodecLaws.UInt32
  decide
example : CodecLaws.KeyValueRepresentable (.ternary 255 0) := by trivial
example : ¬ CodecLaws.KeyValueRepresentable (.lpm 0 (2 ^ 32)) := by
  unfold CodecLaws.KeyValueRepresentable CodecLaws.UInt32
  decide
example : KeyValue.decode "" (KeyValue.ternary 255 0).toJson = .ok (.ternary 255 0) :=
  CodecLaws.keyValue_roundtrip _ _ (by trivial)
example : KeyValue.decode "" (KeyValue.lpm (10 ^ 100) 0).toJson = .ok (.lpm (10 ^ 100) 0) :=
  CodecLaws.keyValue_roundtrip _ _ (by
    unfold CodecLaws.KeyValueRepresentable CodecLaws.UInt32
    decide)
example : KeyValue.decode "" (KeyValue.lpm 0 (2 ^ 32)).toJson =
    .error "lpm.prefix_len: 4294967296 does not fit in uint32" := by
  change (do
    let value ← Decode.decimal "lpm.value" (toString (0 : Nat))
    let prefixLen ← Decode.uint32 "lpm.prefix_len" (toJson (2 ^ 32 : Nat))
    pure (KeyValue.lpm value prefixLen)) = _
  rw [CodecLaws.decimal_toString]
  change (do
    let prefixLen ← Decode.uint32 "lpm.prefix_len" (toJson (2 ^ 32 : Nat))
    pure (KeyValue.lpm 0 prefixLen)) = _
  rw [CodecLaws.uint32_toJson_reject _ _ (by unfold CodecLaws.UInt32; decide)]
  rfl

def nestedExpression : Expr := .mux (.literal (.boolean false))
  (.binary .sub (.member (.var "x") "field")
    (.index (.var "array") (.literal (.bits 0 (10 ^ 100)))))
  (.slice (.var "fallback") 1 2)

theorem nestedExpression_representable : CodecLaws.ExprRepresentable nestedExpression := by
  simp [nestedExpression, CodecLaws.ExprRepresentable, CodecLaws.LiteralRepresentable,
    CodecLaws.UInt32]

example (path : String) : Expr.decode path nestedExpression.toJson = .ok nestedExpression :=
  CodecLaws.expr_roundtrip path nestedExpression nestedExpression_representable

example : ¬ CodecLaws.ExprRepresentable (.lookahead (.bits (2 ^ 32))) := by
  simp [CodecLaws.ExprRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]

example : Expr.decode "test" (Json.mkObj [("member", Json.mkObj [])]) =
    .error "test.member.base: no kind set" := by
  rw [Expr.decode_unfold]
  change Expr.decode "test.member.base" (Json.mkObj []) >>= _ = _
  rw [Expr.decode_unfold]
  rfl

def nestedLValue : LValue := .member
  (.index (.next (.next (.var ""))) nestedExpression) ""

theorem nestedLValue_representable : CodecLaws.LValueRepresentable nestedLValue := by
  simp [nestedLValue, CodecLaws.LValueRepresentable, nestedExpression_representable]

example (path : String) : LValue.decode path nestedLValue.toJson = .ok nestedLValue :=
  CodecLaws.lvalue_roundtrip path nestedLValue nestedLValue_representable

example (path : String) : Arg.decode path (Arg.lvalue nestedLValue).toJson =
    .ok (.lvalue nestedLValue) :=
  CodecLaws.arg_roundtrip path _ nestedLValue_representable

example (path : String) : Arg.decode path (Arg.expr nestedExpression).toJson =
    .ok (.expr nestedExpression) :=
  CodecLaws.arg_roundtrip path _ nestedExpression_representable

example : ¬ CodecLaws.LValueRepresentable
    (.index (.var "array") (.lookahead (.bits (2 ^ 32)))) := by
  simp [CodecLaws.LValueRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]

example : LValue.decode "test" (Json.mkObj [("next", Json.mkObj [])]) =
    .error "test.next.stack: no kind set" := by
  rw [LValue.decode_unfold]
  change LValue.next <$> LValue.decode "test.next.stack" (Json.mkObj []) = _
  rw [LValue.decode_unfold]
  rfl

/-- A separate semantic observation, not the production wire encoder. -/
def literalValue : Literal → Json
  | .bits width value => Json.mkObj
      [("tag", .str "bits"), ("width", toJson width), ("value", .str (toString value))]
  | .boolean value => Json.mkObj [("tag", .str "boolean"), ("value", .bool value)]
  | .enumMember enumType member => Json.mkObj
      [("tag", .str "enum_member"), ("enum_type", .str enumType), ("member", .str member)]
  | .error name => Json.mkObj [("tag", .str "error"), ("name", .str name)]

def typeValue : Ty → Json
  | .bits width => Json.mkObj [("tag", .str "bits"), ("width", toJson width)]
  | .boolean => Json.mkObj [("tag", .str "boolean")]
  | .header name => Json.mkObj [("tag", .str "header"), ("name", .str name)]
  | .struct name => Json.mkObj [("tag", .str "struct"), ("name", .str name)]
  | .enumType name => Json.mkObj [("tag", .str "enum_type"), ("name", .str name)]
  | .error => Json.mkObj [("tag", .str "error")]
  | .stack header size => Json.mkObj
      [("tag", .str "stack"), ("header", .str header), ("size", toJson size)]

def keyValue : KeyValue → Json
  | .exact value => Json.mkObj [("tag", .str "exact"), ("value", .str (toString value))]
  | .lpm value prefixLen => Json.mkObj
      [("tag", .str "lpm"), ("value", .str (toString value)), ("prefix_len", toJson prefixLen)]
  | .ternary value mask => Json.mkObj
      [("tag", .str "ternary"), ("value", .str (toString value)), ("mask", .str (toString mask))]

/-- Independent constructor observations: never consult the production wire
enum table, which both encoder and decoder can get consistently wrong. -/
def unaryOpValue : UnaryOp → String
  | .not => "UNARY_OP_NOT"
  | .complement => "UNARY_OP_COMPLEMENT"
  | .negate => "UNARY_OP_NEGATE"

def binaryOpValue : BinaryOp → String
  | .add => "BINARY_OP_ADD"
  | .sub => "BINARY_OP_SUB"
  | .mul => "BINARY_OP_MUL"
  | .addSat => "BINARY_OP_ADD_SAT"
  | .subSat => "BINARY_OP_SUB_SAT"
  | .bitAnd => "BINARY_OP_BIT_AND"
  | .bitOr => "BINARY_OP_BIT_OR"
  | .bitXor => "BINARY_OP_BIT_XOR"
  | .shl => "BINARY_OP_SHL"
  | .shr => "BINARY_OP_SHR"
  | .concat => "BINARY_OP_CONCAT"
  | .eq => "BINARY_OP_EQ"
  | .ne => "BINARY_OP_NE"
  | .lt => "BINARY_OP_LT"
  | .le => "BINARY_OP_LE"
  | .gt => "BINARY_OP_GT"
  | .ge => "BINARY_OP_GE"
  | .and => "BINARY_OP_AND"
  | .or => "BINARY_OP_OR"

def exprValue : Expr → Json
  | .literal value => Json.mkObj [("tag", .str "literal"), ("value", literalValue value)]
  | .var name => Json.mkObj [("tag", .str "var"), ("name", .str name)]
  | .member base field => Json.mkObj
      [("tag", .str "member"), ("base", exprValue base), ("field", .str field)]
  | .index base index => Json.mkObj
      [("tag", .str "index"), ("base", exprValue base), ("index", exprValue index)]
  | .lastIndex stack => Json.mkObj [("tag", .str "last_index"), ("stack", exprValue stack)]
  | .unary op operand => Json.mkObj
      [("tag", .str "unary"), ("op", .str (unaryOpValue op)), ("operand", exprValue operand)]
  | .binary op left right => Json.mkObj
      [("tag", .str "binary"), ("op", .str (binaryOpValue op)),
       ("left", exprValue left), ("right", exprValue right)]
  | .cast to operand => Json.mkObj
      [("tag", .str "cast"), ("to", typeValue to), ("operand", exprValue operand)]
  | .slice operand hi lo => Json.mkObj
      [("tag", .str "slice"), ("operand", exprValue operand), ("hi", toJson hi), ("lo", toJson lo)]
  | .isValid header => Json.mkObj [("tag", .str "is_valid"), ("header", exprValue header)]
  | .mux condition then_ otherwise => Json.mkObj
      [("tag", .str "mux"), ("condition", exprValue condition),
       ("then", exprValue then_), ("otherwise", exprValue otherwise)]
  | .lookahead type => Json.mkObj [("tag", .str "lookahead"), ("type", typeValue type)]

def lvalueValue : LValue → Json
  | .var name => Json.mkObj [("tag", .str "var"), ("name", .str name)]
  | .member base field => Json.mkObj
      [("tag", .str "member"), ("base", lvalueValue base), ("field", .str field)]
  | .index base index => Json.mkObj
      [("tag", .str "index"), ("base", lvalueValue base), ("index", exprValue index)]
  | .next stack => Json.mkObj [("tag", .str "next"), ("stack", lvalueValue stack)]

def argValue : Arg → Json
  | .expr value => Json.mkObj [("tag", .str "expr"), ("value", exprValue value)]
  | .lvalue value => Json.mkObj [("tag", .str "lvalue"), ("value", lvalueValue value)]

/-- Independent constructor observation; never derives tags/order from toJson. -/
def stmtValue : Stmt → Json
  | .assign target value => Json.mkObj [("tag", .str "assign"),
      ("target", lvalueValue target), ("value", exprValue value)]
  | .conditional condition thenBranch otherwise => Json.mkObj [("tag", .str "conditional"),
      ("condition", exprValue condition), ("then", toJson (thenBranch.map stmtValue)),
      ("otherwise", toJson (otherwise.map stmtValue))]
  | .apply table hit => Json.mkObj [("tag", .str "apply"), ("table", .str table),
      ("hit", hit.map lvalueValue |>.getD .null)]
  | .callAction action args => Json.mkObj [("tag", .str "call_action"),
      ("action", .str action), ("args", toJson (args.map argValue))]
  | .callBlock block args => Json.mkObj [("tag", .str "call_block"),
      ("block", .str block), ("args", toJson (args.map argValue))]
  | .callExtern inst method args result => Json.mkObj [("tag", .str "call_extern"),
      ("instance", .str inst), ("method", .str method), ("args", toJson (args.map argValue)),
      ("result", result.map lvalueValue |>.getD .null)]
  | .setValid header => Json.mkObj [("tag", .str "set_valid"), ("header", lvalueValue header)]
  | .setInvalid header => Json.mkObj [("tag", .str "set_invalid"), ("header", lvalueValue header)]
  | .push stack count => Json.mkObj [("tag", .str "push"), ("stack", lvalueValue stack), ("count", toJson count)]
  | .pop stack count => Json.mkObj [("tag", .str "pop"), ("stack", lvalueValue stack), ("count", toJson count)]
  | .extract target => Json.mkObj [("tag", .str "extract"), ("target", lvalueValue target)]
  | .advance bits => Json.mkObj [("tag", .str "advance"), ("bits", exprValue bits)]
  | .verify condition error => Json.mkObj [("tag", .str "verify"),
      ("condition", exprValue condition), ("error", .str error)]
  | .emit value => Json.mkObj [("tag", .str "emit"), ("value", exprValue value)]

/-- Test-only access to actual syntax decoding/encoding, without validation. -/
def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  match kind with
  | "literal" =>
    let value ← Literal.decode "leaf" wire
    pure (Json.mkObj [("value", literalValue value), ("encoded", value.toJson)])
  | "type" =>
    let value ← Ty.decode "leaf" wire
    pure (Json.mkObj [("value", typeValue value), ("encoded", value.toJson)])
  | "key" =>
    let value ← KeyValue.decode "leaf" wire
    pure (Json.mkObj [("value", keyValue value), ("encoded", value.toJson)])
  | "expr" =>
    let value ← Expr.decode "leaf" wire
    pure (Json.mkObj [("value", exprValue value), ("encoded", value.toJson)])
  | "lvalue" =>
    let value ← LValue.decode "leaf" wire
    pure (Json.mkObj [("value", lvalueValue value), ("encoded", value.toJson)])
  | "arg" =>
    let value ← Arg.decode "leaf" wire
    pure (Json.mkObj [("value", argValue value), ("encoded", value.toJson)])
  | "stmt" =>
    let value ← Stmt.decode "leaf" wire
    pure (Json.mkObj [("value", stmtValue value), ("encoded", value.toJson)])
  | _ => throw "unsupported test leaf kind"

def tests : T Unit := do
  for n in [0, 1, 9, 10, 99, 100, 2 ^ 32 - 1, 2 ^ 32, 10 ^ 100 + 7] do
    checkOk s!"codec decimal known answer {n}"
      (Decode.decimal "value" (toString n)) (· == n)
    checkOk s!"codec unbounded decimal literal {n}"
      (Literal.decode "" (Literal.bits 0 n).toJson) (· == .bits 0 n)
  for width in [0, 1, 2 ^ 32 - 1] do
    checkOk s!"codec uint32 width {width}"
      (Ty.decode "" (Ty.bits width).toJson) (· == .bits width)
  checkError "codec uint32 rejects first overflow"
    (Ty.decode "" (Ty.bits (2 ^ 32)).toJson) "does not fit in uint32"
  checkError "codec literal width rejects first overflow"
    (Literal.decode "" (Literal.bits (2 ^ 32) 0).toJson) "does not fit in uint32"
  checkOk "codec false oneof remains set"
    (Literal.decode "" (Json.mkObj [("boolean", .bool false)])) (· == .boolean false)
  checkOk "codec empty error oneof remains set"
    (Literal.decode "" (Json.mkObj [("error", .str "")])) (· == .error "")
  checkOk "codec omitted width accepts explicit decimal zero"
    (Literal.decode "" (Json.mkObj [("bits", Json.mkObj [("value", .str "0")])]))
    (· == .bits 0 0)
  for wire in [Json.mkObj [], Json.mkObj [("value", .null)]] do
    checkError "codec missing/null decimal does not mean zero"
      (Literal.decode "" (Json.mkObj [("bits", wire)])) "empty string"
  for bad in ["", "+1", "-1", " 1", "1 ", "0x1", "١"] do
    checkError s!"codec rejects nondecimal {repr bad}" (Decode.decimal "value" bad) "decimal"
  checkOk "codec leading zero normalization is not wire identity"
    (Decode.decimal "value" "0007") (· == 7)
  for n in [0, 1, 2 ^ 32, 10 ^ 100 + 7] do
    checkOk s!"codec exact key {n}"
      (KeyValue.decode "" (KeyValue.exact n).toJson) (· == .exact n)
    checkOk s!"codec zero-prefix key {n}"
      (KeyValue.decode "" (KeyValue.lpm n 0).toJson) (· == .lpm n 0)
  for (value, mask) in [(0, 0), (0, 255), (255, 0), (3, 12), (10 ^ 100, 2 ^ 32)] do
    checkOk s!"codec ternary preserves independent components {value}/{mask}"
      (KeyValue.decode "" (KeyValue.ternary value mask).toJson) (· == .ternary value mask)
  checkOk "codec LPM max uint32 prefix is representable"
    (KeyValue.decode "" (KeyValue.lpm 1 (2 ^ 32 - 1)).toJson) (· == .lpm 1 (2 ^ 32 - 1))
  checkError "codec LPM first overflow is unrepresentable"
    (KeyValue.decode "" (KeyValue.lpm 0 (2 ^ 32)).toJson) "does not fit in uint32"
  checkOk "codec ternary independently named payload"
    (KeyValue.decode "" (Json.mkObj [("ternary", Json.mkObj
      [("value", .str "3"), ("mask", .str "12")])])) (· == .ternary 3 12)
  let left := Json.mkObj [("var", .str "left")]
  let right := Json.mkObj [("var", .str "right")]
  checkOk "codec unary constructor independent of production enum names"
    (Expr.decode "" (Json.mkObj [("unary", Json.mkObj
      [("op", .str "UNARY_OP_NOT"), ("operand", left)])]))
    (· == .unary .not (.var "left"))
  checkOk "codec recursive binary independently ordered operands"
    (Expr.decode "" (Json.mkObj [("binary", Json.mkObj
      [("op", .str "BINARY_OP_SUB"), ("left", left), ("right", right)])]))
    (· == .binary .sub (.var "left") (.var "right"))
  checkOk "codec recursive index independently ordered operands"
    (Expr.decode "" (Json.mkObj [("index", Json.mkObj [("base", left), ("index", right)])]))
    (· == .index (.var "left") (.var "right"))
  checkOk "codec recursive mux independently ordered branches"
    (Expr.decode "" (Json.mkObj [("mux", Json.mkObj
      [("condition", Json.mkObj [("literal", Json.mkObj [("boolean", .bool false)])]),
       ("then", left), ("otherwise", right)])]))
    (· == .mux (.literal (.boolean false)) (.var "left") (.var "right"))
  checkOk "codec nested invalid-but-representable expression"
    (Expr.decode "" nestedExpression.toJson) (· == nestedExpression)
  check "codec missing nested message retains exact path"
    (match Expr.decode "test" (Json.mkObj [("member", Json.mkObj [])]) with
     | .error message => message == "test.member.base: no kind set"
     | .ok _ => false)
  check "codec oneof diagnostics precede child decoding"
    (match Expr.decode "test" (Json.mkObj [("var", .num 1), ("literal", .num 2)]) with
     | .error message => message == "test: more than one kind set: [literal, var]"
     | .ok _ => false)
  checkOk "codec lvalue index independently ordered operands"
    (LValue.decode "" (Json.mkObj [("index", Json.mkObj [("base", left), ("index", right)])]))
    (· == .index (.var "left") (.var "right"))
  checkOk "codec lvalue next and member independent shape"
    (LValue.decode "" (Json.mkObj [("member", Json.mkObj
      [("base", Json.mkObj [("next", Json.mkObj [("stack", left)])]),
       ("field", .str "field")])]))
    (· == .member (.next (.var "left")) "field")
  checkOk "codec arg expr independent branch"
    (Arg.decode "" (Json.mkObj [("expr", left)])) (· == .expr (.var "left"))
  checkOk "codec arg lvalue independent branch"
    (Arg.decode "" (Json.mkObj [("lvalue", left)])) (· == .lvalue (.var "left"))
  checkOk "codec nested invalid-but-representable lvalue"
    (LValue.decode "" nestedLValue.toJson) (· == nestedLValue)
  checkOk "codec nested invalid-but-representable argument"
    (Arg.decode "" (Arg.lvalue nestedLValue).toJson) (· == .lvalue nestedLValue)
  check "codec lvalue missing stack retains exact path"
    (match LValue.decode "test" (Json.mkObj [("next", Json.mkObj [])]) with
     | .error message => message == "test.next.stack: no kind set"
     | .ok _ => false)
  check "codec lvalue index reports base error first"
    (match LValue.decode "test" (Json.mkObj [("index", Json.mkObj
      [("base", Json.mkObj []), ("index", Json.mkObj [])])]) with
     | .error message => message == "test.index.base: no kind set"
     | .ok _ => false)
  check "codec arg oneof diagnostics retain declared order"
    (match Arg.decode "test" (Json.mkObj [("expr", Json.mkObj []),
      ("lvalue", Json.mkObj [])]) with
     | .error message => message == "test: more than one kind set: [expr, lvalue]"
     | .ok _ => false)
  let c := Json.mkObj [("var", .str "condition")]
  let emit := Json.mkObj [("emit", Json.mkObj [("value", Json.mkObj [("var", .str "first")])])]
  let invalid := Json.mkObj [("set_invalid", Json.mkObj [("header", Json.mkObj [("var", .str "last")])])]
  let conditional := Json.mkObj [("conditional", Json.mkObj [("condition", c),
    ("then", .arr #[emit, invalid]), ("otherwise", .arr #[invalid])])]
  checkOk "codec stmt unequal branches retain constructor and order" (Stmt.decode "test" conditional)
    (· == .conditional (.var "condition") [.emit (.var "first"), .setInvalid (.var "last")]
      [.setInvalid (.var "last")])
  checkOk "codec stmt set-valid is independently anchored"
    (Stmt.decode "test" (Json.mkObj [("set_valid", Json.mkObj [("header", Json.mkObj [("var", .str "h")])])]))
    (· == .setValid (.var "h"))
  check "codec stmt recursive array reports first failing index"
    (match Stmt.decode "test" (Json.mkObj [("conditional", Json.mkObj [("condition", c),
      ("then", .arr #[emit, Json.mkObj []]), ("otherwise", .bool false)])]) with
     | .error message => message == "test.conditional.then[1]: no kind set"
     | .ok _ => false)
  checkOk "codec stmt null arrays retain empty default"
    (Stmt.decode "test" (Json.mkObj [("conditional", Json.mkObj [("condition", c),
      ("then", .null), ("otherwise", .null)])]))
    (· == .conditional (.var "condition") [] [])

end CodecLawTests
