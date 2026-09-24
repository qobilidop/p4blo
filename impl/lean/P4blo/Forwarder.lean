import P4blo.Interpreter
import P4blo.NamedFields
import P4blo.HeaderFields

/-!
# The corpus IPv4 forwarder, authored in Lean

This is the existing `tests/corpus/forwarder` program, not the separate
validity-guarded rewriting example. Named scalar paths are checked by the
typed authoring library. Parser, action, table, subtraction, concatenation
and extern assembly below are ordinary IR definitions: they are visible,
unverified authoring seams, not a claim of a verified whole frontend.

In particular, the action runs with an action frame, not `BlockFrame`.
TTL wraps, the source MAC receives the OLD destination MAC, and checksum
computation follows table application even when its selected action drops.
-/

namespace P4blo.Forwarder

open P4bloIR Fields

def ethernetFields : Layout :=
  .cons "dstAddr" (.scalar (.bits 48)) <|
  .cons "srcAddr" (.scalar (.bits 48)) <|
  .cons "etherType" (.scalar (.bits 16)) .nil

def ipv4Fields : Layout :=
  .cons "version" (.scalar (.bits 4)) <|
  .cons "ihl" (.scalar (.bits 4)) <|
  .cons "diffserv" (.scalar (.bits 8)) <|
  .cons "totalLen" (.scalar (.bits 16)) <|
  .cons "identification" (.scalar (.bits 16)) <|
  .cons "flags" (.scalar (.bits 3)) <|
  .cons "fragOffset" (.scalar (.bits 13)) <|
  .cons "ttl" (.scalar (.bits 8)) <|
  .cons "protocol" (.scalar (.bits 8)) <|
  .cons "hdrChecksum" (.scalar (.bits 16)) <|
  .cons "srcAddr" (.scalar (.bits 32)) <|
  .cons "dstAddr" (.scalar (.bits 32)) .nil

def headersFields : Layout :=
  .cons "ethernet" (.aggregate .header "ethernet_t" ethernetFields) <|
  .cons "ipv4" (.aggregate .header "ipv4_t" ipv4Fields) .nil

def metadataFields : Layout :=
  .cons "ingress_port" (.scalar (.bits 9)) <|
  .cons "egress_port" (.scalar (.bits 9)) <|
  .cons "drop" (.scalar .boolean) .nil

def roots : Layout :=
  .cons "hdr" (.aggregate .struct "headers" headersFields) <|
  .cons "meta" (.aggregate .struct "metadata" metadataFields) .nil

def ethDst : Ref roots (.bits 48) := .named ["hdr", "ethernet", "dstAddr"]
def ethSrc : Ref roots (.bits 48) := .named ["hdr", "ethernet", "srcAddr"]
def ethType : Ref roots (.bits 16) := .named ["hdr", "ethernet", "etherType"]
def version : Ref roots (.bits 4) := .named ["hdr", "ipv4", "version"]
def ihl : Ref roots (.bits 4) := .named ["hdr", "ipv4", "ihl"]
def diffserv : Ref roots (.bits 8) := .named ["hdr", "ipv4", "diffserv"]
def totalLen : Ref roots (.bits 16) := .named ["hdr", "ipv4", "totalLen"]
def identification : Ref roots (.bits 16) := .named ["hdr", "ipv4", "identification"]
def flags : Ref roots (.bits 3) := .named ["hdr", "ipv4", "flags"]
def fragOffset : Ref roots (.bits 13) := .named ["hdr", "ipv4", "fragOffset"]
def ttl : Ref roots (.bits 8) := .named ["hdr", "ipv4", "ttl"]
def protocol : Ref roots (.bits 8) := .named ["hdr", "ipv4", "protocol"]
def hdrChecksum : Ref roots (.bits 16) := .named ["hdr", "ipv4", "hdrChecksum"]
def ipSrc : Ref roots (.bits 32) := .named ["hdr", "ipv4", "srcAddr"]
def ipDst : Ref roots (.bits 32) := .named ["hdr", "ipv4", "dstAddr"]
def egress : Ref roots (.bits 9) := .named ["meta", "egress_port"]
def dropFlag : Ref roots .boolean := .named ["meta", "drop"]

def ipv4 : HeaderRef roots := .mk .here (.field (.there .here) .here)

private def hdrParam (direction : Direction) : Param :=
  ⟨"hdr", .struct "headers", direction⟩
private def metaParam : Param := ⟨"meta", .struct "metadata", .inout⟩

def parser : Block :=
  { (default : Block) with
    name := "MyParser", kind := .parser
    params := [hdrParam .out, metaParam]
    startState := "start"
    states := [
      ⟨"start", [], .direct (.state "parse_ethernet")⟩,
      ⟨"parse_ethernet", [.extract (.member (.var "hdr") "ethernet")],
        .select [ethType.expr] [
          ⟨[.exact (.bits 16 2048)], .state "parse_ipv4"⟩,
          ⟨[.dontCare], .accept⟩]⟩,
      ⟨"parse_ipv4", [.extract (.member (.var "hdr") "ipv4")], .direct .accept⟩] }

def noAction : Action := ⟨"NoAction", [], []⟩
def dropAction : Action :=
  ⟨"drop", [], [.assign dropFlag.lvalue (.literal (.boolean true))]⟩

def forwardAction : Action :=
  ⟨"ipv4_forward", [⟨"dstAddr", .bits 48, .none⟩, ⟨"port", .bits 9, .none⟩], [
    .assign egress.lvalue (.var "port"),
    .assign ethSrc.lvalue ethDst.expr,
    .assign ethDst.lvalue (.var "dstAddr"),
    .assign ttl.lvalue (.binary .sub ttl.expr (.literal (.bits 8 1))) ]⟩

def ipv4Table : Table :=
  { name := "ipv4_lpm", keys := [⟨ipDst.expr, .lpm, ""⟩]
    actions := ["ipv4_forward", "drop", "NoAction"]
    defaultAction := some ⟨"drop", []⟩
    constDefaultAction := false, constEntries := [], size := 1024 }

/-- Left-associated 144-bit input, omitting the checksum field itself. -/
def checksumInput : P4bloIR.Expr :=
  [ihl.expr, diffserv.expr, totalLen.expr, identification.expr, flags.expr,
    fragOffset.expr, ttl.expr, protocol.expr, ipSrc.expr, ipDst.expr].foldl
    (.binary .concat) version.expr

def ingress : Block :=
  { (default : Block) with
    name := "MyIngress", kind := .control
    params := [hdrParam .inout, metaParam]
    actions := [noAction, dropAction, forwardAction], tables := [ipv4Table]
    body := [
      .conditional ipv4.expr [.apply "ipv4_lpm" none] [],
      .conditional ipv4.expr
        [.callExtern "csum" "compute" [.expr checksumInput] (some hdrChecksum.lvalue)] []] }

def deparser : Block :=
  { (default : Block) with
    name := "MyDeparser", kind := .deparser, params := [hdrParam .in]
    body := [.emit (.member (.var "hdr") "ethernet"),
      .emit (.member (.var "hdr") "ipv4")] }

def program : Program :=
  { name := "forwarder"
    errors := ["NoError", "PacketTooShort", "NoMatch", "StackOutOfBounds",
      "HeaderTooShort", "ParserTimeout", "ParserInvalidArgument"]
    headerTypes := [⟨"ethernet_t", ethernetFields.fields⟩, ⟨"ipv4_t", ipv4Fields.fields⟩]
    structTypes := [⟨"headers", headersFields.fields⟩, ⟨"metadata", metadataFields.fields⟩]
    enumTypes := []
    externTypes := [⟨"checksum16", [], [⟨"compute", [⟨"data", .bits 144, .in⟩],
      some (.bits 16)⟩]⟩]
    externInstances := [⟨"csum", "checksum16", []⟩]
    blocks := [parser, ingress, deparser]
    headers := "headers", metadata := "metadata"
    exports := [⟨"parser", "MyParser"⟩, ⟨"control", "MyIngress"⟩,
      ⟨"deparser", "MyDeparser"⟩] }

end P4blo.Forwarder
