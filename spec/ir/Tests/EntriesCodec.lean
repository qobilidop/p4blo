import Tests.ProgramCodec

open Lean P4bloIR

namespace EntriesCodecTests

def tableEntriesValue (t : TableEntries) : Json := Json.mkObj
  [("block", .str t.block), ("table", .str t.table),
   ("entries", toJson (t.entries.map TableCodecTests.entryValue)),
   ("default_action", t.defaultAction.map TableCodecTests.actionValue |>.getD .null)]
def entriesValue (e : Entries) : Json := Json.mkObj
  [("tables", toJson (e.tables.map tableEntriesValue))]

def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  match kind with
  | "table_entries" =>
    let t ← TableEntries.decode "leaf" wire
    pure (Json.mkObj [("value", tableEntriesValue t), ("encoded", t.toJson)])
  | "entries" =>
    let e ← Entries.decode "leaf" wire
    pure (Json.mkObj [("value", entriesValue e), ("encoded", e.toJson)])
  | _ => ProgramCodecTests.reply request

private def empty : Json := Json.mkObj []
def tests : T Unit := do
  checkOk "entries empty defaults" (Entries.decode "" empty) (· == ⟨[]⟩)
  checkOk "table entries empty defaults" (TableEntries.decode "" empty) (· == ⟨"", "", [], none⟩)
  for wire in [empty, Json.mkObj [("default_action", .null)]] do
    checkOk "host absent default" (TableEntries.decode "" wire) (·.defaultAction == none)
  checkOk "host present empty default"
    (TableEntries.decode "" (Json.mkObj [("default_action", empty)]))
    (·.defaultAction == some ⟨"", []⟩)
  check "host default presence observer"
    (((tableEntriesValue ⟨"", "", [], none⟩).getObjVal? "default_action").toOption == some .null &&
     ((tableEntriesValue ⟨"", "", [], some ⟨"", []⟩⟩).getObjVal? "default_action").toOption ==
       some (Json.mkObj [("action", .str ""), ("args", .arr #[])]))
  checkOk "host complete asymmetric ordered records"
    (Entries.fromJsonString "{\"tables\":[{\"block\":\"left\",\"table\":\"right\",\"entries\":[{\"keys\":[{\"exact\":\"9\"}],\"action\":{\"action\":\"A\"},\"priority\":7},{},{\"priority\":4294967295}],\"default_action\":{}},{},{\"block\":\"right\",\"table\":\"left\"}]}")
    (· == ⟨[⟨"left", "right", [⟨[.exact 9], ⟨"A", []⟩, 7⟩, ⟨[], ⟨"", []⟩, 0⟩,
      ⟨[], ⟨"", []⟩, 2 ^ 32 - 1⟩], some ⟨"", []⟩⟩, ⟨"", "", [], none⟩,
      ⟨"right", "left", [], none⟩]⟩)
  for (first, second, what) in [("block", "table", "a string"),
      ("table", "entries", "a string"), ("entries", "default_action", "an array")] do
    check "host adjacent first error"
      (match TableEntries.decode "" (Json.mkObj [(first, .bool false), (second, .bool false)]) with
       | .error e => e == first ++ ": expected " ++ what
       | .ok _ => false)
  check "host later nested first error"
    (Entries.fromJsonString "{\"tables\":[{}, {\"entries\":[{}, {\"priority\":4294967296}]}]}" matches
      .error "tables[1].entries[1].priority: 4294967296 does not fit in uint32")
  -- Actual host installation must reject before an independently observable
  -- missing-parser trap. This is operational precedence, not global validity.
  let indexed := Index.build { (default : Program) with structTypes := [⟨"M", []⟩] }
  match indexed with
  | .error _ => check "host trap index builds" false
  | .ok index => do
    let sw : Switch := {
      index, parser := "PacketEntryTrap", control := "", deparser := ""
      metadataType := "M", ingressPort := none, parserError := none
      egressPort := none, drop := none, flood := none, ports := 4 }
    let externs : Externs := { instances := Std.HashMap.ofList [("sentinel", .counter #[7, 0, 19])] }
    check "host trap control reaches actual packet entry"
      (sw.run externs ⟨[]⟩ 0 ByteArray.empty matches .error "unknown block 'PacketEntryTrap'")
    for host in [Entries.mk [⟨"C", "Missing", [], some ⟨"NoAction", []⟩⟩],
        Entries.mk [⟨"C", "Missing", [⟨[], ⟨"NoAction", []⟩, 0⟩], none⟩]] do
      check "host rejection precedes actual packet entry"
        (sw.run externs host 0 ByteArray.empty matches .error "no table 'Missing' in block 'C'")

end EntriesCodecTests
