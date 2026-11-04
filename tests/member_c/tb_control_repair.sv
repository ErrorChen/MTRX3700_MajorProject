`timescale 1ns/1ps
module tb_control_repair;
 import perception_pkg::*;
 logic clk=0,reset=1,power_frame=0,estop_frame=0;
 always #10 clk=~clk;
 logic [31:0] timeUs=0;
 always @(posedge clk)if(reset)timeUs<=0;else timeUs<=timeUs+1;
 logic [5:0] selection=1;
 logic [1:0] mode=2;
 logic debugStart=0,debugStop=0,modeChanged=0,rawMode=0,injectLeaseValid=1,scanCalibrated=0,visualStart=0;
 logic [31:0] scanBudgetUs=100000;
 logic cameraFifoFault=0,cameraAbandonEvent=0;
 perceptionStatus_t status;
 targetRequest_t req,held;
 targetReport_t rpt;
 logic qr=0,rv=0;
 wire qv,rr;
 logic distance_valid=1,distanceSample=0;
 logic [11:0] distance_mm=1000;
 wire signed [6:0] l,r;
 wire permit,used,estop,sonar_stop,motionTargetValid,zeroSent,uartBusy,tx;
 wire [3:0] state;wire [2:0] reason;
 wire [511:0] statusWords;
 int checks=0,frame=0,lineCount=0,spinLines=0,driveLines=0,zeroLines=0;
 string lines[0:255];
 member_c_control #(.SELECTION_STABLE_CLKS(3),.ACQUIRE_SETTLE_US(50),
   .ACQUIRE_TIMEOUT_US(20000),.LOST_WAIT_US(1000),.TASK_TIMEOUT_US(2000000)) dut(
   .clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),.selection(selection),
   .mode(mode),.visualStart(visualStart),.debugStart(debugStart),.debugStop(debugStop),.modeChanged(modeChanged),.rawMode(rawMode),
   .injectLeaseValid(injectLeaseValid),.scanCalibrated(scanCalibrated),.scanBudgetUs(scanBudgetUs),.timeUs(timeUs),
   .cameraFifoFault(cameraFifoFault),.cameraAbandonEvent(cameraAbandonEvent),.status(status),
   .targetRequest(req),.targetRequestValid(qv),.targetRequestReady(qr),
   .targetReport(rpt),.targetReportValid(rv),.targetReportReady(rr),
   .distance_valid(distance_valid),.distanceSample(distanceSample),.distance_mm(distance_mm),
   .zeroSent(zeroSent),.uartBusy(uartBusy),.left_cm_s(l),.right_cm_s(r),
   .permit(permit),.used(used),.estop(estop),.sonar_stop(sonar_stop),.motionTargetValid(motionTargetValid),
   .motionState(state),.stop_reason(reason),.statusWords(statusWords));
 chassis_command #(.CLKS_PER_BIT(4),.PERIOD_CLKS(10000),.USE_WHEEL_REQUESTS(1)) uart(
   .clk(clk),.reset(reset),.armed(permit),.left_cm_s(-l),.right_cm_s(-r),
   .motion(2'b00),.speed(2'b00),.feedback(1'b0),.tx(tx),.busy(uartBusy),.zeroSent(zeroSent));
 task automatic ck(input bit ok,input string label);checks++;if(!ok)$fatal(1,"%s state=%0d time=%0d",label,state,timeUs);endtask
 task automatic tick(input int n=1);repeat(n)begin @(posedge clk);#1;end endtask
 task automatic samples(input int n=3);
   repeat(n)begin @(negedge clk);distanceSample=1;tick();@(negedge clk);distanceSample=0;tick();end
 endtask
 task automatic send(input bit visible=0,input int u=120,input bit locked=1,input int kind=0);
   @(negedge clk);frame++;rpt='0;rpt.requestTag=dut.requestTag;rpt.frameId=16'(frame);
   rpt.captureStartUs=timeUs;rpt.configVersion=status.activeCfgVersion;rpt.markerType=MARKER_BAY;
   rpt.digit=dut.selectedDigit;rpt.targetSelected=1;rpt.frameGood=1;
   rpt.observed=visible;rpt.locked=visible && locked;rpt.centreU=8'(u);rpt.centreV=160;rpt.quality=200;
   rpt.reason=visible?(locked?REPORT_OK:REPORT_ACQUIRING):REPORT_NOT_FOUND;
   case(kind)
     1:rpt.digit=6;
     2:rpt.configVersion=status.activeCfgVersion-1;
     3:rpt.captureStartUs=timeUs+100;
     4:rpt.frameId=dut.frameId;
     5:rpt.centreU=250;
     6:begin rpt.ambiguous=1;rpt.reason=REPORT_DUPLICATE_ID;end
     7:begin rpt.frameGood=0;rpt.observed=0;rpt.locked=0;rpt.reason=REPORT_FRAME_BAD;end
     8:begin rpt.frameGood=0;rpt.observed=0;rpt.locked=0;rpt.reason=REPORT_RESOURCE_DROP;end
     9:rpt.captureStartUs=dut.adapter.requestFenceUs;
   endcase
   rv=1;tick();ck(rr,"report consumed");@(negedge clk);rv=0;tick(3);
 endtask
 task automatic fresh(input bit visible=0,input int u=120);repeat(3)begin tick(10);send(visible,u);end endtask
 task automatic arm;
   @(negedge clk);debugStart=1;tick();@(negedge clk);debugStart=0;tick(3);
 endtask
 task automatic stopTask;
   @(negedge clk);debugStop=1;tick();@(negedge clk);debugStop=0;tick(3);
 endtask
 task automatic switchMode(input logic[1:0] m);
   @(negedge clk);mode=m;modeChanged=1;tick();@(negedge clk);modeChanged=0;tick(12);
 endtask
 task automatic stopped(input string label);ck(!permit && l==0 && r==0,label);endtask
 task automatic acquired(input int u=120);
   // Wait for a complete UART zero and the subsequent dwell/fence.
   wait(dut.motion.acquirePhase==2);tick(3);fresh(1,u);tick(4);
 endtask
 task automatic readLine;
   logic [7:0] ch;string line;line="";
   for(int n=0;n<29;n++)begin
     @(negedge tx);#40;
     for(int b=0;b<8;b++)begin #80;ch[b]=tx;end
     #80;if(tx!==1)$fatal(1,"UART stop bit");line={line,ch};
     if(ch==10)begin
       if(lineCount<256)lines[lineCount]=line;
       lineCount++;
       if(line=="{\"T\":1,\"L\":0.00,\"R\":0.00}\n")zeroLines++;
       else if(line=="{\"T\":1,\"L\":0.04,\"R\":-0.04}\n" || line=="{\"T\":1,\"L\":-0.04,\"R\":0.04}\n")spinLines++;
       else if(line=="{\"T\":1,\"L\":-0.05,\"R\":-0.05}\n" || line=="{\"T\":1,\"L\":-0.03,\"R\":-0.03}\n")driveLines++;
       else $fatal(1,"Malformed or unexpected UART JSON: %s",line);
       return;
     end
   end
   $fatal(1,"UART missing LF");
 endtask
 initial forever readLine();
 initial begin
   status='0;status.perceptionReady=1;status.activeCfgVersion=1;rpt='0;
   tick(3);@(negedge clk);reset=0;tick(12);
   ck(qv,"request pending before ARM");held=req;selection=2;tick(10);ck(qv && held==req,"immutable request during switch change/backpressure");
   @(negedge clk);qr=1;tick(20);ck(dut.selectedDigit==2 && dut.adapter.accepted,"new stable selection delivered after old request");
   for(int n=0;n<6;n++)begin
     @(negedge clk);selection=6'(1<<n);tick(15);ck(dut.selectedDigit==n+1 && dut.selectionValid,"six one-hot choices");
   end
   @(negedge clk);selection=3;tick(15);ck(dut.selectionConflict && req.operation==TARGET_CLEAR,"conflict clears target");arm();stopped("conflict cannot ARM");
   @(negedge clk);selection=0;tick(15);ck(!dut.selectionValid && !dut.selectionConflict,"no selection");
   @(negedge clk);selection=1;tick(15);samples();fresh();ck(dut.sourceHealthyFresh,"healthy NOT_FOUND source");
   arm();ck(state==1 && permit && l==-4 && r==4,"healthy no target really searches");tick(2600);ck(spinLines>0,"search reaches actual signed UART JSON");
   begin logic[31:0] spent;spent=dut.scanElapsedUs;arm();ck(dut.scanElapsedUs>=spent,"repeated ARM cannot reset budget");end
   send(1,80,0);stopped("single observed frame stops scan before lock");ck(state==6,"ACQUIRE entered");
   fresh(1,80);stopped("pre-settle frames cannot restart movement");
   acquired(80);ck(state==2 && permit && l==-4 && r==4,"post-fence three fresh frames align left");
   send(1,160);ck(l==4 && r==-4,"right coordinate reverses turn");
   send(1,120);tick(5);ck(state==3 && l==5 && r==5,"centred target approaches");tick(4000);ck(driveLines>0,"approach reaches UART");
   distance_mm=450;tick();ck(l==3 && r==3,"fine approach speed");
   distance_mm=350;tick(4);ck(state==4 && !dut.taskActive,"DOCKED disarms");stopped("DOCKED zero");
   distance_valid=0;tick(3);distance_valid=1;distance_mm=1000;samples();fresh(1);tick(3);ck(state==4 && !dut.taskActive,"sonar recovery cannot restart DOCKED");
   arm();tick(3);ck(dut.taskActive,"new task after DOCKED without reset");
   @(negedge clk);selection=2;#1;stopped("selection mismatch cancels immediately");tick(15);fresh(1);stopped("new selection requires new ARM");
   arm();ck(permit,"new selected task starts");
   injectLeaseValid=0;#1;stopped("lease expiry directly stops");tick(3);injectLeaseValid=1;fresh(1);stopped("lease renewal cannot rearm");
   arm();estop_frame=1;#1;stopped("IR dominates motion");tick();estop_frame=0;tick(2);ck(estop,"IR latch retained");
   debugStart=1;tick();debugStart=0;ck(estop,"JTAG cannot release IR");
   power_frame=1;tick();power_frame=0;tick(3);ck(!estop && !dut.taskActive,"first POWER only releases");
   power_frame=1;tick();power_frame=0;tick(3);ck(dut.taskActive,"second fresh POWER starts");
   distance_mm=200;#1;stopped("sonar hazard immediately stops");tick(3);ck(state==7,"hazard enters HOLD");
   distance_mm=1000;tick(20);ck(sonar_stop,"same distance cannot count as new samples");samples(2);ck(sonar_stop,"two new samples insufficient");samples(1);ck(!sonar_stop,"three samples release HOLD");
   acquired(120);ck(permit,"HOLD recovers through fresh target confirmation");
   rawMode=1;#1;stopped("raw mode immediately stops");tick(3);rawMode=0;fresh(1);stopped("raw mode off cannot resume old task");
   switchMode(1);fresh(1);arm();stopped("VISION_ONLY remains read-only despite ARM and lock");ck(motionTargetValid,"VISION_ONLY retains tracking");
   switchMode(0);fresh();arm();ck(state==8 && dut.failureReason==3,"uncalibrated integrated search refused");
   fresh(1);arm();tick(4);ck(permit,"uncalibrated integrated visible target can approach");
   // Red2 refreshes only an idle/terminal real-source task and never ARM in vision.
   stopTask();switchMode(1);fresh(1);
   begin logic[15:0] oldTag;oldTag=dut.requestTag;
     visualStart=1;tick();visualStart=0;tick(12);fresh(1);
     ck(dut.requestTag!=oldTag && motionTargetValid && !dut.taskActive,"red2 VISION_ONLY reselects without motion");
   end
   // Real-board red2 correction: an uncalibrated task must not consume its
   // start on the first acquiring report and terminate before the third lock.
   switchMode(0);scanCalibrated=0;fresh(1);
   visualStart=1;tick();visualStart=0;tick(12);
   send(1,120,0);ck(!dut.taskActive && dut.pendingVisualStart && state==0,"uncalibrated red2 waits after first acquiring frame");
   send(1,120,0);ck(!dut.taskActive && dut.pendingVisualStart && state==0,"uncalibrated red2 waits after second acquiring frame");
   send(1,120,1);tick(4);ck(dut.taskActive && motionTargetValid && permit && state==3,"uncalibrated red2 starts on third new locked frame");
   stopTask();visualStart=1;tick();visualStart=0;tick(12);fresh();
   ck(!dut.taskActive && dut.pendingVisualStart && state==0,"uncalibrated red2 never starts on healthy NOT_FOUND");
   // Advance the shared microsecond test clock, retaining the production 1 s
   // pending window; the next edge must discard the absent-target request.
   @(negedge clk);timeUs=dut.visualStartUs+1000001;tick(3);
   ck(!dut.taskActive && !dut.pendingVisualStart,"uncalibrated absent-target red2 expires after one second");
   fresh(1);ck(!dut.taskActive,"late target lock cannot revive expired red2 authorization");
   scanCalibrated=1;fresh(1);
   begin logic[15:0] oldTag;oldTag=dut.requestTag;
     visualStart=1;tick();visualStart=0;tick(12);ck(!dut.taskActive && dut.pendingVisualStart,"red2 waits for new request report");
     fresh(1);tick(4);ck(dut.requestTag!=oldTag && dut.taskActive,"red2 starts current switch selection after fresh boundary");
     oldTag=dut.requestTag;visualStart=1;tick();visualStart=0;tick(4);
     ck(dut.requestTag==oldTag,"active red2 cannot reset task or request");
   end
   stopTask();visualStart=1;tick();visualStart=0;tick(2);stopTask();fresh(1);ck(!dut.taskActive,"STOP cancels pending red2 start");
   distance_valid=0;tick(3);visualStart=1;tick();visualStart=0;tick(12);distance_valid=1;samples();fresh(1);
   ck(!dut.taskActive && !dut.pendingVisualStart,"unsafe red2 cannot start on later recovery");
   arm();tick(3);
   // Hardware correction: sticky candidate-overflow history must not deadlock
   // otherwise healthy real vision, while each new failed frame forces recovery.
   status.faultFlags=16'd2;#1;stopped("first candidate overflow immediately revokes motion");tick(3);
   ck(dut.adapter.recoveryPending && !dut.sourceHealthyFresh && !dut.targetObserved,"overflow edge establishes recovery fence");
   send();ck(!dut.sourceHealthyFresh,"overflow first healthy NOT_FOUND cannot recover");
   send();ck(!dut.sourceHealthyFresh,"overflow second healthy NOT_FOUND cannot recover");
   send();ck(dut.sourceHealthyFresh && !motionTargetValid && status.faultFlags[1],"third healthy NOT_FOUND recovers despite retained overflow history");
   send(1);ck(!motionTargetValid,"first observed frame cannot restore target lock");
   send(1);ck(!motionTargetValid,"second observed frame cannot restore target lock");
   send(1);ck(motionTargetValid,"third observed frame restores target lock");
   send(0,120,0,7);stopped("current bad frame stops immediately despite no new sticky edge");
   ck(dut.adapter.recoveryPending && !dut.sourceHealthyFresh && !dut.targetObserved,"bad report establishes a new recovery fence");
   send(0,120,0,9);ck(!dut.sourceHealthyFresh && dut.adapter.healthyCount==0,"capture at fence cannot count for recovery");
   send();ck(!dut.sourceHealthyFresh,"bad-frame first fresh recovery frame");
   send();ck(!dut.sourceHealthyFresh,"bad-frame second fresh recovery frame");
   send();ck(dut.sourceHealthyFresh && !motionTargetValid,"bad-frame third adjacent NOT_FOUND restores health only");
   send(0,120,0,8);ck(!dut.sourceHealthyFresh && dut.adapter.recoveryPending,"RESOURCE_DROP enters the same fenced recovery");
   fresh();ck(dut.sourceHealthyFresh,"RESOURCE_DROP recovers after three new healthy frames");
   status.faultFlags=16'd6;#1;stopped("mask bank hard fault remains blocking with overflow history");
   fresh(1);ck(!dut.sourceHealthyFresh && !motionTargetValid,"good frames cannot override asserted mask-bank hard fault");
   status.faultFlags=16'd2;fresh(1);
   cameraAbandonEvent=1;#1;stopped("abandon stops immediately");tick();cameraAbandonEvent=0;status.faultFlags=3;
   send();ck(!dut.sourceHealthyFresh,"abandon first NOT_FOUND stays inhibited");send();ck(!dut.sourceHealthyFresh,"abandon second NOT_FOUND stays inhibited");send();ck(dut.sourceHealthyFresh && !motionTargetValid,"third healthy NOT_FOUND recovers search health only");
   cameraFifoFault=1;tick();cameraFifoFault=0;fresh(1);stopped("FIFO fatal cannot clear by good frames");
   switchMode(2);status.faultFlags=0;fresh(1);arm();ck(permit,"injection ignores preserved real-camera fatal");
   switchMode(0);fresh(1);arm();stopped("switching back reapplies preserved fatal");
   switchMode(2);fresh(1);arm();
   for(int k=1;k<=6;k++)begin send(1,120,1,k);stopped("malformed/stale/duplicate report fails closed");fresh(1);end
   stopTask();scanBudgetUs=2000;fresh();arm();tick(2200);ck(state==6,"budget enters final stationary acquisition");
   // Keep health fresh while final acquisition expires.
   repeat(25)begin tick(1000);send();end
   ck(state==8 && !dut.taskActive && dut.failureReason==1,"bounded NOT_FOUND disarms");samples();fresh(1);stopped("NOT_FOUND cannot auto-resume");
   tick(2500);ck(zeroLines>0 && zeroSent,"completed UART zero observed separately from logical stop");
   $display("PASS: tb_control_repair checks=%0d UART lines=%0d spin=%0d drive=%0d zero=%0d",checks,lineCount,spinLines,driveLines,zeroLines);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog state=%0d phase=%0d",state,dut.motion.acquirePhase);end
endmodule
