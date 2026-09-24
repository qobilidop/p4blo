-- SPDX-FileCopyrightText: 2019 Stephen Ibanez
-- SPDX-License-Identifier: Apache-2.0
import P4blo.Forwarder

/-!
# The existing tutorial Bloom firewall, authored in Lean

Adapted from the pinned tutorial solution, with the same architecture mapping
as the Python corpus. Named field paths are checked by the typed library.
Parser/table/action/extern assembly and operators below remain visible raw IR
seams, not a verified complete frontend. No application behavior is an extern.
Forwarder layouts are reused as data, not its two-header frame/proof premises.
-/

namespace P4blo.TutorialFirewall
open P4bloIR Fields

def tcpFields : Layout :=
  .cons "srcPort" (.scalar (.bits 16)) <|
  .cons "dstPort" (.scalar (.bits 16)) <|
  .cons "seqNo" (.scalar (.bits 32)) <|
  .cons "ackNo" (.scalar (.bits 32)) <|
  .cons "dataOffset" (.scalar (.bits 4)) <|
  .cons "res" (.scalar (.bits 4)) <|
  .cons "cwr" (.scalar (.bits 1)) <|
  .cons "ece" (.scalar (.bits 1)) <|
  .cons "urg" (.scalar (.bits 1)) <|
  .cons "ack" (.scalar (.bits 1)) <|
  .cons "psh" (.scalar (.bits 1)) <|
  .cons "rst" (.scalar (.bits 1)) <|
  .cons "syn" (.scalar (.bits 1)) <|
  .cons "fin" (.scalar (.bits 1)) <|
  .cons "window" (.scalar (.bits 16)) <|
  .cons "checksum" (.scalar (.bits 16)) <|
  .cons "urgentPtr" (.scalar (.bits 16)) .nil

def headersFields : Layout :=
  .cons "ethernet" (.aggregate .header "ethernet_t" Forwarder.ethernetFields) <|
  .cons "ipv4" (.aggregate .header "ipv4_t" Forwarder.ipv4Fields) <|
  .cons "tcp" (.aggregate .header "tcp_t" tcpFields) .nil

def localFields : Layout :=
  .cons "reg_pos_one" (.scalar (.bits 32)) <|
  .cons "reg_pos_two" (.scalar (.bits 32)) <|
  .cons "reg_val_one" (.scalar (.bits 1)) <|
  .cons "reg_val_two" (.scalar (.bits 1)) <|
  .cons "direction" (.scalar (.bits 1)) <|
  .cons "crc16_result" (.scalar (.bits 16)) <|
  .cons "check_ports_hit" (.scalar .boolean) .nil

def roots : Layout :=
  .cons "hdr" (.aggregate .struct "headers" headersFields) <|
  .cons "meta" (.aggregate .struct "metadata" Forwarder.metadataFields) localFields

def ethDst : Ref roots (.bits 48) := .named ["hdr", "ethernet", "dstAddr"]
def ethSrc : Ref roots (.bits 48) := .named ["hdr", "ethernet", "srcAddr"]
def ethType : Ref roots (.bits 16) := .named ["hdr", "ethernet", "etherType"]
def ipSrc : Ref roots (.bits 32) := .named ["hdr", "ipv4", "srcAddr"]
def ipDst : Ref roots (.bits 32) := .named ["hdr", "ipv4", "dstAddr"]
def ipProtocol : Ref roots (.bits 8) := .named ["hdr", "ipv4", "protocol"]
def ttl : Ref roots (.bits 8) := .named ["hdr", "ipv4", "ttl"]
def hdrChecksum : Ref roots (.bits 16) := .named ["hdr", "ipv4", "hdrChecksum"]
def tcpSrc : Ref roots (.bits 16) := .named ["hdr", "tcp", "srcPort"]
def tcpDst : Ref roots (.bits 16) := .named ["hdr", "tcp", "dstPort"]
def tcpSyn : Ref roots (.bits 1) := .named ["hdr", "tcp", "syn"]
def ingressPort : Ref roots (.bits 9) := .named ["meta", "ingress_port"]
def egressPort : Ref roots (.bits 9) := .named ["meta", "egress_port"]
def dropFlag : Ref roots .boolean := .named ["meta", "drop"]
def regPosOne : Ref roots (.bits 32) := .named ["reg_pos_one"]
def regPosTwo : Ref roots (.bits 32) := .named ["reg_pos_two"]
def regValOne : Ref roots (.bits 1) := .named ["reg_val_one"]
def regValTwo : Ref roots (.bits 1) := .named ["reg_val_two"]
def direction : Ref roots (.bits 1) := .named ["direction"]
def crc16Result : Ref roots (.bits 16) := .named ["crc16_result"]
def checkPortsHit : Ref roots .boolean := .named ["check_ports_hit"]

def ipv4 : HeaderRef roots := .mk .here (.field (.there .here) .here)
def tcp : HeaderRef roots := .mk .here (.field (.there (.there .here)) .here)

private def bits (width value : Nat) : P4bloIR.Expr := .literal (.bits width value)
private def hdrParam (dir : Direction) : Param := ⟨"hdr", .struct "headers", dir⟩
private def metaParam : Param := ⟨"meta", .struct "metadata", .inout⟩

def parser : Block :=
  { (default : Block) with
    name := "MyParser", kind := .parser, params := [hdrParam .out, metaParam]
    startState := "start"
    states := [
      ⟨"start", [], .direct (.state "parse_ethernet")⟩,
      ⟨"parse_ethernet", [.extract (.member (.var "hdr") "ethernet")],
        .select [ethType.expr] [⟨[.exact (.bits 16 2048)], .state "parse_ipv4"⟩,
          ⟨[.dontCare], .accept⟩]⟩,
      ⟨"parse_ipv4", [.extract (.member (.var "hdr") "ipv4")],
        .select [ipProtocol.expr] [⟨[.exact (.bits 8 6)], .state "tcp"⟩,
          ⟨[.dontCare], .accept⟩]⟩,
      ⟨"tcp", [.extract (.member (.var "hdr") "tcp")], .direct .accept⟩] }

def noAction : Action := ⟨"NoAction", [], []⟩
def dropAction : Action := ⟨"drop", [], [
  .assign dropFlag.lvalue (.literal (.boolean true)),
  .assign egressPort.lvalue (bits 9 511)]⟩

/-- The complete 104-bit tuple, with visible left-associated field order. -/
def hashInput : P4bloIR.Expr :=
  [.var "ipAddr2", .var "port1", .var "port2", ipProtocol.expr].foldl
    (.binary .concat) (.var "ipAddr1")

def computeHashes : Action :=
  ⟨"compute_hashes", [⟨"ipAddr1", .bits 32, .none⟩, ⟨"ipAddr2", .bits 32, .none⟩,
    ⟨"port1", .bits 16, .none⟩, ⟨"port2", .bits 16, .none⟩], [
    .callExtern "hash16" "compute" [.expr hashInput] (some crc16Result.lvalue),
    .assign regPosOne.lvalue (.cast (.bits 32) (.binary .bitAnd crc16Result.expr (bits 16 4095))),
    .callExtern "hash32" "compute" [.expr hashInput] (some regPosTwo.lvalue),
    .assign regPosTwo.lvalue (.binary .bitAnd regPosTwo.expr (bits 32 4095))]⟩

def forwardAction : Action :=
  ⟨"ipv4_forward", [⟨"dstAddr", .bits 48, .none⟩, ⟨"port", .bits 9, .none⟩], [
    .assign egressPort.lvalue (.var "port"),
    .assign ethSrc.lvalue ethDst.expr,
    .assign ethDst.lvalue (.var "dstAddr"),
    .assign ttl.lvalue (.binary .sub ttl.expr (bits 8 1))]⟩

def setDirection : Action :=
  ⟨"set_direction", [⟨"dir", .bits 1, .none⟩], [.assign direction.lvalue (.var "dir")]⟩

def ipv4Table : Table :=
  ⟨"ipv4_lpm", [⟨ipDst.expr, .lpm, ""⟩], ["ipv4_forward", "drop", "NoAction"],
    some ⟨"drop", []⟩, false, [], 1024⟩
def directionTable : Table :=
  ⟨"check_ports", [⟨ingressPort.expr, .exact, ""⟩, ⟨egressPort.expr, .exact, ""⟩],
    ["set_direction", "NoAction"], some ⟨"NoAction", []⟩, false, [], 1024⟩

def insertBloom : List Stmt := [
  .callExtern "bloom_filter_1" "write" [.expr regPosOne.expr, .expr (bits 1 1)] none,
  .callExtern "bloom_filter_2" "write" [.expr regPosTwo.expr, .expr (bits 1 1)] none]

def checkBloom : List Stmt := [
  .callExtern "bloom_filter_1" "read" [.lvalue regValOne.lvalue, .expr regPosOne.expr] none,
  .callExtern "bloom_filter_2" "read" [.lvalue regValTwo.lvalue, .expr regPosTwo.expr] none,
  .conditional (.binary .or (.binary .ne regValOne.expr (bits 1 1))
    (.binary .ne regValTwo.expr (bits 1 1))) [.callAction "drop" []] []]

def filterBody : List Stmt := [
  .conditional (.binary .eq direction.expr (bits 1 0))
    [.callAction "compute_hashes" [.expr ipSrc.expr, .expr ipDst.expr,
      .expr tcpSrc.expr, .expr tcpDst.expr]]
    [.callAction "compute_hashes" [.expr ipDst.expr, .expr ipSrc.expr,
      .expr tcpDst.expr, .expr tcpSrc.expr]],
  .conditional (.binary .eq direction.expr (bits 1 0))
    [.conditional (.binary .eq tcpSyn.expr (bits 1 1)) insertBloom []]
    [.conditional (.binary .eq direction.expr (bits 1 1)) checkBloom []]]

/-- The source paths coincide with the forwarder's shared IPv4 layout.
Reusing this raw expression is not reusing its two-header frame theorem. -/
def checksumInput : P4bloIR.Expr := Forwarder.checksumInput

def ingress : Block :=
  { (default : Block) with
    name := "MyIngress", kind := .control, params := [hdrParam .inout, metaParam]
    locals := localFields.fields.map fun f => ⟨f.name, f.type⟩
    actions := [noAction, dropAction, computeHashes, forwardAction, setDirection]
    tables := [ipv4Table, directionTable]
    body := [
      .conditional ipv4.expr [
        .apply "ipv4_lpm" none,
        .conditional tcp.expr [
          .assign direction.lvalue (bits 1 0),
          .apply "check_ports" (some checkPortsHit.lvalue),
          .conditional checkPortsHit.expr filterBody []] []] [],
      .conditional ipv4.expr
        [.callExtern "csum" "compute" [.expr checksumInput] (some hdrChecksum.lvalue)] []] }

def deparser : Block :=
  { (default : Block) with
    name := "MyDeparser", kind := .deparser, params := [hdrParam .in]
    body := [.emit (.member (.var "hdr") "ethernet"),
      .emit (.member (.var "hdr") "ipv4"), .emit (.member (.var "hdr") "tcp")] }

def registerType : ExternType :=
  ⟨"register", [⟨"size", .bits 32, .in⟩], [
    ⟨"read", [⟨"result", .bits 1, .out⟩, ⟨"index", .bits 32, .in⟩], none⟩,
    ⟨"write", [⟨"index", .bits 32, .in⟩, ⟨"value", .bits 1, .in⟩], none⟩]⟩

private def computeType (name : String) (input output : Nat) : ExternType :=
  ⟨name, [], [⟨"compute", [⟨"data", .bits input, .in⟩], some (.bits output)⟩]⟩

def program : Program :=
  { name := "tutorial_firewall"
    errors := ["NoError", "PacketTooShort", "NoMatch", "StackOutOfBounds",
      "HeaderTooShort", "ParserTimeout", "ParserInvalidArgument"]
    headerTypes := [⟨"ethernet_t", Forwarder.ethernetFields.fields⟩,
      ⟨"ipv4_t", Forwarder.ipv4Fields.fields⟩, ⟨"tcp_t", tcpFields.fields⟩]
    structTypes := [⟨"headers", headersFields.fields⟩, ⟨"metadata", Forwarder.metadataFields.fields⟩]
    enumTypes := []
    externTypes := [registerType, computeType "crc16" 104 16,
      computeType "crc32" 104 32, computeType "checksum16" 144 16]
    externInstances := [⟨"bloom_filter_1", "register", [.bits 32 4096]⟩,
      ⟨"bloom_filter_2", "register", [.bits 32 4096]⟩, ⟨"hash16", "crc16", []⟩,
      ⟨"hash32", "crc32", []⟩, ⟨"csum", "checksum16", []⟩]
    blocks := [parser, ingress, deparser]
    headers := "headers", metadata := "metadata"
    exports := [⟨"parser", "MyParser"⟩, ⟨"control", "MyIngress"⟩, ⟨"deparser", "MyDeparser"⟩] }

end P4blo.TutorialFirewall
