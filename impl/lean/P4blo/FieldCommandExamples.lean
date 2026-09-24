import P4blo.FieldCommands
import P4bloArch.Externs

namespace P4blo.FieldCommandExamples

open Fields
open scoped Scalar

def ethernetFields : Layout := .cons "dst" (.scalar (.bits 48))
  (.cons "src" (.scalar (.bits 48)) (.cons "etherType" (.scalar (.bits 16)) .nil))
def ethernet : Shape := .aggregate .header "Ethernet" ethernetFields
def ipv4Fields : Layout := .cons "ttl" (.scalar (.bits 8))
  (.cons "protocol" (.scalar (.bits 8)) (.cons "checksum" (.scalar (.bits 16)) .nil))
def ipv4 : Shape := .aggregate .header "IPv4" ipv4Fields
def headerFields : Layout := .cons "ethernet" ethernet (.cons "ipv4" ipv4 .nil)
def headers : Shape := .aggregate .struct "Headers" headerFields
def metaFields : Layout := .cons "port" (.scalar (.bits 9))
  (.cons "drop" (.scalar .boolean) (.cons "sentinel" (.scalar (.bits 16)) .nil))
def metadata : Shape := .aggregate .struct "Metadata" metaFields
def routeFields : Layout := .cons "hit" (.scalar .boolean) (.cons "dst" (.scalar (.bits 48))
  (.cons "src" (.scalar (.bits 48)) (.cons "port" (.scalar (.bits 9)) .nil)))
def route : Shape := .aggregate .struct "Route" routeFields
def roots : Layout := .cons "hdr" headers (.cons "meta" metadata
  (.cons "route" route (.cons "scratch" (.scalar (.bits 8)) .nil)))

def modes : Modes roots := .cons (.param .inout) (.cons (.param .inout)
  (.cons (.param .«in») (.cons .local .nil)))

def dst : Place modes (.bits 48) := ⟨.mk .here (.field .here (.field .here .scalar)), rfl⟩
def src : Place modes (.bits 48) := ⟨.mk .here (.field .here (.field (.there .here) .scalar)), rfl⟩
def ttl : Place modes (.bits 8) := ⟨.mk .here (.field (.there .here) (.field .here .scalar)), rfl⟩
def protocol : Place modes (.bits 8) :=
  ⟨.mk .here (.field (.there .here) (.field (.there .here) .scalar)), rfl⟩
def port : Place modes (.bits 9) := ⟨.mk (.there .here) (.field .here .scalar), rfl⟩
def drop : Place modes .boolean := ⟨.mk (.there .here) (.field (.there .here) .scalar), rfl⟩
def scratch : Place modes (.bits 8) := ⟨.mk (.there (.there (.there .here))) .scalar, rfl⟩
def routeHit : Ref roots .boolean := .mk (.there (.there .here)) (.field .here .scalar)
def routeDst : Ref roots (.bits 48) := .mk (.there (.there .here)) (.field (.there .here) .scalar)
def routeSrc : Ref roots (.bits 48) := .mk (.there (.there .here)) (.field (.there (.there .here)) .scalar)
def routePort : Ref roots (.bits 9) :=
  .mk (.there (.there .here)) (.field (.there (.there (.there .here))) .scalar)

/-- Dependent writes to the same header, a condition using the updated
value, two branches and a shared tail writing a different root. -/
def dependent : Cmd modes :=
  Cmd.block [
    Cmd.assign ttl (ttl.read + bits[8, 1]),
    Cmd.assign protocol (ttl.read + protocol.read),
    Cmd.ite (ttl.read === bits[8, 0])
      (Cmd.block [Cmd.assign port (.read routePort), Cmd.assign drop (.boolean true)])
      (Cmd.block [Cmd.assign port (port.read + bits[9, 1]), Cmd.assign drop (.boolean false)]),
    Cmd.assign scratch ttl.read]

/-- Already-parsed, route-selected forwarding rewrite. The caller supplies
route hit and fields. Checksum recomputation, parsing, validity tests, table
lookup, architecture packet fate and deparsing are not authored here. -/
def forward : Cmd modes :=
  let reject := Cmd.assign drop (.boolean true)
  let rewrite := Cmd.block [
    Cmd.assign dst (.read routeDst),
    Cmd.assign src (.read routeSrc),
    Cmd.assign ttl (ttl.read + bits[8, 255]),
    Cmd.assign port (.read routePort),
    Cmd.assign drop (.boolean false)]
  Cmd.ite (.read routeHit)
    (Cmd.ite (ttl.read === bits[8, 0]) reject
      (Cmd.ite (ttl.read === bits[8, 1]) reject rewrite)) reject

def store (initialTTL : Fin 256) (ethernetValid ipv4Valid hit : Bool) : Store roots :=
  .cons (.aggregate () (.cons (.aggregate ethernetValid
      (.cons (.scalar 0x111213141516) (.cons (.scalar 0x212223242526) (.cons (.scalar 0x0800) .nil))))
    (.cons (.aggregate ipv4Valid
      (.cons (.scalar initialTTL) (.cons (.scalar 6) (.cons (.scalar 0xabcd) .nil)))) .nil)))
  (.cons (.aggregate () (.cons (.scalar 3) (.cons (.scalar true) (.cons (.scalar 0x1234) .nil))))
  (.cons (.aggregate () (.cons (.scalar hit) (.cons (.scalar 0xaabbccddeeff)
    (.cons (.scalar 0x102030405060) (.cons (.scalar 7) .nil)))))
  (.cons (.scalar 19) .nil)))

def program : P4bloIR.Program :=
  { (default : P4bloIR.Program) with
    name := "field-command-witness",
    headerTypes := [⟨"Ethernet", ethernetFields.fields⟩, ⟨"IPv4", ipv4Fields.fields⟩],
    structTypes := [⟨"Headers", headerFields.fields⟩, ⟨"Metadata", metaFields.fields⟩, ⟨"Route", routeFields.fields⟩],
    blocks := [modes.scope.block] }

def index : P4bloIR.Index :=
  { program,
    headerTypes := (({} : Std.HashMap String P4bloIR.HeaderType).insert
      "Ethernet" ⟨"Ethernet", ethernetFields.fields⟩).insert "IPv4" ⟨"IPv4", ipv4Fields.fields⟩,
    structTypes := ((({} : Std.HashMap String P4bloIR.StructType).insert
      "Headers" ⟨"Headers", headerFields.fields⟩).insert "Metadata" ⟨"Metadata", metaFields.fields⟩).insert
      "Route" ⟨"Route", routeFields.fields⟩ }

theorem rootWF : RootWellFormed roots := by
  refine ⟨by decide, by decide, ?_⟩
  simp [roots, headers, headerFields, ethernet, ethernetFields, ipv4, ipv4Fields,
    metadata, metaFields, route, routeFields, Layout.LocallyWellFormed,
    Shape.LocallyWellFormed, P4bloIR.FieldLaws.NamesWellFormed,
    Layout.fields, Shape.toIR, Layout.Scalars]

theorem indexAgrees : roots.IndexAgrees index := by
  simp [roots, headers, headerFields, ethernet, ethernetFields, ipv4, ipv4Fields,
    metadata, metaFields, route, routeFields, Layout.IndexAgrees, Shape.IndexAgrees,
    P4bloIR.FieldLaws.Declared, P4bloIR.FieldLaws.NamesWellFormed, index,
    Layout.fields, Shape.toIR, Std.HashMap.getElem_insert]

def initial (source : Store roots) : P4bloIR.Run :=
  { index, frame := { modes.frame source with
      vars := source.bindings.insert "outside" (.header "Outside" false [.bool true]) },
    packet := some { data := ⟨#[0xde, 0xad, 0xbe, 0xef]⟩, value := 0xdeadbeef, cursor := 3 },
    emitter := some { value := 5, width := 3 },
    entries := some { index, defaults := (({} : Std.HashMap P4bloIR.TableRef (Option P4bloIR.ActionCall)).insert
      ("untouched", "table") (some ⟨"action", []⟩)) },
    externs := { model := P4bloArch.model, instances := (({} : Std.HashMap String P4bloIR.ExternState).insert
      "untouched-register" (.register 8 #[3, 9, 27])) },
    visits := ({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 13 }

theorem initial_matches (source : Store roots) : FrameMatches source (initial source).frame := by
  intro shape root
  have hn : root.name ≠ "outside" := by
    cases root with
    | here => decide
    | there root => cases root with
      | here => decide
      | there root => cases root with
        | here => decide
        | there root => cases root with
          | here => decide
          | there root => cases root
  simpa [initial, Modes.frame, Record.frame, P4bloIR.Frame.read?,
    Std.HashMap.getElem?_insert, Ne.symm hn] using source.bindings_get root rootWF.1

theorem correct (cmd : Cmd modes) (source : Store roots) :
    ∃ final, (P4bloIR.execute cmd.lower).run (initial source) = (.ok (), final) ∧
      FrameMatches (cmd.denote source) final.frame ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars (initial source) final ∧
      P4bloIR.ScalarStatements.PreservesOutside cmd.targets (initial source) final := by
  obtain ⟨_, final, executed, hm, _, _, hc, ho⟩ :=
    cmd.execute_correct source (initial source) rootWF indexAgrees
      (modes.scope_agrees rootWF) (initial_matches source) ⟨rfl, rfl⟩
  exact ⟨final, executed, hm, hc, ho⟩

structure Case where
  name : String
  command : Cmd modes
  initialTTL : Fin 256
  ethernetValid : Bool
  ipv4Valid : Bool
  hit : Bool

def cases : List Case :=
  [⟨"dependent-wrap-valid", dependent, 255, true, true, true⟩,
   ⟨"dependent-wrap-invalid", dependent, 255, false, false, true⟩,
   ⟨"dependent-next", dependent, 3, true, false, true⟩,
   ⟨"dependent-protocol-wrap", dependent, 249, false, true, false⟩,
   ⟨"forward-hit", forward, 64, true, true, true⟩,
   ⟨"forward-two", forward, 2, true, true, true⟩,
   ⟨"forward-max", forward, 255, true, true, true⟩,
   ⟨"forward-zero", forward, 0, true, true, true⟩,
   ⟨"forward-one", forward, 1, true, true, true⟩,
   ⟨"forward-miss", forward, 64, true, true, false⟩]

end P4blo.FieldCommandExamples
