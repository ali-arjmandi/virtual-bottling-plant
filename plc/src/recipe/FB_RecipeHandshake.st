(* Recipe download, Req/Ack/Nak handshake (PLC-31, contracts.md §2). A new request is checked
   on the rising edge of Recipe_Req: rejected while the line is producing or when a value is
   out of range (plc-io.yaml ranges); otherwise it becomes the active recipe. Ack/Nak clear
   when the bridge drops Recipe_Req. A default orange recipe is active from cold start. *)
FUNCTION_BLOCK FB_RecipeHandshake
  VAR_INPUT
    Req : ST_RecipeRequest;
    LineState : E_PackMLState;   (* F-401, the constraint machine *)
  END_VAR
  VAR_OUTPUT
    Resp : ST_RecipeResponse;
    Active : ST_Recipe;
  END_VAR
  VAR
    Initialised : BOOL;
    ReqEdge : R_TRIG;
    Nak : E_RecipeNak;
    LineIdle : BOOL;
  END_VAR
  VAR CONSTANT
    EPS : REAL := 0.0001;        (* scaled-integer values land exactly on the limits *)
  END_VAR

  IF NOT Initialised THEN
    Active.RecipeId := 0;
    Active.RecipeVersion := 0;
    Active.ProductCode := 1;
    Active.BrixTarget := 11.5;
    Active.BrixTol := 0.3;
    Active.ConcRatio := 0.162;
    Active.FillTargetG := 1005.0;
    Active.LineSpeed := 120.0;
    Active.CapTorque := 2.2;
    Initialised := TRUE;
  END_IF;

  LineIdle := LineState = PML_STOPPED OR LineState = PML_IDLE OR LineState = PML_ABORTED
              OR LineState = PML_COMPLETE;
  ReqEdge(CLK := Req.Recipe_Req);
  IF ReqEdge.Q THEN
    Nak := NAK_NONE;
    IF NOT LineIdle THEN
      Nak := NAK_IN_EXECUTE;
    ELSIF Req.ProductCode < 1 OR Req.ProductCode > 2 THEN
      Nak := NAK_UNKNOWN_PRODUCT;
    ELSIF Req.BrixTarget < 9.0 - EPS OR Req.BrixTarget > 14.0 + EPS
          OR Req.BrixTol < 0.1 - EPS OR Req.BrixTol > 1.0 + EPS THEN
      Nak := NAK_BRIX_OUT_OF_RANGE;
    ELSIF Req.ConcRatio < 0.1 - EPS OR Req.ConcRatio > 0.25 + EPS THEN
      Nak := NAK_CONC_RATIO_OUT_OF_RANGE;
    ELSIF Req.FillTargetG < 995.0 - EPS OR Req.FillTargetG > 1020.0 + EPS THEN
      Nak := NAK_FILL_WEIGHT_OUT_OF_RANGE;
    ELSIF Req.LineSpeed < 60 OR Req.LineSpeed > 120 THEN
      Nak := NAK_LINE_SPEED_OUT_OF_RANGE;
    ELSIF Req.CapTorque < 1.5 - EPS OR Req.CapTorque > 3.0 + EPS THEN
      Nak := NAK_CAP_TORQUE_OUT_OF_RANGE;
    END_IF;
    IF Nak = NAK_NONE THEN
      Active.RecipeId := Req.RecipeId;
      Active.RecipeVersion := Req.RecipeVersion;
      Active.ProductCode := Req.ProductCode;
      Active.BrixTarget := Req.BrixTarget;
      Active.BrixTol := Req.BrixTol;
      Active.ConcRatio := Req.ConcRatio;
      Active.FillTargetG := Req.FillTargetG;
      Active.LineSpeed := INT_TO_REAL(Req.LineSpeed);
      Active.CapTorque := Req.CapTorque;
    END_IF;
    Resp.Recipe_Ack := Nak = NAK_NONE;
    Resp.Recipe_Nak := Nak;
  ELSIF NOT Req.Recipe_Req THEN
    Resp.Recipe_Ack := FALSE;
    Resp.Recipe_Nak := NAK_NONE;
  END_IF;
END_FUNCTION_BLOCK
