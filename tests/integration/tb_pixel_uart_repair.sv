`timescale 1ns/1ps
// Production pixel pipeline -> public report -> production C -> serialized UART.
// Fixed 25 fps synthetic sheet translation; no forced internal observations or
// ready/status bits. Short settle and scan budgets are simulation parameters,
// not mechanical calibration or live-camera evidence.
module tb_pixel_uart_repair;
 logic red2Reset=0; // No mode change in this pixel fixture.
 import perception_pkg::*;
 logic clk=0,pclk=0,reset=1,resetPclk=1;
 always #10 clk=~clk;
 initial begin #7;forever #25 pclk=~pclk;end
 logic cameraFrameStart=0,cameraPixelValid=0;
 logic [15:0] cameraPixel=0;
 logic [9:0] cameraX=0;logic [8:0] cameraY=0;
 logic [31:0] timeUs=0;integer divider=0;
 always @(posedge clk)if(reset)begin divider<=0;timeUs<=0;end
 else if(divider==49)begin divider<=0;timeUs<=timeUs+1;end else divider<=divider+1;
 // This scene tests navigation with the default profile. Calibration has its
 // separate real-pixel regression and must not consume this test's frames.
 logic interactionEnable=0,interactionPermit=1,debugCalArm=0,debugSpeechArm=0;
 logic [1:0] orientationProfile=0;
 logic bypassPerspective=0,processingEnable=1;
 wire debugInteractionArmReady,cameraFifoFault,cameraAbandonEvent;
 targetRequest_t targetRequest;wire targetRequestValid,targetRequestReady;
 targetReport_t targetReport;wire targetReportValid,targetReportReady;
 queryResult_t queryResult;wire queryResultValid,queryBusy;logic queryResultReady=1;
 userEvent_t userEvent;wire userEventValid;logic userEventReady=1;
 perceptionStatus_t status;wire [DEBUG_WORD_COUNT*32-1:0] debugWords;
 wire completedFrame;wire [15:0] completedFrameId;
 perceptionCore core(.*);
 logic power_frame=0,debugStop=0,distanceSample=0;
 wire signed [6:0] leftRequest,rightRequest;
 wire permit,used,estop,sonarStop,motionTargetValid;
 wire [3:0] motionState;wire [2:0] stopReason;
 wire [511:0] statusWords;
 wire tx,uartBusy,zeroSent;
 // E7070005 production convention, verified against real body-left low U.
 // Pixel input and the public U/V contract remain unchanged.
 member_c_control #(.TURN_SIGN(-1),.RUNTIME_TUNING(1),.SELECTION_STABLE_CLKS(4),.ACQUIRE_SETTLE_US(1000),
   .ACQUIRE_TIMEOUT_US(300000),.LOST_WAIT_US(80000),.TASK_TIMEOUT_US(1500000)) control(
   .clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(1'b0),.visualStart(1'b0),
   .selection(6'b000001),.mode(2'd0),.debugStart(1'b0),.debugStop(debugStop),
   .modeChanged(1'b0),.rawMode(1'b0),.injectLeaseValid(1'b0),
   .scanCalibrated(1'b1),.scanBudgetUs(32'd700000),.timeUs(timeUs),.tuningWord(32'h001e3544),
   .cameraFifoFault(cameraFifoFault),.cameraAbandonEvent(cameraAbandonEvent),.status(status),
   .targetRequest(targetRequest),.targetRequestValid(targetRequestValid),.targetRequestReady(targetRequestReady),
   .targetReport(targetReport),.targetReportValid(targetReportValid),.targetReportReady(targetReportReady),
   .distance_valid(1'b1),.distanceSample(distanceSample),.distance_mm(12'd1000),
   .zeroSent(zeroSent),.uartBusy(uartBusy),.left_cm_s(leftRequest),.right_cm_s(rightRequest),
   .permit(permit),.used(used),.estop(estop),.sonar_stop(sonarStop),.motionTargetValid(motionTargetValid),
   .motionState(motionState),.stop_reason(stopReason),.statusWords(statusWords));
 // Accelerated baud only: transmit every real complete JSON and decode its pin.
 chassis_command #(.USE_WHEEL_REQUESTS(1),.CLKS_PER_BIT(4),.PERIOD_CLKS(100000)) sender(
   .clk(clk),.reset(reset),.armed(permit),.left_cm_s(-leftRequest),.right_cm_s(-rightRequest),
   .motion(2'b00),.speed(2'b00),.feedback(1'b0),.tx(tx),.busy(uartBusy),.zeroSent(zeroSent));
 logic [15:0] pixels[0:76799];string scenePath;
 integer frameNumber=0,reports=0,notFoundReports=0,observedReports=0;
 // E10 enters forward steering directly after confirmed acquisition at U80.
 // Keep complete forward JSON coverage distinct from forbidden tracking spins.
 integer searchLines=0,leftLines=0,forwardLines=0,rightLines=0,zeroLines=0;
 integer leftSpinLines=0,rightSpinLines=0,coarseLeftLines=0,coarseRightLines=0;
 integer fineLeftLines=0,fineRightLines=0;
 integer acquireFrames=0,lastReportId=0;
 logic fenceSeen=0,acquireSeen=0,started=0;
 logic [31:0] acquireFenceUs=0;
 logic [3:0] oldState=0;
 string line="";logic [7:0] uartByte;
 time sofTime=0,previousSof=0;
 initial forever begin
   @(negedge tx);#40;
   if(tx!==0)$fatal(1,"UART start bit");
   for(int bitIndex=0;bitIndex<8;bitIndex++)begin #80;uartByte[bitIndex]=tx;end
   #80;if(tx!==1)$fatal(1,"UART stop bit");
   line={line,uartByte};
   if(uartByte==10)begin
     if(line=="{\"T\":1,\"L\":0.00,\"R\":0.00}\n")zeroLines++;
     else if(line=="{\"T\":1,\"L\":-0.04,\"R\":0.04}\n")begin
       if(!acquireSeen)searchLines++;else begin leftLines++;leftSpinLines++;end
     end else if(line=="{\"T\":1,\"L\":-0.05,\"R\":-0.05}\n")forwardLines++;
     else if(line=="{\"T\":1,\"L\":0.04,\"R\":-0.04}\n")begin rightLines++;rightSpinLines++;end
     // Production motor polarity is negative. With TURN_SIGN=-1, low U
     // uses logical L>R; high U uses R>L, with both wheels still forward.
     else if(line=="{\"T\":1,\"L\":-0.05,\"R\":-0.03}\n")begin leftLines++;coarseLeftLines++;end
     else if(line=="{\"T\":1,\"L\":-0.03,\"R\":-0.05}\n")begin rightLines++;coarseRightLines++;end
     else if(line=="{\"T\":1,\"L\":-0.04,\"R\":-0.03}\n")begin leftLines++;fineLeftLines++;end
     else if(line=="{\"T\":1,\"L\":-0.03,\"R\":-0.04}\n")begin rightLines++;fineRightLines++;end
     else $fatal(1,"Malformed/unexpected physical UART JSON: %s",line);
     line="";
   end
 end
 always @(negedge clk)begin
   power_frame=0;distanceSample=0;
   if(!reset)begin
     // Independent new sonar samples; never count one held sample repeatedly.
     if(divider==0 && timeUs!=0 && timeUs%10000==0)distanceSample=1;
     if(!started && timeUs>=40000)begin power_frame=1;started=1;end
   end
 end
 always @(posedge clk)if(!reset)begin
   if(cameraFifoFault||cameraAbandonEvent)$fatal(1,"fixed 25 fps source transport fault");
   if(motionState!=oldState)begin
     $display("PIXEL_UART_STATE us=%0d state=%0d U=%0d fresh=%0b locked=%0b",timeUs,motionState,control.centreU,control.sourceHealthyFresh,motionTargetValid);
     oldState=motionState;
   end
   if(motionState==6)begin
     acquireSeen=1;
     if(permit||leftRequest!=0||rightRequest!=0)$fatal(1,"ACQUIRE emitted motion");
   end
   if(control.acquireFencePulse)begin
     if(!zeroSent)$fatal(1,"new capture fence preceded zero JSON completion");
     fenceSeen=1;acquireFenceUs=timeUs;acquireFrames=0;
   end
   if(targetReportValid&&targetReportReady)begin
     reports++;
     if(!targetReport.frameGood || targetReport.frameId!=lastReportId+1 ||
        targetReport.requestTag!=control.requestTag || targetReport.digit!=1 ||
        targetReport.markerType!=MARKER_BAY || timeUs-targetReport.captureStartUs>150000)
       $fatal(1,"invalid/stale/reordered actual pixel report frame=%0d prev=%0d reason=%0d",targetReport.frameId,lastReportId,targetReport.reason);
     lastReportId=targetReport.frameId;
     if(targetReport.observed)begin
       observedReports++;
       if(fenceSeen && targetReport.captureStartUs>acquireFenceUs)acquireFrames++;
     end else if(targetReport.reason==REPORT_NOT_FOUND)notFoundReports++;
     else $fatal(1,"unexpected pixel-report refusal reason %0d",targetReport.reason);
     $display("PIXEL_UART_REPORT frame=%0d good=%0b observed=%0b locked=%0b U=%0d age=%0d",targetReport.frameId,targetReport.frameGood,targetReport.observed,targetReport.locked,targetReport.centreU,timeUs-targetReport.captureStartUs);
   end
   if((motionState==2||motionState==3)&&(!fenceSeen||acquireFrames<3))
     $fatal(1,"tracking began without three independent post-stop-fence pixel frames");
   if(motionState==2)
     $fatal(1,"far U80/120/160 fixture entered ALIGN instead of direct forward approach");
   if(motionState==3 && motionTargetValid && permit && control.centreU==80 &&
      (leftRequest!=5 || rightRequest!=3))
     $fatal(1,"U80 initial approach did not request exact forward left correction 5/3");
   if(motionState==3 && motionTargetValid && permit && control.centreU==120 &&
      (leftRequest!=5 || rightRequest!=5))
     $fatal(1,"U120 centred approach did not request exact straight forward 5/5");
   if(motionState==3 && motionTargetValid && permit && control.centreU==160 &&
      (leftRequest!=3 || rightRequest!=5))
     $fatal(1,"U160 in-corridor approach did not request exact forward right correction 3/5");
   if(debugStop&&permit)$fatal(1,"STOP retained motion permission");
 end
 task automatic frame(input integer shiftY,input bit visible);
   integer sy;
   begin
     frameNumber++;cameraFrameStart=1;sofTime=$time;
     if(previousSof!=0 && sofTime-previousSof!=40000000)$fatal(1,"source is not fixed 25 fps");
     previousSof=sofTime;
     @(negedge pclk);cameraFrameStart=0;repeat(8)@(negedge pclk);
     for(int py=0;py<240;py++)begin
       for(int px=0;px<320;px++)begin
         sy=py-shiftY;
         cameraX=10'(px*2);cameraY=9'(py*2);
         cameraPixel=visible&&sy>=0&&sy<240?pixels[sy*320+px]:16'hffff;
         cameraPixelValid=1;@(negedge pclk);cameraPixelValid=0;repeat(3)@(negedge pclk);
       end
       repeat(150)@(negedge pclk);
     end
     while($time-sofTime<40000000)@(negedge pclk);
   end
 endtask
 initial begin
   if(!$value$plusargs("SCENE=%s",scenePath))scenePath="tests/vectors/sheet_320x240_rgb565.hex";
   $readmemh(scenePath,pixels);
   repeat(10)@(negedge clk);reset=0;resetPclk=0;
   repeat(30)@(negedge pclk);
   frame(0,0);frame(0,0);
   repeat(5)frame(28,1); // Blue1 U=80 -> acquisition -> direct forward correction 5/3.
   repeat(4)frame(68,1); // U=120 -> forward.
   repeat(2)frame(108,1); // U=160 in APPROACH -> forward right correction 3/5.
   frame(0,0); // Real no-target frame -> stop translation.
   if(searchLines==0||leftLines==0||forwardLines==0||rightLines==0||!fenceSeen||notFoundReports<2||observedReports<6)
     $fatal(1,"pixel/UART coverage missing search=%0d left=%0d forward=%0d right=%0d reports=%0d",searchLines,leftLines,forwardLines,rightLines,reports);
   if(coarseLeftLines==0 || coarseRightLines==0 || leftSpinLines!=0 || rightSpinLines!=0)
     $fatal(1,"U80/U160 require complete forward 5/3 and 3/5 JSON without tracking spins: left=%0d right=%0d leftSpin=%0d rightSpin=%0d",coarseLeftLines,coarseRightLines,leftSpinLines,rightSpinLines);
   @(negedge clk);debugStop=1;
   repeat(200000)@(negedge clk);
   if(permit||leftRequest!=0||rightRequest!=0||!zeroSent||motionState!=0||zeroLines==0)
     $fatal(1,"STOP did not complete a zero JSON and cancel task");
   $display("PASS tb_pixel_uart_repair frames=%0d reports=%0d search=%0d leftCorrection=%0d forward=%0d rightCorrection=%0d zero=%0d coarseLeft=%0d coarseRight=%0d fineLeft=%0d fineRight=%0d leftSpin=%0d rightSpin=%0d fixed25fps pixel-to-UART",frameNumber,reports,searchLines,leftLines,forwardLines,rightLines,zeroLines,coarseLeftLines,coarseRightLines,fineLeftLines,fineRightLines,leftSpinLines,rightSpinLines);
   $finish;
 end
 initial begin #650000000;$fatal(1,"pixel/UART watchdog");end
endmodule
