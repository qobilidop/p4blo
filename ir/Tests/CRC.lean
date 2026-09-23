import Tests.Check
import P4blo.Observe

open P4blo

namespace CRCTests

def declaration (name : String) (inputWidth outputWidth : Nat) : ExternType :=
  { name, constructorParams := [], methods := [
    { name := "compute"
      params := [{ name := "data", direction := .«in», type := .bits inputWidth }]
      returns := some (.bits outputWidth) }] }

def bindOne (decl : ExternType) : Except String Externs := do
  let index ← Index.build { (default : Program) with
    externTypes := [decl]
    externInstances := [{ name := "hash", externType := decl.name, args := [] }] }
  Externs.bind index

def tests : T Unit := do
  let vectors := [(104, 0x0a0000010a0000023039005006, 0x17c6, 0x7dd597c3),
    (104, 0, 0, 0x0f744682), (104, 0xffffffffffffffffffffffffff, 0x7f01, 0xf2d6f3c1),
    (72, 0x313233343536373839, 0xbb3d, 0xcbf43926),
    (8, 0, 0, 0xd202ef8d), (8, 255, 0x4040, 0xff000000),
    (16, 1, 0xc0c1, 0x36de2269), (8, 1, 0xc0c1, 0xa505df1b),
    (16, 0, 0, 0x41d912ff)]
  for (width, value, expected16, expected32) in vectors do
    check s!"CRC16 known answer width {width} value {value}" (crc16 width value == expected16)
    check s!"CRC32 known answer width {width} value {value}" (crc32 width value == expected32)
  for (family, outputWidth) in [("crc16", 16), ("crc32", 32)] do
    for width in [0, 1, 7, 9, 103, 105] do
      checkError s!"{family} rejects width {width}"
        (bindOne (declaration s!"{family}.bad" width outputWidth))
        "data width must be a positive multiple of 8"
    for suffix in ["", ".104", ".multiple.dots"] do
      checkOk s!"{family}{suffix} binds"
        ((bindOne (declaration (family ++ suffix) 104 outputWidth)).map (·.instances.size))
        (· == 1)
    checkError s!"{family} rejects wrong output width"
      (bindOne (declaration family 104 (outputWidth + 1))) "expected bit"
  checkError "CRC16 rejects mismatched bound width"
    ((ExternState.crc16 8).call "compute" [.bits (Bits.wrap 16 1)]) "bound width"
  checkError "CRC32 rejects mismatched bound width"
    ((ExternState.crc32 8).call "compute" [.bits (Bits.wrap 16 1)]) "bound width"
  checkOk "CRC16 call returns full answer and stateless observation"
    ((ExternState.crc16 72).call "compute" [.bits (Bits.wrap 72 0x313233343536373839)])
    (fun (s, result) => result.returns == some (.bits (Bits.wrap 16 0xbb3d)) &&
      s.observe == Lean.Json.mkObj [("kind", .str "crc16")])
  checkOk "CRC32 call returns full answer and stateless observation"
    ((ExternState.crc32 72).call "compute" [.bits (Bits.wrap 72 0x313233343536373839)])
    (fun (s, result) => result.returns == some (.bits (Bits.wrap 32 0xcbf43926)) &&
      s.observe == Lean.Json.mkObj [("kind", .str "crc32")])

end CRCTests
