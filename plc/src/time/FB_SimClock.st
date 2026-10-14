(* PLC time base from the sim clock register (PLC-14), so timers and the PID follow simulated
   time under ×10 / ×60 acceleration. NowMs is the PLC's own monotonic sim time: a sim reset
   (time back to 0) or a jump over a long comms gap adds nothing instead of a huge step. *)
FUNCTION_BLOCK FB_SimClock
  VAR_INPUT
    SimTimeMs : UDINT;    (* unit 9 IR 0-1, wraps at 2^32 *)
  END_VAR
  VAR_OUTPUT
    NowMs : UDINT;        (* monotonic, wraps at 2^32: compare with subtraction only *)
    DtMs : UDINT;
    DtS : REAL;
  END_VAR
  VAR
    LastSimMs : UDINT;
    Started : BOOL;
  END_VAR
  VAR CONSTANT
    MAX_STEP_MS : UDINT := 60000;
  END_VAR

  IF NOT Started THEN
    LastSimMs := SimTimeMs;
    Started := TRUE;
  END_IF;
  DtMs := SimTimeMs - LastSimMs;  (* unsigned: correct across the 2^32 wrap *)
  IF DtMs > MAX_STEP_MS THEN
    DtMs := 0;
  END_IF;
  LastSimMs := SimTimeMs;
  NowMs := NowMs + DtMs;
  DtS := UDINT_TO_REAL(DtMs) / 1000.0;
END_FUNCTION_BLOCK
