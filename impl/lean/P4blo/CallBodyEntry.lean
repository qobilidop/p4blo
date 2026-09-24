import P4blo.CallEntry
import P4blo.GuardedForwardPolicy

/-! Exact selected guarded-wrapper syntax, for a body-bearing entry witness.
The observer is test scaffolding; neither it nor the initializers execute in
this checkpoint. No caller/full-program identity or validity is claimed. -/

namespace P4blo.CallBodyEntry
open P4bloIR

private def member (root : String) (path : List String) : Expr :=
  path.foldl Expr.member (.var root)

private def boolByte (value : Expr) : Expr := .cast (.bits 1) value

private def valid (name : String) : Expr :=
  let header := member "hdr" [name]
  boolByte (.isValid (.mux (.literal (.boolean true)) header header))

/-- This list is independently checked against the real Python wrapper,
including order, casts and the test-only identity header muxes. -/
def observations : List (String × Nat × Expr) :=
  [("dst", 48, member "hdr" ["ethernet", "dst"]),
   ("src", 48, member "hdr" ["ethernet", "src"]),
   ("etherType", 16, member "hdr" ["ethernet", "etherType"]),
   ("ethernetValid", 8, valid "ethernet"),
   ("ttl", 8, member "hdr" ["ipv4", "ttl"]),
   ("protocol", 8, member "hdr" ["ipv4", "protocol"]),
   ("checksum", 16, member "hdr" ["ipv4", "checksum"]),
   ("ipv4Valid", 8, valid "ipv4"),
   ("port", 16, member "meta" ["port"]),
   ("drop", 8, boolByte (member "meta" ["drop"])),
   ("sentinel", 16, member "meta" ["sentinel"]),
   ("routeHit", 8, boolByte (member "route" ["hit"])),
   ("routeDst", 48, member "route" ["dst"]),
   ("routeSrc", 48, member "route" ["src"]),
   ("routePort", 16, member "route" ["port"]),
   ("scratch", 8, .var "scratch"),
   ("unrelated", 8, .var "unrelated")]

def observerSuffix : List Stmt := observations.map fun (name, width, value) =>
  .assign (.member (.member (.var "observer") "result") name) (.cast (.bits width) value)

def initializers : List Stmt :=
  [.assign (.var "scratch") (.literal (.bits 8 19)),
   .assign (.var "unrelated") (.literal (.bits 8 165))]

def body : List Stmt := initializers ++ GuardedForwardPolicy.guardedForward.lower ++ observerSuffix

/-- Real Index.build, not the previous empty-body index with a substituted
runBlock work item. The common family discharges initialization once. -/
abbrev program := CallEntry.WithBody.program body
abbrev index := CallEntry.WithBody.index body
abbrev block := CallEntry.WithBody.block body

theorem index_built : Index.build program = .ok index := CallEntry.WithBody.index_built body
theorem block_lookup : index.blocks["RewriteBody"]? = some block := CallEntry.WithBody.block_lookup body
theorem body_nonempty : body ≠ [] := by decide +kernel

end P4blo.CallBodyEntry
