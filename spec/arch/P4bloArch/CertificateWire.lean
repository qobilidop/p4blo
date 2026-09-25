import P4bloArch.Assembly
import P4bloArch.Certificate
import P4bloIR.Json
import P4bloIR.Hex

/-!
# Wire boundary for the fixed stateful certificate experiment

The artifact carries the actual program, canonical initial values, budget,
and tagged observation. Only `P4bloArch.Certificate.Example.program` is
accepted; this is not a general program or switch verifier. Decoding and
the compiled runtime remain outside `ExecutionCertificate.check_sound`.
-/

namespace P4bloArch.CertificateWire

open P4bloIR

open Lean (Json)
open P4bloIR.ExecutionCertificate P4bloArch.Certificate

private def pair (j : Json) : Except String (Json × Json) := do
  let values ← j.getArr?
  if values.size != 2 then throw "expected a pair"
  pure (values[0]!, values[1]!)

private def natural (j : Json) : Except String Nat := do
  let s ← j.getStr?
  if !s.startsWith "0x" then throw "expected a canonical hexadecimal natural"
  let digits := (s.drop 2).toString
  if digits.isEmpty then throw "empty hexadecimal natural"
  let n ← digits.toList.foldlM (fun n c => do
    let some digit := hexDigit? c | throw "invalid hexadecimal digit"
    pure (n * 16 + digit)) 0
  if "0x" ++ String.ofList (Nat.toDigits 16 n) != s then
    throw "noncanonical hexadecimal natural"
  pure n

private def naturals (j : Json) : Except String (List Nat) := do
  (← j.getArr?).toList.mapM natural

private def optional (decode : Json → Except String α) (j : Json) : Except String (Option α) :=
  match j with
  | .null => pure none
  | _ => some <$> decode j

private def completion (j : Json) : Except String Example.Completion := do
  match ← (← j.getObjVal? "kind").getStr? with
  | "success" => pure .success
  | "interp" => pure (.interp (← (← j.getObjVal? "message").getStr?))
  | "parse" => pure (.parse (← (← j.getObjVal? "message").getStr?))
  | _ => throw "unknown completion kind"

private def register (j : Json) : Except String (Nat × List Nat) := do
  let (width, cells) ← pair j
  pure (← width.getNat?, ← naturals cells)

private def localValue (j : Json) : Except String (Nat × Nat) := do
  let (width, value) ← pair j
  pure (← width.getNat?, ← natural value)

private def observation (j : Json) : Except String Example.Observation := do
  pure {
    completion := ← completion (← j.getObjVal? "completion"),
    register := ← optional register (← j.getObjVal? "register"),
    counter := ← optional naturals (← j.getObjVal? "counter"),
    localValue := ← optional localValue (← j.getObjVal? "local") }

/-- Verify the fixed experiment's concrete program and complete claimed
observation. Reexecution uses the proven checker; the second bounded run
only distinguishes mismatch from budget exhaustion for diagnostics. -/
def verify (artifact : Json) : Except String String := do
  if (← (← artifact.getObjVal? "format").getStr?) != "p4blo.example-certificate" then
    throw "unknown certificate format"
  if (← (← artifact.getObjVal? "version").getNat?) != 1 then
    throw "unknown certificate version"
  if (← (← artifact.getObjVal? "example").getStr?) != "register-counter-v1" then
    throw "unknown certificate example"
  let program ← BlockAssembly.decode "program" (← artifact.getObjVal? "program")
  if program != Example.program then throw "certificate program is not the fixed example"
  let (reg, count) ← pair (← artifact.getObjVal? "initial")
  let initial ← Example.initial (← natural reg) (← natural count)
  let fuel ← (← artifact.getObjVal? "fuel").getNat?
  let claim ← observation (← artifact.getObjVal? "claim")
  if check fuel initial Example.observe claim then return "accepted"
  match bounded fuel initial with
  | .exhausted => pure "exhausted"
  | .finished _ => pure "mismatch"

end P4bloArch.CertificateWire
