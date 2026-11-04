// Synthetic visual source only. IR/J3 remain outside this mux and cannot be injected.
// All interface signals use CLOCK_50; stable templates make 25 Hz independent frames.
module syntheticPerception #(parameter int FRAME_PERIOD_US=40000)(
 input logic clk,reset,enabled,sourceChanged,leaseValid,templateValid,
 input logic [31:0] timeUs,observation0,observation1,
 input perception_pkg::targetRequest_t targetRequest,
 input logic targetRequestValid,
 output wire targetRequestReady,
 output perception_pkg::targetReport_t targetReport,
 output logic targetReportValid,
 input logic targetReportReady,
 output perception_pkg::perceptionStatus_t status
);
 import perception_pkg::*;
 targetRequest_t activeRequest;
 logic selected;
 logic [15:0] frameId;
 logic [31:0] lastFrameUs,requestFence;
 logic [1:0] lockCount;
 wire producing=enabled && leaseValid && templateValid && observation0[20];
 wire visible=observation0[17] && !observation0[18] && observation0[19] && observation0[31:24]!=0;
 wire [31:0] sinceFrame=timeUs-lastFrameUs;
 wire [31:0] sinceRequest=timeUs-requestFence;
 assign targetRequestReady=!reset && enabled && !sourceChanged && (!targetReportValid || targetReportReady);
 always_comb begin
   status='0;
   status.perceptionReady=producing;
   status.activeCfgVersion=16'd1;
 end
 always_ff @(posedge clk)begin
   if(reset)begin
     activeRequest<='0;selected<=0;frameId<=0;lastFrameUs<=0;requestFence<=0;
     lockCount<=0;targetReport<='0;targetReportValid<=0;
   end else if(sourceChanged || !enabled)begin
     selected<=0;targetReportValid<=0;lockCount<=0;lastFrameUs<=timeUs;requestFence<=timeUs;
   end else begin
     if(targetReportValid && targetReportReady)targetReportValid<=0;
     if(!producing)lockCount<=0;
     if(targetRequestValid && targetRequestReady)begin
       activeRequest<=targetRequest;
       selected<=targetRequest.operation==TARGET_SELECT && targetRequest.markerType==MARKER_BAY && bayEnabled(targetRequest.digit);
       requestFence<=timeUs;lastFrameUs<=timeUs;lockCount<=0;targetReportValid<=0;
     end else if(producing && selected && !targetReportValid &&
                 sinceFrame>=FRAME_PERIOD_US && !sinceFrame[31] && sinceRequest!=0 && !sinceRequest[31])begin
       lastFrameUs<=timeUs;frameId<=frameId+16'd1;
       targetReport<='0;
       targetReport.requestTag<=activeRequest.requestTag;
       targetReport.frameId<=frameId+16'd1;
       targetReport.captureStartUs<=timeUs;
       targetReport.configVersion<=16'd1;
       targetReport.markerType<=MARKER_BAY;
       targetReport.digit<=activeRequest.digit;
       targetReport.targetSelected<=1;
       targetReport.frameGood<=observation0[19];
       targetReport.observed<=observation0[17];
       targetReport.ambiguous<=observation0[18];
       targetReport.centreU<=observation0[7:0];
       targetReport.centreV<=observation0[16:8];
       targetReport.boxWidth<=observation1[7:0];
       targetReport.boxHeight<=observation1[16:8];
       targetReport.quality<=observation0[31:24];
       targetReport.locked<=visible && lockCount>=2;
       if(!observation0[19])targetReport.reason<=REPORT_FRAME_BAD;
       else if(observation0[18])targetReport.reason<=REPORT_DUPLICATE_ID;
       else if(!observation0[17])targetReport.reason<=REPORT_NOT_FOUND;
       else if(observation0[31:24]==0)targetReport.reason<=REPORT_LOW_QUALITY;
       else targetReport.reason<=lockCount>=2 ? REPORT_OK : REPORT_ACQUIRING;
       if(visible)begin if(lockCount<3)lockCount<=lockCount+2'd1;end else lockCount<=0;
       targetReportValid<=1;
     end
   end
 end
endmodule
