(* One alarm (PLC-20): priority, active, acknowledged, first-out (PLC-22).
   An alarm stays shown until it is inactive AND acknowledged. First-out: the first alarm to
   come in while nothing was shown takes the shared FirstOutFree token (FB_AlarmTable re-arms
   it once the table is clear), so the HMI and MES can tell cause from consequence. *)
FUNCTION_BLOCK FB_Alarm
  VAR_INPUT
    Condition : BOOL;
    AckId : INT;           (* this alarm's id, or -1 for all *)
    Id : INT;
    Priority : INT;        (* 1 = high ... 4 = low *)
  END_VAR
  VAR_IN_OUT
    FirstOutFree : BOOL;
  END_VAR
  VAR_OUTPUT
    Active : BOOL;
    Acked : BOOL := TRUE;
    FirstOut : BOOL;
    Shown : BOOL;
    StatusWord : UINT;     (* bit0 active, bit1 acked, bit2 first-out, bits 8-11 priority *)
  END_VAR
  VAR
    Rise : R_TRIG;
  END_VAR

  Rise(CLK := Condition);
  IF Rise.Q THEN
    Acked := FALSE;
    IF FirstOutFree THEN
      FirstOut := TRUE;
      FirstOutFree := FALSE;
    END_IF;
  END_IF;
  Active := Condition;
  IF AckId <> 0 AND (AckId = Id OR AckId = -1) THEN
    Acked := TRUE;
  END_IF;
  Shown := Active OR NOT Acked;
  IF NOT Shown THEN
    FirstOut := FALSE;
  END_IF;
  StatusWord := BOOL_TO_UINT(Active) + 2 * BOOL_TO_UINT(Acked) + 4 * BOOL_TO_UINT(FirstOut)
          + 256 * INT_TO_UINT(Priority);
END_FUNCTION_BLOCK
