import P4blo.ForwarderAction

/-! Actual-installed, bounded IPv4 route selection. This module does not
execute the selected action, apply a table, or claim arbitrary-table validity. -/
namespace P4blo.ForwarderTables
open P4bloIR

structure RouteData where
  dst : Fin (2 ^ 48)
  port : Fin 512
  deriving Repr, DecidableEq

inductive Shape where
  | empty | network | host | networkHost | hostNetwork
  deriving Repr, DecidableEq

inductive Default where
  | drop | noAction | forward (data : RouteData)
  deriving Repr, DecidableEq

structure Config where
  shape : Shape
  network : RouteData
  host : RouteData
  otherwise : Default
  deriving Repr, DecidableEq

inductive Decision where
  | network | host | drop | noAction | forwardDefault
  deriving Repr, DecidableEq

/-- Independent numeric policy, not the runtime prefix matcher/fold. -/
def select (c : Config) (q : Fin (2 ^ 32)) : Decision :=
  if (c.shape = .host ∨ c.shape = .networkHost ∨ c.shape = .hostNetwork) ∧
      q.val = 0x0a000202 then .host
  else if (c.shape = .network ∨ c.shape = .networkHost ∨ c.shape = .hostNetwork) ∧
      0x0a000200 ≤ q.val ∧ q.val < 0x0a000300 then .network
  else match c.otherwise with
    | .drop => .drop
    | .noAction => .noAction
    | .forward _ => .forwardDefault

def RouteData.call (d : RouteData) : ActionCall :=
  ⟨"ipv4_forward", [.bits 48 d.dst.val, .bits 9 d.port.val]⟩
def Default.call : Default → ActionCall
  | .drop => ⟨"drop", []⟩
  | .noAction => ⟨"NoAction", []⟩
  | .forward d => d.call
def Decision.result (c : Config) : Decision → Match
  | .network => ⟨some c.network.call, true⟩
  | .host => ⟨some c.host.call, true⟩
  | .drop => ⟨some ⟨"drop", []⟩, false⟩
  | .noAction => ⟨some ⟨"NoAction", []⟩, false⟩
  | .forwardDefault => ⟨some c.otherwise.call, false⟩

def ref : TableRef := ("MyIngress", "ipv4_lpm")
def networkEntry (d : RouteData) : Entry := ⟨[.lpm 0x0a000200 24], d.call, 0⟩
def hostEntry (d : RouteData) : Entry := ⟨[.lpm 0x0a000202 32], d.call, 0⟩
def Config.entries (c : Config) : List Entry := match c.shape with
  | .empty => []
  | .network => [networkEntry c.network]
  | .host => [hostEntry c.host]
  | .networkHost => [networkEntry c.network, hostEntry c.host]
  | .hostNetwork => [hostEntry c.host, networkEntry c.network]
def Config.input (c : Config) : Entries :=
  ⟨[⟨ref.1, ref.2, c.entries, match c.otherwise with
    | .drop => none
    | d => some d.call⟩]⟩

private def seed : Installed :=
  { index := Forwarder.index
    entries := ({} : Std.HashMap TableRef (Array Entry)).insert ref #[]
    defaults := ({} : Std.HashMap TableRef (Option ActionCall)).insert ref (some ⟨"drop", []⟩) }

private theorem seed_built : Installed.build Forwarder.index = .ok seed := by cbv
private theorem seed_table : seed.table? ref = .ok Forwarder.ipv4Table := by cbv
private theorem seed_widths : seed.keyWidths ref = .ok [32] := by cbv

theorem table_lookup (i : Installed) (hi : i.index = Forwarder.index) :
    i.table? ref = .ok Forwarder.ipv4Table := by
  change ({ index := i.index } : Installed).table? ref = _
  rw [hi]
  exact seed_table

private theorem key_widths (i : Installed) (hi : i.index = Forwarder.index) :
    i.keyWidths ref = .ok [32] := by
  change ({ index := i.index } : Installed).keyWidths ref = _
  rw [hi]
  exact seed_widths

private theorem forward_lookup :
    Forwarder.index.scopes[ref.1]?.bind (·.actions["ipv4_forward"]?) =
      some Forwarder.forwardAction := by cbv

private theorem check_forward (i : Installed) (hi : i.index = Forwarder.index) (d : RouteData) :
    i.checkAction ref Forwarder.ipv4Table d.call = .ok () := by
  have hp : d.port.val < 2 ^ 9 := d.port.isLt
  simp [Installed.checkAction, Forwarder.ipv4Table, RouteData.call, hi, forward_lookup,
    Forwarder.forwardAction, Installed.literalFits, d.dst.isLt, hp,
    bind, pure, Except.bind, Except.pure]

private def append (i : Installed) (e : Entry) : Installed :=
  { i with entries := i.entries.insert ref ((i.entries.getD ref #[]).push e) }

private theorem duplicate_loop (entries : Array Entry) (entry : Entry) (msg : String)
    (fresh : ∀ e ∈ entries, Installed.sameKeys entry e = false) :
    (forIn entries PUnit.unit fun other _ => do
      if Installed.sameKeys entry other then throw msg
      pure (.yield PUnit.unit)) = (Except.ok PUnit.unit : Except String PUnit) := by
  rw [← Array.forIn_toList]
  have hf : ∀ e ∈ entries.toList, Installed.sameKeys entry e = false := by simpa using fresh
  generalize entries.toList = es at hf ⊢
  induction es with
  | nil => rfl
  | cons e es ih =>
    have h := ih (fun x hx => hf x (by simp [hx]))
    simp [hf e (by simp)]
    simpa using h

private theorem install_network (i : Installed) (d : RouteData)
    (hi : i.index = Forwarder.index)
    (fresh : ∀ e ∈ i.entries.getD ref #[], Installed.sameKeys (networkEntry d) e = false) :
    i.install ref (networkEntry d) = .ok (append i (networkEntry d)) := by
  simp only [Installed.install, table_lookup i hi, key_widths i hi,
    bind, pure, Except.bind, Except.pure, networkEntry, check_forward i hi]
  simp [
    Forwarder.ipv4Table, Installed.checkKeyValue, Installed.fitsWidth,
    append, bind, pure, Except.bind, Except.pure,
    show (MatchKind.lpm == MatchKind.ternary) = false from rfl]
  have h := duplicate_loop (i.entries.getD ref #[]) (networkEntry d)
    (toString "table '" ++ toString "ipv4_lpm" ++ toString "': duplicate entry") fresh
  simpa [bind, pure, Except.bind, Except.pure, Except.map, networkEntry, append] using
    congrArg (fun r => r.map (fun _ => append i (networkEntry d))) h

private theorem install_host (i : Installed) (d : RouteData)
    (hi : i.index = Forwarder.index)
    (fresh : ∀ e ∈ i.entries.getD ref #[], Installed.sameKeys (hostEntry d) e = false) :
    i.install ref (hostEntry d) = .ok (append i (hostEntry d)) := by
  simp only [Installed.install, table_lookup i hi, key_widths i hi,
    bind, pure, Except.bind, Except.pure, hostEntry, check_forward i hi]
  simp [Forwarder.ipv4Table, Installed.checkKeyValue, Installed.fitsWidth,
    append, bind, pure, Except.bind, Except.pure,
    show (MatchKind.lpm == MatchKind.ternary) = false from rfl]
  have h := duplicate_loop (i.entries.getD ref #[]) (hostEntry d)
    (toString "table '" ++ toString "ipv4_lpm" ++ toString "': duplicate entry") fresh
  simpa [bind, pure, Except.bind, Except.pure, Except.map, hostEntry, append] using
    congrArg (fun r => r.map (fun _ => append i (hostEntry d))) h

private def entriesInstalled (c : Config) : Installed := c.entries.foldl append seed

private theorem entries_installed (c : Config) :
    (forIn c.entries seed fun entry i => do pure (.yield (← i.install ref entry))) =
      (Except.ok (entriesInstalled c) : Except String Installed) := by
  have hn := install_network seed c.network rfl (by simp [seed])
  have hh := install_host seed c.host rfl (by simp [seed])
  have hnh := install_host (append seed (networkEntry c.network)) c.host rfl (by
    simp [append, seed, Installed.sameKeys, networkEntry, hostEntry]
    exact ⟨_, _, ⟨rfl, rfl⟩, rfl⟩)
  have hhn := install_network (append seed (hostEntry c.host)) c.network rfl (by
    simp [append, seed, Installed.sameKeys, networkEntry, hostEntry]
    exact ⟨_, _, ⟨rfl, rfl⟩, rfl⟩)
  cases hs : c.shape <;> simp [Config.entries, hs, entriesInstalled, hn, hh, hnh, hhn,
    bind, pure, Except.bind, Except.pure]

private theorem build_host (c : Config) :
    Installed.build Forwarder.index (some c.input) = (match c.otherwise with
      | .drop => .ok (entriesInstalled c)
      | d => (entriesInstalled c).setDefault ref (some d.call)) := by
  have hs := seed_built
  have he := entries_installed c
  simp [Installed.build] at hs
  simp at he
  simp [Installed.build, Config.input, hs]
  simp only [bind, pure, Except.bind, Except.pure]
  rw [he]
  cases hd : c.otherwise with
  | drop => rfl
  | noAction =>
    cases hx : (entriesInstalled c).setDefault ref (some Default.noAction.call) <;>
      simp [hx, Functor.map, Except.map]
  | forward d =>
    cases hx : (entriesInstalled c).setDefault ref (some (Default.forward d).call) <;>
      simp [hx, Functor.map, Except.map]

private theorem no_action_lookup :
    Forwarder.index.scopes[ref.1]?.bind (·.actions["NoAction"]?) =
      some Forwarder.noAction := by cbv

private theorem set_no_action (i : Installed) (hi : i.index = Forwarder.index) :
    i.setDefault ref (some Default.noAction.call) =
      .ok { i with defaults := i.defaults.insert ref (some Default.noAction.call) } := by
  simp only [Installed.setDefault, table_lookup i hi, bind, pure, Except.bind, Except.pure]
  simp [Forwarder.ipv4Table, Default.call, Installed.checkAction, hi, no_action_lookup,
    Forwarder.noAction, bind, pure, Except.bind, Except.pure]

private theorem set_forward (i : Installed) (hi : i.index = Forwarder.index) (d : RouteData) :
    i.setDefault ref (some d.call) =
      .ok { i with defaults := i.defaults.insert ref (some d.call) } := by
  simp only [Installed.setDefault, table_lookup i hi, bind, pure, Except.bind, Except.pure,
    check_forward i hi]
  rfl

private theorem entries_index (c : Config) : (entriesInstalled c).index = Forwarder.index := by
  cases hs : c.shape <;> simp [entriesInstalled, Config.entries, hs, append, seed]

private def expected (c : Config) : Installed := match c.otherwise with
  | .drop => entriesInstalled c
  | d => { entriesInstalled c with defaults :=
      (entriesInstalled c).defaults.insert ref (some d.call) }

private theorem build_expected (c : Config) :
    Installed.build Forwarder.index (some c.input) = .ok (expected c) := by
  rw [build_host]
  cases hd : c.otherwise with
  | drop => simp [expected, hd]
  | noAction => simpa [expected, hd] using set_no_action _ (entries_index c)
  | forward d => simpa [expected, hd, Default.call] using set_forward _ (entries_index c) d

/-- The public witness is the actual installer result; `installed_built`
rules out the fallback for every fitting payload in the profile. -/
def installed (c : Config) : Installed :=
  (Installed.build Forwarder.index (some c.input)).toOption.getD seed

private theorem installed_eq (c : Config) : installed c = expected c := by
  simp [installed, build_expected, Except.toOption]

theorem installed_built (c : Config) :
    Installed.build Forwarder.index (some c.input) = .ok (installed c) := by
  rw [installed_eq, build_expected]

theorem installed_index (c : Config) : (installed c).index = Forwarder.index := by
  rw [installed_eq]
  cases hd : c.otherwise <;> simp [expected, hd, entries_index]

theorem installed_entries (c : Config) : (installed c).entries.getD ref #[] = c.entries.toArray := by
  rw [installed_eq]
  cases hd : c.otherwise <;> cases hs : c.shape <;>
    simp [expected, entriesInstalled, hd, Config.entries, hs, append, seed]

theorem installed_default (c : Config) :
    (installed c).defaults.getD ref none = some c.otherwise.call := by
  rw [installed_eq]
  cases hd : c.otherwise <;> cases hs : c.shape <;>
    simp [expected, entriesInstalled, hd, Config.entries, hs, append, seed, Default.call]



-- A proof-only abbreviation of the actual loop body, not the source policy.
private def consider (q : Bits) (best : Option Entry) (entry : Entry) : Option Entry :=
  if (entry.keys.zip [q]).all (fun (kv, k) => Installed.keyValueMatches kv k) then
    match best with
    | none => some entry
    | some b => if Installed.beats entry b false then some entry else best
  else best

private def finish (fallback : Option ActionCall) : Option Entry → Match
  | none => ⟨fallback, false⟩
  | some entry => ⟨some entry.action, true⟩

private theorem lookup_empty (i : Installed) (decl : Table) (q : Bits)
    (ht : i.table? ref = .ok decl) (hk : decl.keys.length = 1)
    (he : i.entries.getD ref #[] = #[]) :
    i.lookup ref [q] = .ok (finish (i.defaults.getD ref none) none) := by
  simp [Installed.lookup, ht, hk, he, bind, pure, Except.bind, Except.pure, finish]

private theorem lookup_one (i : Installed) (decl : Table) (q : Bits) (a : Entry)
    (ht : i.table? ref = .ok decl) (hk : decl.keys.length = 1)
    (he : i.entries.getD ref #[] = #[a]) :
    i.lookup ref [q] = .ok (finish (i.defaults.getD ref none) (consider q none a)) := by
  cases hm : ((a.keys.zip [q]).all fun (kv, k) => Installed.keyValueMatches kv k) <;>
    simp [Installed.lookup, ht, hk, he, bind, pure, Except.bind, Except.pure, hm, consider, finish]

private theorem lookup_two (i : Installed) (decl : Table) (q : Bits) (a b : Entry)
    (ht : i.table? ref = .ok decl) (hk : decl.keys.length = 1)
    (hn : decl.keys.any (fun k => k.matchKind == .ternary) = false)
    (he : i.entries.getD ref #[] = #[a, b]) :
    i.lookup ref [q] = .ok (finish (i.defaults.getD ref none)
      (consider q (consider q none a) b)) := by
  simp only [Installed.lookup, ht, bind, Except.bind, pure, Except.pure, hk, hn, he]
  cases ha : ((a.keys.zip [q]).all fun (kv, k) => Installed.keyValueMatches kv k) <;>
    cases hb : ((b.keys.zip [q]).all fun (kv, k) => Installed.keyValueMatches kv k) <;>
    cases hc : Installed.beats b a false <;>
    simp [ha, hb, hc, bind, pure, Except.bind, Except.pure, consider, finish]

def query (q : Fin (2 ^ 32)) : Bits := ⟨32, q.val, q.isLt⟩

private theorem quotient_range (q : Nat) :
    (q / 256 == 655362) = decide (167772672 ≤ q ∧ q < 167772928) := by
  apply Bool.eq_iff_iff.mpr
  simp
  omega

private theorem network_matches (q : Fin (2 ^ 32)) (d : RouteData) :
    ((networkEntry d).keys.zip [query q]).all
        (fun (kv, k) => Installed.keyValueMatches kv k) =
      decide (0x0a000200 ≤ q.val ∧ q.val < 0x0a000300) := by
  simp only [networkEntry, List.zip_cons_cons, List.zip_nil_left, List.all_cons,
    List.all_nil, Bool.and_true, query, Installed.keyValueMatches]
  change (q.val >>> 8 == 0x0a000200 >>> 8) = _
  rw [Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow]
  exact quotient_range q.val

private theorem host_matches (q : Fin (2 ^ 32)) (d : RouteData) :
    ((hostEntry d).keys.zip [query q]).all
        (fun (kv, k) => Installed.keyValueMatches kv k) =
      decide (q.val = 0x0a000202) := by
  simp [hostEntry, query, Installed.keyValueMatches]
  rfl

/-- Every 32-bit address and every fitting route/default payload in the five
installation shapes. The conclusion names the independent source decision;
no assumption states that lookup or selection is correct. -/
theorem lookup_correct (c : Config) (q : Fin (2 ^ 32)) :
    (installed c).lookup ref [query q] = .ok ((select c q).result c) := by
  have ht := table_lookup (installed c) (installed_index c)
  have he := installed_entries c
  have hd := installed_default c
  cases hs : c.shape with
  | empty =>
    have h := lookup_empty (installed c) Forwarder.ipv4Table (query q) ht rfl
      (by simpa [Config.entries, hs] using he)
    rw [h, hd]
    cases hx : c.otherwise <;> simp [finish, select, hs, hx, Decision.result, Default.call]
  | network =>
    have h := lookup_one (installed c) Forwarder.ipv4Table (query q) (networkEntry c.network)
      ht rfl (by simpa [Config.entries, hs] using he)
    rw [h, hd]
    simp only [consider, network_matches]
    by_cases hn : 0x0a000200 ≤ q.val ∧ q.val < 0x0a000300 <;>
      cases hx : c.otherwise <;>
      simp [hn, finish, select, hs, hx, Decision.result, Default.call, networkEntry]
  | host =>
    have h := lookup_one (installed c) Forwarder.ipv4Table (query q) (hostEntry c.host)
      ht rfl (by simpa [Config.entries, hs] using he)
    rw [h, hd]
    simp only [consider, host_matches]
    by_cases hh : q.val = 0x0a000202 <;> cases hx : c.otherwise <;>
      simp [hh, finish, select, hs, hx, Decision.result, Default.call, hostEntry]
  | networkHost =>
    have h := lookup_two (installed c) Forwarder.ipv4Table (query q)
      (networkEntry c.network) (hostEntry c.host) ht rfl rfl
      (by simpa [Config.entries, hs] using he)
    rw [h, hd]
    simp only [consider, network_matches, host_matches]
    by_cases hn : 0x0a000200 ≤ q.val ∧ q.val < 0x0a000300 <;>
      by_cases hh : q.val = 0x0a000202 <;> cases hx : c.otherwise <;>
      simp [hn, hh, finish, select, hs, hx, Decision.result, Default.call,
        networkEntry, hostEntry, Installed.beats, Installed.prefixLength]
  | hostNetwork =>
    have h := lookup_two (installed c) Forwarder.ipv4Table (query q)
      (hostEntry c.host) (networkEntry c.network) ht rfl rfl
      (by simpa [Config.entries, hs] using he)
    rw [h, hd]
    simp only [consider, network_matches, host_matches]
    by_cases hn : 0x0a000200 ≤ q.val ∧ q.val < 0x0a000300 <;>
      by_cases hh : q.val = 0x0a000202 <;> cases hx : c.otherwise <;>
      simp [hn, hh, finish, select, hs, hx, Decision.result, Default.call,
        networkEntry, hostEntry, Installed.beats, Installed.prefixLength]

theorem installed_other_entries (c : Config) (other : TableRef) (h : other ≠ ref) :
    (installed c).entries[other]? = none := by
  rw [installed_eq]
  cases hd : c.otherwise <;> cases hs : c.shape <;>
    simp [expected, entriesInstalled, hd, Config.entries, hs, append, seed, Ne.symm h]

theorem installed_other_defaults (c : Config) (other : TableRef) (h : other ≠ ref) :
    (installed c).defaults[other]? = none := by
  rw [installed_eq]
  cases hd : c.otherwise <;> cases hs : c.shape <;>
    simp [expected, entriesInstalled, hd, Config.entries, hs, append, seed, Ne.symm h]

/-- A host cannot remove this program's default by passing `none`. -/
theorem restore_default (c : Config) :
    (installed c).setDefault ref none =
      .ok { (installed c) with defaults := (installed c).defaults.insert ref (some ⟨"drop", []⟩) } := by
  simp only [Installed.setDefault, table_lookup _ (installed_index c),
    bind, pure, Except.bind, Except.pure]
  rfl

theorem order_independent (c : Config) (q : Fin (2 ^ 32)) :
    (installed { c with shape := .networkHost }).lookup ref [query q] =
      (installed { c with shape := .hostNetwork }).lookup ref [query q] := by
  rw [lookup_correct, lookup_correct]
  simp [select, Decision.result]

end P4blo.ForwarderTables
