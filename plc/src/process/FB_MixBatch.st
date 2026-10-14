(* T-101 batch sequence (PLC-03, ISA-88 phases): Fill (dose water, concentrate, sugar by
   flow totals), Mix, Transfer to T-301 through P-201. A recipe with another product first
   drains T-101 and T-301, then runs CIP. There is no time-of-day window: a new batch starts
   whenever T-101 is empty. One mix tank only (decision P2, see l1-plc.md). *)
FUNCTION_BLOCK FB_MixBatch
  VAR_INPUT
    Recipe : ST_Recipe;
    WaterFlow : REAL;        (* FT101, L/min *)
    ConcFlow : REAL;         (* FT102 *)
    SugarFlow : REAL;        (* FT103 *)
    Brix : REAL;             (* AT101 *)
    TankEmpty : BOOL;        (* LSL101 *)
    BufferLevel : REAL;      (* LT301, % *)
    CipDone : BOOL;
    NowMs : UDINT;
    DtS : REAL;
  END_VAR
  VAR_OUTPUT
    WaterValve : BOOL;
    ConcValve : BOOL;
    SugarValve : BOOL;
    Agitator : BOOL;
    TransferPump : BOOL;
    TankDrain : BOOL;
    BufferDrain : BOOL;
    CipRun : BOOL;
    ConcSelect : REAL;       (* product code to the concentrate feed selector *)
    Status : ST_T101Status;
    BrixAlarm : BOOL;
  END_VAR
  VAR
    MixTimer : FB_SimTon;
    NotEmptyInIdle : FB_SimTon;
    TargetWater : REAL;
    TargetConc : REAL;
    TargetSugar : REAL;
    DosedWater : REAL;
    DosedConc : REAL;
    DosedSugar : REAL;
    ConcBrix : REAL;
    PumpOn : BOOL;
  END_VAR
  VAR CONSTANT
    BATCH_L : REAL := 5000.0;
    SUGAR_SYRUP_BRIX : REAL := 67.0;
    MIX_MS : UDINT := 900000;        (* 15 min *)
    BUFFER_PUMP_ON : REAL := 90.0;   (* % T-301 *)
    BUFFER_PUMP_OFF : REAL := 98.0;
    BUFFER_EMPTY : REAL := 0.5;
  END_VAR

  WaterValve := FALSE; ConcValve := FALSE; SugarValve := FALSE; Agitator := FALSE;
  TransferPump := FALSE; TankDrain := FALSE; BufferDrain := FALSE; CipRun := FALSE;
  IF Status.ProductCode = 0 THEN
    Status.ProductCode := Recipe.ProductCode;  (* cold start: assume the recipe's product *)
  END_IF;

  NotEmptyInIdle(IN := Status.Phase = PHASE_IDLE AND NOT TankEmpty, PT := 10000,
                 NowMs := NowMs);
  CASE Status.Phase OF
    PHASE_IDLE:
      IF Recipe.ProductCode <> Status.ProductCode THEN
        Status.Phase := PHASE_DRAIN;
      ELSIF TankEmpty THEN
        IF Status.ProductCode = 2 THEN ConcBrix := 70.0; ELSE ConcBrix := 65.0; END_IF;
        TargetConc := Recipe.ConcRatio * BATCH_L;
        TargetSugar := MAX(0.0, (Recipe.BrixTarget - Recipe.ConcRatio * ConcBrix) * BATCH_L
                                / SUGAR_SYRUP_BRIX);
        TargetWater := BATCH_L - TargetConc - TargetSugar;
        DosedWater := 0.0; DosedConc := 0.0; DosedSugar := 0.0;
        Status.BatchNo := (Status.BatchNo + 1) MOD 30000;
        Status.BatchActive := TRUE;
        Status.BrixOk := FALSE;
        Status.BatchBrix := 0.0;
        BrixAlarm := FALSE;
        Status.Phase := PHASE_FILL;
      ELSIF NotEmptyInIdle.Q THEN
        (* Content of unknown dosing, e.g. after a PLC restart mid-batch: mix it, check the
           Brix and transfer it as its own batch rather than wait forever for an empty tank.
           Debounced: a sim reset clears its registers, so LSL101 reads 'not empty' briefly. *)
        Status.BatchNo := (Status.BatchNo + 1) MOD 30000;
        Status.BatchActive := TRUE;
        Status.Phase := PHASE_MIX;
      END_IF;

    PHASE_FILL:
      DosedWater := DosedWater + WaterFlow * DtS / 60.0;
      DosedConc := DosedConc + ConcFlow * DtS / 60.0;
      DosedSugar := DosedSugar + SugarFlow * DtS / 60.0;
      WaterValve := DosedWater < TargetWater;
      ConcValve := DosedConc < TargetConc;
      SugarValve := DosedSugar < TargetSugar;
      IF NOT (WaterValve OR ConcValve OR SugarValve) THEN
        Status.Phase := PHASE_MIX;
      END_IF;

    PHASE_MIX:
      Agitator := TRUE;
      IF MixTimer.Q THEN
        Status.BatchBrix := Brix;
        Status.BrixOk := ABS(Brix - Recipe.BrixTarget) <= Recipe.BrixTol;
        BrixAlarm := NOT Status.BrixOk;
        PumpOn := FALSE;
        Status.Phase := PHASE_TRANSFER;
      END_IF;

    PHASE_TRANSFER:
      Agitator := TRUE;
      IF BufferLevel < BUFFER_PUMP_ON THEN
        PumpOn := TRUE;
      ELSIF BufferLevel > BUFFER_PUMP_OFF THEN
        PumpOn := FALSE;
      END_IF;
      TransferPump := PumpOn AND NOT TankEmpty;
      IF TankEmpty THEN
        Status.BatchActive := FALSE;
        Status.Phase := PHASE_IDLE;
      END_IF;

    PHASE_DRAIN:
      TankDrain := NOT TankEmpty;
      BufferDrain := BufferLevel >= BUFFER_EMPTY;
      IF TankEmpty AND BufferLevel < BUFFER_EMPTY THEN
        Status.BatchActive := FALSE;
        Status.Phase := PHASE_CIP;
      END_IF;

    PHASE_CIP:
      CipRun := NOT CipDone;
      IF CipDone THEN
        Status.ProductCode := Recipe.ProductCode;
        Status.Phase := PHASE_IDLE;
      END_IF;
  END_CASE;

  MixTimer(IN := Status.Phase = PHASE_MIX, PT := MIX_MS, NowMs := NowMs);
  ConcSelect := INT_TO_REAL(Status.ProductCode);
END_FUNCTION_BLOCK
