# The reference architecture specification

Lake package `p4blo-arch`, imported as `P4bloArch`, depending one way on
the IR specification in `../ir`. It holds everything that runs an IR
program and that the IR itself does not decide (docs/arch-supports.md):

- `P4bloArch/Externs.lean`: the extern families the supplied architectures
  provide (`register`, `counter`, `checksum16`, `crc16`, `crc32`), their
  shapes and closed behaviors, and the model and registry that
  `P4bloIR.Externs.bind` takes. The IR sees an extern as a contract and
  carries its state as data; this package interprets the calls.
- `P4bloArch/Switch.lean`: the switch, the Lean twin of
  `impl/python/p4blo/arch/switch.py`, following the rules every supplied
  architecture shares.
- `P4bloArch/Certificate.lean`, `CertificateWire.lean`: the fixed
  register/counter experiment for `P4bloIR.ExecutionCertificate`.
- `Main.lean`: the `p4blo-lean` conformance endpoint the differential
  tests drive, which loads a program under the switch with these families.

`lake test` replays the forwarder's vectors under the switch and checks
the families, the certificate and its wire adapter, reading the fixtures
from `../ir/P4bloIRTest/`. `scripts/check-lean.sh` from the repository root
builds and tests all three packages in dependency order.
