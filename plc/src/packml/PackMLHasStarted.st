(* TRUE once a machine has left Idle on its way to production (running, waiting or held). *)
FUNCTION PackMLHasStarted : BOOL
  VAR_INPUT
    State : E_PackMLState;
  END_VAR
  PackMLHasStarted := State = PML_STARTING OR State = PML_EXECUTE OR State = PML_SUSPENDING
                      OR State = PML_SUSPENDED OR State = PML_UNSUSPENDING
                      OR State = PML_HOLDING OR State = PML_HELD OR State = PML_UNHOLDING;
END_FUNCTION
