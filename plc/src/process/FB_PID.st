(* PI(D) controller with feedforward and anti-windup by conditional integration: the integral
   only moves when the output is not saturated in the direction the error pushes it.
   Dt comes from the sim clock (PLC-14), so tuning holds under time acceleration. *)
FUNCTION_BLOCK FB_PID
  VAR_INPUT
    Enable : BOOL;
    PV : REAL;
    SP : REAL;
    FF : REAL;          (* feedforward, added to the output *)
    Kp : REAL;          (* output % per unit of error *)
    Ti_s : REAL;        (* integral time, s (0 = no integral) *)
    Td_s : REAL;        (* derivative time on PV, s *)
    DtS : REAL;
    OutMin : REAL;
    OutMax : REAL;
  END_VAR
  VAR_OUTPUT
    Out : REAL;
    Error : REAL;
  END_VAR
  VAR
    ITerm : REAL;
    NextITerm : REAL;
    Unclamped : REAL;
    LastPV : REAL;
    DTerm : REAL;
  END_VAR

  Error := SP - PV;
  IF NOT Enable THEN
    ITerm := 0.0;
    Out := OutMin;
  ELSE
    IF DtS > 0.0 THEN
      DTerm := -Kp * Td_s * (PV - LastPV) / DtS;
      IF Ti_s > 0.0 THEN
        NextITerm := ITerm + Kp * Error * DtS / Ti_s;
        Unclamped := FF + Kp * Error + NextITerm + DTerm;
        IF (Unclamped < OutMax OR Error < 0.0) AND (Unclamped > OutMin OR Error > 0.0) THEN
          ITerm := NextITerm;
        END_IF;
      END_IF;
    END_IF;
    Out := LIMIT(OutMin, FF + Kp * Error + ITerm + DTerm, OutMax);
  END_IF;
  LastPV := PV;
END_FUNCTION_BLOCK
