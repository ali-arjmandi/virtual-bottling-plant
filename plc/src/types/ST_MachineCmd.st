(* One-scan PackML commands to one machine (from FB_LineSequencer). *)
TYPE
  ST_MachineCmd : STRUCT
    Start : BOOL;
    Stop : BOOL;
    Reset : BOOL;   (* Stopped → Idle, and Held → Unholding (unhold) *)
    Abort : BOOL;
    Clear : BOOL;
  END_STRUCT;
END_TYPE
