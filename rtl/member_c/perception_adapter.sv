// Public v3 types are copied verbatim from the read-only Member B package.
module perception_adapter #(parameter logic [31:0] MAX_AGE_US=150000)(
 input logic clk, reset, power_frame, cancel,
 input logic [2:0] selection,
 input logic [31:0] timeUs,
 input logic cameraFifoFault, cameraAbandonEvent, // synchronous CLOCK_50 private safety link
 input perception_pkg::perceptionStatus_t status,
 output perception_pkg::targetRequest_t targetRequest,
 output logic targetRequestValid, input logic targetRequestReady,
 input perception_pkg::targetReport_t targetReport,
 input logic targetReportValid, output logic targetReportReady,
 output logic taskActive, startPulse,
 output logic [3:0] selectedDigit,
 output wire [7:0] centreU, output wire motionTargetValid
);
 import perception_pkg::*;
 logic accepted, haveMeasurement, haveSequence;
 logic [15:0] tag, lastFrame, cachedConfig, previousConfig;
 logic [31:0] fenceUs, stamp;
 logic [7:0] cachedU;
 // FIFO faults remain fatal until reset, even if the input were later removed.
 logic fifoFatal, abandonSeen, recoveryPending;
 logic [1:0] recoveryCount;
 wire healthy=status.perceptionReady && !status.interactionBusy &&
     !cameraFifoFault && !fifoFatal &&
     ((status.faultFlags & ~((16'b1 << FAULT_AUDIO_CAPTURE) |
       (abandonSeen ? (16'b1 << FAULT_CAMERA_TRANSPORT) : 16'b0)))==0);
 wire configChange=previousConfig!=status.activeCfgVersion;
 wire [31:0] afterFence=targetReport.captureStartUs-fenceUs;
 wire [31:0] afterLast=targetReport.captureStartUs-stamp;
 wire usableFrame=accepted && taskActive && healthy && !configChange && !cancel && !cameraAbandonEvent &&
     targetReport.requestTag==tag && targetReport.markerType==MARKER_BAY &&
     targetReport.digit==selectedDigit && targetReport.configVersion==status.activeCfgVersion &&
     targetReport.frameGood && targetReport.observed &&
     targetReport.targetSelected && !targetReport.ambiguous &&
      (targetReport.locked ? targetReport.reason==REPORT_OK : targetReport.reason==REPORT_ACQUIRING) &&
     targetReport.quality!=0 && targetReport.centreU<240 &&
     freshTime(timeUs,targetReport.captureStartUs,MAX_AGE_US) &&
     afterFence!=0 && !afterFence[31] &&
     (!haveSequence || (newerSequence(targetReport.frameId,lastFrame) && afterLast!=0 && !afterLast[31]));
 wire [15:0] frameStep=targetReport.frameId-lastFrame;
 wire recoveryThird=recoveryCount==2 && haveSequence && frameStep==1;
 wire goodReport=usableFrame && targetReport.locked && targetReport.reason==REPORT_OK &&
     (!recoveryPending || recoveryThird);
 assign targetReportReady=!reset && !targetRequestValid;
 wire takeReport=targetReportValid && targetReportReady;
 assign motionTargetValid=!reset && !cameraAbandonEvent && !cancel && taskActive && accepted && healthy && !configChange &&
     (takeReport ? goodReport : (!recoveryPending && haveMeasurement && cachedConfig==status.activeCfgVersion &&
       freshTime(timeUs,stamp,MAX_AGE_US)));
 assign centreU=takeReport && goodReport ? targetReport.centreU : cachedU;
 always_ff @(posedge clk) begin
   if(reset) begin
     targetRequest<='0;targetRequestValid<=0;taskActive<=0;startPulse<=0;selectedDigit<=0;
     accepted<=0;haveMeasurement<=0;haveSequence<=0;tag<=0;lastFrame<=0;
     cachedConfig<=0;previousConfig<=0;fenceUs<=0;stamp<=0;cachedU<=0;
     fifoFatal<=0;abandonSeen<=0;recoveryPending<=0;recoveryCount<=0;
   end else begin
     startPulse<=0;previousConfig<=status.activeCfgVersion;
     if(targetRequestValid && targetRequestReady) begin
       targetRequestValid<=0;accepted<=1;fenceUs<=timeUs;haveMeasurement<=0;haveSequence<=0;
     end
     if(takeReport) begin
       // Any unusable report revokes the cache, including wrong identity/replays.
       haveMeasurement<=goodReport;
       if(goodReport || (recoveryPending && usableFrame)) begin
         cachedU<=targetReport.centreU;stamp<=targetReport.captureStartUs;
         cachedConfig<=targetReport.configVersion;lastFrame<=targetReport.frameId;haveSequence<=1;
       end
       if(recoveryPending) begin
         if(!usableFrame) recoveryCount<=0;
         else if(goodReport) begin recoveryPending<=0;recoveryCount<=0;end
         else recoveryCount<=recoveryCount!=0 && haveSequence && frameStep==1 ?
              (recoveryCount<2 ? recoveryCount+2'd1 : 2'd2) : 2'd1;
       end
     end
     if(configChange) begin recoveryCount<=0;haveMeasurement<=0;haveSequence<=0;fenceUs<=timeUs;end
     if(!healthy || cancel || (!takeReport && !freshTime(timeUs,stamp,MAX_AGE_US))) begin
       haveMeasurement<=0;recoveryCount<=0;
     end
     if(power_frame && !taskActive && !cancel && selection>=1 && selection<=6) begin
       recoveryCount<=0;
       taskActive<=1;startPulse<=1;selectedDigit<={1'b0,selection};tag<=tag+1'b1;
       targetRequest.operation<=TARGET_SELECT;targetRequest.requestTag<=tag+1'b1;
       targetRequest.markerType<=MARKER_BAY;targetRequest.digit<={1'b0,selection};
       targetRequestValid<=1;accepted<=0;haveMeasurement<=0;haveSequence<=0;fenceUs<=timeUs;
     end
     // Last assignments win over report/request handshakes on this same edge.
     // The fence is CLOCK_50 time, conservatively later than buffered SOF stamps.
     if(cameraFifoFault) fifoFatal<=1;
     if(cameraAbandonEvent) begin
       abandonSeen<=1;recoveryPending<=1;recoveryCount<=0;
       haveMeasurement<=0;haveSequence<=0;fenceUs<=timeUs;
     end
   end
 end
endmodule
