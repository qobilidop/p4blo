import P4bloArchTest.Check

/-! The reference extern families under actual control runs: binding,
persistence across runs, out-of-range policy and the checksum arithmetic. -/

open P4bloIR P4bloArch

namespace ExternTests

def lit (w v : Nat) : Expr := .literal (.bits w v)
def bin (op : BinaryOp) (a b : Expr) : Expr := .binary op a b
def bits (w v : Nat) : Value := .bits (Bits.wrap w v)

/-- A program declaring `register` (16-bit cells), `counter` and
`checksum16` with one instance each, and a control that reads and writes
them. -/
def externProgram : BlockLibrary :=
  { (default : BlockLibrary) with
    name := "x", errors := ["NoError"],
    structTypes := [{ name := "H", fields := [] },
                    { name := "M", fields := [{ name := "a", type := .bits 16 }, { name := "c", type := .bits 16 }] }],
    externTypes := [
      { name := "register", constructorParams := [{ name := "size", type := .bits 32, direction := .«in» }],
        methods := [{ name := "read", params := [{ name := "result", type := .bits 16, direction := .out },
                                                 { name := "index", type := .bits 32, direction := .«in» }], returns := none },
                    { name := "write", params := [{ name := "index", type := .bits 32, direction := .«in» },
                                                  { name := "value", type := .bits 16, direction := .«in» }], returns := none }] },
      { name := "counter", constructorParams := [{ name := "size", type := .bits 32, direction := .«in» }],
        methods := [{ name := "count", params := [{ name := "index", type := .bits 32, direction := .«in» }], returns := none }] },
      { name := "checksum16", constructorParams := [],
        methods := [{ name := "compute", params := [{ name := "data", type := .bits 64, direction := .«in» }],
                      returns := some (.bits 16) }] }],
    externInstances := [{ name := "r", externType := "register", args := [.bits 32 4] },
                        { name := "k", externType := "counter", args := [.bits 32 2] },
                        { name := "ck", externType := "checksum16", args := [] }],
    blocks := [{ (default : Block) with
      name := "C", kind := .control,
      params := [{ name := "hdr", type := .struct "H", direction := .inout },
                 { name := "meta", type := .struct "M", direction := .inout }],
      body := [
        -- meta.a += r[1]; r[1] = meta.a; count 1 twice and 9 once; meta.c = checksum of the RFC example
        .callExtern "r" "read" [.lvalue (.member (.var "meta") "c"), .expr (lit 32 1)] none,
        .assign (.member (.var "meta") "a") (bin .add (.member (.var "meta") "a") (.member (.var "meta") "c")),
        .callExtern "r" "write" [.expr (lit 32 1), .expr (.member (.var "meta") "a")] none,
        .callExtern "k" "count" [.expr (lit 32 1)] none,
        .callExtern "k" "count" [.expr (lit 32 1)] none,
        .callExtern "k" "count" [.expr (lit 32 9)] none,
        .callExtern "ck" "compute" [.expr (lit 64 0x0001f203f4f5f6f7)] (some (.member (.var "meta") "c"))] }] }

def tests : T Unit := do
  checkOk "RFC 1071 worked example" (pure (internetChecksum 64 0x0001f203f4f5f6f7) : Except String Nat)
    (· == (0xffff - 0xddf2))
  checkOk "checksum validates an IPv4 header"
    (do
      let header ← hexToBytes? "450000730000400040110000c0a80001c0a800c7"
      let sum := internetChecksum (header.size * 8) (bytesToNat header)
      let withSum ← hexToBytes? "45000073000040004011b861c0a80001c0a800c7"
      pure (sum, internetChecksum (withSum.size * 8) (bytesToNat withSum)))
    (· == (0xb861, 0))
  checkOk "checksum pads an odd width at the end"
    (pure (internetChecksum 8 0x12) : Except String Nat) (· == (0xffff - 0x1200))
  let runTwice : Except String (Value × Value × Externs) := do
    let index ← Index.build externProgram
    let externs ← P4bloArch.bind index
    let entries ← Installed.build index none
    let (_, m1, externs) ← runControl index "C" (.struct "H" []) (.struct "M" [bits 16 5, bits 16 0]) entries externs
    let (_, m2, externs) ← runControl index "C" (.struct "H" []) (.struct "M" [bits 16 7, bits 16 0]) entries externs
    pure (m1, m2, externs)
  checkOk "register state persists across runs; out args and return values are written back"
    (runTwice.map fun (m1, m2, _) => (m1, m2))
    (· == (.struct "M" [bits 16 5, bits 16 0x220d], .struct "M" [bits 16 12, bits 16 0x220d]))
  checkOk "counter counts in range and ignores out of range"
    (runTwice.map fun (_, _, e) => e.instances["k"]?.bind (·.counter?))
    (· == some #[0, 4])
  checkOk "register out of range reads zero and ignores writes"
    (do
      let (s, r) ← P4bloArch.call (.register 16 #[0, 0]) "read" [bits 16 0, bits 32 7]
      let (s, _) ← P4bloArch.call s "write" [bits 32 7, bits 16 1]
      pure (r.outs, s.register?))
    (· == ([bits 16 0], some (16, #[0, 0])))
  checkError "an unknown extern type does not bind"
    (Index.build { externProgram with
        externInstances := [{ name := "m", externType := "mystery", args := [] }],
        externTypes := externProgram.externTypes ++ [{ name := "mystery", constructorParams := [], methods := [] }] }
      >>= P4bloArch.bind)
    "no implementation"
  checkError "an inconsistent width variable does not bind"
    (Index.build { externProgram with externTypes := externProgram.externTypes.map fun t =>
        if t.name == "register" then { t with methods := t.methods.map fun m =>
          if m.name == "write" then { m with params := m.params.map fun p =>
            if p.name == "value" then { p with type := .bits 8 } else p } else m } else t }
      >>= P4bloArch.bind)
    "T is bit<16> elsewhere"
  checkError "an extra method does not bind"
    (Index.build { externProgram with externTypes := externProgram.externTypes.map fun t =>
        if t.name == "counter" then { t with methods := t.methods ++ [{ name := "clear", params := [], returns := none }] } else t }
      >>= P4bloArch.bind)
    "methods"
  checkError "a constructor argument must fit"
    (Index.build { externProgram with externInstances := externProgram.externInstances.map fun i =>
        if i.name == "k" then { i with args := [.bits 8 2] } else i }
      >>= P4bloArch.bind)
    "does not fit"


end ExternTests
