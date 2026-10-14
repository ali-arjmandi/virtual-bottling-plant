(* L-601 labeler. *)
FUNCTION_BLOCK FB_Labeler
  VAR_INPUT
    LineCmd : ST_MachineCmd;
    OwnCmd : E_Command;
    StopReasonCmd : INT;
    HoldId : INT;
    LineHoldId : INT;
    Running : BOOL;
    InputFill : REAL;          (* CV2_Fill, bottles *)
    UpstreamExecute : BOOL;    (* the machine feeding CV2 is producing *)
    OutputFull : BOOL;         (* CV3_Full *)
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
       LineHoldId := LineHoldId, Blocked := OutputFull,
       Starved := InputFill < 1.0 AND NOT UpstreamExecute,
       StarvedDelayMs := 2000, Running := Running, NowMs := NowMs);
  Status := Unit.Status;
  Run := Unit.RunOut;
  SpeedSP := Recipe.LineSpeed + 10.0;
END_FUNCTION_BLOCK
