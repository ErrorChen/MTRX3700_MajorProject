module member_c_control #(
 parameter int ULTRASONIC_ESTOP_MM=250,TURN_SIGN=1,
 parameter int ALIGN_LOW=90,ALIGN_HIGH=150,
 parameter int SELECTION_STABLE_CLKS=1_000_000,
 parameter int APPROACH_TRACK_ERROR=45,FINE_STEER_CM_S=4,
 parameter int BACKTRACK_PULSE_US=150000,BACKTRACK_MAX_STEPS=3,
 parameter int ALIGN_FINE_CM_S=3,ALIGN_FINE_ERROR=30,
 parameter int ALIGN_US_PER_PIXEL=2000,ALIGN_MIN_PULSE_US=20000,ALIGN_MAX_PULSE_US=100000,
 parameter int ACQUIRE_SETTLE_US=1500000,ACQUIRE_TIMEOUT_US=900000,
 parameter int LOST_WAIT_US=300000,TASK_TIMEOUT_US=120000000
)(
 input logic clk,reset,power_frame,estop_frame,
 input logic [5:0] selection,
 input logic [1:0] mode,
 input logic debugStart,debugStop,modeChanged,rawMode,injectLeaseValid,scanCalibrated,visualStart,
 input logic [31:0] scanBudgetUs,timeUs,
 input logic cameraFifoFault,cameraAbandonEvent,
 input perception_pkg::perceptionStatus_t status,
 output perception_pkg::targetRequest_t targetRequest,
 output wire targetRequestValid,input logic targetRequestReady,
 input perception_pkg::targetReport_t targetReport,
 input logic targetReportValid,output wire targetReportReady,
 input logic distance_valid,distanceSample,input logic [11:0] distance_mm,
 input logic zeroSent,uartBusy,
 output wire signed [6:0] left_cm_s,right_cm_s,
 output wire permit,used,estop,sonar_stop,motionTargetValid,
 output wire [3:0] motionState,output wire [2:0] stop_reason,
 output logic [511:0] statusWords
);
 logic taskActive,pendingVisualStart;
 logic [15:0] visualPreviousTag;
 logic [31:0] visualStartUs;
 wire startPulse,taskEnabled,taskDone;
 wire [3:0] selectedDigit,failureReason;
 wire [5:0] stableMask;
 wire selectionValid,selectionConflict,selectionMatches,fatalFault;
 wire [7:0] centreU;
 wire sourceHealthyFresh,targetObserved,acquireFencePulse;
 wire [15:0] requestTag,frameId;
 wire [31:0] inputAgeUs,scanElapsedUs,scanRemainingUs;
 wire signed [6:0] reqL,reqR;
 wire modePermit=mode!=1 && mode<=2 && !rawMode && (mode!=2 || injectLeaseValid);
 wire cancel=debugStop || modeChanged || rawMode || !selectionMatches || !selectionValid ||
   estop_frame || estop || fatalFault || (mode==2 && !injectLeaseValid);
 wire scanAllowed=scanCalibrated || mode==2;
 wire terminalState=motionState==0 || motionState==4 || motionState==8;
 // A newly presented red2 takes the current physical selection, refreshes
 // its request fence, then may start once a fresh report belongs to that tag.
 // Active tasks ignore this event so it cannot replenish search budgets.
 wire visualReselect=visualStart && mode!=2 && !taskActive && terminalState && selectionValid && selectionMatches;
 // Without a calibrated scan, the first healthy/acquiring frame cannot
 // start SEARCH: wait for the new request's three-frame target lock instead.
 wire visualStartReady=pendingVisualStart && requestTag!=visualPreviousTag &&
   (scanAllowed || motionTargetValid);
 assign startPulse=(power_frame || debugStart || visualStartReady) && !taskActive && terminalState && !cancel &&
   modePermit && !sonar_stop && distance_valid && distance_mm>ULTRASONIC_ESTOP_MM && sourceHealthyFresh;
 always_ff @(posedge clk)begin
   if(reset)begin pendingVisualStart<=0;visualPreviousTag<=0;visualStartUs<=0;end
   else if(cancel || sonar_stop || !distance_valid || distance_mm<=ULTRASONIC_ESTOP_MM ||
           !modePermit || startPulse || timeUs-visualStartUs>=1000000)pendingVisualStart<=0;
   // First establish a healthy physical safety condition; restoring a hazard
   // later must never activate an earlier red2 presentation.
   if(!reset && visualReselect)begin
     pendingVisualStart<=!cancel && modePermit && !sonar_stop && distance_valid && distance_mm>ULTRASONIC_ESTOP_MM;
     visualPreviousTag<=requestTag;visualStartUs<=timeUs;
   end
 end
 always_ff @(posedge clk)begin
   if(reset || cancel)taskActive<=0;
   else if(startPulse)taskActive<=1;
   else if(taskDone)taskActive<=0;
 end
 perception_adapter #(.SELECTION_STABLE_CLKS(SELECTION_STABLE_CLKS)) adapter(
   .clk(clk),.reset(reset),.selection(selection),.timeUs(timeUs),
   .sourceChanged(modeChanged),.refreshRequest(visualReselect),.syntheticSource(mode==2),.acquireFencePulse(acquireFencePulse),
   .cameraFifoFault(cameraFifoFault),.cameraAbandonEvent(cameraAbandonEvent),.status(status),
   .targetRequest(targetRequest),.targetRequestValid(targetRequestValid),.targetRequestReady(targetRequestReady),
   .targetReport(targetReport),.targetReportValid(targetReportValid),.targetReportReady(targetReportReady),
   .stableMask(stableMask),.selectedDigit(selectedDigit),.selectionValid(selectionValid),
   .selectionConflict(selectionConflict),.selectionMatches(selectionMatches),.centreU(centreU),
   .sourceHealthyFresh(sourceHealthyFresh),.targetObserved(targetObserved),.motionTargetValid(motionTargetValid),
   .requestTag(requestTag),.frameId(frameId),.inputAgeUs(inputAgeUs),.fatalFault(fatalFault));
 motion_fsm #(.SAFETY_MM(ULTRASONIC_ESTOP_MM),.TURN_SIGN(TURN_SIGN),.ALIGN_LOW(ALIGN_LOW),.ALIGN_HIGH(ALIGN_HIGH),
   .APPROACH_TRACK_ERROR(APPROACH_TRACK_ERROR),.FINE_STEER_CM_S(FINE_STEER_CM_S),
   .BACKTRACK_PULSE_US(BACKTRACK_PULSE_US),.BACKTRACK_MAX_STEPS(BACKTRACK_MAX_STEPS),
   .ALIGN_FINE_CM_S(ALIGN_FINE_CM_S),.ALIGN_FINE_ERROR(ALIGN_FINE_ERROR),
   .ALIGN_US_PER_PIXEL(ALIGN_US_PER_PIXEL),.ALIGN_MIN_PULSE_US(ALIGN_MIN_PULSE_US),.ALIGN_MAX_PULSE_US(ALIGN_MAX_PULSE_US),
   .ACQUIRE_SETTLE_US(ACQUIRE_SETTLE_US),.ACQUIRE_TIMEOUT_US(ACQUIRE_TIMEOUT_US),
   .LOST_WAIT_US(LOST_WAIT_US),.TASK_TIMEOUT_US(TASK_TIMEOUT_US)) motion(
   .clk(clk),.reset(reset),.startPulse(startPulse),.cancel(cancel),.taskActive(taskActive),
   .safetyHalt(estop_frame || estop || sonar_stop),.sourceHealthyFresh(sourceHealthyFresh),
   .targetObserved(targetObserved),.motionTargetValid(motionTargetValid),
   .distance_valid(distance_valid),.distance_mm(distance_mm),.centreU(centreU),
   .scanAllowed(scanAllowed),.scanBudgetUs(scanBudgetUs),.timeUs(timeUs),
   .zeroSent(zeroSent),.motionApplied(permit && motionState==1),
   .left_cm_s(reqL),.right_cm_s(reqR),.state(motionState),.acquireFencePulse(acquireFencePulse),
   .taskDone(taskDone),.scanElapsedUs(scanElapsedUs),.scanRemainingUs(scanRemainingUs),.failureReason(failureReason));
 safety_arbiter #(.ULTRASONIC_ESTOP_MM(ULTRASONIC_ESTOP_MM)) safety(
   .clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),
   .motion_enable(reqL!=0 || reqR!=0),.taskArmed(taskActive && !taskDone),.cancel(cancel),
   .modePermit(modePermit),.distanceSample(distanceSample),
   .distance_valid(distance_valid),.distance_mm(distance_mm),.permit(permit),.taskEnabled(taskEnabled),
   .used(used),.estop(estop),.sonar_stop(sonar_stop),.reason(stop_reason));
 assign left_cm_s=permit?reqL:7'sd0;
 assign right_cm_s=permit?reqR:7'sd0;
 always_comb begin
   statusWords='0;
   statusWords[0*32+:32]={selectionMatches,sonar_stop,estop,permit,motionTargetValid,targetObserved,
     sourceHealthyFresh,motionState,taskActive,selectedDigit,selectionConflict,selectionValid,stableMask,selection,mode};
   statusWords[1*32+:32]={frameId,requestTag};
   statusWords[2*32+:32]={status.faultFlags,status.activeCfgVersion};
   statusWords[3*32+:32]=inputAgeUs;
   statusWords[4*32+:32]=scanElapsedUs;
   statusWords[5*32+:32]=scanRemainingUs;
   statusWords[6*32+:32]=scanBudgetUs;
   statusWords[7*32+:32]={5'd0,stop_reason,failureReason,(mode==2),scanCalibrated,rawMode,modePermit,1'b0,right_cm_s,1'b0,left_cm_s};
   statusWords[8*32+:32]={16'd0,zeroSent,uartBusy,distanceSample,distance_valid,distance_mm};
   statusWords[9*32+:32]=timeUs;
   statusWords[10*32+:32]={25'd0,pendingVisualStart,fatalFault,modeChanged,debugStop,cancel,taskDone,acquireFencePulse};
   statusWords[11*32+:32]={28'd0,status.interactionBusy,status.calibrated,status.perceptionReady,injectLeaseValid};
 end
endmodule
