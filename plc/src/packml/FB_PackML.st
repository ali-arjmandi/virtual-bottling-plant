(* PackML state machine (PLC-01, ISA-TR88.00.02), shared by every packaging machine.
   Acting states (Starting, Holding, Stopping...) complete on the motor feedback, or after
   FEEDBACK_TIMEOUT_MS so a missing feedback can never lock the machine in a transition. *)
FUNCTION_BLOCK FB_PackML
  VAR_INPUT
    Cmd : ST_MachineCmd;     (* one-scan commands *)
    HoldCause : BOOL;        (* internal fault: jam, breakdown, material out, comms (PLC-10) *)
    SuspendCause : BOOL;     (* external: blocked or starved (PLC-10) *)
    Running : BOOL;          (* motor running feedback *)
    NowMs : UDINT;
  END_VAR
  VAR_OUTPUT
    State : E_PackMLState := PML_STOPPED;
    RunOut : BOOL;           (* motor run command *)
  END_VAR
  VAR
    InState : FB_SimTon;
    LastState : E_PackMLState := PML_STOPPED;
  END_VAR
  VAR CONSTANT
    FEEDBACK_TIMEOUT_MS : UDINT := 5000;
  END_VAR

  InState(IN := TRUE, PT := FEEDBACK_TIMEOUT_MS, NowMs := NowMs);

  IF Cmd.Abort AND State <> PML_ABORTING AND State <> PML_ABORTED THEN
    State := PML_ABORTING;
  END_IF;

  CASE State OF
    PML_ABORTING:
      IF NOT Running OR InState.Q THEN State := PML_ABORTED; END_IF;
    PML_ABORTED:
      IF Cmd.Clear THEN State := PML_CLEARING; END_IF;
    PML_CLEARING:
      State := PML_STOPPED;
    PML_STOPPED:
      IF Cmd.Reset THEN State := PML_RESETTING; END_IF;
    PML_RESETTING:
      State := PML_IDLE;
    PML_IDLE:
      IF Cmd.Stop THEN
        State := PML_STOPPING;
      ELSIF Cmd.Start AND NOT HoldCause THEN
        State := PML_STARTING;
      END_IF;
    PML_STARTING, PML_UNHOLDING:
      IF Cmd.Stop THEN
        State := PML_STOPPING;
      ELSIF HoldCause THEN
        State := PML_HOLDING;
      ELSIF Running OR InState.Q THEN
        State := PML_EXECUTE;
      END_IF;
    PML_EXECUTE:
      IF Cmd.Stop THEN
        State := PML_STOPPING;
      ELSIF HoldCause THEN
        State := PML_HOLDING;
      ELSIF SuspendCause THEN
        State := PML_SUSPENDING;
      END_IF;
    PML_SUSPENDING:
      State := PML_SUSPENDED;
    PML_SUSPENDED:
      IF Cmd.Stop THEN
        State := PML_STOPPING;
      ELSIF HoldCause THEN
        State := PML_HOLDING;
      ELSIF NOT SuspendCause THEN
        State := PML_UNSUSPENDING;
      END_IF;
    PML_UNSUSPENDING:
      State := PML_EXECUTE;
    PML_HOLDING:
      IF NOT Running OR InState.Q THEN State := PML_HELD; END_IF;
    PML_HELD:
      IF Cmd.Stop THEN
        State := PML_STOPPING;
      ELSIF Cmd.Reset AND NOT HoldCause THEN
        State := PML_UNHOLDING;
      END_IF;
    PML_STOPPING:
      IF NOT Running OR InState.Q THEN State := PML_STOPPED; END_IF;
    PML_COMPLETE:
      IF Cmd.Reset THEN State := PML_RESETTING; END_IF;
  ELSE
    State := PML_STOPPED;
  END_CASE;

  IF State <> LastState THEN
    LastState := State;
    InState(IN := FALSE, PT := FEEDBACK_TIMEOUT_MS, NowMs := NowMs);
  END_IF;

  (* Suspended keeps the motor on: the machine waits for bottles or room and resumes by itself *)
  RunOut := State = PML_STARTING OR State = PML_EXECUTE OR State = PML_SUSPENDING
            OR State = PML_SUSPENDED OR State = PML_UNSUSPENDING OR State = PML_UNHOLDING;
END_FUNCTION_BLOCK
