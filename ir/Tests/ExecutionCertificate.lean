import Tests.Check

open P4blo

namespace ExecutionCertificateTests

open ExecutionCertificate

private def expected : Example.Observation := {
  completion := .success, register := some (8, [42]), counter := some [10], localValue := some (8, 42) }

def tests : T Unit := do
  let experiment := Example.initial 41 9
  checkOk "certificate accepts the stateful register/counter claim"
    (experiment.map fun machine => ExecutionCertificate.check 10 machine Example.observe expected) id
  checkOk "certificate rejects a changed register initial state"
    ((Example.initial 42 9).map fun machine =>
      !ExecutionCertificate.check 10 machine Example.observe expected) id
  checkOk "certificate rejects a changed counter initial state"
    ((Example.initial 41 10).map fun machine =>
      !ExecutionCertificate.check 10 machine Example.observe expected) id
  checkOk "certificate rejects a changed claimed register result"
    (experiment.map fun machine =>
      !ExecutionCertificate.check 10 machine Example.observe { expected with register := some (8, [43]) }) id
  checkOk "certificate rejects a changed claimed fault tag"
    (experiment.map fun machine =>
      !ExecutionCertificate.check 10 machine Example.observe { expected with completion := .parse "NoError" }) id
  checkOk "certificate rejects insufficient execution fuel"
    (experiment.map fun machine => !ExecutionCertificate.check 9 machine Example.observe expected) id
  checkOk "certificate exhaustion is its own verdict, not ParserTimeout"
    (experiment.map fun machine => bounded 9 machine matches .exhausted) id
  checkOk "certificate zero budget cannot certify a terminal machine"
    (experiment.map fun machine => bounded 0 { machine with work := [] } matches .exhausted) id
  checkOk "certificate binds pending faults in the full initial machine"
    (experiment.map fun machine =>
      !ExecutionCertificate.check 10 { machine with fault := some (.parse "NoError") }
        Example.observe expected) id
  checkOk "certificate binds the work in the full initial machine"
    (experiment.map fun machine =>
      !ExecutionCertificate.check 10 { machine with work := [] } Example.observe expected) id
  let faulting := experiment.map fun machine =>
    { machine with work := [.statements (Example.block.body ++ [
      .verify (.literal (.boolean false)) "NoError"])] }
  checkOk "certificate cannot hide a semantic fault behind matching extern state"
    (faulting.map fun machine => !ExecutionCertificate.check 12 machine Example.observe expected) id
  checkOk "certificate retains semantic faults as finished outcomes"
    (faulting.map fun machine =>
      ExecutionCertificate.check 12 machine Example.observe { expected with completion := .parse "NoError" }) id
  let internalFault := experiment.map fun machine =>
    { machine with work := [.statements (Example.block.body ++ [
      .callExtern "missing" "count" [] none])] }
  checkOk "certificate cannot hide an internal fault behind matching extern state"
    (internalFault.map fun machine => !ExecutionCertificate.check 12 machine Example.observe expected) id
  checkOk "certificate distinguishes the exact internal fault message"
    (internalFault.map fun machine => ExecutionCertificate.check 12 machine Example.observe {
      expected with completion := .interp "unknown extern instance 'missing'" }) id
  checkOk "certificate checks wrapping state changes through real extern calls"
    ((Example.initial 255 9).map fun machine =>
      ExecutionCertificate.check 10 machine Example.observe {
        expected with register := some (8, [0]), localValue := some (8, 0) }) id
  checkError "certificate fixture refuses a noncanonical initial register"
    ((Example.initial 256 9).map fun _ => ()) "does not fit"

end ExecutionCertificateTests
