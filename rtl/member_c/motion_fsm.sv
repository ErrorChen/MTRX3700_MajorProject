// Logical forward-positive cm/s. All time arguments are unsigned microseconds.
module motion_fsm #(
 parameter int ALIGN_LOW=110,ALIGN_HIGH=130,DOCK_STOP_MM=350,
 parameter int SAFETY_MM=250,FINE_MM=500,
 parameter int TURN_CM_S=4,APPROACH_CM_S=5,FINE_CM_S=3,TURN_SIGN=1,
 parameter int ACQUIRE_SETTLE_US=200000,ACQUIRE_TIMEOUT_US=900000,
 parameter int LOST_WAIT_US=300000,TASK_TIMEOUT_US=120000000
)(
 input logic clk,reset,startPulse,cancel,taskActive,safetyHalt,
 input logic sourceHealthyFresh,targetObserved,motionTargetValid,distance_valid,
 input logic scanAllowed,zeroSent,motionApplied,
 input logic [31:0] timeUs,scanBudgetUs,
 input logic [7:0] centreU,input logic [11:0] distance_mm,
 output logic signed [6:0] left_cm_s,right_cm_s,
 output logic [3:0] state,
 output logic acquireFencePulse,
 output wire taskDone,
 output logic [31:0] scanElapsedUs,
 output wire [31:0] scanRemainingUs,
 output logic [3:0] failureReason
);
 localparam logic [3:0] IDLE=0,SEARCH=1,ALIGN=2,APPROACH=3,DOCKED=4,LOST=5,ACQUIRE=6,HOLD=7,NOT_FOUND=8;
 localparam int TURN=(TURN_CM_S>=3 && TURN_CM_S<=5 && (TURN_SIGN==1 || TURN_SIGN==-1))?TURN_CM_S*TURN_SIGN:0;
 localparam int DRIVE=(APPROACH_CM_S>=3 && APPROACH_CM_S<=15)?APPROACH_CM_S:0;
 localparam int FINE=(FINE_CM_S>=3 && FINE_CM_S<=15)?FINE_CM_S:0;
 logic [31:0] taskStartUs,stateStartUs,settleStartUs,lastTimeUs;
 logic [1:0] acquirePhase;
 logic finalAcquire;
 wire [31:0] deltaUs=timeUs-lastTimeUs;
 wire centred=centreU>=ALIGN_LOW && centreU<=ALIGN_HIGH;
 wire safeRange=distance_valid && distance_mm>SAFETY_MM && !safetyHalt;
 wire budgetDone=scanElapsedUs>=scanBudgetUs || scanBudgetUs==0;
 assign scanRemainingUs=budgetDone?32'd0:scanBudgetUs-scanElapsedUs;
 assign taskDone=state==DOCKED || state==NOT_FOUND;
 always_ff @(posedge clk)begin
   if(reset)begin
     state<=IDLE;taskStartUs<=0;stateStartUs<=0;settleStartUs<=0;lastTimeUs<=0;
     acquirePhase<=0;acquireFencePulse<=0;scanElapsedUs<=0;finalAcquire<=0;failureReason<=0;
   end else begin
     acquireFencePulse<=0;lastTimeUs<=timeUs;
     if(state==SEARCH && motionApplied && !deltaUs[31])begin
       if(deltaUs>=scanRemainingUs)scanElapsedUs<=scanBudgetUs;
       else scanElapsedUs<=scanElapsedUs+deltaUs;
     end
     if(cancel)begin state<=IDLE;acquirePhase<=0;end
     else if(startPulse)begin
       scanElapsedUs<=0;taskStartUs<=timeUs;stateStartUs<=timeUs;failureReason<=0;finalAcquire<=0;
       if(motionTargetValid)state<=ALIGN;
       else if(!scanAllowed)begin state<=NOT_FOUND;failureReason<=3;end
       else if(targetObserved)begin state<=ACQUIRE;acquirePhase<=0;end
       else state<=SEARCH;
     end else if(taskActive && !taskDone)begin
       if(timeUs-taskStartUs>=TASK_TIMEOUT_US)begin state<=NOT_FOUND;failureReason<=2;end
       else if(!safeRange)begin state<=HOLD;stateStartUs<=timeUs;end
       else case(state)
         SEARCH:begin
           if(!scanAllowed)begin state<=NOT_FOUND;failureReason<=3;end
           else if(targetObserved || budgetDone)begin
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
           end
         end
         ACQUIRE:begin
           if(acquirePhase==0 && zeroSent)begin settleStartUs<=timeUs;acquirePhase<=1;end
           else if(acquirePhase==1 && timeUs-settleStartUs>=ACQUIRE_SETTLE_US)begin
             acquireFencePulse<=1;acquirePhase<=2;stateStartUs<=timeUs;
           end else if(acquirePhase==2)begin
             if(motionTargetValid && !acquireFencePulse)state<=ALIGN;
             else if(timeUs-stateStartUs>=ACQUIRE_TIMEOUT_US)begin
               if(finalAcquire || budgetDone)begin state<=NOT_FOUND;failureReason<=1;end
               else state<=SEARCH;
             end
           end
         end
         ALIGN:begin
           if(!sourceHealthyFresh || !motionTargetValid)begin state<=LOST;stateStartUs<=timeUs;end
           else if(centred)state<=APPROACH;
         end
         APPROACH:begin
           if(!sourceHealthyFresh || !motionTargetValid)begin state<=LOST;stateStartUs<=timeUs;end
           else if(!centred)state<=ALIGN;
           else if(distance_mm<=DOCK_STOP_MM)state<=DOCKED;
         end
         LOST:begin
           if(timeUs-stateStartUs>=LOST_WAIT_US)begin
             if(targetObserved || budgetDone)begin state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;end
             else state<=SEARCH;
           end
         end
         HOLD:begin
           if(targetObserved || budgetDone)begin state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;end
           else state<=SEARCH;
         end
         default:;
       endcase
     end
   end
 end
 always_comb begin
   left_cm_s=0;right_cm_s=0;
   if(!reset && !cancel && taskActive && safeRange && sourceHealthyFresh)begin
     if(state==SEARCH && scanAllowed && !budgetDone && !targetObserved)begin left_cm_s=7'(-TURN);right_cm_s=7'(TURN);end
     else if(state==ALIGN && motionTargetValid)begin
       if(centreU<ALIGN_LOW)begin left_cm_s=7'(-TURN);right_cm_s=7'(TURN);end
       else if(centreU>ALIGN_HIGH)begin left_cm_s=7'(TURN);right_cm_s=7'(-TURN);end
     end else if(state==APPROACH && motionTargetValid && centred && distance_mm>DOCK_STOP_MM)begin
       left_cm_s=distance_mm<=FINE_MM?7'(FINE):7'(DRIVE);right_cm_s=left_cm_s;
     end
   end
 end
endmodule
