// Sole request owner. CLOCK_50 domain; selection has already passed two FFs.
// Requests remain immutable under backpressure. Selection stabilises as a whole.
module perception_adapter #(
 parameter int SELECTION_STABLE_CLKS=1_000_000,
 parameter logic [31:0] MAX_AGE_US=150000
)(
 input logic clk,reset,
 input logic [5:0] selection,
 input logic [31:0] timeUs,
 input logic sourceChanged, refreshRequest, syntheticSource, acquireFencePulse,
 input logic cameraFifoFault,cameraAbandonEvent,
 input perception_pkg::perceptionStatus_t status,
 output perception_pkg::targetRequest_t targetRequest,
 output logic targetRequestValid,input logic targetRequestReady,
 input perception_pkg::targetReport_t targetReport,
 input logic targetReportValid,output wire targetReportReady,
 output logic [5:0] stableMask,
 output logic [3:0] selectedDigit,
 output wire selectionValid,selectionConflict,selectionMatches,
 output wire [7:0] centreU,
 output wire sourceHealthyFresh,targetObserved,motionTargetValid,
 output wire [15:0] requestTag,frameId,
 output wire [31:0] inputAgeUs,
 output wire fatalFault
);
 import perception_pkg::*;
 localparam int CW=SELECTION_STABLE_CLKS>1?$clog2(SELECTION_STABLE_CLKS):1;
 logic [CW-1:0] stableCount;
 logic [5:0] candidateMask;
 logic requestDirty,accepted,haveSequence,haveHealthy,haveObserved,haveLock;
 logic [15:0] tagCounter,activeTag,lastFrame,previousConfig;
 logic [31:0] requestFenceUs,targetFenceUs,stamp;
 logic [7:0] cachedU;
 logic fifoFatal,abandonSeen,recoveryPending,previousCandidateOverflow;
 logic [1:0] healthyCount,targetCount;
 assign selectionValid=stableMask!=0 && (stableMask & (stableMask-6'd1))==0;
 assign selectionConflict=stableMask!=0 && !selectionValid;
 assign selectionMatches=selection==stableMask;
 always_comb begin
   selectedDigit=0;
   for(int n=0;n<6;n=n+1)if(selectionValid && stableMask[n])selectedDigit=4'(n+1);
 end
 assign fatalFault=!syntheticSource && (fifoFatal || cameraFifoFault);
 wire applicableAbandon=!syntheticSource && cameraAbandonEvent;
 // Candidate capacity is per-frame rejection. Its sticky history is diagnostic,
 // unlike FIFO / mask-bank / protocol faults, which still inhibit the source.
 wire candidateOverflowEdge=!syntheticSource && status.faultFlags[FAULT_CANDIDATE_OVERFLOW] &&
   !previousCandidateOverflow;
 wire healthy=status.perceptionReady && !status.interactionBusy && !fatalFault &&
   ((status.faultFlags & ~((16'b1<<FAULT_AUDIO_CAPTURE) | (16'b1<<FAULT_CANDIDATE_OVERFLOW) |
      ((!syntheticSource && abandonSeen)?(16'b1<<FAULT_CAMERA_TRANSPORT):16'b0)))==0);
 wire configChange=previousConfig!=status.activeCfgVersion;
 wire active=accepted && selectionValid && selectionMatches && !requestDirty && !sourceChanged && !refreshRequest;
 wire [31:0] afterFence=targetReport.captureStartUs-requestFenceUs;
 wire [31:0] afterTargetFence=targetReport.captureStartUs-targetFenceUs;
 wire [31:0] afterLast=targetReport.captureStartUs-stamp;
 wire [15:0] frameStep=targetReport.frameId-lastFrame;
 wire consecutive=haveSequence && frameStep==16'd1;
 wire identity=targetReport.requestTag==activeTag && targetReport.markerType==MARKER_BAY &&
   targetReport.digit==selectedDigit && targetReport.configVersion==status.activeCfgVersion &&
   targetReport.targetSelected;
 wire observedFrame=targetReport.observed && !targetReport.ambiguous && targetReport.quality!=0 &&
   targetReport.centreU<240 && targetReport.centreV<320 &&
   ((targetReport.locked && targetReport.reason==REPORT_OK) ||
    (!targetReport.locked && targetReport.reason==REPORT_ACQUIRING));
 wire absentFrame=!targetReport.observed && !targetReport.locked && !targetReport.ambiguous &&
   targetReport.reason==REPORT_NOT_FOUND;
 wire currentReport=active && !configChange && !applicableAbandon && identity &&
   freshTime(timeUs,targetReport.captureStartUs,MAX_AGE_US) && afterFence!=0 && !afterFence[31] &&
   (!haveSequence || (newerSequence(targetReport.frameId,lastFrame) && afterLast!=0 && !afterLast[31]));
 wire badCurrentFrame=currentReport && (!targetReport.frameGood ||
   targetReport.reason==REPORT_FRAME_BAD || targetReport.reason==REPORT_RESOURCE_DROP);
 wire usableFrame=currentReport && healthy && !candidateOverflowEdge &&
   targetReport.frameGood && (observedFrame || absentFrame);
 wire usableTarget=usableFrame && observedFrame && afterTargetFence!=0 && !afterTargetFence[31] && !acquireFencePulse;
 wire recoveryThird=healthyCount==2 && consecutive;
 wire healthyReport=usableFrame && (!recoveryPending || recoveryThird);
 wire lockedReport=usableTarget && targetCount>=2 && consecutive && targetReport.locked &&
   (!recoveryPending || recoveryThird);
 assign targetReportReady=!reset && !targetRequestValid;
 wire takeReport=targetReportValid && targetReportReady;
 wire current= !reset && active && healthy && !configChange && !applicableAbandon && !candidateOverflowEdge;
 assign sourceHealthyFresh=current && (takeReport?healthyReport:
   (haveHealthy && !recoveryPending && freshTime(timeUs,stamp,MAX_AGE_US)));
 assign targetObserved=current && (takeReport?(usableFrame && observedFrame):
   (haveObserved && freshTime(timeUs,stamp,MAX_AGE_US)));
 assign motionTargetValid=sourceHealthyFresh && !acquireFencePulse && (takeReport?lockedReport:
   (haveLock && freshTime(timeUs,stamp,MAX_AGE_US)));
 assign centreU=takeReport && usableTarget?targetReport.centreU:cachedU;
 assign requestTag=activeTag;
 assign frameId=lastFrame;
 assign inputAgeUs=timeUs-stamp;
 always_ff @(posedge clk)begin
   if(reset)begin
     stableMask<=0;candidateMask<=0;stableCount<=0;requestDirty<=1;
     targetRequest<='0;targetRequestValid<=0;accepted<=0;tagCounter<=0;activeTag<=0;
     haveSequence<=0;haveHealthy<=0;haveObserved<=0;haveLock<=0;
     lastFrame<=0;previousConfig<=0;requestFenceUs<=0;targetFenceUs<=0;stamp<=0;cachedU<=0;
     fifoFatal<=0;abandonSeen<=0;recoveryPending<=0;previousCandidateOverflow<=0;healthyCount<=0;targetCount<=0;
   end else begin
     previousConfig<=status.activeCfgVersion;
     previousCandidateOverflow<=!syntheticSource && status.faultFlags[FAULT_CANDIDATE_OVERFLOW];
     if(selection!=candidateMask)begin candidateMask<=selection;stableCount<=0;end
     else if(stableCount<CW'(SELECTION_STABLE_CLKS-1))stableCount<=stableCount+1'b1;
     else if(stableMask!=candidateMask)begin stableMask<=candidateMask;requestDirty<=1;accepted<=0;end
     if(!targetRequestValid && requestDirty && stableMask==candidateMask && selection==stableMask)begin
       targetRequest.operation<=selectionValid?TARGET_SELECT:TARGET_CLEAR;
       targetRequest.markerType<=selectionValid?MARKER_BAY:MARKER_NONE;
       targetRequest.digit<=selectedDigit;
       targetRequest.requestTag<=tagCounter+16'd1;
       tagCounter<=tagCounter+16'd1;targetRequestValid<=1;requestDirty<=0;
       accepted<=0;haveSequence<=0;haveHealthy<=0;haveObserved<=0;haveLock<=0;targetCount<=0;healthyCount<=0;
     end
     if(targetRequestValid && targetRequestReady)begin
       targetRequestValid<=0;
       accepted<=targetRequest.operation==TARGET_SELECT;
       activeTag<=targetRequest.requestTag;requestFenceUs<=timeUs;targetFenceUs<=timeUs;
       haveSequence<=0;haveHealthy<=0;haveObserved<=0;haveLock<=0;healthyCount<=0;targetCount<=0;
     end
     if(takeReport)begin
       haveHealthy<=healthyReport;haveObserved<=usableFrame && observedFrame;haveLock<=lockedReport;
       if(usableFrame)begin
         lastFrame<=targetReport.frameId;stamp<=targetReport.captureStartUs;haveSequence<=1;
         if(usableTarget)cachedU<=targetReport.centreU;
       end
       if(usableTarget)targetCount<=consecutive && targetCount!=0 ? (targetCount<3?targetCount+2'd1:2'd3):2'd1;
       else targetCount<=0;
       if(recoveryPending)begin
         if(!usableFrame)healthyCount<=0;
         else if(recoveryThird)begin recoveryPending<=0;healthyCount<=0;end
         else healthyCount<=consecutive && healthyCount!=0 ? healthyCount+2'd1:2'd1;
       end
     end
     if(!healthy || !selectionMatches || (!takeReport && !freshTime(timeUs,stamp,MAX_AGE_US)))begin
       haveHealthy<=0;haveObserved<=0;haveLock<=0;
       // A newly accepted report below the age boundary retains its count.
       if(!takeReport)begin healthyCount<=0;targetCount<=0;end
     end
     if(configChange || sourceChanged || refreshRequest || applicableAbandon || candidateOverflowEdge || (takeReport && badCurrentFrame))begin
       haveHealthy<=0;haveObserved<=0;haveLock<=0;haveSequence<=0;healthyCount<=0;targetCount<=0;
       requestFenceUs<=timeUs;targetFenceUs<=timeUs;
       recoveryPending<=!(sourceChanged || refreshRequest);
       // Keep the rejected frame sequence as a lower bound. The new reception-
       // time fence excludes buffered pre-fault captures; only three later,
       // adjacent healthy frames may restore search qualification.
       if(takeReport && badCurrentFrame)begin
         haveSequence<=1;lastFrame<=targetReport.frameId;stamp<=targetReport.captureStartUs;
       end
     end
     if(sourceChanged || refreshRequest)begin accepted<=0;requestDirty<=1;end
     if(acquireFencePulse)begin targetFenceUs<=timeUs;haveLock<=0;targetCount<=0;end
     if(cameraFifoFault)fifoFatal<=1;
     if(applicableAbandon)abandonSeen<=1;
   end
 end
endmodule
