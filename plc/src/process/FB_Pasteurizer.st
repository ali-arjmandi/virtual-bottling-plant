(* P-201 HTST pasteuriser (PLC-12): outlet temperature PI on the steam valve with flow
   feedforward, and the divert valve. Without feedforward a step from recirculation to
   transfer flow drops the outlet below 83 °C for minutes (Phase 1 finding).
   The temperature rise per % steam scales with 1 / flow (8x at recirculation), so the gain
   is scheduled on flow. On a pump start or stop the flow measurement arrives a poll cycle
   late; the feedforward uses the commanded flow until FT201 agrees with it.
   Divert (PLC-11): opens at once below 83 °C; closes after 30 s stable at SP - 0.5 °C or more. *)
FUNCTION_BLOCK FB_Pasteurizer
  VAR_INPUT
    OutTemp : REAL;          (* TT202, °C *)
    Flow : REAL;             (* FT201, L/min *)
    SteamPressure : REAL;    (* PT201, bar *)
    TempSPCmd : REAL;        (* engineering setpoint from the bridge, 0 = keep *)
    PumpCmd : BOOL;          (* P101 transfer pump commanded *)
    NowMs : UDINT;
    DtS : REAL;
  END_VAR
  VAR_OUTPUT
    SteamValve : REAL;       (* TCV201, % *)
    Divert : BOOL := TRUE;   (* XV203, fail-safe: divert until proven hot *)
    Status : ST_P201Status;
    LowTempAlarm : BOOL;
    SteamLowAlarm : BOOL;
  END_VAR
  VAR
    TempCtrl : FB_PID;
    StableHot : FB_SimTon;
    SteamLow : FB_SimTon;
    DivertEdge : R_TRIG;
    Setpoint : REAL := 85.0;
    ExpectedFlow : REAL;
    FlowFF : REAL;
  END_VAR
  VAR CONSTANT
    MIN_SAFE_TEMP : REAL := 83.0;
    STABLE_MS : UDINT := 30000;
    NOMINAL_FLOW : REAL := 400.0;   (* L/min transfer *)
    RECIRC_FLOW : REAL := 50.0;     (* L/min, pump off *)
    FF_AT_NOMINAL : REAL := 60.0;   (* % steam valve at nominal flow *)
    KP_AT_NOMINAL : REAL := 2.0;    (* % per °C at nominal flow *)
    TI_S : REAL := 60.0;
    STEAM_LOW_BAR : REAL := 2.4;    (* nominal 3.0 bar *)
  END_VAR

  IF TempSPCmd >= 70.0 AND TempSPCmd <= 90.0 THEN
    Setpoint := TempSPCmd;
  END_IF;

  IF PumpCmd THEN
    ExpectedFlow := NOMINAL_FLOW;
  ELSE
    ExpectedFlow := RECIRC_FLOW;
  END_IF;
  IF ABS(Flow - ExpectedFlow) > 0.2 * ExpectedFlow THEN
    FlowFF := ExpectedFlow;               (* pump just started or stopped *)
  ELSE
    FlowFF := MAX(Flow, RECIRC_FLOW);
  END_IF;
  TempCtrl(Enable := TRUE, PV := OutTemp, SP := Setpoint,
           FF := FF_AT_NOMINAL * FlowFF / NOMINAL_FLOW,
           Kp := KP_AT_NOMINAL * FlowFF / NOMINAL_FLOW, Ti_s := TI_S, Td_s := 0.0,
           DtS := DtS, OutMin := 0.0, OutMax := 100.0);
  SteamValve := TempCtrl.Out;

  StableHot(IN := OutTemp >= Setpoint - 0.5, PT := STABLE_MS, NowMs := NowMs);
  IF OutTemp < MIN_SAFE_TEMP THEN
    Divert := TRUE;
  ELSIF StableHot.Q THEN
    Divert := FALSE;
  END_IF;
  DivertEdge(CLK := Divert);
  IF DivertEdge.Q THEN
    Status.DivertCount := (Status.DivertCount + 1) MOD 30000;
  END_IF;

  SteamLow(IN := SteamPressure < STEAM_LOW_BAR, PT := 5000, NowMs := NowMs);
  LowTempAlarm := OutTemp < MIN_SAFE_TEMP;
  SteamLowAlarm := SteamLow.Q;
  Status.TempSP := Setpoint;
  Status.ForwardFlowOk := NOT Divert;
END_FUNCTION_BLOCK
