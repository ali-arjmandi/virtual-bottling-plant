(* On-delay timer on sim time (TON semantics, PT and ET in ms of simulated time). *)
FUNCTION_BLOCK FB_SimTon
  VAR_INPUT
    IN : BOOL;
    PT : UDINT;
    NowMs : UDINT;
  END_VAR
  VAR_OUTPUT
    Q : BOOL;
    ET : UDINT;
  END_VAR
  VAR
    StartMs : UDINT;
    Timing : BOOL;
  END_VAR

  IF NOT IN THEN
    Timing := FALSE;
    Q := FALSE;
    ET := 0;
  ELSE
    IF NOT Timing THEN
      Timing := TRUE;
      StartMs := NowMs;
    END_IF;
    ET := NowMs - StartMs;
    Q := ET >= PT;
  END_IF;
END_FUNCTION_BLOCK
