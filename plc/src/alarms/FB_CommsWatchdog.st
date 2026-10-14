(* Comms watchdog for one remote I/O station (PLC-15). OpenPLC keeps the last values when a
   slave stops answering, so a frozen heartbeat register is the only sign (ADR 0005).
   Real time on purpose: comms health does not depend on the sim clock or a paused sim. *)
FUNCTION_BLOCK FB_CommsWatchdog
  VAR_INPUT
    Heartbeat : UINT;      (* {EQ}_Heartbeat: +1 per 100 ms while the station answers *)
  END_VAR
  VAR_OUTPUT
    Ok : BOOL;
  END_VAR
  VAR
    LastHeartbeat : UINT;
    Silence : TON;
  END_VAR

  Silence(IN := Heartbeat = LastHeartbeat, PT := T#1500ms);
  LastHeartbeat := Heartbeat;
  Ok := NOT Silence.Q;
END_FUNCTION_BLOCK
