// Logical forward-positive cm/s. All time arguments are unsigned microseconds.
module motion_fsm #(
 parameter bit RUNTIME_TUNING=0,
 parameter int ALIGN_LOW=90,ALIGN_HIGH=150,DOCK_STOP_MM=350,
 parameter int SAFETY_MM=250,FINE_MM=500,
 parameter int TURN_CM_S=4,APPROACH_CM_S=5,FINE_CM_S=3,TURN_SIGN=1,
 parameter int APPROACH_TRACK_ERROR=45,FINE_STEER_CM_S=4,
 parameter int BACKTRACK_PULSE_US=150000,BACKTRACK_MAX_STEPS=3,
 parameter int ALIGN_FINE_CM_S=3,ALIGN_FINE_ERROR=30,
 parameter int ALIGN_US_PER_PIXEL=2000,ALIGN_MIN_PULSE_US=20000,ALIGN_MAX_PULSE_US=100000,
 parameter int ACQUIRE_SETTLE_US=1500000,ACQUIRE_TIMEOUT_US=900000,
 parameter int LOST_WAIT_US=300000,TASK_TIMEOUT_US=120000000
)(
 input logic clk,reset,startPulse,cancel,taskActive,safetyHalt,
 input logic sourceHealthyFresh,targetObserved,motionTargetValid,distance_valid,
 input logic scanAllowed,zeroSent,motionApplied,
 input logic [31:0] timeUs,scanBudgetUs,
 input logic [31:0] tuningWord,
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
 localparam int ALIGN_CENTRE=RUNTIME_TUNING?120:(ALIGN_LOW+ALIGN_HIGH)/2;
 localparam int DRIVE=(APPROACH_CM_S>=3 && APPROACH_CM_S<=15)?APPROACH_CM_S:0;
 localparam int FINE=(FINE_CM_S>=3 && FINE_CM_S<=15)?FINE_CM_S:0;
 localparam int FINE_STEER=(FINE_STEER_CM_S>=3 && FINE_STEER_CM_S<=5)?FINE_STEER_CM_S:0;
 // CCTL only changes this word while stationary. Keep the runtime datapath
 // narrow; an invalid word also inhibits every wheel request at this boundary.
 wire tuningValid;
 wire signed [6:0] searchTurn,coarseTurn,fineTurn,driveSpeed,fineSpeed,fineSteerSpeed;
 wire [7:0] alignLowBound,alignHighBound;
 generate
   if(RUNTIME_TUNING)begin: runtimeTuning
     wire [3:0] searchValue=tuningWord[3:0],turnValue=tuningWord[7:4];
     wire [3:0] driveValue=tuningWord[11:8],fineValue=tuningWord[15:12];
     wire [5:0] tolerance=tuningWord[21:16];
     wire signed [6:0] searchMagnitude={3'd0,searchValue};
     wire signed [6:0] turnMagnitude={3'd0,turnValue};
     assign tuningValid=tuningWord[31:22]==0 &&
       searchValue>=3 && searchValue<=5 && turnValue>=3 && turnValue<=5 &&
       driveValue>=4 && driveValue<=8 && fineValue>=3 && fineValue<=4 &&
       driveValue>fineValue && tolerance>=10 && tolerance<=40 &&
       (TURN_SIGN==1 || TURN_SIGN==-1);
     assign searchTurn=TURN_SIGN==-1?-searchMagnitude:searchMagnitude;
     assign coarseTurn=TURN_SIGN==-1?-turnMagnitude:turnMagnitude;
     assign fineTurn=TURN_SIGN==-1?-7'sd3:7'sd3;
     assign driveSpeed={3'd0,driveValue};
     assign fineSpeed={3'd0,fineValue};
     assign fineSteerSpeed={3'd0,fineValue}+7'd1;
     assign alignLowBound=8'd120-{2'd0,tolerance};
     assign alignHighBound=8'd120+{2'd0,tolerance};
   end else begin: fixedTuning
     assign tuningValid=1'b1;
     assign searchTurn=7'(TURN);
     assign coarseTurn=7'(TURN);
     assign fineTurn=7'(FINE_TURN);
     assign driveSpeed=7'(DRIVE);
     assign fineSpeed=7'(FINE);
     assign fineSteerSpeed=7'(FINE_STEER);
     assign alignLowBound=8'(ALIGN_LOW);
     assign alignHighBound=8'(ALIGN_HIGH);
   end
 endgenerate
 // Zero disables recovery; unsupported counts/durations fail closed. The
 // two-bit counter never wraps, and is replenished only for a new task.
 localparam int BACKTRACK_LIMIT=(BACKTRACK_MAX_STEPS>=1 && BACKTRACK_MAX_STEPS<=3 &&
   BACKTRACK_PULSE_US>=1 && BACKTRACK_PULSE_US<=200000)?BACKTRACK_MAX_STEPS:0;
 logic [31:0] taskStartUs,stateStartUs,settleStartUs,lastTimeUs;
 logic [1:0] acquirePhase;
 logic finalAcquire;
 logic backtracking,backtrackAuthorized,stationaryRecoveryRequired;
 logic [1:0] backtrackSteps;
 logic alignTurn,alignLow;
 logic signed [6:0] alignSpeed;
 logic [31:0] alignPulseUs;
 wire [31:0] deltaUs=timeUs-lastTimeUs;
 // The fixed branch retains the original full-width parameter comparisons.
 wire centred=RUNTIME_TUNING ? centreU>=alignLowBound && centreU<=alignHighBound :
   centreU>=ALIGN_LOW && centreU<=ALIGN_HIGH;
 wire belowAlign=RUNTIME_TUNING ? centreU<alignLowBound : centreU<ALIGN_LOW;
 wire [31:0] alignErrorPixels,nextAlignPulseUs;
 generate
   if((RUNTIME_TUNING || ALIGN_LOW+ALIGN_HIGH==240) && ALIGN_US_PER_PIXEL==2000 &&
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
 // A fresh lock may enter this corridor directly outside the dock distance;
 // the narrower straight/docking tolerance and stationary qualification remain.
 wire approachTrackable=alignErrorPixels<=APPROACH_TRACK_ERROR;
 // A freshly locked target inside the existing forward-steering corridor
 // need not pivot first. Never enter forward travel at the docking distance.
 wire approachEntry=distance_valid && distance_mm>DOCK_STOP_MM && approachTrackable;
 wire approachLeftFast=belowAlign ? TURN_SIGN==-1 : TURN_SIGN==1;
 wire signed [6:0] approachFast=distance_mm<=FINE_MM?fineSteerSpeed:driveSpeed;
 // Entry latches direction, speed and duration. A new image cannot extend a
 // turn or reverse it in flight; centring/crossing first requires a full stop.
 wire alignCrossed=RUNTIME_TUNING ?
   (alignLow ? centreU>=alignLowBound : centreU<=alignHighBound) :
   (alignLow ? centreU>=ALIGN_LOW : centreU<=ALIGN_HIGH);
 wire alignExpired=timeUs-stateStartUs>=alignPulseUs;
 wire safeRange=distance_valid && distance_mm>SAFETY_MM && !safetyHalt;
 wire budgetDone=scanElapsedUs>=scanBudgetUs || scanBudgetUs==0;
 wire backtrackExpired=backtracking && timeUs-stateStartUs>=BACKTRACK_PULSE_US;
 assign scanRemainingUs=budgetDone?32'd0:scanBudgetUs-scanElapsedUs;
 assign taskDone=state==DOCKED || state==NOT_FOUND;
 always_ff @(posedge clk)begin
   if(reset)begin
     state<=IDLE;taskStartUs<=0;stateStartUs<=0;settleStartUs<=0;lastTimeUs<=0;
     acquirePhase<=0;acquireFencePulse<=0;scanElapsedUs<=0;finalAcquire<=0;failureReason<=0;
     alignTurn<=0;alignLow<=0;alignSpeed<=0;alignPulseUs<=0;
     backtracking<=0;backtrackAuthorized<=0;backtrackSteps<=0;stationaryRecoveryRequired<=0;
   end else begin
     acquireFencePulse<=0;lastTimeUs<=timeUs;
     // A source interruption invalidates the sighting, but does not refund
     // recovery attempts already used in this task.
     if(!sourceHealthyFresh)backtrackAuthorized<=0;
     // Capture loss before HOLD priority so a simultaneous near obstacle cannot
     // discard the stationary recovery obligation. Cancel/new START clear it.
     if(taskActive && (state==ALIGN || state==APPROACH) &&
        (!sourceHealthyFresh || !motionTargetValid))stationaryRecoveryRequired<=1;
     if(state==SEARCH && motionApplied && !deltaUs[31])begin
       if(deltaUs>=scanRemainingUs)scanElapsedUs<=scanBudgetUs;
       else scanElapsedUs<=scanElapsedUs+deltaUs;
     end
     if(cancel)begin
       state<=IDLE;acquirePhase<=0;backtracking<=0;backtrackAuthorized<=0;backtrackSteps<=0;stationaryRecoveryRequired<=0;
     end
     else if(startPulse)begin
       scanElapsedUs<=0;taskStartUs<=timeUs;stateStartUs<=timeUs;failureReason<=0;finalAcquire<=0;
       backtracking<=0;backtrackAuthorized<=0;backtrackSteps<=0;stationaryRecoveryRequired<=0;
       if(motionTargetValid)begin
         state<=approachEntry?APPROACH:ALIGN;alignTurn<=!centred;alignLow<=belowAlign;
         alignSpeed<=(alignErrorPixels<=ALIGN_FINE_ERROR)?fineTurn:coarseTurn;alignPulseUs<=nextAlignPulseUs;
       end
       else if(!scanAllowed)begin state<=NOT_FOUND;failureReason<=3;end
       else if(targetObserved)begin state<=ACQUIRE;acquirePhase<=0;end
       else state<=SEARCH;
     end else if(taskActive && !taskDone)begin
       if(timeUs-taskStartUs>=TASK_TIMEOUT_US)begin
         state<=NOT_FOUND;failureReason<=2;backtracking<=0;backtrackAuthorized<=0;stationaryRecoveryRequired<=0;
       end else if(!safeRange)begin
         state<=HOLD;stateStartUs<=timeUs;backtracking<=0;backtrackAuthorized<=0;
       end else if(backtracking && !sourceHealthyFresh)begin
         state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;backtracking<=0;backtrackAuthorized<=0;
       end
       else case(state)
         SEARCH:begin
           if(!scanAllowed)begin
             state<=NOT_FOUND;failureReason<=3;backtracking<=0;backtrackAuthorized<=0;stationaryRecoveryRequired<=0;
           end else if(targetObserved || budgetDone || backtrackExpired)begin
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
             // Only a forward SEARCH sighting authorizes local recovery.
             // A reverse sighting may stop, but cannot refill its allowance.
             if(budgetDone)backtrackAuthorized<=0;
             else if(!backtracking)backtrackAuthorized<=targetObserved && sourceHealthyFresh && backtrackSteps<BACKTRACK_LIMIT;
             backtracking<=0;
           end
         end
         ACQUIRE:begin
           // A lost target or interrupted reverse must complete stationary
           // recovery after the source returns; a HOLD cannot bypass it.
           if(stationaryRecoveryRequired && !sourceHealthyFresh)acquirePhase<=0;
           else if(acquirePhase==0 && zeroSent)begin settleStartUs<=timeUs;acquirePhase<=1;end
           else if(acquirePhase==1 && timeUs-settleStartUs>=ACQUIRE_SETTLE_US)begin
             acquireFencePulse<=1;acquirePhase<=2;stateStartUs<=timeUs;
           end else if(acquirePhase==2)begin
             if(motionTargetValid && !acquireFencePulse)begin
               state<=approachEntry?APPROACH:ALIGN;stateStartUs<=timeUs;alignTurn<=!centred;alignLow<=belowAlign;
               alignSpeed<=(alignErrorPixels<=ALIGN_FINE_ERROR)?fineTurn:coarseTurn;alignPulseUs<=nextAlignPulseUs;
               backtrackAuthorized<=0;backtracking<=0;stationaryRecoveryRequired<=0;
             end
             else if(timeUs-stateStartUs>=ACQUIRE_TIMEOUT_US)begin
               if(finalAcquire || budgetDone)begin
                 state<=NOT_FOUND;failureReason<=1;backtrackAuthorized<=0;backtracking<=0;stationaryRecoveryRequired<=0;
               end else if(backtrackAuthorized && sourceHealthyFresh && !targetObserved && backtrackSteps<BACKTRACK_LIMIT)begin
                 // Same SEARCH state and motionApplied accounting: reverse
                 // motion consumes the original remaining scan budget.
                 state<=SEARCH;backtracking<=1;stateStartUs<=timeUs;backtrackSteps<=backtrackSteps+1'b1;stationaryRecoveryRequired<=1;
               end else begin
                 state<=SEARCH;backtracking<=0;backtrackAuthorized<=0;stationaryRecoveryRequired<=0;
               end
             end
           end
         end
         ALIGN:begin
           if(!sourceHealthyFresh || !motionTargetValid)begin
             state<=LOST;stateStartUs<=timeUs;
           end
           else if(!alignTurn && centred)state<=APPROACH;
           else if(!alignTurn || alignExpired || alignCrossed)begin
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
           end
         end
         APPROACH:begin
           if(!sourceHealthyFresh || !motionTargetValid)begin
             state<=LOST;stateStartUs<=timeUs;
           end
           else if(!approachTrackable || (!centred && distance_mm<=DOCK_STOP_MM))begin
             // Do not reverse a wheel immediately after forward travel.
             // Complete zero UART, dwell, and fresh qualification before pivoting.
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
           end
           else if(centred && distance_mm<=DOCK_STOP_MM)state<=DOCKED;
         end
         LOST:begin
           if(timeUs-stateStartUs>=LOST_WAIT_US)begin
             // A brief recognition gap must not issue a new search turn before
             // zero completion, the stationary dwell and new-frame confirmation.
             state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;
           end
         end
         HOLD:begin
           if(stationaryRecoveryRequired || targetObserved || budgetDone)begin state<=ACQUIRE;stateStartUs<=timeUs;acquirePhase<=0;finalAcquire<=budgetDone;end
           else state<=SEARCH;
         end
         default:;
       endcase
     end
   end
 end
 always_comb begin
   left_cm_s=0;right_cm_s=0;
   if(!reset && !cancel && taskActive && safeRange && sourceHealthyFresh && tuningValid)begin
     if(state==SEARCH && scanAllowed && !budgetDone && !targetObserved && !backtrackExpired)begin
       left_cm_s=backtracking?searchTurn:-searchTurn;right_cm_s=-left_cm_s;
     end
     else if(state==ALIGN && motionTargetValid && alignTurn && !alignExpired && !alignCrossed)begin
       if(alignLow)begin left_cm_s=-alignSpeed;right_cm_s=alignSpeed;end
       else begin left_cm_s=alignSpeed;right_cm_s=-alignSpeed;end
     end else if(state==APPROACH && motionTargetValid && approachTrackable && distance_mm>DOCK_STOP_MM)begin
       if(centred)begin
         left_cm_s=distance_mm<=FINE_MM?fineSpeed:driveSpeed;right_cm_s=left_cm_s;
       end else if((TURN_SIGN==1 || TURN_SIGN==-1) && approachFast>=3 && fineSpeed>=3)begin
         left_cm_s=approachLeftFast?approachFast:fineSpeed;
         right_cm_s=approachLeftFast?fineSpeed:approachFast;
       end
     end
   end
 end
endmodule
