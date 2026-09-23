import P4blo.ForwardPolicy

namespace P4blo.ForwardPolicyTests

open ForwardPolicy

def input : Snapshot :=
  ⟨0x112233445566, 0x778899aabbcc, 0x86dd, false,
    202, 17, 0xfedc, true, 509, false, 0x9876, true,
    0x123456789abc, 0xcba987654321, 511, 213⟩

/-- Independent named expected full state; notably checksum and header
validity are untouched even when stored Ethernet fields are rewritten. -/
def forwarded : Snapshot :=
  ⟨0x123456789abc, 0xcba987654321, 0x86dd, false,
    201, 17, 0xfedc, true, 511, false, 0x9876, true,
    0x123456789abc, 0xcba987654321, 511, 213⟩

/-- Independent constructor anchor, not a call to restore or source refs. -/
def manual : Fields.Store FieldCommandExamples.roots :=
  .cons (.aggregate () (.cons (.aggregate false
    (.cons (.scalar 0x112233445566) (.cons (.scalar 0x778899aabbcc) (.cons (.scalar 0x86dd) .nil))))
    (.cons (.aggregate true
      (.cons (.scalar 202) (.cons (.scalar 17) (.cons (.scalar 0xfedc) .nil)))) .nil)))
  (.cons (.aggregate () (.cons (.scalar 509) (.cons (.scalar false) (.cons (.scalar 0x9876) .nil))))
  (.cons (.aggregate () (.cons (.scalar true) (.cons (.scalar 0x123456789abc)
    (.cons (.scalar 0xcba987654321) (.cons (.scalar 511) .nil)))))
  (.cons (.scalar 213) .nil)))

-- These anchors check the meaning assigned to each position independently
-- of the paired reconstruction/observation laws.
example : observe manual = input := rfl
example : restore input = manual := rfl

def cases : List (String × Snapshot × Snapshot) :=
  [("arbitrary-forward", input, forwarded),
   ("already-drop-forward", { input with drop := true }, forwarded),
   ("miss", { input with routeHit := false }, { input with routeHit := false, drop := true }),
   ("zero", { input with ttl := 0 }, { input with ttl := 0, drop := true }),
   ("one", { input with ttl := 1 }, { input with ttl := 1, drop := true }),
   ("two", { input with ttl := 2 }, { forwarded with ttl := 1 }),
   ("max", { input with ttl := 255 }, { forwarded with ttl := 254 })]

def run : IO Unit := do
  unless observe manual == input do
    throw (IO.userError "independent forwarding observation anchor")
  for (name, source, expected) in cases do
    unless policy source == expected do
      throw (IO.userError s!"independent forwarding policy: {name}")
    unless observe (restore source) == source do
      throw (IO.userError s!"forwarding complete observation: {name}")
    unless observe (FieldCommandExamples.forward.denote (restore source)) == expected do
      throw (IO.userError s!"authored forwarding source: {name}")
    let initial := FieldCommandExamples.initial (restore source)
    let (result, final) := (P4bloIR.execute FieldCommandExamples.forward.lower).run initial
    match result with
    | .error _ => throw (IO.userError s!"actual forwarding execution: {name}")
    | .ok () => pure ()
    for root in ["hdr", "meta", "route", "scratch"] do
      unless final.frame.read? root == (restore expected).bindings[root]? do
        throw (IO.userError s!"actual forwarding complete root {root}: {name}")
    unless final.frame.read? "outside" == initial.frame.read? "outside" do
      throw (IO.userError s!"actual forwarding unrelated root: {name}")
  IO.println "7 independent forwarding policy/source/runtime answers passed"

end P4blo.ForwardPolicyTests
