(* F-401 rotary filler, the line constraint. Interlock PLC-11: it fills only while T-301
   is above its start level (FB_Tank hysteresis), otherwise it is Suspended (starved) with the
   motor off, so it cannot run the buffer dry. *)
FUNCTION_BLOCK FB_Filler
  VAR_INPUT
    LineCmd : ST_MachineCmd;
    OwnCmd : E_Command;
    StopReasonCmd : INT;
    HoldId : INT;
    LineHoldId : INT;
    Running : BOOL;
    OutputFull : BOOL;         (* CV1_Full *)
    BufferPermissive : BOOL;   (* T-301 above the filler start level *)
    Recipe : ST_Recipe;
    NowMs : UDINT;
  END_VAR
  VAR_OUTPUT
    Status : ST_PackagingStatus;
    Run : BOOL;
    SpeedSP : REAL;
    FillTargetG : REAL;
  END_VAR
  VAR
    Unit : FB_PackagingUnit;
  END_VAR

  Unit(LineCmd := LineCmd, OwnCmd := OwnCmd, StopReasonCmd := StopReasonCmd, HoldId := HoldId,
       LineHoldId := LineHoldId, Blocked := OutputFull, Starved := NOT BufferPermissive,
       StarvedDelayMs := 2000, Running := Running, NowMs := NowMs);
  Status := Unit.Status;
  Run := Unit.RunOut AND BufferPermissive;
  SpeedSP := Recipe.LineSpeed;
  FillTargetG := Recipe.FillTargetG;
END_FUNCTION_BLOCK
