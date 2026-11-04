// Logical forward-positive cm/s. All time arguments are unsigned microseconds.
module motion_fsm #(
 parameter int ALIGN_LOW=110,ALIGN_HIGH=130,DOCK_STOP_MM=350,
 parameter int SAFETY_MM=250,FINE_MM=500,
 parameter int TURN_CM_S=4,APPROACH_CM_S=5,FINE_CM_S=3,TURN_SIGN=1,
 parameter int APPROACH_TRACK_ERROR=45,FINE_STEER_CM_S=4,
 parameter int ALIGN_FINE_CM_S=3,ALIGN_FINE_ERROR=30,
 parameter int ALIGN_US_PER_PIXEL=2000,ALIGN_MIN_PULSE_US=20000,ALIGN_MAX_PULSE_US=100000,
 parameter int ACQUIRE_SETTLE_US=1500000,ACQUIRE_TIMEOUT_US=900000,
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
 localparam int FINE_TURN=(ALIGN_FINE_CM_S>=3 && ALIGN_FINE_CM_S<=5 && (TURN_SIGN==1 || TURN_SIGN==-1))?ALIGN_FINE_CM_S*TURN_SIGN:0;
 localparam int ALIGN_CENTRE=(ALIGN_LOW+ALIGN_HIGH)/2;
 localparam int DRIVE=(APPROACH_CM_S>=3 && APPROACH_CM_S<=15)?APPROACH_CM_S:0;
 localparam int FINE=(FINE_CM_S>=3 && FINE_CM_S<=15)?FINE_CM_S:0;
 localparam int FINE_STEER=(FINE_STEER_CM_S>=3 && FINE_STEER_CM_S<=5)?FINE_STEER_CM_S:0;
 logic [31:0] taskStartUs,stateStartUs,settleStartUs,lastTimeUs;
 logic [1:0] acquirePhase;
 logic finalAcquire;
 logic alignTurn,alignLow;
 logic signed [6:0] alignSpeed;
 logic [31:0] alignPulseUs;
 wire [31:0] deltaUs=timeUs-lastTimeUs;
 wire centred=centreU>=ALIGN_LOW && centreU<=ALIGN_HIGH;
 wire [31:0] alignErrorPixels,nextAlignPulseUs;
 generate
   if(ALIGN_LOW==110 && ALIGN_HIGH==130 && ALIGN_US_PER_PIXEL==2000 &&
      ALIGN_MIN_PULSE_US==20000 && ALIGN_MAX_PULSE_US==100000)begin: boundedAlignMath
     // Exact default mapping for all 256 U values. Clamp before scaling so
     // the report/fence mux does not feed a pair of serial 32-bit DSPs.
     wire [7:0] errorPixels=centreU < 8'd120 ? 8'd120-centreU : centreU-8'd120;
     wire [5:0] boundedPixels=errorPixels < 8'd10 ? 6'd10 :
       errorPixels > 8'd50 ? 6'd50 : errorPixels[5:0];
     wire [16:0] pixelsWide={11'd0,boundedPixels};
     wire [16:0] scaledPulseUs=(pixelsWide<<11)-(pixelsWide<<5)-(pixelsWide<<4);
     // Speed selection must retain the actual, unclamped pixel error.
     assign alignErrorPixels={24'd0,errorPixels};
     assign nextAlignPulseUs=centred?32'd0:{15'd0,scaledPulseUs};
   end else begin: genericAlignMath
     // Preserve the parameterized mapping outside the optimized defaults.
     wire [31:0] requestedPulseUs=alignErrorPixels*ALIGN_US_PER_PIXEL;
     assign alignErrorPixels=centreU<ALIGN_CENTRE ? ALIGN_CENTRE-{24'd0,centreU} : {24'd0,centreU}-ALIGN_CENTRE;
     assign nextAlignPulseUs=centred?32'd0:
       requestedPulseUs<ALIGN_MIN_PULSE_US?32'(ALIGN_MIN_PULSE_US):
       requestedPulseUs>ALIGN_MAX_PULSE_US?32'(ALIGN_MAX_PULSE_US):requestedPulseUs;
   end
 endgenerate
 // Keep both wheels moving during small visual corrections. Repeated full
 // stops on the tested floor made startup asymmetry dominate each short turn.
 // This corridor applies only after centred entry into APPROACH; the original
 // alignment/docking deadband and stationary qualification remain unchanged.
 wire approachTrackable=alignErrorPixels<=APPROACH_TRACK_ERROR;
 wire approachLeftFast=centreU<ALIGN_LOW ? TURN_SIGN==-1 : TURN_SIGN==1;
 wire signed [6:0] approachFast=distance_mm<=FINE_MM?7'(FINE_STEER):7'(DRIVE);
 // Entry latches direction, speed and duration. A new image cannot extend a
 // turn or reverse it in flight; centring/crossing first requires a full stop.
 wire alignCrossed=alignLow ? centreU>=ALIGN_LOW : centreU<=ALIGN_HIGH;
 wire alignExpired=timeUs-stateStartUs>=alignPulseUs;
 wire safeRange=distance_valid && distance_mm>SAFETY_MM && !safetyHalt;
 wire budgetDone=scanElapsedUs>=scanBudgetUs || scanBudgetUs==0;
 assign scanRemainingUs=budgetDone?32'd0:scanBudgetUs-scanElapsedUs;
 assign taskDone=state==DOCKED || state==NOT_FOUND;
 always_ff @(posedge clk)begin
   if(reset)begin
     state<=IDLE;taskStartUs<=0;stateStartUs<=0;settleStartUs<=0;lastTimeUs<=0;
     acquirePhase<=0;acquireFencePulse<=0;scanElapsedUs<=0;finalAcquire<=0;failureReason<=0;
     alignTurn<=0;alignLow<=0;alignSpeed<=0;alignPulseUs<=0;
   end else begin
     acquireFencePulse<=0;lastTimeUs<=timeUs;
     if(state==SEARCH && motionApplied && !deltaUs[31])begin
       if(deltaUs>=scanRemainingUs)scanElapsedUs<=scanBudgetUs;
       else scanElapsedUs<=scanElapsedUs+deltaUs;
     end
     if(cancel)begin state<=IDLE;acquirePhase<=0;end
     else if(startPulse)begin
       scanElapsedUs<=0;taskStartUs<=timeUs;stateStartUs<=timeUs;failureReason<=0;finalAcquire<=0;
       if(motionTargetValid)begin
         state<=ALIGN;alignTurn<=!centred;alignLow<=centreU<ALIGN_LOW;
         alignSpeed<=7'(alignErrorPixels<=ALIGN_FINE_ERROR?FINE_TURN:TURN);alignPulseUs<=nextAlignPulseUs;
       end
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
             if(motionTargetValid && !acquireFencePulse)begin
               state<=ALIGN;stateStartUs<=timeUs;alignTurn<=!centred;alignLow<=centreU<ALIGN_LOW;
               alignSpeed<=7'(alignErrorPixels<=ALIGN_FINE_ERROR?FINE_TURN:TURN);alignPulseUs<=nextAlignPulseUs;
             end
             else if(timeUs-stateStartUs>=ACQUIRE_TIMEOUT_US)begin
               if(finalAcquire || budgetDone)begin state<=NOT_FOUND;failureReason<=1;end
               else state<=SEARCH;
             end
           end
         end
         ALIGN:begin
           if(!sourceHealthyFresh || !motionTargetValid)begin state<=LOST;stateStartUs<=timeUs;end
           else if(!alignTurn && centred)state<=APPROACH;
           else if(!alignTurn || alignExpired || alignCrossed)begin
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
           end
         end
         APPROACH:begin
           if(!sourceHealthyFresh || !motionTargetValid)begin state<=LOST;stateStartUs<=timeUs;end
           else if(!approachTrackable || (!centred && distance_mm<=DOCK_STOP_MM))begin
             // Do not reverse a wheel immediately after forward travel.
             // Complete zero UART, dwell, and fresh qualification before pivoting.
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
           end
           else if(centred && distance_mm<=DOCK_STOP_MM)state<=DOCKED;
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
     else if(state==ALIGN && motionTargetValid && alignTurn && !alignExpired && !alignCrossed)begin
       if(alignLow)begin left_cm_s=-alignSpeed;right_cm_s=alignSpeed;end
       else begin left_cm_s=alignSpeed;right_cm_s=-alignSpeed;end
     end else if(state==APPROACH && motionTargetValid && approachTrackable && distance_mm>DOCK_STOP_MM)begin
       if(centred)begin
         left_cm_s=distance_mm<=FINE_MM?7'(FINE):7'(DRIVE);right_cm_s=left_cm_s;
       end else if((TURN_SIGN==1 || TURN_SIGN==-1) && approachFast>=3 && FINE>=3)begin
         left_cm_s=approachLeftFast?approachFast:7'(FINE);
         right_cm_s=approachLeftFast?7'(FINE):approachFast;
       end
     end
   end
 end
endmodule
