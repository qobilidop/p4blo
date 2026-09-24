# Milestone profile and evidence review

2026-09-23. Independent read-only review by the usability agent of the root
agent's `docs/profile.md`, `docs/evidence.md`, and pending coverage/semantics
diff on main. This is a documentation review, not a fresh full gate.

Disposition: **CLEAR** for the inspected draft. No implementation or final
milestone completion is implied. Program/Entries integration, reproducible
sensitivity/replay command, quickstart and final gates remain explicitly
pending in the evidence document. One terminology correction was sent to
the root: the parked ingress is the original-forwarder ingress prefix, not
the already-proved guarded forwarding/control-call example. Use that exact
name instead of "Guarded ingress" in the authored-applications row.

Checked the claimed package/validator boundary, actual table install/default
and lookup APIs, eDSL limitations, required-test naming, ten-second DRT
deadline, scalar checker theorem names and parser extract/emit theorem. The
ACL README confirms the formerly planned action-run elaboration is now an
implemented control-local marker. Firewall source/initialization/Bloom notes
support the stated complete execution versus scoped proof distinction.

The profile appropriately separates canonical interchange from arbitrary
protobuf-JSON acceptance, invalid-but-representable syntax from valid programs,
preflight state preservation from rollback after execution, native/proof/DRT
evidence from oracle coverage, and finite runtime resources from termination
proofs. Coverage no longer claims every absent corpus operator is necessarily
covered by the same differential test. The semantics diff removes obsolete
pre-Lean and unsupported totality claims without changing runtime meaning.

No wording implies universal Python correctness, full P4 coverage, verified
complete frontends or whole pipelines. The known strict expected discrepancies
and compile-only XDP exclusion are visible. Root retains responsibility for
updating the pending closeout rows after their actual integration/gates.
