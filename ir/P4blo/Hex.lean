/-!
# Hex encoding of packets

The differential-testing pipe and the vector fixtures carry packets as hex
strings, two digits per byte, as STF writes them.
-/

namespace P4blo

/-- The value of a hex digit. -/
def hexDigit? (c : Char) : Option Nat :=
  if '0' ≤ c && c ≤ '9' then some (c.toNat - '0'.toNat)
  else if 'a' ≤ c && c ≤ 'f' then some (c.toNat - 'a'.toNat + 10)
  else if 'A' ≤ c && c ≤ 'F' then some (c.toNat - 'A'.toNat + 10)
  else none

/-- The bytes a hex string spells; whitespace is ignored, an odd digit
count or a non-digit is an error. -/
def hexToBytes? (s : String) : Except String ByteArray := do
  let digits := s.toList.filter (!·.isWhitespace)
  if digits.length % 2 != 0 then throw s!"{digits.length} hex digits is not whole bytes"
  let rec go : List Char → List UInt8 → Except String (List UInt8)
    | [], acc => pure acc.reverse
    | hi :: lo :: rest, acc => do
      let some h := hexDigit? hi | throw s!"'{hi}' is not a hex digit"
      let some l := hexDigit? lo | throw s!"'{lo}' is not a hex digit"
      go rest (UInt8.ofNat (h * 16 + l) :: acc)
    | [_], _ => throw "odd number of hex digits"
  pure ⟨(← go digits []).toArray⟩

/-- The lower-case hex spelling of `bytes`. -/
def bytesToHex (bytes : ByteArray) : String :=
  let digit (n : Nat) : Char := if n < 10 then Char.ofNat ('0'.toNat + n) else Char.ofNat ('a'.toNat + n - 10)
  String.ofList (bytes.toList.flatMap fun b => [digit (b.toNat / 16), digit (b.toNat % 16)])

end P4blo
