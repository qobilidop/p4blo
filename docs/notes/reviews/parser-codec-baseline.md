# Parser-syntax codec baseline review

Final baseline review: CLEAR. Test/observer evidence only; universal laws,
new proof audits and deliberate source-fault campaigns remain later work.

2026-09-23. Read all six owned changes in `p4blo-parser-codecs` at `1c1b08e`:
new native/Python observer modules and note, narrow endpoint/native-driver
registrations and shared kind union extension. No implementation edits or
candidate builds were performed by this reviewer.

## Independent meanings and permissive domains

All five new endpoint labels observe actual decoded values directly. Target,
KeySet and Transition constructors are matched explicitly; SelectCase and State
include every field, ordered list and nested member. Observations do not reuse
production wire-label tables or encoded JSON. Existing independent Literal,
Expr and Stmt descriptors remain unchanged and old endpoint labels delegate
through the prior dispatch.

Native literal anchors distinguish accept/reject from their separate descriptor
anchors, asymmetric masked operands/range endpoints and ordered cases/bodies.
The Python fixtures independently state full abstract answers plus canonical
wire, preserving zero-width/large literals, all nested expression/statement
families, malformed semantic placements, unresolved/cyclic names, unequal
arity and duplicate keys. No index/validator/parser execution is used to filter
this intentionally permissive wire evidence.

Empty select versus empty direct, selected empty state string, missing/null/
empty nested oneofs and null list elements are distinct. Competing errors pin
kind selection order before payloads, masked/range operand order, sets before
target, keys before cases and name/body/transition order. Later nested indices
reuse independent member answers with explicit path-prefix changes. Root empty
path and nonempty path have native anchors. Normalization tests preserve the
current ignored-annotation/null/default/decimal behavior without claiming a
general compatibility policy.

Public protobuf wrappers use real Program/Block/State/select message fields and
SetInParent to retain empty-message presence, then dump/load the complete wrapper
and recover the selected message. The wrapper deliberately need not validate.
Strict same_json/duplicate-rejecting response loads and process-error retention
remain unchanged shared infrastructure.

## Independent execution and frozen provenance

Independent focused Python execution: 283 passed, exit 0 (4.80 seconds).
Direct native endpoint self-test: 133 checks, exit 0 with empty stderr, including
all 27 new anchors. Verified exact nonzero inventory: 231 unique ordered inputs,
51 canonical successes, 155 errors and 25 normalized successes.

Independently matched every artifact input and independent expected answer to
current tracked fixtures and exact compact-plus-LF stdin. Reran all 231 against
the stable endpoint: stdout/stderr/status byte-identical to capture, clean exit
and strict expected JSON in every case. Passed all 76 ACTUAL encoded replies
through the public protobuf wrapper, not just the expected encodings.

All thirteen captured source hashes match current frozen sources. Actual Json
is byte-identical to `git show 1c1b08e:ir/P4bloIR/Json.lean`, SHA-256
`0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
Artifact is 411,355 bytes, SHA-256
`454ff7c9b2c68b02ec81eb07d0897355b75721fad2ebe742000ffcb348a5e2bb`.
Reviewed reconstruction refuses changed actual production bytes and existing
output, checks strict answers/nonempty unique inventory, then rechecks source
hashes. Future proof witnesses must compare this baseline's source hashes to
its eventual historical commit rather than recapturing evidence.

Owner-attributed gates: both packages/default/native tests pass (567 spec
checks), all seven codec files 1,332 pass, scoped lint/format/type checks pass.
The reviewer independently ran the focused/native/raw/protobuf checks above,
not the entire combined suite. This checkpoint adds no production codec/proof,
runtime/schema/golden behavior or parser-correctness claim. No outstanding
baseline finding; clear for the separately authorized small test commit before
universal-law implementation and isolated fault evidence.
