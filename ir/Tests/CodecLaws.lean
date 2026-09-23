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

/-- Test-only access to actual leaf decoding/encoding, without validation. -/
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

end CodecLawTests
