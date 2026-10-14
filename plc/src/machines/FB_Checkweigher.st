(* Q-701 checkweigher. Rejects bottles below the fill target minus 10 g (995 g at 1005 g). *)
FUNCTION_BLOCK FB_Checkweigher
  VAR_INPUT
    LineCmd : ST_MachineCmd;
    OwnCmd : E_Command;
    StopReasonCmd : INT;
    HoldId : INT;
    LineHoldId : INT;
    Running : BOOL;
    InputFill : REAL;          (* CV3_Fill, bottles *)
    UpstreamExecute : BOOL;    (* the machine feeding CV3 is producing *)
    OutputFull : BOOL;         (* CV4_Full *)
    Count : UDINT;             (* bottles weighed *)
    RejectCount : UDINT;
    Recipe : ST_Recipe;
    NowMs : UDINT;
  END_VAR
  VAR_OUTPUT
    Status : ST_PackagingStatus;
    Run : BOOL;
    SpeedSP : REAL;
    RejectLimitG : REAL;
    GoodCount : UDINT;
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
  SpeedSP := Recipe.LineSpeed + 20.0;
  RejectLimitG := Recipe.FillTargetG - 10.0;
  IF Count >= RejectCount THEN
    GoodCount := Count - RejectCount;
  ELSE
    GoodCount := 0;  (* one counter wrapped before the other *)
  END_IF;
END_FUNCTION_BLOCK
