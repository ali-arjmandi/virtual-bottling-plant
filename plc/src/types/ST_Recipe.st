(* Active recipe in the PLC (PLC-30). Written only by FB_RecipeHandshake. *)
TYPE
  ST_Recipe : STRUCT
    RecipeId : INT;
    RecipeVersion : INT;
    ProductCode : INT;      (* 1 = orange, 2 = apple *)
    BrixTarget : REAL;      (* °Bx *)
    BrixTol : REAL;         (* ± °Bx *)
    ConcRatio : REAL;       (* L concentrate per L of batch *)
    FillTargetG : REAL;     (* g per bottle *)
    LineSpeed : REAL;       (* bpm at the filler, the line constraint *)
    CapTorque : REAL;       (* Nm *)
  END_STRUCT;
END_TYPE
