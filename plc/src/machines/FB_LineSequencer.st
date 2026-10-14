(* Line start/stop from the local panel (sim operator) or the HMI line command.
   Start: each machine is reset if Stopped, then started once the machine after it is running,
   so the line starts from the case packer back to the filler. Stop: every machine stops.
   Reset: unholds machines whose cause is gone (and resets stopped ones). *)
FUNCTION_BLOCK FB_LineSequencer
  VAR_INPUT
    PbStart : BOOL;
    PbStop : BOOL;
    PbReset : BOOL;
    LineCmd : E_Command;
    F401State : E_PackMLState;
    C501State : E_PackMLState;
    L601State : E_PackMLState;
    Q701State : E_PackMLState;
    K801State : E_PackMLState;
  END_VAR
  VAR_OUTPUT
    F401 : ST_MachineCmd;
    C501 : ST_MachineCmd;
    L601 : ST_MachineCmd;
    Q701 : ST_MachineCmd;
    K801 : ST_MachineCmd;
    StartRequested : BOOL;
  END_VAR
  VAR
    StartEdge : R_TRIG;
    StopEdge : R_TRIG;
    ResetEdge : R_TRIG;
    Stop : BOOL;
    Reset : BOOL;
    Abort : BOOL;
    Clear : BOOL;
  END_VAR

  StartEdge(CLK := PbStart);
  StopEdge(CLK := PbStop);
  ResetEdge(CLK := PbReset);
  Stop := StopEdge.Q OR LineCmd = CMD_STOP;
  Reset := ResetEdge.Q OR LineCmd = CMD_RESET;
  Abort := LineCmd = CMD_ABORT;
  Clear := LineCmd = CMD_CLEAR;

  IF Stop OR Abort THEN
    StartRequested := FALSE;
  ELSIF StartEdge.Q OR LineCmd = CMD_START THEN
    StartRequested := TRUE;
  END_IF;

  K801.Start := StartRequested AND K801State = PML_IDLE;
  Q701.Start := StartRequested AND Q701State = PML_IDLE AND PackMLHasStarted(K801State);
  L601.Start := StartRequested AND L601State = PML_IDLE AND PackMLHasStarted(Q701State);
  C501.Start := StartRequested AND C501State = PML_IDLE AND PackMLHasStarted(L601State);
  F401.Start := StartRequested AND F401State = PML_IDLE AND PackMLHasStarted(C501State);

  K801.Reset := Reset OR (StartRequested AND K801State = PML_STOPPED);
  Q701.Reset := Reset OR (StartRequested AND Q701State = PML_STOPPED);
  L601.Reset := Reset OR (StartRequested AND L601State = PML_STOPPED);
  C501.Reset := Reset OR (StartRequested AND C501State = PML_STOPPED);
  F401.Reset := Reset OR (StartRequested AND F401State = PML_STOPPED);

  K801.Stop := Stop;
  K801.Abort := Abort;
  K801.Clear := Clear;
  Q701.Stop := Stop;
  Q701.Abort := Abort;
  Q701.Clear := Clear;
  L601.Stop := Stop;
  L601.Abort := Abort;
  L601.Clear := Clear;
  C501.Stop := Stop;
  C501.Abort := Abort;
  C501.Clear := Clear;
  F401.Stop := Stop;
  F401.Abort := Abort;
  F401.Clear := Clear;

  (* The request ends once every machine is under way; later stops are not undone. *)
  IF StartRequested AND PackMLHasStarted(F401State) AND PackMLHasStarted(C501State)
     AND PackMLHasStarted(L601State) AND PackMLHasStarted(Q701State)
     AND PackMLHasStarted(K801State) THEN
    StartRequested := FALSE;
  END_IF;
END_FUNCTION_BLOCK
