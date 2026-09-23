import P4bloIR.Json

/- Diagnostic-only control for the pinned `partial_fixpoint` alternative.
These Nat probes are not codecs. The expected failure deliberately remains
unguarded so the documented command exits 1 with the monotonicity obligation. -/
namespace CodecFixpointProbe

def tail (n : Nat) : Except String Nat :=
  if n = 0 then .ok 0 else tail (n - 1)
partial_fixpoint

#print axioms tail.eq_def

def nested (n : Nat) : Except String Nat := do
  if n = 0 then pure 0
  else
    let value ← nested (n - 1)
    pure (value + 1)
partial_fixpoint

end CodecFixpointProbe
