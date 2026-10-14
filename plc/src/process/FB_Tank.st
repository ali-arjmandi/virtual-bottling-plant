(* Tank level monitor with a low-level hysteresis (T-301 filler interlock, PLC-11):
   Low below LowLimit, clears only at or above LowReset. *)
FUNCTION_BLOCK FB_Tank
  VAR_INPUT
    Level : REAL;        (* % *)
    LowLimit : REAL;     (* % *)
    LowReset : REAL;     (* % *)
  END_VAR
  VAR_OUTPUT
    Low : BOOL := TRUE;
    AboveLow : BOOL;
  END_VAR

  IF Level < LowLimit THEN
    Low := TRUE;
  ELSIF Level >= LowReset THEN
    Low := FALSE;
  END_IF;
  AboveLow := NOT Low;
END_FUNCTION_BLOCK
