(* Line 1 control program. Wiring only: every decision lives in a function block.
   Runs after the generated IO_* and Bridge_* programs, which fill G_In and G_Cmd for this
   scan; their outputs (G_Out, G_Status...) reach the sim and the bridge on the next scan. *)
PROGRAM PRG_Main
  VAR_EXTERNAL
    G_In : ST_SimInputs;
    G_Out : ST_SimOutputs;
    G_Status : ST_Status;
    G_Comms : ST_CommsStatus;
    G_Alarms : ST_AlarmSummary;
    G_Counters : ST_Counters;
    G_Cmd : ST_Commands;
    G_RecipeReq : ST_RecipeRequest;
    G_RecipeResp : ST_RecipeResponse;
  END_VAR
  VAR
    Clock : FB_SimClock;
    WdT101 : FB_CommsWatchdog;
    WdP201 : FB_CommsWatchdog;
    WdT301 : FB_CommsWatchdog;
    WdF401 : FB_CommsWatchdog;
    WdC501 : FB_CommsWatchdog;
    WdL601 : FB_CommsWatchdog;
    WdQ701 : FB_CommsWatchdog;
    WdK801 : FB_CommsWatchdog;
    WdLINE : FB_CommsWatchdog;
    Recipe : FB_RecipeHandshake;
    MixBatch : FB_MixBatch;
    Pasteurizer : FB_Pasteurizer;
    Buffer : FB_Tank;
    Alarms : FB_AlarmTable;
    Sequencer : FB_LineSequencer;
    Filler : FB_Filler;
    Capper : FB_Capper;
    Labeler : FB_Labeler;
    Checkweigher : FB_Checkweigher;
    CasePacker : FB_CasePacker;
    Line : FB_LineStatus;
  END_VAR

  Clock(SimTimeMs := G_In.SIM_TimeMs);

  (* Remote I/O comms health (PLC-15) *)
  WdT101(Heartbeat := G_In.T101_Heartbeat, Ok => G_Comms.T101);
  WdP201(Heartbeat := G_In.P201_Heartbeat, Ok => G_Comms.P201);
  WdT301(Heartbeat := G_In.T301_Heartbeat, Ok => G_Comms.T301);
  WdF401(Heartbeat := G_In.F401_Heartbeat, Ok => G_Comms.F401);
  WdC501(Heartbeat := G_In.C501_Heartbeat, Ok => G_Comms.C501);
  WdL601(Heartbeat := G_In.L601_Heartbeat, Ok => G_Comms.L601);
  WdQ701(Heartbeat := G_In.Q701_Heartbeat, Ok => G_Comms.Q701);
  WdK801(Heartbeat := G_In.K801_Heartbeat, Ok => G_Comms.K801);
  WdLINE(Heartbeat := G_In.LINE_Heartbeat, Ok => G_Comms.LINE);

  Recipe(Req := G_RecipeReq, LineState := G_Status.F401.State, Resp => G_RecipeResp);

  (* Process: T-101 batch, P-201 HTST, T-301 buffer *)
  MixBatch(Recipe := Recipe.Active, WaterFlow := G_In.FT101_WaterFlow,
           ConcFlow := G_In.FT102_ConcFlow, SugarFlow := G_In.FT103_SugarFlow,
           Brix := G_In.AT101_Brix, TankEmpty := G_In.LSL101_Empty,
           BufferLevel := G_In.LT301_Level, CipDone := G_In.T101_CipDone,
           NowMs := Clock.NowMs, DtS := Clock.DtS,
           WaterValve => G_Out.XV101_Water, ConcValve => G_Out.XV102_Conc,
           SugarValve => G_Out.XV103_Sugar, Agitator => G_Out.M101_Agitator,
           TransferPump => G_Out.P101_TransferPump, TankDrain => G_Out.XV109_Drain,
           BufferDrain => G_Out.XV309_Drain, CipRun => G_Out.T101_CipRun,
           ConcSelect => G_Out.T101_ConcSelect, Status => G_Status.T101);
  Pasteurizer(OutTemp := G_In.TT202_OutTemp, Flow := G_In.FT201_Flow,
              SteamPressure := G_In.PT201_SteamPressure, TempSPCmd := G_Cmd.P201_TempSP,
              PumpCmd := MixBatch.TransferPump,
              NowMs := Clock.NowMs, DtS := Clock.DtS,
              SteamValve => G_Out.TCV201_SteamValve, Divert => G_Out.XV203_Divert,
              Status => G_Status.P201);
  Buffer(Level := G_In.LT301_Level, LowLimit := 20.0, LowReset := 25.0,
         AboveLow => G_Status.T301.FillerPermissive);

  (* Alarms (PLC-20..22) *)
  Alarms(AckId := G_Cmd.AlarmAck,
         T101_BrixOutOfSpec := MixBatch.BrixAlarm, T101_CommsLost := NOT G_Comms.T101,
         P201_LowTemp := Pasteurizer.LowTempAlarm, P201_SteamLow := Pasteurizer.SteamLowAlarm,
         P201_CommsLost := NOT G_Comms.P201,
         T301_LowLevel := Buffer.Low, T301_CommsLost := NOT G_Comms.T301,
         F401_NozzleLeak := G_In.F401_NozzleLeak, F401_CommsLost := NOT G_Comms.F401,
         C501_Jam := G_In.C501_Jam, C501_Breakdown := G_In.C501_Breakdown,
         C501_CapsEmpty := G_In.LSL502_CapsEmpty, C501_CommsLost := NOT G_Comms.C501,
         L601_RollEmpty := G_In.L601_RollEmpty, L601_LabelError := G_In.L601_LabelError,
         L601_Breakdown := G_In.L601_Breakdown, L601_CommsLost := NOT G_Comms.L601,
         Q701_CommsLost := NOT G_Comms.Q701,
         K801_Jam := G_In.K801_Jam, K801_Breakdown := G_In.K801_Breakdown,
         K801_CommsLost := NOT G_Comms.K801, LINE_CommsLost := NOT G_Comms.LINE,
         Summary => G_Alarms);

  (* Packaging: line sequence, then each machine (PLC-01, PLC-02) *)
  Sequencer(PbStart := G_In.PB_Start, PbStop := G_In.PB_Stop, PbReset := G_In.PB_Reset,
            LineCmd := G_Cmd.LINE_Cmd, F401State := G_Status.F401.State,
            C501State := G_Status.C501.State, L601State := G_Status.L601.State,
            Q701State := G_Status.Q701.State, K801State := G_Status.K801.State);
  Filler(LineCmd := Sequencer.F401, OwnCmd := G_Cmd.F401_Cmd,
         StopReasonCmd := G_Cmd.F401_StopReason, HoldId := G_Alarms.F401_ActiveId,
         LineHoldId := G_Alarms.LINE_ActiveId, Running := G_In.F401_Running,
         OutputFull := G_In.CV1_Full, BufferPermissive := Buffer.AboveLow,
         Recipe := Recipe.Active, NowMs := Clock.NowMs,
         Status => G_Status.F401, Run => G_Out.F401_Run, SpeedSP => G_Out.F401_SpeedSP,
         FillTargetG => G_Out.F401_FillTargetG);
  Capper(LineCmd := Sequencer.C501, OwnCmd := G_Cmd.C501_Cmd,
         StopReasonCmd := G_Cmd.C501_StopReason, HoldId := G_Alarms.C501_ActiveId,
         LineHoldId := G_Alarms.LINE_ActiveId, Running := G_In.C501_Running,
         InputFill := G_In.CV1_Fill, OutputFull := G_In.CV2_Full,
         UpstreamExecute := G_Status.F401.State = PML_EXECUTE,
         Recipe := Recipe.Active, NowMs := Clock.NowMs,
         Status => G_Status.C501, Run => G_Out.C501_Run, SpeedSP => G_Out.C501_SpeedSP);
  Labeler(LineCmd := Sequencer.L601, OwnCmd := G_Cmd.L601_Cmd,
          StopReasonCmd := G_Cmd.L601_StopReason, HoldId := G_Alarms.L601_ActiveId,
          LineHoldId := G_Alarms.LINE_ActiveId, Running := G_In.L601_Running,
          InputFill := G_In.CV2_Fill, OutputFull := G_In.CV3_Full,
          UpstreamExecute := G_Status.C501.State = PML_EXECUTE,
          Recipe := Recipe.Active, NowMs := Clock.NowMs,
          Status => G_Status.L601, Run => G_Out.L601_Run, SpeedSP => G_Out.L601_SpeedSP);
  Checkweigher(LineCmd := Sequencer.Q701, OwnCmd := G_Cmd.Q701_Cmd,
               StopReasonCmd := G_Cmd.Q701_StopReason, HoldId := G_Alarms.Q701_ActiveId,
               LineHoldId := G_Alarms.LINE_ActiveId, Running := G_In.Q701_Running,
               InputFill := G_In.CV3_Fill, OutputFull := G_In.CV4_Full,
               UpstreamExecute := G_Status.L601.State = PML_EXECUTE,
               Count := G_In.Q701_Count, RejectCount := G_In.Q701_RejectCount,
               Recipe := Recipe.Active, NowMs := Clock.NowMs,
               Status => G_Status.Q701, Run => G_Out.Q701_Run, SpeedSP => G_Out.Q701_SpeedSP,
               RejectLimitG => G_Out.Q701_RejectLimitG, GoodCount => G_Counters.Q701_GoodCount);
  CasePacker(LineCmd := Sequencer.K801, OwnCmd := G_Cmd.K801_Cmd,
             StopReasonCmd := G_Cmd.K801_StopReason, HoldId := G_Alarms.K801_ActiveId,
             LineHoldId := G_Alarms.LINE_ActiveId, Running := G_In.K801_Running,
             InputFill := G_In.CV4_Fill, UpstreamExecute := G_Status.Q701.State = PML_EXECUTE,
             Recipe := Recipe.Active, NowMs := Clock.NowMs,
             Status => G_Status.K801, Run => G_Out.K801_Run, SpeedSP => G_Out.K801_SpeedSP);

  Line(FillerState := G_Status.F401.State, Recipe := Recipe.Active, Status => G_Status.LINE);
END_PROGRAM
