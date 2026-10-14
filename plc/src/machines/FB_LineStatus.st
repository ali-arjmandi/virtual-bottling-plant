(* Line-level status block: the line is in the state of its constraint machine, F-401. *)
FUNCTION_BLOCK FB_LineStatus
  VAR_INPUT
    FillerState : E_PackMLState;
    Recipe : ST_Recipe;
  END_VAR
  VAR_OUTPUT
    Status : ST_LINEStatus;
  END_VAR

  Status.State := FillerState;
  Status.RecipeId := Recipe.RecipeId;
  Status.RecipeVersion := Recipe.RecipeVersion;
  Status.ProductCode := Recipe.ProductCode;
  (* Lets the bridge see that the PLC program is scanning *)
  Status.PlcHeartbeat := (Status.PlcHeartbeat + 1) MOD 30000;
END_FUNCTION_BLOCK
