(* What every packaging machine has in common: PackML, merged line/HMI commands, debounced
   blocked/starved, and Admin.StopReason (PLC-13). Machine FBs add their own causes and
   setpoints. *)
FUNCTION_BLOCK FB_PackagingUnit
  VAR_INPUT
    LineCmd : ST_MachineCmd;   (* from FB_LineSequencer *)
    OwnCmd : E_Command;        (* from the bridge, this machine only *)
    StopReasonCmd : INT;       (* operator reason code from the HMI, 0 = none *)
    HoldId : INT;              (* first active alarm of this machine, 0 = none *)
    LineHoldId : INT;          (* line alarm that holds every machine, 0 = none *)
    Blocked : BOOL;            (* raw: output conveyor full *)
    Starved : BOOL;            (* raw: no input and nothing coming (upstream not producing) *)
    StarvedDelayMs : UDINT;
    Running : BOOL;
    NowMs : UDINT;
  END_VAR
  VAR_OUTPUT
    Status : ST_PackagingStatus;
    RunOut : BOOL;
  END_VAR
  VAR
    PackML : FB_PackML;
    BlockedDelay : FB_SimTon;
    StarvedDelay : FB_SimTon;
    Cmd : ST_MachineCmd;
    LastState : E_PackMLState;
  END_VAR
  VAR CONSTANT
    BLOCKED_DELAY_MS : UDINT := 2000;
  END_VAR

  BlockedDelay(IN := Blocked, PT := BLOCKED_DELAY_MS, NowMs := NowMs);
  StarvedDelay(IN := Starved, PT := StarvedDelayMs, NowMs := NowMs);

  Cmd.Start := LineCmd.Start OR OwnCmd = CMD_START;
  Cmd.Stop := LineCmd.Stop OR OwnCmd = CMD_STOP;
  Cmd.Reset := LineCmd.Reset OR OwnCmd = CMD_RESET;
  Cmd.Abort := LineCmd.Abort OR OwnCmd = CMD_ABORT;
  Cmd.Clear := LineCmd.Clear OR OwnCmd = CMD_CLEAR;

  PackML(Cmd := Cmd, HoldCause := HoldId <> 0 OR LineHoldId <> 0,
         SuspendCause := BlockedDelay.Q OR StarvedDelay.Q, Running := Running, NowMs := NowMs);

  (* StopReason: cleared when production resumes, set automatically to the alarm id on a
     hold (1-99), overwritten by the operator's reason code from the HMI (>= 100). *)
  IF PackML.State = PML_EXECUTE AND LastState <> PML_EXECUTE THEN
    Status.StopReason := 0;
  END_IF;
  IF (PackML.State = PML_HOLDING OR PackML.State = PML_HELD) AND Status.StopReason = 0 THEN
    IF HoldId <> 0 THEN
      Status.StopReason := HoldId;
    ELSE
      Status.StopReason := LineHoldId;
    END_IF;
  END_IF;
  IF StopReasonCmd <> 0 THEN
    Status.StopReason := StopReasonCmd;
  END_IF;
  LastState := PackML.State;

  Status.State := PackML.State;
  Status.Mode := MODE_PRODUCTION;
  Status.Blocked := BlockedDelay.Q;
  Status.Starved := StarvedDelay.Q;
  RunOut := PackML.RunOut;
END_FUNCTION_BLOCK
