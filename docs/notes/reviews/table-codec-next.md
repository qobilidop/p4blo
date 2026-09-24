# Table declaration codec plan review

Final review: clear for the planning checkpoint; historical correction and
its resolution follow below. Implementation acceptance remains pending.

2026-09-23. Independently read the complete plan and unregistered probe in
`p4blo-table-codec-next` at `77b9890`, alongside the actual Key, ActionCall,
Entry and Table decoder/encoder definitions. No candidate files changed or
libraries rebuilt.

The proposed four-law slice is coherent and already total. Its only new
numeric bounds are Entry.priority and Table.size; nested Expr/Literal/KeyValue
bounds must propagate without semantic name, match-width/arity, positivity,
resolution or const-default restrictions. All match kinds and arbitrary finite
ordered arrays remain represented. Existing array/member proofs are adequate
dependencies; the declaration-law branch is unnecessary for this slice.

Independently ran the complete standalone probe with pinned Lean 4.34.0 and
warningAsError: exit 0, four printed roots exactly the standard three axioms.
It proves actual Key, ActionCall and Entry correspondence plus a constructive
unusual Entry, NOT the Table law. The plan correctly leaves Table composition
as implementation work rather than claiming complete feasibility evidence.

The proposed pre-proof baseline, independent constructor descriptors/native
anchors, shared MatchKind permutation, paired Boolean/default challenges and
exact competing-error observations address distinct proof blind spots. In
particular, successful roundtrip alone cannot establish intended enum names,
default meanings or malformed-input error order. A direct codec runner under
a separately failing packet preflight must remain honestly labeled.

One sentence currently calls Entry.action a missing required action message.
Actual msgField supplies an empty object on absence/null and ActionCall
accepts that object. Independently kernel-checked with rfl: Entry{} and
Entry{action:null} both decode successfully to empty keys, an empty action
name/argument list and priority zero. Table default absence decodes to none,
whereas present {} decodes to some empty ActionCall. Requested explicit
wording and baseline controls for this difference; do not imply required
wire presence or alter existing decoder behavior.

Otherwise no blocker found. Keep wire-only scope, initial frozen baseline,
proof registrations/witnesses and actual source-matched live/restored faults
as implementation acceptance. No table-selection or whole Program theorem
follows from this planning checkpoint.

The requested correction is now explicit in the final plan: Entry's absent,
null and present-empty action all succeed with the same empty ActionCall;
Table's absent/null default is none, while present-empty is some empty call.
All six cases are now independent rfl kernel anchors in the probe. Read the
changes and independently reran the entire updated probe with pinned Lean
and warningAsError: exit 0; all four printed roots retain exactly standard
axioms. No remaining planning blocker found.
