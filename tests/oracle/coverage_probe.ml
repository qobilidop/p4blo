(* p4blo's coverage probe, built by tests/oracle/coverage.py (`build`) in a
   directory beside the P4-SpecTec checkout, never inside it. It links the
   checkout's `p4spectec` library and uses its public entry points only:
   `P4spectec.structure`, `P4spectec.build_sim`, `Inst.Hook` and
   `Simulator.run_stf_test`. coverage.py's docstring says what it prints and
   how the lines become rule names. *)

open Lang
open Sl
open Util.Source
module Sig = Runtime.Sim.Signature

let kind_of (instr : instr) =
  match instr.it with
  | IfI _ -> "if" | HoldI _ -> "hold" | CaseI _ -> "case" | GroupI _ -> "group"
  | LetI _ -> "let" | RuleI _ -> "rule" | ResultI _ -> "result"
  | ReturnI _ -> "return" | DebugI _ -> "debug"

let () =
  match Array.to_list Sys.argv with
  | _ :: out :: spec :: include_ :: pairs ->
      let oc = open_out out in
      let pr fmt = Printf.fprintf oc fmt in
      let rec walk_block origin parent block =
        List.iter (walk_instr origin parent) block
      and walk_instr origin parent (instr : instr) =
        let r = instr.at in
        (* A rule instruction whose whole block is its `Result`, with no
           iteration premises: the only shape the interpreter tail-calls
           (interp-sl/interp.ml, `eval_rule_instr`). *)
        let tail =
          match instr.it with
          | RuleI (_, _, _, [], [ { it = ResultI _; _ } ]) -> 1
          | _ -> 0
        in
        pr "I\t%d\t%s\t%s\t%d\t%s\t%d\t%d\n" instr.note.iid (kind_of instr)
          origin parent r.left.file r.left.line tail;
        let sub = walk_block origin instr.note.iid in
        match instr.it with
        | IfI (_, _, b, _) -> sub b
        | HoldI (_, _, _, BothH (b1, b2)) -> sub b1; sub b2
        | HoldI (_, _, _, HoldH (b, _)) | HoldI (_, _, _, NotHoldH (b, _)) -> sub b
        | CaseI (_, cases, _) -> List.iter (fun (_, b) -> sub b) cases
        | GroupI (_, _, _, b) | LetI (_, _, _, b) | RuleI (_, _, _, _, b) -> sub b
        | DebugI _ | ResultI _ | ReturnI _ -> ()
      in
      let walk_def (def : def) =
        let d kind (id : id) =
          pr "D\t%s\t%s\t%s\t%d\n" kind id.it def.at.left.file def.at.left.line
        in
        let body (id : id) block elseblock =
          walk_block id.it (-1) block;
          Option.iter (walk_block id.it (-1)) elseblock
        in
        match def.it with
        | RelD (id, _, _, b, e, _) -> d "relation" id; body id b e
        | FuncDecD (id, _, _, _, b, e, _) -> d "function" id; body id b e
        | TableDecD (id, _, _, rows, _) ->
            d "function" id;
            List.iter (fun (_, _, b) -> walk_block id.it (-1) b) rows
        | BuiltinDecD (id, _, _, _, _) | ExternDecD (id, _, _, _, _) ->
            d "function" id
        | ExternRelD (id, _, _, _) -> d "relation" id
        (* Types and meta-variables have no instructions and are never
           entered; listed so that a new kind of definition fails to build. *)
        | ExternTypD _ | TypD _ | VarD _ -> ()
      in
      let spec_sl =
        match P4spectec.structure ~final:true [ spec ] with
        | Ok s -> s
        | Error _ -> failwith "the spec does not structure"
      in
      List.iter walk_def spec_sl;
      let spec_sim = Sig.SL spec_sl in
      let (module Simulator : Sig.SIM) =
        match P4spectec.build_sim ~cache:false ~arch:"v1model" spec_sim with
        | Ok s -> s
        | Error _ -> failwith "the simulator does not build"
      in
      let rec run index = function
        | p4 :: stf :: rest ->
            let instrs = Hashtbl.create 4096 and calls = Hashtbl.create 1024 in
            let bump tbl key =
              Hashtbl.replace tbl key
                (1 + Option.value ~default:0 (Hashtbl.find_opt tbl key))
            in
            let module H : Inst.Handler.HANDLER = struct
              include Inst.Handler.Default
              let on_instr (instr : instr) = bump instrs instr.note.iid
              let on_rel_enter (id : id) _ = bump calls ("relation\t" ^ id.it)
              let on_func_enter (id : id) _ = bump calls ("function\t" ^ id.it)
            end in
            Inst.Hook.register [ (module H : Inst.Handler.HANDLER) ];
            Inst.Hook.init_spec spec_sim;
            let result = Simulator.run_stf_test [ include_ ] p4 stf in
            Inst.Hook.finish ();
            let verdict =
              match result with
              | Pass () -> "pass"
              | Fail (`Syntax _) -> "syntax"
              | Fail (`Runtime _) -> "runtime"
            in
            pr "P\t%d\t%s\t%s\t%s\n" index p4 stf verdict;
            Hashtbl.iter (fun iid n -> pr "H\t%d\t%d\t%d\n" index iid n) instrs;
            Hashtbl.iter (fun key n -> pr "C\t%d\t%s\t%d\n" index key n) calls;
            run (index + 1) rest
        | [] -> ()
        | _ -> failwith "programs and vectors must come in pairs"
      in
      run 0 pairs;
      close_out oc
  | _ -> failwith "usage: probe OUT SPEC INCLUDE [P4 STF]..."
