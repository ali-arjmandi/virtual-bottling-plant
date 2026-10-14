(* K-801 case packer, end of line (never blocked). It waits for 6 bottles per case. *)
FUNCTION_BLOCK FB_CasePacker
  VAR_INPUT
    LineCmd : ST_MachineCmd;
    OwnCmd : E_Command;
    StopReasonCmd : INT;
    HoldId : INT;
    LineHoldId : INT;
    Running : BOOL;
    InputFill : REAL;          (* CV4_Fill, bottles *)
    UpstreamExecute : BOOL;    (* the machine feeding CV4 is producing *)
    Recipe : ST_Recipe;
    NowMs : UDINT;
  END_VAR
  VAR_OUTPUT
    Status : ST_PackagingStatus;
    Run : BOOL;
    SpeedSP : REAL;
  END_VAR
  VAR
    Unit : FB_PackagingUnit;
  END_VAR

  Unit(LineCmd := LineCmd, OwnCmd := OwnCmd, StopReasonCmd := StopReasonCmd, HoldId := HoldId,
       LineHoldId := LineHoldId, Blocked := FALSE,
       Starved := InputFill < 6.0 AND NOT UpstreamExecute,
       StarvedDelayMs := 2000, Running := Running, NowMs := NowMs);
  Status := Unit.Status;
  Run := Unit.RunOut;
  SpeedSP := Recipe.LineSpeed / 6.0 + 2.0;  (* cases/min, a little faster than the filler *)
END_FUNCTION_BLOCK
