import P4blo.NamedFields
import P4blo.FieldCommandExamples

namespace P4blo.NamedFieldsTests

open Fields

private def namedDst : Place FieldCommandExamples.modes (.bits 48) :=
  Place.named ["hdr", "ethernet", "dst"]
private def namedSrc : Ref FieldCommandExamples.roots (.bits 48) :=
  Ref.named ["hdr", "ethernet", "src"]
private def namedTTL : Place FieldCommandExamples.modes (.bits 8) :=
  Place.named ["hdr", "ipv4", "ttl"]
private def namedRoutePort : Ref FieldCommandExamples.roots (.bits 9) :=
  Ref.named ["route", "port"]

-- Check actual constructed paths/lowered spellings, not just the requested
-- string or successful type inference. Same-width siblings must stay distinct.
example : namedDst.ref.segments = ["hdr", "ethernet", "dst"] :=
  (Place.named_sound (modes := FieldCommandExamples.modes) (t := .bits 48) _ (by decide +kernel)).1
example : namedTTL.ref.segments = ["hdr", "ipv4", "ttl"] :=
  (Place.named_sound (modes := FieldCommandExamples.modes) (t := .bits 8) _ (by decide +kernel)).1
example : namedSrc.expr = .member (.member (.var "hdr") "ethernet") "src" := by
  apply Option.some.inj
  exact Ref.named_expr (roots := FieldCommandExamples.roots) (t := .bits 48) _ (by decide +kernel)
example : namedDst.ref.lvalue = .member (.member (.var "hdr") "ethernet") "dst" := by
  apply Option.some.inj
  exact Place.named_lvalue (modes := FieldCommandExamples.modes) (t := .bits 48) _ (by decide +kernel)
example : namedRoutePort.expr = .member (.var "route") "port" := by
  apply Option.some.inj
  exact Ref.named_expr (roots := FieldCommandExamples.roots) (t := .bits 9) _ (by decide +kernel)

private def first : Layout := .cons "other" (.scalar (.bits 8))
  (.cons "wanted" (.scalar (.bits 8)) .nil)
private def reordered : Layout := .cons "wanted" (.scalar (.bits 8))
  (.cons "other" (.scalar (.bits 8)) .nil)
private def firstRoots : Layout := .cons "root" (.aggregate .struct "Pair" first) .nil
private def reorderedRoots : Layout := .cons "root" (.aggregate .struct "Pair" reordered) .nil
private def firstRef : Ref firstRoots (.bits 8) := Ref.named ["root", "wanted"]
private def reorderedRef : Ref reorderedRoots (.bits 8) := Ref.named ["root", "wanted"]

private theorem firstSpelling : firstRef.expr = .member (.var "root") "wanted" := by
  apply Option.some.inj
  exact Ref.named_expr (roots := firstRoots) (t := .bits 8) _ (by decide +kernel)
private theorem reorderedSpelling : reorderedRef.expr = .member (.var "root") "wanted" := by
  apply Option.some.inj
  exact Ref.named_expr (roots := reorderedRoots) (t := .bits 8) _ (by decide +kernel)
example : firstRef.expr = reorderedRef.expr := firstSpelling.trans reorderedSpelling.symm
example : firstRef.expr = .member (.var "root") "wanted" := firstSpelling
example : firstRef.segments = ["root", "wanted"] :=
  (Ref.named_sound (roots := firstRoots) (t := .bits 8) _ (by decide +kernel)).1

private def duplicateRoots : Layout := .cons "x" (.scalar (.bits 8))
  (.cons "x" (.scalar .boolean) .nil)
private def duplicateFields : Layout := .cons "root" (.aggregate .struct "Dup"
  (.cons "x" (.scalar (.bits 8)) (.cons "x" (.scalar (.bits 8)) .nil))) .nil
private def duplicateTail : Layout := .cons "unrelated" (.scalar .boolean)
  (.cons "x" (.scalar .boolean) (.cons "x" (.scalar (.bits 8)) .nil))
private def duplicateKinds : Layout := .cons "root" (.aggregate .struct "DupKinds"
  (.cons "x" (.scalar (.bits 8)) (.cons "x" (.aggregate .header "H" .nil) .nil))) .nil
private def scalarRoots : Layout := .cons "x" (.scalar (.bits 8)) .nil
private def zeroRoots : Layout := .cons "x" (.scalar (.bits 0)) .nil
private def inputModes : Modes scalarRoots := .cons (.param .«in») .nil
private def directionlessModes : Modes scalarRoots := .cons (.param .none) .nil
private def outputModes : Modes scalarRoots := .cons (.param .out) .nil
private def inoutModes : Modes scalarRoots := .cons (.param .inout) .nil
private def localModes : Modes scalarRoots := .cons .local .nil

private def error? : Except ResolutionError α → Option ResolutionError
  | .ok _ => none
  | .error error => some error

example : error? (Ref.resolve scalarRoots (.bits 8) []) = some .emptyPath := by decide +kernel
example : error? (Ref.resolve scalarRoots (.bits 8) [""]) = some .emptySegment := by decide +kernel
example : error? (Ref.resolve firstRoots (.bits 8) ["root", ""]) = some .emptySegment := by decide +kernel
example : error? (Ref.resolve firstRoots (.bits 8) ["root", "absent"]) = some (.missing "absent") := by decide +kernel
example : error? (Ref.resolve scalarRoots (.bits 8) ["absent"]) = some (.missing "absent") := by decide +kernel
example : error? (Ref.resolve duplicateRoots (.bits 8) ["x"]) = some (.ambiguous "x") := by decide +kernel
example : error? (Ref.resolve duplicateFields (.bits 8) ["root", "x"]) = some (.ambiguous "x") := by decide +kernel
example : error? (Ref.resolve duplicateTail (.bits 8) ["x"]) = some (.ambiguous "x") := by decide +kernel
example : error? (Ref.resolve duplicateKinds (.bits 8) ["root", "x"]) = some (.ambiguous "x") := by decide +kernel
example : error? (Ref.resolve scalarRoots (.bits 8) ["x", "child"]) = some (.notAggregate "child") := by decide +kernel
example : error? (Ref.resolve firstRoots (.bits 8) ["root"]) = some .aggregateEndpoint := by decide +kernel
example : error? (Ref.resolve scalarRoots (.bits 9) ["x"]) = some (.typeMismatch (.bits 8) (.bits 9)) := by decide +kernel
example : error? (Ref.resolve scalarRoots .boolean ["x"]) = some (.typeMismatch (.bits 8) .boolean) := by decide +kernel
example : error? (Ref.resolve zeroRoots (.bits 0) ["x"]) = some (.invalidScalar (.bits 0)) := by decide +kernel
example : error? (Place.resolve inputModes (.bits 8) ["x"]) = some (.readonly "x") := by decide +kernel
example : error? (Place.resolve directionlessModes (.bits 8) ["x"]) = some (.readonly "x") := by decide +kernel
example : error? (Place.resolve FieldCommandExamples.modes (.bits 9) ["route", "port"]) =
    some (.readonly "route") := by decide +kernel

example : Place outputModes (.bits 8) := Place.named ["x"]
example : Place inoutModes (.bits 8) := Place.named ["x"]
example : Place localModes (.bits 8) := Place.named ["x"]
example : Ref scalarRoots (.bits 8) := Ref.named ["x"]

-- A valid selected path does not certify unvisited names or the whole schema.
example : (Ref.resolve (.cons "bad" (.scalar .boolean) (.cons "bad" (.scalar (.bits 0))
    (.cons "good" (.scalar (.bits 8)) .nil))) (.bits 8) ["good"]).isOk = true := by decide +kernel

example : True := by
  fail_if_success have bad : Ref scalarRoots (.bits 8) := by exact Ref.named []
  trivial
example : True := by
  fail_if_success have bad : Ref scalarRoots (.bits 8) := by exact Ref.named [""]
  trivial
example : True := by
  fail_if_success have bad : Ref scalarRoots (.bits 8) := by exact Ref.named ["missing"]
  trivial
example : True := by
  fail_if_success have bad : Ref duplicateRoots (.bits 8) := by exact Ref.named ["x"]
  trivial
example : True := by
  fail_if_success have bad : Ref scalarRoots (.bits 8) := by exact Ref.named ["x", "child"]
  trivial
example : True := by
  fail_if_success have bad : Ref firstRoots (.bits 8) := by exact Ref.named ["root"]
  trivial
example : True := by
  fail_if_success have bad : Ref scalarRoots (.bits 9) := by exact Ref.named ["x"]
  trivial
example : True := by
  fail_if_success have bad : Ref scalarRoots .boolean := by exact Ref.named ["x"]
  trivial
example : True := by
  fail_if_success have bad : Ref zeroRoots (.bits 0) := by exact Ref.named ["x"]
  trivial
example : True := by
  fail_if_success have bad : Place inputModes (.bits 8) := by exact Place.named ["x"]
  trivial
example : True := by
  fail_if_success have bad : Place directionlessModes (.bits 8) := by exact Place.named ["x"]
  trivial

def run : IO Unit := do
  let source := FieldCommandExamples.store 64 true false true
  let selectedDst : Place FieldCommandExamples.modes (.bits 48) :=
    Place.named ["hdr", "ethernet", "dst"]
  unless (selectedDst.ref.get source).val == 0x111213141516 do
    throw (IO.userError "authored destination name must select the independent destination value")
  unless (namedDst.ref.get source).val == 0x111213141516 &&
      (namedSrc.get source).val == 0x212223242526 &&
      (namedTTL.ref.get source).val == 64 && (namedRoutePort.get source).val == 7 do
    throw (IO.userError "named references must select the independently expected field values")
  let firstStore : Store firstRoots := .cons (.aggregate ()
    (.cons (.scalar 3) (.cons (.scalar 7) .nil))) .nil
  let secondStore : Store reorderedRoots := .cons (.aggregate ()
    (.cons (.scalar 7) (.cons (.scalar 3) .nil))) .nil
  unless (firstRef.get firstStore).val == 7 && (reorderedRef.get secondStore).val == 7 do
    throw (IO.userError "unrelated schema reordering must not change selected field")
  match Ref.resolve firstRoots (.bits 8) ["root", "other"] with
  | .error error => throw (IO.userError s!"existing sibling name must resolve: {repr error}")
  | .ok other =>
    unless (other.get firstStore).val == 3 && other.expr == .member (.var "root") "other" do
      throw (IO.userError "a changed requested spelling must visibly select the changed field")
  IO.println "Named field values/reordering/spellings, 17 exact diagnostics and 11 rejected constructors passed"

end P4blo.NamedFieldsTests
