`timescale 1ns/1ps
module tb_control_repair #(parameter int TURN_SIGN=-1,parameter bit STRICT_ALIGN_BAND=0,
 parameter bit RUNTIME_TUNING=1);
 import perception_pkg::*;
 logic clk=0,reset=1,power_frame=0,estop_frame=0;
 always #10 clk=~clk;
 logic [31:0] timeUs=0;
 always @(posedge clk)if(reset)timeUs<=0;else timeUs<=timeUs+1;
 logic [5:0] selection=1;
 logic [1:0] mode=2;
 logic debugStart=0,debugStop=0,modeChanged=0,rawMode=0,injectLeaseValid=1,scanCalibrated=0,visualStart=0;
 logic [31:0] scanBudgetUs=100000;
 logic [31:0] tuningWord=RUNTIME_TUNING?(STRICT_ALIGN_BAND?32'h000a3544:32'h001e3544):32'hxxxxxxxx;
 logic [31:0] alignTimingWord=RUNTIME_TUNING?32'h00015420:32'hxxxxxxxx;
 logic [7:0] timingProbeU=0;
 logic [31:0] timingProbeWord=32'h00015420;
 wire [31:0] dutPulseMathWidth;
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
 int lowTurnLines=0,highTurnLines=0,lowFineTurnLines=0,highFineTurnLines=0,fineLines=0;
 int lowSteerLines=0,highSteerLines=0,lowFineSteerLines=0,highFineSteerLines=0;
 int runtimeLines=0,runtimeAllowedCount=0;
 string runtimeAllowed[0:31];
 localparam int TEST_SETTLE_US=1500; // Accelerated protocol dwell; production is 1500000 us.
 localparam int TEST_BACKTRACK_US=150000; // Keep the production reverse duration.
 localparam int TEST_ALIGN_LOW=STRICT_ALIGN_BAND?110:90,TEST_ALIGN_HIGH=STRICT_ALIGN_BAND?130:150;
 localparam int NEAR_LOW=TEST_ALIGN_LOW-1,NEAR_HIGH=TEST_ALIGN_HIGH+1;
 localparam int NEAR_PULSE_US=(120-NEAR_LOW)*2000;
 localparam int LOW_L=-4*TURN_SIGN,LOW_R=4*TURN_SIGN;
 localparam int LOW_FINE_L=-3*TURN_SIGN,LOW_FINE_R=3*TURN_SIGN;
 localparam int NEAR_L=STRICT_ALIGN_BAND?LOW_FINE_L:LOW_L,NEAR_R=STRICT_ALIGN_BAND?LOW_FINE_R:LOW_R;
 localparam int LOW_STEER_L=TURN_SIGN==-1 ? 5:3,LOW_STEER_R=TURN_SIGN==-1 ? 3:5;
 localparam int LOW_FINE_STEER_L=TURN_SIGN==-1 ? 4:3,LOW_FINE_STEER_R=TURN_SIGN==-1 ? 3:4;
 localparam string LOW_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":-0.04,\"R\":0.04}\n" : "{\"T\":1,\"L\":0.04,\"R\":-0.04}\n";
 localparam string HIGH_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":0.04,\"R\":-0.04}\n" : "{\"T\":1,\"L\":-0.04,\"R\":0.04}\n";
 localparam string LOW_FINE_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":-0.03,\"R\":0.03}\n" : "{\"T\":1,\"L\":0.03,\"R\":-0.03}\n";
 localparam string HIGH_FINE_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":0.03,\"R\":-0.03}\n" : "{\"T\":1,\"L\":-0.03,\"R\":0.03}\n";
 localparam string LOW_STEER_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":-0.05,\"R\":-0.03}\n" : "{\"T\":1,\"L\":-0.03,\"R\":-0.05}\n";
 localparam string HIGH_STEER_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":-0.03,\"R\":-0.05}\n" : "{\"T\":1,\"L\":-0.05,\"R\":-0.03}\n";
 localparam string LOW_FINE_STEER_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":-0.04,\"R\":-0.03}\n" : "{\"T\":1,\"L\":-0.03,\"R\":-0.04}\n";
 localparam string HIGH_FINE_STEER_JSON=TURN_SIGN==-1 ? "{\"T\":1,\"L\":-0.03,\"R\":-0.04}\n" : "{\"T\":1,\"L\":-0.04,\"R\":-0.03}\n";
 string lines[0:1023];
 // Default follows the E7070012 runtime-enabled production top; +1 remains an explicit
 // generic convention regression, not the corrected hardware configuration.
 member_c_control #(.RUNTIME_TUNING(RUNTIME_TUNING),.TURN_SIGN(TURN_SIGN),.ALIGN_LOW(TEST_ALIGN_LOW),.ALIGN_HIGH(TEST_ALIGN_HIGH),
   .SELECTION_STABLE_CLKS(3),.ACQUIRE_SETTLE_US(TEST_SETTLE_US),
   .ACQUIRE_TIMEOUT_US(20000),.LOST_WAIT_US(1000),.TASK_TIMEOUT_US(2000000)) dut(
   .clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),.selection(selection),
   .mode(mode),.visualStart(visualStart),.debugStart(debugStart),.debugStop(debugStop),.modeChanged(modeChanged),.rawMode(rawMode),
   .injectLeaseValid(injectLeaseValid),.scanCalibrated(scanCalibrated),.scanBudgetUs(scanBudgetUs),.timeUs(timeUs),.tuningWord(tuningWord),.alignTimingWord(alignTimingWord),
   .cameraFifoFault(cameraFifoFault),.cameraAbandonEvent(cameraAbandonEvent),.status(status),
   .targetRequest(req),.targetRequestValid(qv),.targetRequestReady(qr),
   .targetReport(rpt),.targetReportValid(rv),.targetReportReady(rr),
   .distance_valid(distance_valid),.distanceSample(distanceSample),.distance_mm(distance_mm),
   .zeroSent(zeroSent),.uartBusy(uartBusy),.left_cm_s(l),.right_cm_s(r),
   .permit(permit),.used(used),.estop(estop),.sonar_stop(sonar_stop),.motionTargetValid(motionTargetValid),
   .motionState(state),.stop_reason(reason),.statusWords(statusWords));
 // Independent combinational probe checks the optimized runtime arithmetic
 // against full-width reference multiplication over every possible U.
 motion_fsm #(.RUNTIME_TUNING(1),.TURN_SIGN(TURN_SIGN)) timingProbe(
   .clk(clk),.reset(reset),.startPulse(1'b0),.cancel(1'b0),.taskActive(1'b0),.safetyHalt(1'b0),
   .sourceHealthyFresh(1'b0),.targetObserved(1'b0),.motionTargetValid(1'b0),.distance_valid(1'b0),
   .scanAllowed(1'b0),.zeroSent(1'b0),.motionApplied(1'b0),.timeUs(32'd0),.scanBudgetUs(32'd0),
   .tuningWord(32'h001e3544),.alignTimingWord(timingProbeWord),.centreU(timingProbeU),.distance_mm(12'd0),
   .left_cm_s(),.right_cm_s(),.state(),.acquireFencePulse(),.taskDone(),.scanElapsedUs(),.scanRemainingUs(),.failureReason());
 generate if(RUNTIME_TUNING)begin: runtimeMathWidth
   assign dutPulseMathWidth=$bits(dut.motion.runtimeAlignMath.scaledPulseUs);
 end else begin: legacyMathWidth
   assign dutPulseMathWidth=$bits(dut.motion.boundedAlignMath.scaledPulseUs);
 end endgenerate
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
     10:rpt.captureStartUs=dut.adapter.targetFenceUs;
     11:distance_mm=240; // Loss and near range arrive on this same sampling edge.
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
 function automatic string wheelJson(input int logicalL,input int logicalR);
   int wl,wr;string leftText,rightText;wl=-logicalL;wr=-logicalR;
   leftText=$sformatf("0.0%0d",wl<0?-wl:wl);rightText=$sformatf("0.0%0d",wr<0?-wr:wr);
   if(wl<0)leftText={"-",leftText};if(wr<0)rightText={"-",rightText};
   return {"{\"T\":1,\"L\":",leftText,",\"R\":",rightText,"}\n"};
 endfunction
 function automatic bit allowedRuntimeLine(input string line);
   for(int i=0;i<runtimeAllowedCount;i++)if(line==runtimeAllowed[i])return 1;
   return 0;
 endfunction
 task automatic allowRuntimeWheels(input int expectedL,input int expectedR);
   string expected;expected=wheelJson(expectedL,expectedR);
   if(!allowedRuntimeLine(expected))begin
     ck(runtimeAllowedCount<32,"bounded runtime UART expectation table");
     runtimeAllowed[runtimeAllowedCount]=expected;runtimeAllowedCount++;
   end
 endtask
 task automatic verifyRuntimeWheels(input int expectedL,input int expectedR,input string label);
   int first;bit found;string expected;
   ck(permit && l==expectedL && r==expectedR,label);
   first=lineCount;expected=wheelJson(expectedL,expectedR);tick(12000);found=0;
   for(int i=first;i<lineCount;i++)if(lines[i]==expected)found=1;
   if(!found)begin
     $display("RUNTIME UART expected=[%s] first=%0d end=%0d",expected,first,lineCount);
     for(int i=first;i<lineCount;i++)$display("RUNTIME UART actual=[%s]",lines[i]);
   end
   ck(found,"runtime command reaches a complete exact UART JSON line");
 endtask
 task automatic configureTuning(input int search,input int turn,input int drive,input int fine,input int tolerance);
   stopTask();wait(zeroSent && !uartBusy);
   @(negedge clk);tuningWord={10'd0,6'(tolerance),4'(fine),4'(drive),4'(turn),4'(search)};tick(3);
   ck(dut.motion.tuningValid,"valid runtime tuple accepted by controller datapath");
 endtask
 task automatic configureTiming(input int kickUnits,input int minUnits,input int maxUnits,input int kickSpeed);
   stopTask();wait(zeroSent && !uartBusy);
   @(negedge clk);alignTimingWord={14'd0,4'(kickSpeed),5'(maxUnits),5'(minUnits),4'(kickUnits)};tick(3);
   ck(dut.motion.alignTimingValid && dut.motion.tuningValid,"valid two-stage timing tuple accepted while stopped");
 endtask
 task automatic runtimeStart(input int u,input int mm,input int expectedL,input int expectedR,input string label);
   stopTask();wait(zeroSent && !uartBusy);distance_mm=12'(mm);samples();fresh(1,u);
   allowRuntimeWheels(expectedL,expectedR);arm();verifyRuntimeWheels(expectedL,expectedR,label);
 endtask
 task automatic pulseEnd(input int expectedUs,input int refreshU=-1);
   logic[31:0] began,taskStart,spent;
   int remainingUs;
   began=dut.motion.stateStartUs;taskStart=dut.motion.taskStartUs;spent=dut.scanElapsedUs;
   remainingUs=expectedUs-int'(timeUs-began)-1;
   while(refreshU>=0 && remainingUs>100000)begin
     tick(80000);send(1,refreshU);remainingUs=expectedUs-int'(timeUs-began)-1;
   end
   ck(remainingUs>0,"pulse boundary checked before expiry");
   tick(remainingUs);ck(permit && state==2,"turn remains permitted just before latched pulse limit");
   tick();stopped("pulse deadline gates logical wheels without waiting for next state edge");
   tick();ck(state==6 && dut.taskActive,"pulse expires into stationary acquisition without disarming");
   ck(dut.scanElapsedUs==spent && dut.motion.taskStartUs==taskStart,"ALIGN pulse does not replenish search or total-task time");
 endtask
 task automatic startMissedSighting(input int budget=1000000);
   stopTask();distance_valid=1;distance_mm=1000;samples();scanBudgetUs=budget;fresh();arm();
   ck(state==1 && !dut.motion.backtracking && dut.motion.backtrackSteps==0,"new task starts forward SEARCH with a fresh recovery allowance");
   tick(2500);send(1,80,0);
   ck(state==6 && dut.motion.backtrackAuthorized,"only a forward SEARCH sighting authorizes recovery");
   stopped("search sighting stops before stationary confirmation");send();
   wait(dut.motion.acquirePhase==2);tick(3);send();
   wait(dut.motion.backtracking);tick(2);
   ck(state==1 && permit && l==LOW_R && r==LOW_L && dut.motion.backtrackSteps==1,"missed stationary sighting starts first bounded reverse step");
 endtask
 task automatic reverseEnd;
   logic[31:0] began,spent,taskStart;int remainingUs,expectedBudgetUs;
   began=dut.motion.stateStartUs;spent=dut.scanElapsedUs;taskStart=dut.motion.taskStartUs;
   expectedBudgetUs=TEST_BACKTRACK_US-int'(timeUs-began);
   // A real camera keeps reporting during the 150 ms command. Refresh the
   // public NOT_FOUND report, rather than disabling its production age check.
   while(timeUs-began<TEST_BACKTRACK_US-40001)begin
     tick(35000);send();ck(dut.motion.backtracking && permit,"healthy reports cannot extend or prematurely end reverse pulse");
   end
   remainingUs=TEST_BACKTRACK_US-int'(timeUs-began)-1;ck(remainingUs>0,"reverse deadline checked before expiry");
   tick(remainingUs);ck(dut.motion.backtracking && permit,"reverse remains permitted immediately before 150 ms limit");
   tick();stopped("reverse expiry removes wheel request combinationally");tick();
   ck(state==6 && !dut.motion.backtracking && dut.motion.stationaryRecoveryRequired,"reverse always enters full stationary acquisition");
   ck(dut.scanElapsedUs-spent>=expectedBudgetUs-10 && dut.scanElapsedUs-spent<=expectedBudgetUs+2,
     "reverse logical motion consumes the original scan budget");
   ck(dut.motion.taskStartUs==taskStart,"reverse step cannot reset total-task wall time");
 endtask
 task automatic readLine;
   logic [7:0] ch;string line;line="";
   for(int n=0;n<29;n++)begin
     @(negedge tx);#40;
     for(int b=0;b<8;b++)begin #80;ch[b]=tx;end
     #80;if(tx!==1)$fatal(1,"UART stop bit");line={line,ch};
     if(ch==10)begin
       if(lineCount>=1024)$fatal(1,"UART capture capacity exceeded");
       lines[lineCount]=line;
       lineCount++;
       if(line=="{\"T\":1,\"L\":0.00,\"R\":0.00}\n")zeroLines++;
       else if(line==LOW_JSON)begin spinLines++;lowTurnLines++;end
       else if(line==HIGH_JSON)begin spinLines++;highTurnLines++;end
       else if(line==LOW_FINE_JSON)begin spinLines++;lowFineTurnLines++;end
       else if(line==HIGH_FINE_JSON)begin spinLines++;highFineTurnLines++;end
       else if(line==LOW_STEER_JSON)begin driveLines++;lowSteerLines++;end
       else if(line==HIGH_STEER_JSON)begin driveLines++;highSteerLines++;end
       else if(line==LOW_FINE_STEER_JSON)begin driveLines++;lowFineSteerLines++;end
       else if(line==HIGH_FINE_STEER_JSON)begin driveLines++;highFineSteerLines++;end
       else if(line=="{\"T\":1,\"L\":-0.05,\"R\":-0.05}\n")driveLines++;
       else if(line=="{\"T\":1,\"L\":-0.03,\"R\":-0.03}\n")begin driveLines++;fineLines++;end
       else if(RUNTIME_TUNING && allowedRuntimeLine(line))runtimeLines++;
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
   ck(TURN_SIGN==1 || TURN_SIGN==-1,"test convention is explicit");
   scanBudgetUs=500000;
   arm();ck(state==1 && permit && l==LOW_L && r==LOW_R,"healthy no target searches in selected turn convention");
   tick(2600);ck(lowTurnLines>0 && highTurnLines==0,"SEARCH emits exact L/R UART JSON in selected convention");
   tick(50000);send();tick(50000);send();
   ck(state==1 && permit && dut.scanElapsedUs>100000 && l==LOW_L && r==LOW_R,"SEARCH remains continuous 4 cm/s beyond ALIGN maximum pulse");
   begin logic[31:0] spent;spent=dut.scanElapsedUs;arm();ck(dut.scanElapsedUs>=spent,"repeated ARM cannot reset budget");end
   send(1,80,0);stopped("single observed frame stops scan before lock");ck(state==6,"ACQUIRE entered");
   fresh(1,80);stopped("pre-settle frames cannot restart movement");
   begin int beforeLow;logic[31:0] pulseStart,taskStart;beforeLow=lowTurnLines;
     acquired(30);ck(state==2 && permit && l==LOW_L && r==LOW_R,"post-fence far low-U alignment uses selected convention");
     ck(dut.motion.alignPulseUs==100000,"far error pulse is clamped to 100 ms");
     pulseStart=dut.motion.stateStartUs;taskStart=dut.motion.taskStartUs;
     tick(4000);ck(lowTurnLines>beforeLow,"low-U ALIGN emits exact complete UART JSON");
     send(1,STRICT_ALIGN_BAND?90:89);ck(l==LOW_L && r==LOW_R && dut.motion.alignPulseUs==100000 && dut.motion.stateStartUs==pulseStart,
       "same-side fresh U cannot alter latched speed, width or pulse origin");
     pulseEnd(100000);
     // E10 far in-corridor locks now enter forward steering. Exercise the
     // retained pivot widths at a safe docking distance, without forward motion.
     distance_mm=350;
     wait(dut.motion.acquirePhase==1);tick(2);
     ck(zeroSent && uartBusy==0,"post-pulse dwell begins only after actual zero JSON completion");
     fresh(1,89);stopped("frames during stationary dwell cannot restart a pulse");
     ck(dut.motion.acquirePhase==1,"scaled dwell is not skipped by early good reports");
     wait(dut.motion.acquirePhase==2);tick(3);
     ck(timeUs-dut.motion.settleStartUs>=TEST_SETTLE_US,"new target fence follows full zero-confirmed dwell");
     send(1,89,1,10);stopped("capture at the new fence cannot count toward reacquisition");
     send(1,89);stopped("one post-fence frame cannot restart");
     send(1,89);stopped("two post-fence frames cannot restart");
     send(1,89);ck(state==2 && permit && l==LOW_L && r==LOW_R,"third new frame starts error31 coarse turn");
     ck(dut.motion.alignPulseUs==62000 && dut.motion.taskStartUs==taskStart,"fresh pulse width uses new error without resetting task lifetime");
     send(1,STRICT_ALIGN_BAND?90:89);ck(l==LOW_L && r==LOW_R && dut.motion.alignPulseUs==62000,"same-side update cannot change current coarse pulse");
   end
   begin int beforeHigh;beforeHigh=highTurnLines;
     send(1,160);stopped("crossing to high-U stops instead of reversing current pulse");ck(state==6,"opposite side requires ACQUIRE");
     acquired(160);ck(l==LOW_R && r==LOW_L,"fresh stationary high-U lock chooses opposite coarse turn");
     tick(4000);ck(highTurnLines>beforeHigh,"high-U ALIGN emits opposite complete UART JSON");
   end
   // Fine pivot is unreachable inside the widened production centre band.
   // Retain its exact UART/width assertions for the explicit legacy band run.
   if(STRICT_ALIGN_BAND)begin int beforeFine;beforeFine=lowFineTurnLines;
     send(1,90);stopped("reverse into fine zone also requires a complete stop");acquired(90);
     ck(l==LOW_FINE_L && r==LOW_FINE_R && dut.motion.alignPulseUs==60000,"error30 selects latched 3 cm/s and 60 ms");
     tick(4000);ck(lowFineTurnLines>beforeFine,"fine low-U turn emits exact opposite-sign 0.03 JSON");
     beforeFine=highFineTurnLines;send(1,150);stopped("fine pulse never directly reverses");acquired(150);
     ck(l==LOW_FINE_R && r==LOW_FINE_L && dut.motion.alignPulseUs==60000,"error30 high side uses 3 cm/s");
     tick(4000);ck(highFineTurnLines>beforeFine,"fine high-U turn emits exact opposite-sign 0.03 JSON");
   end
   send(1,NEAR_LOW);stopped("near low target first stops old high-side pulse");acquired(NEAR_LOW);
   ck(state==2 && l==NEAR_L && r==NEAR_R && dut.motion.alignPulseUs==NEAR_PULSE_US,"outside centre band selects the corresponding latched pivot width and speed");
   pulseEnd(NEAR_PULSE_US);acquired(NEAR_LOW);
   send(1,TEST_ALIGN_LOW);tick(3);stopped("reaching centre during a turn cannot immediately translate");ck(state==6,"turn-to-centre waits for stationary fresh lock");
   distance_mm=1000;
   acquired(TEST_ALIGN_LOW);ck(state==3 && l==5 && r==5,"stationary lower inclusive centre permits unchanged forward signs");
   send(1,TEST_ALIGN_HIGH);tick(3);ck(state==3 && l==5 && r==5,"upper inclusive centre limit keeps forward signs");
   begin int beforeLine;logic[31:0] taskStart,spent;
     taskStart=dut.motion.taskStartUs;spent=dut.scanElapsedUs;
     beforeLine=highSteerLines;send(1,NEAR_HIGH);tick(3);
     ck(state==3 && permit && l==LOW_STEER_R && r==LOW_STEER_L,"one pixel above centre stays APPROACH with positive high-side 5/3 steering");
     tick(4000);ck(highSteerLines>beforeLine,"high-side forward steering emits complete 5/3 JSON");
     beforeLine=lowSteerLines;send(1,NEAR_LOW);tick(3);
     ck(state==3 && permit && l==LOW_STEER_L && r==LOW_STEER_R,"one pixel below centre stays APPROACH with positive low-side 5/3 steering");
     tick(4000);ck(lowSteerLines>beforeLine,"low-side forward steering emits complete 5/3 JSON");
     send(1,75);ck(state==3 && l==LOW_STEER_L && r==LOW_STEER_R,"U75 inclusive error45 keeps forward steering");
     send(1,165);ck(state==3 && l==LOW_STEER_R && r==LOW_STEER_L,"U165 inclusive error45 keeps forward steering");
     repeat(3)begin tick(35000);send(1,80);ck(state==3 && permit && l>0 && r>0,"small-error APPROACH remains continuous beyond 100 ms ALIGN limit");end
     ck(dut.motion.taskStartUs==taskStart && dut.scanElapsedUs==spent,"forward steering does not reset task or consume SEARCH budget");
     distance_mm=501;send(1,80);ck(l==LOW_STEER_L && r==LOW_STEER_R,"501 mm retains coarse 5/3 steering");
     beforeLine=lowFineSteerLines;distance_mm=500;tick();
     ck(state==3 && l==LOW_FINE_STEER_L && r==LOW_FINE_STEER_R,"500 mm inclusive chooses fine low-side 4/3 steering");
     tick(4000);ck(lowFineSteerLines>beforeLine,"fine low-side steering emits complete 4/3 JSON");
     beforeLine=highFineSteerLines;send(1,160);tick(3);
     ck(state==3 && l==LOW_FINE_STEER_R && r==LOW_FINE_STEER_L,"fine high-side steering keeps both wheels forward");
     tick(4000);ck(highFineSteerLines>beforeLine,"fine high-side steering emits complete 4/3 JSON");
     send(1,TEST_ALIGN_LOW);ck(state==3 && l==3 && r==3,"fine lower centre endpoint remains straight 3/3");
     send(1,TEST_ALIGN_HIGH);ck(state==3 && l==3 && r==3,"fine upper centre endpoint remains straight 3/3");
   end
   distance_mm=1000;send(1,80);ck(state==3 && l==LOW_STEER_L && r==LOW_STEER_R,"forward steering active before target loss");
   send();stopped("healthy NOT_FOUND immediately removes forward steering");
   ck(state==5 && dut.sourceHealthyFresh && !motionTargetValid,"target loss retains source health but enters LOST");
   begin logic[31:0] originalTask,spent;int beforeSpin;
     originalTask=dut.motion.taskStartUs;spent=dut.scanElapsedUs;beforeSpin=spinLines;
     tick(1100);ck(state==6 && dut.motion.stationaryRecoveryRequired,
       "continued NOT_FOUND past LOST wait enters stationary acquisition, never immediate SEARCH");
     stopped("lost target remains zero while waiting for UART completion");
     wait(dut.motion.acquirePhase==1);tick(2);fresh(1,120);
     stopped("target returning before stationary dwell cannot resume motion");
     ck(dut.motion.acquirePhase==1,"returning target does not shorten loss recovery dwell");
     wait(dut.motion.acquirePhase==2);tick(3);
     send(1,120,1,10);stopped("capture at loss-recovery fence cannot qualify");
     send(1);stopped("first fresh target after loss fence stays stopped");
     send(1);stopped("second fresh target after loss fence stays stopped");send(1);tick(3);
     ck(state==3 && permit && l==5 && r==5 && !dut.motion.stationaryRecoveryRequired,
       "third new frame resumes approach without a search pulse");
     ck(dut.motion.taskStartUs==originalTask && dut.scanElapsedUs==spent && spinLines==beforeSpin,
       "stationary loss recovery neither turns nor refunds task/search budget");
   end
   send(1,80);ck(state==3 && l==LOW_STEER_L && r==LOW_STEER_R,"forward steering active before bad-frame loss");
   send(0,120,0,7);stopped("bad-frame health failure immediately removes forward steering");
   ck(state==5 && !dut.sourceHealthyFresh,"source health failure cannot keep differential motion");
   tick(1100+TEST_SETTLE_US);ck(state==6 && dut.motion.acquirePhase==0 && dut.motion.stationaryRecoveryRequired,
     "unhealthy loss cannot consume stationary recovery dwell");
   fresh();wait(dut.motion.acquirePhase==1);tick(2);stopped("healthy NOT_FOUND starts a full stationary dwell");
   acquired(120);
   send(0,120,0,11);ck(state==7 && dut.motion.stationaryRecoveryRequired,
     "simultaneous near-range HOLD and target loss retains recovery obligation");
   stopped("simultaneous obstacle and target loss remains zero");
   distance_mm=1000;samples();tick(3);
   ck(state==6 && dut.motion.stationaryRecoveryRequired && !dut.targetObserved,
     "HOLD release with no target cannot bypass stationary reacquisition");
   acquired(120);
   send();tick(1100);wait(dut.motion.acquirePhase==2);tick(20003);
   ck(state==1 && permit && !dut.motion.backtracking && !dut.motion.backtrackAuthorized &&
      !dut.motion.stationaryRecoveryRequired && dut.motion.backtrackSteps==0,
      "continued absence resumes ordinary SEARCH only after full stationary confirmation timeout");
   stopTask();fresh(1);arm();send();stopTask();fresh(1);tick(3000);
   ck(!dut.taskActive && !dut.motion.stationaryRecoveryRequired,"STOP cancels pending loss recovery without auto-restart");
   arm();tick(3);
   // Leaving the steering corridor requires zero completion, dwell and fresh
   // confirmation before the existing pivot pulse; it cannot reverse in place.
   send(1,166);tick(3);stopped("U166 outside error45 stops forward steering");
   ck(state==6,"U166 outside corridor requires stationary acquisition");acquired(166);
   ck(state==2 && l==LOW_R && r==LOW_L && dut.motion.alignPulseUs==92000,"U166 outside error45 returns to latched high-side ALIGN");
   send(1,120);stopped("large-error ALIGN still stops on crossing into centre");acquired(120);
   send(1,74);tick(3);stopped("U74 outside error45 stops forward steering");
   ck(state==6,"U74 outside corridor requires stationary acquisition");acquired(74);
   ck(state==2 && l==LOW_L && r==LOW_R && dut.motion.alignPulseUs==92000,"U74 outside error45 returns to latched low-side ALIGN");
   send(1,120);stopped("opposite large-error ALIGN also reacquires before forward");acquired(120);
   distance_mm=351;send(1,NEAR_HIGH);
   ck(state==3 && l==LOW_FINE_STEER_R && r==LOW_FINE_STEER_L,"351 mm off-centre may still steer forward");
   @(negedge clk);distance_mm=350;#1;stopped("350 mm off-centre cuts forward combinationally before state edge");
   tick(3);ck(state==6,"350 mm off-centre stops into ACQUIRE, never DOCKED");stopped("off-centre dock distance remains stationary pending fresh confirmation");
   acquired(NEAR_HIGH);ck(state==2 && l==NEAR_R && r==NEAR_L && dut.motion.alignPulseUs==NEAR_PULSE_US,"350 mm fresh off-centre lock chooses pivot instead of forward or DOCKED");
   ck(!(l>0 && r>0),"350 mm off-centre cannot command both wheels forward");
   send(1,120);stopped("350 mm turning-to-centre first stops and reacquires");acquired(120);
   ck(state==4 && !dut.taskActive,"350 mm newly confirmed centred target DOCKED");stopped("centred docking remains zero");
   distance_mm=1000;samples();fresh(1);arm();tick(3);
   ck(state==3 && l==5 && r==5,"stationary centred target approaches");tick(4000);ck(driveLines>0,"approach reaches UART");
   distance_mm=450;tick();ck(l==3 && r==3,"fine approach speed");tick(4000);ck(fineLines>0,"fine straight UART remains -0.03/-0.03");
   send(1,160);ck(state==3 && l==LOW_FINE_STEER_R && r==LOW_FINE_STEER_L,"fine forward steering active before explicit STOP");
   begin int beforeZero;beforeZero=zeroLines;
     stopTask();stopped("explicit STOP still clears corrected direction requests");tick(4000);
     ck(zeroSent && zeroLines>beforeZero && !dut.taskActive,"STOP completes exact zero UART and remains unarmed");
   end
   fresh(1);arm();tick(3);ck(state==3 && l==3 && r==3,"new explicit task retains corrected steering and unchanged forward speed");
   distance_mm=350;tick(4);ck(state==4 && !dut.taskActive,"DOCKED disarms");stopped("DOCKED zero");
   distance_valid=0;tick(3);distance_valid=1;distance_mm=1000;samples();fresh(1);tick(3);ck(state==4 && !dut.taskActive,"sonar recovery cannot restart DOCKED");
   arm();tick(3);ck(dut.taskActive,"new task after DOCKED without reset");
   @(negedge clk);selection=2;#1;stopped("selection mismatch cancels immediately");tick(15);fresh(1);stopped("new selection requires new ARM");
   arm();send(1,80);ck(permit && state==3 && l==LOW_STEER_L && r==LOW_STEER_R,"new selected task reaches forward steering");
   injectLeaseValid=0;#1;stopped("lease expiry directly stops");tick(3);injectLeaseValid=1;fresh(1);stopped("lease renewal cannot rearm");
   arm();send(1,160);ck(state==3 && l==LOW_STEER_R && r==LOW_STEER_L,"fresh task can steer opposite side before IR");
   estop_frame=1;#1;stopped("IR dominates forward steering");tick();estop_frame=0;tick(2);ck(estop,"IR latch retained");
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

   // E10 explicitly accepts the wider straight/docking band. The unchanged
   // outer steering corridor can also be entered from a freshly locked START;
   // this replaces E9's mandatory far-target pivot, without changing pixels.
   scanBudgetUs=1000000;
   for(int entryCase=0;entryCase<8;entryCase++)begin
     int u;
     case(entryCase)
       0:u=TEST_ALIGN_LOW;1:u=TEST_ALIGN_HIGH;2:u=NEAR_LOW;3:u=NEAR_HIGH;
       4:u=75;5:u=165;6:u=74;default:u=166;
     endcase
     stopTask();distance_mm=1000;samples();fresh(1,u);arm();
     if(entryCase<6)begin
       ck(state==3 && permit,"fresh locked START in the corridor enters APPROACH directly");
       if(entryCase<2)ck(l==5 && r==5,"both inclusive centre endpoints start straight without pivot");
       else if(entryCase==2 || entryCase==4)ck(l==LOW_STEER_L && r==LOW_STEER_R,"low-side entry requests exact positive 5/3 steering");
       else ck(l==LOW_STEER_R && r==LOW_STEER_L,"high-side entry requests exact positive 3/5 steering");
     end else begin
       ck(state==2 && permit,"fresh START just outside the corridor retains latched pivot");
       if(entryCase==6)ck(l==LOW_L && r==LOW_R,"U74 START pivots in the selected convention");
       else ck(l==LOW_R && r==LOW_L,"U166 START pivots opposite the selected convention");
     end
     tick(2500);stopTask();stopped("entry boundary task remains explicitly cancellable");
   end
   // Reacquisition may take the same direct path only after the complete
   // stationary fence. One or two new reports still cannot move the vehicle.
   for(int entrySide=0;entrySide<2;entrySide++)begin
     int u;u=entrySide==0?75:165;
     fresh();arm();send(1,u,0);ck(state==6,"SEARCH sighting still stops into ACQUIRE");
     fresh(1,u);stopped("pre-dwell corridor reports cannot bypass stationary confirmation");
     wait(dut.motion.acquirePhase==2);tick(3);
     send(1,u);stopped("direct-entry reacquisition still needs more than one new frame");
     send(1,u);stopped("direct-entry reacquisition still needs more than two new frames");
     send(1,u);ck(state==3 && permit && !dut.motion.backtrackAuthorized && dut.motion.backtrackSteps==0,
       "third post-fence corridor frame enters forward approach and clears reverse authority");
     if(entrySide==0)ck(l==LOW_STEER_L && r==LOW_STEER_R,"low corridor ACQUIRE exit requests exact forward steering");
     else ck(l==LOW_STEER_R && r==LOW_STEER_L,"high corridor ACQUIRE exit requests exact forward steering");
     tick(2500);stopTask();
   end
   // At 351 mm forward is allowed; at 350 mm the same centre band docks,
   // while one pixel outside it must pivot without any forward entry.
   for(int nearCase=0;nearCase<8;nearCase++)begin
     int u;
     case(nearCase%4)
       0:u=TEST_ALIGN_LOW;1:u=TEST_ALIGN_HIGH;2:u=NEAR_LOW;default:u=NEAR_HIGH;
     endcase
     distance_mm=nearCase<4?351:350;fresh(1,u);arm();
     if(nearCase<4)begin
       ck(state==3 && permit,"351 mm locked corridor target can directly approach");
       if(nearCase<2)ck(l==3 && r==3,"351 mm inclusive centre enters straight 3/3");
       else if(nearCase==2)ck(l==LOW_FINE_STEER_L && r==LOW_FINE_STEER_R,"351 mm low-side entry uses exact 4/3");
       else ck(l==LOW_FINE_STEER_R && r==LOW_FINE_STEER_L,"351 mm high-side entry uses exact 3/4");
     end else if(nearCase<6)begin
       ck(state==4 && !dut.taskActive,"350 mm either centre endpoint is accepted as DOCKED");
       stopped("direct docking never requests forward motion");
     end else begin
       ck(state==2 && permit && !(l>0 && r>0),"350 mm off-centre entry pivots without forward or DOCKED");
       if(nearCase==6)ck(l==NEAR_L && r==NEAR_R,"350 mm low-side pivot respects current centre tolerance");
       else ck(l==NEAR_R && r==NEAR_L,"350 mm high-side pivot respects current centre tolerance");
     end
     tick(2500);stopTask();
   end
   ck(dutPulseMathWidth==(RUNTIME_TUNING?19:17),"runtime and legacy pulse arithmetic retain bounded narrow widths");
   if(!STRICT_ALIGN_BAND)ck(lowFineTurnLines==0 && highFineTurnLines==0,"expanded production centre band does not invent fine pivots within tolerance");

   // Ordinary approach/alignment acquisition must never invent a SEARCH
   // sighting. This also protects E8's already-passing visible-target path.
   stopTask();scanBudgetUs=1000000;distance_mm=1000;fresh(1);arm();send(1,166);send();
   ck(state==6 && !dut.motion.backtrackAuthorized,"APPROACH-to-ACQUIRE grants no reverse authority");
   wait(dut.motion.acquirePhase==2);tick(20003);
   ck(state==1 && !dut.motion.backtracking && dut.motion.backtrackSteps==0,"ordinary acquisition timeout returns only to forward search");
   // Three reversals at most for the entire task, even if another forward
   // sighting later arrives. Each retry has its own zero/dwell/fresh boundary.
   startMissedSighting();
   begin int beforeReverse;logic[31:0] originalTask;beforeReverse=highTurnLines;originalTask=dut.motion.taskStartUs;
     tick(2500);ck(highTurnLines>beforeReverse,"reverse SEARCH emits the exact complete opposite 4 cm/s UART JSON");
     for(int step=1;step<=3;step++)begin
       reverseEnd();wait(dut.motion.acquirePhase==1);tick(2);
       ck(zeroSent && uartBusy==0,"each reverse retry waits for complete zero UART before dwell");
       wait(dut.motion.acquirePhase==2);tick(3);send();
       ck(timeUs-dut.motion.settleStartUs>=TEST_SETTLE_US,"each reverse retry establishes a post-dwell target fence");
       tick(20003);
       ck(dut.motion.taskStartUs==originalTask,"retries preserve the original task deadline");
       if(step<3)ck(dut.motion.backtracking && dut.motion.backtrackSteps==step+1,"failed fresh confirmation advances bounded reverse count");
       else ck(state==1 && !dut.motion.backtracking && !dut.motion.backtrackAuthorized && dut.motion.backtrackSteps==3,
         "third failed recovery resumes original direction without replenishing attempts");
     end
     ck(l==LOW_L && r==LOW_R && dut.scanElapsedUs>3*TEST_BACKTRACK_US-20,"forward search resumes with reverse time already charged");
     send(1,80,0);send();wait(dut.motion.acquirePhase==2);tick(20003);
     ck(!dut.motion.backtracking && dut.motion.backtrackSteps==3 && l==LOW_L && r==LOW_R,"later forward sighting cannot create a fourth reverse step");
   end
   // A new observation while reversing stops immediately; only three new
   // post-fence observations can unlock ALIGN/APPROACH again.
   startMissedSighting();send(1,120,0);stopped("reverse sighting immediately stops without rearming recovery");
   ck(state==6 && dut.motion.backtrackSteps==1,"reverse sighting does not refill the attempt count");
   fresh(1);stopped("pre-settle reports after reverse cannot directly move forward");
   wait(dut.motion.acquirePhase==2);tick(3);send(1);stopped("reverse recovery first post-fence target stays stopped");
   send(1);stopped("reverse recovery second post-fence target stays stopped");send(1);tick(4);
   ck(state==3 && permit && l==5 && r==5 && !dut.motion.backtrackAuthorized && !dut.motion.stationaryRecoveryRequired && dut.motion.backtrackSteps==1,
     "third new target completes recovery and clears authority without refunding attempts");
   // A short remaining scan allowance truncates a reverse pulse before its
   // nominal duration and finishes through the existing final ACQUIRE.
   startMissedSighting(3500);
   begin logic[31:0] began;began=dut.motion.stateStartUs;
     wait(!dut.motion.backtracking);tick(2);stopped("remaining-budget exhaustion immediately stops reverse");
     ck(state==6 && dut.motion.finalAcquire && dut.scanElapsedUs==3500 && timeUs-began<TEST_BACKTRACK_US,
       "reverse cannot exceed a shorter remaining total budget");
     wait(dut.motion.acquirePhase==2);tick(20003);
     ck(state==8 && !dut.taskActive && dut.failureReason==1,"reverse budget exhaustion reaches bounded NOT_FOUND");fresh(1);stopped("late target cannot revive budget-exhausted reverse task");
   end
   // Source interruption revokes authority, retains the spent attempt, and
   // cannot fall through LOST directly into forward motion before full dwell.
   startMissedSighting();tick(2500);send(0,120,0,7);stopped("source failure immediately cancels reverse output");
   ck(state==6 && !dut.motion.backtrackAuthorized && dut.motion.stationaryRecoveryRequired && dut.motion.backtrackSteps==1,
     "source interruption retains required stationary recovery and spent count");
   tick(TEST_SETTLE_US+1000);ck(dut.motion.acquirePhase==0,"unhealthy source cannot consume the recovery dwell");
   fresh();wait(dut.motion.acquirePhase==1);tick(2);stopped("restored source begins a full zero-confirmed dwell");
   wait(dut.motion.acquirePhase==2);tick(3);send();tick(20003);
   ck(state==1 && !dut.motion.backtracking && dut.motion.backtrackSteps==1 && l==LOW_L && r==LOW_R,
     "source recovery resumes forward only after full stationary confirmation, with no refund");
   // Near/invalid protection must not bypass that same stationary recovery.
   startMissedSighting();tick(2500);distance_mm=200;#1;stopped("hazard immediately stops reverse");tick(3);
   begin logic[31:0] spent;spent=dut.scanElapsedUs;tick(5000);
     ck(state==7 && !dut.motion.backtrackAuthorized && dut.motion.stationaryRecoveryRequired && dut.motion.backtrackSteps==1 && dut.scanElapsedUs==spent,
       "HOLD keeps reverse authority revoked, count spent and scan time paused");
   end
   distance_mm=1000;samples();tick(3);ck(state==6 && dut.motion.stationaryRecoveryRequired,"HOLD recovery cannot jump directly from reverse to forward SEARCH");
   wait(dut.motion.acquirePhase==2);tick(3);send();tick(20003);
   ck(state==1 && !dut.motion.backtracking && dut.motion.backtrackSteps==1 && l==LOW_L && r==LOW_R,"HOLD recovery completes stationary confirmation without refund");
   send(1,80,0);send();wait(dut.motion.acquirePhase==2);tick(3);send();wait(dut.motion.backtracking);tick(2);
   ck(dut.motion.backtrackSteps==2,"a later valid sighting uses the second attempt after interrupted first step");
   // Existing cancellation sources must also discard a live reverse grant.
   for(int cancelCase=0;cancelCase<7;cancelCase++)begin
     startMissedSighting();
     case(cancelCase)
       0:stopTask();
       1:begin estop_frame=1;tick();estop_frame=0;tick(2);power_frame=1;tick();power_frame=0;tick(3);end
       2:begin selection=selection==1?6'd2:6'd1;tick(15);end
       3:begin switchMode(1);switchMode(2);end
       4:begin rawMode=1;tick(3);rawMode=0;tick(3);end
       5:begin injectLeaseValid=0;tick(3);injectLeaseValid=1;tick(3);end
       6:begin reset=1;tick(3);reset=0;tick(20);samples();end
     endcase
     fresh();tick(2500);stopped("cancellation and safe restoration cannot resurrect a reverse task");
     ck(!dut.taskActive && !dut.motion.backtracking && !dut.motion.backtrackAuthorized && !dut.motion.stationaryRecoveryRequired && dut.motion.backtrackSteps==0 && zeroSent,
       "STOP/IR/selection/mode/raw/lease/reset discard reverse authority and complete zero");
   end
   if(RUNTIME_TUNING && !STRICT_ALIGN_BAND)begin
     // Datapath tests deliberately drive the register input directly. CCTL's
     // VISION_ONLY/write validation is independently tested at that endpoint.
     configureTuning(3,5,8,4,40);distance_mm=1000;samples();scanBudgetUs=1000000;fresh();
     allowRuntimeWheels(-3*TURN_SIGN,3*TURN_SIGN);allowRuntimeWheels(3*TURN_SIGN,-3*TURN_SIGN);
     arm();verifyRuntimeWheels(-3*TURN_SIGN,3*TURN_SIGN,"runtime SEARCH uses search3 independently of turn5");
     send(1,80,0);send();wait(dut.motion.acquirePhase==2);tick(20003);
     ck(dut.motion.backtracking && dut.motion.backtrackSteps==1,"runtime search still grants only bounded missed-sighting recovery");
     verifyRuntimeWheels(3*TURN_SIGN,-3*TURN_SIGN,"runtime reverse uses the same search3 magnitude");
     runtimeStart(80,1000,8,8,"runtime tolerance40 lower boundary permits drive8 straight");
     runtimeStart(160,1000,8,8,"runtime tolerance40 upper boundary permits drive8 straight");
     runtimeStart(120,500,4,4,"runtime fine4 applies at inclusive500 mm");
     runtimeStart(120,501,8,8,"runtime drive8 applies above500 mm");
     runtimeStart(79,1000,TURN_SIGN==-1?8:4,TURN_SIGN==-1?4:8,"runtime far low correction uses drive8/fine4");
     runtimeStart(161,1000,TURN_SIGN==-1?4:8,TURN_SIGN==-1?8:4,"runtime far high correction uses fine4/drive8");
     runtimeStart(75,500,TURN_SIGN==-1?5:4,TURN_SIGN==-1?4:5,"runtime near low correction retains U75 corridor and fine+1");
     runtimeStart(165,500,TURN_SIGN==-1?4:5,TURN_SIGN==-1?5:4,"runtime near high correction retains U165 corridor and fine+1");
     runtimeStart(74,1000,-5*TURN_SIGN,5*TURN_SIGN,"runtime U74 remains outside corridor and uses turn5");
     runtimeStart(166,1000,5*TURN_SIGN,-5*TURN_SIGN,"runtime U166 remains outside corridor and uses turn5");
     stopTask();wait(zeroSent && !uartBusy);distance_mm=350;samples();fresh(1,80);arm();tick(4);
     ck(state==4 && !dut.taskActive,"runtime tolerance40 lower endpoint docks at350 mm");
     configureTuning(5,3,4,3,10);distance_mm=1000;samples();fresh();
     allowRuntimeWheels(-5*TURN_SIGN,5*TURN_SIGN);arm();
     verifyRuntimeWheels(-5*TURN_SIGN,5*TURN_SIGN,"runtime SEARCH upper bound5 is independent of turn3");
     runtimeStart(74,1000,-3*TURN_SIGN,3*TURN_SIGN,"runtime coarse ALIGN lower speed bound3");
     runtimeStart(110,1000,4,4,"runtime tolerance10 lower endpoint uses drive4");
     runtimeStart(130,1000,4,4,"runtime tolerance10 upper endpoint uses drive4");
     runtimeStart(109,1000,TURN_SIGN==-1?4:3,TURN_SIGN==-1?3:4,"runtime outside lower tolerance steers with drive4/fine3");
     runtimeStart(131,1000,TURN_SIGN==-1?3:4,TURN_SIGN==-1?4:3,"runtime outside upper tolerance steers with fine3/drive4");
     configureTuning(5,5,4,3,10);
     runtimeStart(109,350,-3*TURN_SIGN,3*TURN_SIGN,"runtime near-target fine ALIGN remains3 despite coarse turn5");
     runtimeStart(131,350,3*TURN_SIGN,-3*TURN_SIGN,"runtime high-side fine ALIGN retains3 and corrected sign");
     stopTask();wait(zeroSent && !uartBusy);distance_mm=350;samples();fresh(1,130);arm();tick(4);
     ck(state==4 && !dut.taskActive,"runtime tolerance10 upper endpoint docks at350 mm");
     // Even if a writer bypassed CCTL, no malformed tuple can reach the wheels.
     configureTuning(4,4,5,3,30);distance_mm=1000;samples();fresh();arm();
     begin logic[31:0] invalidWord,spent;
       for(int invalidCase=0;invalidCase<12;invalidCase++)begin
         invalidWord=32'h001e3544;
         case(invalidCase)
           0:invalidWord[3:0]=2;1:invalidWord[3:0]=6;
           2:invalidWord[7:4]=2;3:invalidWord[7:4]=6;
           4:invalidWord[11:8]=3;5:invalidWord[11:8]=9;
           6:invalidWord[15:12]=2;7:invalidWord[15:12]=5;
           8:invalidWord[21:16]=9;9:invalidWord[21:16]=41;
           10:invalidWord[15:8]=8'h44;
           11:invalidWord[22]=1;
         endcase
         @(negedge clk);tuningWord=invalidWord;#1;stopped("malformed runtime word gates SEARCH combinationally");
         tick(2);spent=dut.scanElapsedUs;tick(3);
         ck(!dut.motion.tuningValid && dut.scanElapsedUs==spent,"invalid word neither permits nor charges scan motion");
       end
     end
     configureTuning(4,4,5,3,30);fresh(1);arm();
     @(negedge clk);tuningWord=0;#1;stopped("invalid word also gates live APPROACH");
     configureTuning(4,4,5,3,30);fresh(1,30);arm();
     @(negedge clk);tuningWord=0;#1;stopped("invalid word also gates latched ALIGN speed");
     configureTuning(4,4,5,3,30);stopped("restoring tuning while stopped cannot ARM");

     // The default profile must preserve E11 for all 256 input U values;
     // other profiles exercise the full 300 ms cap and minimum clamp.
     for(int profile=0;profile<3;profile++)begin
       int minUs,maxUs;
       case(profile)
         0:begin timingProbeWord=32'h00015420;minUs=20000;maxUs=100000;end
         1:begin timingProbeWord={14'd0,4'd8,5'd30,5'd2,4'd10};minUs=20000;maxUs=300000;end
         2:begin timingProbeWord={14'd0,4'd3,5'd30,5'd30,4'd1};minUs=300000;maxUs=300000;end
       endcase
       for(int u=0;u<256;u++)begin
         int expectedPulse;
         @(negedge clk);timingProbeU=8'(u);#1;
         expectedPulse=(u<120?120-u:u-120)*2000;
         if(expectedPulse<minUs)expectedPulse=minUs;
         if(expectedPulse>maxUs)expectedPulse=maxUs;
         if(u>=90 && u<=150)expectedPulse=0;
         ck(timingProbe.nextAlignPulseUs==32'(expectedPulse),"runtime pulse arithmetic matches full-width reference over every U");
       end
     end

     // A real complete kick JSON must precede a complete lower-speed JSON,
     // with direction, speed and total time latched for this one pulse.
     configureTuning(3,4,5,3,30);configureTiming(2,10,20,8);
     runtimeStart(30,1000,-8*TURN_SIGN,8*TURN_SIGN,"20 ms kick uses independent upper speed bound8");
     begin logic[31:0] began;int untilKickEnd;
       began=dut.motion.stateStartUs;
       ck(dut.motion.alignPulseUs==180000 && dut.motion.alignKickUs==20000,"2 ms per pixel selects180 ms total and20 ms kick");
       @(negedge clk);alignTimingWord=32'h00015420;tuningWord[7:4]=3;tick(3);
       ck(dut.motion.alignPulseUs==180000 && dut.motion.alignKickUs==20000 && dut.motion.alignSpeed==4*TURN_SIGN && dut.motion.alignKickSpeed==8*TURN_SIGN,
         "valid input changes cannot alter any in-flight phase latch");
       untilKickEnd=20000-int'(timeUs-began)-1;ck(untilKickEnd>0,"kick deadline checked before phase boundary");
       tick(untilKickEnd);ck(l==-8*TURN_SIGN && r==8*TURN_SIGN,"kick stays active immediately before its deadline");
       tick();ck(l==-4*TURN_SIGN && r==4*TURN_SIGN && state==2,"kick deadline changes directly to latched cruise without reversing or restarting");
       verifyRuntimeWheels(-4*TURN_SIGN,4*TURN_SIGN,"complete cruise4 UART follows complete kick8 UART");
       pulseEnd(180000,30);
       tick(2500);ck(zeroSent && state==6,"two-stage turn completes zero UART and stays in acquisition");
     end
     configureTuning(3,4,5,3,30);configureTiming(0,30,30,3);
     runtimeStart(210,1000,4*TURN_SIGN,-4*TURN_SIGN,"disabled kick begins directly with high-side cruise4");
     ck(dut.motion.alignPulseUs==300000 && dut.motion.alignKickUs==0,"maximum total300 ms and disabled kick are exact");
     pulseEnd(300000,210);
     configureTiming(10,2,2,5);
     runtimeStart(210,1000,5*TURN_SIGN,-5*TURN_SIGN,"high-side kick uses its own signed speed");
     ck(dut.motion.alignPulseUs==20000 && dut.motion.alignKickUs==20000,"100 ms requested kick truncates to20 ms total");
     pulseEnd(20000);

     // Every stop condition must interrupt both the kick and cruise phases.
     // Each restoration remains disarmed and zero; no old kick is replayed.
     for(int phase=0;phase<2;phase++)begin
       for(int kill=0;kill<7;kill++)begin
         configureTiming(2,10,20,5);
         runtimeStart(30,1000,-5*TURN_SIGN,5*TURN_SIGN,"fresh two-stage turn starts with bounded kick5");
         if(phase==1)begin
           tick(20001-int'(timeUs-dut.motion.stateStartUs));
           verifyRuntimeWheels(-4*TURN_SIGN,4*TURN_SIGN,"kill test reaches cruise before interruption");
         end
         case(kill)
           0:begin debugStop=1;#1;stopped("STOP immediately interrupts either ALIGN phase");tick(2);debugStop=0;end
           1:begin estop_frame=1;#1;stopped("IR immediately interrupts either ALIGN phase");tick(2);estop_frame=0;end
           2:begin distance_mm=240;#1;stopped("near J3 immediately interrupts either ALIGN phase");tick(2);end
           3:begin send();stopped("target loss interrupts either ALIGN phase");end
           4:begin status.perceptionReady=0;#1;stopped("unhealthy source immediately interrupts either ALIGN phase");tick(2);end
           5:begin send(1,120);stopped("centre crossing stops either phase instead of applying the next phase");end
           6:begin wait(!uartBusy);reset=1;#1;stopped("reset immediately interrupts either ALIGN phase");tick(3);reset=0;tick(20);end
         endcase
         stopTask();wait(zeroSent && !uartBusy);
         reset=1;tick(3);reset=0;status.perceptionReady=1;distance_mm=1000;tick(20);samples();fresh(1,30);tick(2500);
         stopped("restored safety/source after cancellation cannot replay a kick");
         ck(!dut.taskActive && dut.motion.alignKickUs==0 && dut.motion.alignKickSpeed==0,"reset clears phase latches and leaves task disarmed");
       end
     end
     configureTiming(0,2,10,5);fresh();arm();
     begin logic[31:0] invalidWord,spent;
       for(int invalidCase=0;invalidCase<9;invalidCase++)begin
         invalidWord=32'h00015420;
         case(invalidCase)
           0:invalidWord[3:0]=11;1:invalidWord[8:4]=1;2:invalidWord[8:4]=31;
           3:invalidWord[13:9]=1;4:invalidWord[13:9]=31;5:invalidWord[8:4]=11;
           6:invalidWord[17:14]=2;7:invalidWord[17:14]=9;8:invalidWord[18]=1;
         endcase
         @(negedge clk);alignTimingWord=invalidWord;#1;stopped("invalid timing word gates SEARCH immediately");
         tick(2);spent=dut.scanElapsedUs;tick(3);
         ck(!dut.motion.alignTimingValid && !dut.motion.tuningValid && dut.scanElapsedUs==spent,"invalid timing cannot charge or permit scan movement");
       end
     end
     configureTiming(0,2,10,5);runtimeStart(120,1000,5,5,"valid timing retains ordinary forward approach");
     @(negedge clk);alignTimingWord=0;#1;stopped("invalid timing also gates live forward approach");
     configureTiming(2,10,20,5);runtimeStart(30,1000,-5*TURN_SIGN,5*TURN_SIGN,"valid timing restores kick only after explicit new task");
     @(negedge clk);alignTimingWord=0;#1;stopped("invalid timing immediately gates a latched kick");
     configureTiming(0,2,10,5);configureTuning(4,4,5,3,30);stopped("restored default timing never arms the controller");
   end else if(!RUNTIME_TUNING)begin
     ck(dut.motion.tuningValid,"legacy parameter path ignores even an unknown omitted runtime word");
     ck(dut.motion.alignTimingValid && dut.motion.alignKickUs==0,"legacy parameter path ignores unknown timing input and has no kick");
   end
   tick(2500);ck(zeroLines>0 && zeroSent,"completed UART zero observed separately from logical stop");
   $display("PASS: tb_control_repair TURN_SIGN=%0d STRICT_ALIGN_BAND=%0d RUNTIME_TUNING=%0d checks=%0d UART lines=%0d spin=%0d drive=%0d zero=%0d low=%0d high=%0d fineLow=%0d fineHigh=%0d steerLow=%0d steerHigh=%0d fineSteerLow=%0d fineSteerHigh=%0d runtime=%0d",TURN_SIGN,STRICT_ALIGN_BAND,RUNTIME_TUNING,checks,lineCount,spinLines,driveLines,zeroLines,lowTurnLines,highTurnLines,lowFineTurnLines,highFineTurnLines,lowSteerLines,highSteerLines,lowFineSteerLines,highFineSteerLines,runtimeLines);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog state=%0d phase=%0d",state,dut.motion.acquirePhase);end
endmodule
