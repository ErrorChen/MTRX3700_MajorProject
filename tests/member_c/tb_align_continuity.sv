`timescale 1ns/1ps
// Real adapter/control/UART. Time jumps are explicit unsigned microseconds;
// UART baud alone is accelerated. This is not mechanical latency evidence.
module tb_align_continuity #(parameter int TURN_SIGN=-1);
 import perception_pkg::*;
 logic clk=0,reset=1,uartReset=1;
 always #10 clk=~clk;
 logic [31:0] timeUs=1000,scanBudgetUs=15100000;
 logic [31:0] tuningWord=32'h001e4543;
 logic [31:0] alignTimingWord={14'd0,4'd6,5'd20,5'd20,4'd6};
 logic power_frame=0,estop_frame=0,debugStart=0,debugStop=0,modeChanged=0;
 logic rawMode=0,injectLeaseValid=1,scanCalibrated=1,visualStart=0;
 logic cameraFifoFault=0,cameraAbandonEvent=0;
 logic [5:0] selection=1;
 logic [1:0] mode=2;
 logic distance_valid=1,distanceSample=0;
 logic [11:0] distance_mm=1000;
 perceptionStatus_t status;
 targetRequest_t req;
 targetReport_t rpt;
 wire qv,rr;logic rv=0;
 wire signed [6:0] l,r;
 wire permit,used,estop,sonar_stop,motionTargetValid,zeroSent,uartBusy,tx;
 wire [3:0] state;wire [2:0] reason;
 wire [511:0] statusWords;
 int checks=0,frame=0,lineCount=0,zeroLines=0,kickLines=0,cruiseLines=0,forwardLines=0;
 string lines[0:511];
 localparam int LOW_KICK_L=-6*TURN_SIGN,LOW_CRUISE_L=-4*TURN_SIGN;
 member_c_control #(.RUNTIME_TUNING(1),.ALLOW_BOUNDED_ALIGN_GAP(1),.TURN_SIGN(TURN_SIGN),
   .SELECTION_STABLE_CLKS(3)) dut(
   .motionPolicyWord(32'h00000af9),.chassisInitSent(1'b1),
   .clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),
   .selection(selection),.mode(mode),.debugStart(debugStart),.debugStop(debugStop),
   .modeChanged(modeChanged),.rawMode(rawMode),.injectLeaseValid(injectLeaseValid),
   .scanCalibrated(scanCalibrated),.visualStart(visualStart),.scanBudgetUs(scanBudgetUs),.timeUs(timeUs),
   .tuningWord(tuningWord),.alignTimingWord(alignTimingWord),.cameraFifoFault(cameraFifoFault),
   .cameraAbandonEvent(cameraAbandonEvent),.status(status),.targetRequest(req),
   .targetRequestValid(qv),.targetRequestReady(1'b1),.targetReport(rpt),
   .targetReportValid(rv),.targetReportReady(rr),.distance_valid(distance_valid),
   .distanceSample(distanceSample),.distance_mm(distance_mm),.zeroSent(zeroSent),.uartBusy(uartBusy),
   .left_cm_s(l),.right_cm_s(r),.permit(permit),.used(used),.estop(estop),.sonar_stop(sonar_stop),
   .motionTargetValid(motionTargetValid),.motionState(state),.stop_reason(reason),.statusWords(statusWords));
 // Omitting the new parameter retains strict behavior on the same real reports.
 wire signed [6:0] strictL,strictR;
 wire [3:0] strictState;
 motion_fsm #(.RUNTIME_TUNING(1),.TURN_SIGN(TURN_SIGN)) strict(
   .motionPolicyWord(32'h00000af9),
   .clk(clk),.reset(reset),.startPulse(dut.startPulse),.cancel(dut.cancel),.taskActive(dut.taskActive),
   .safetyHalt(estop_frame||estop||sonar_stop),.sourceHealthyFresh(dut.sourceHealthyFresh),
   .targetObserved(dut.targetObserved),.motionTargetValid(motionTargetValid),
   .distance_valid(distance_valid),.distance_mm(distance_mm),.centreU(dut.centreU),
   .scanAllowed(1'b1),.zeroSent(zeroSent),.motionApplied(1'b0),.timeUs(timeUs),.scanBudgetUs(scanBudgetUs),
   .tuningWord(tuningWord),.alignTimingWord(alignTimingWord),.left_cm_s(strictL),.right_cm_s(strictR),
   .state(strictState),.acquireFencePulse(),.taskDone(),.scanElapsedUs(),.scanRemainingUs(),.failureReason());
 chassis_command #(.CLKS_PER_BIT(4),.PERIOD_CLKS(10000),.USE_WHEEL_REQUESTS(1)) sender(
   .initAllowed(1'b0),.softReset(1'b0),.initSent(),
   .clk(clk),.reset(uartReset),.armed(permit),.left_cm_s(-l),.right_cm_s(-r),
   .motion(2'd0),.speed(2'd0),.feedback(1'b0),.tx(tx),.busy(uartBusy),.zeroSent(zeroSent));
 task automatic ck(input bit condition,input string message);
   checks++;if(!condition)$fatal(1,"%s time=%0d state=%0d L/R=%0d/%0d",message,timeUs,state,l,r);
 endtask
 task automatic tick(input int n=1);repeat(n)begin @(posedge clk);#1;end endtask
 task automatic advance(input int unsigned us);
   @(negedge clk);timeUs=timeUs+us;#1;tick(2);
 endtask
 task automatic samples;
   repeat(3)begin @(negedge clk);distanceSample=1;tick();@(negedge clk);distanceSample=0;tick();end
 endtask
 task automatic stopped(input string label);ck(!permit && l==0 && r==0,label);endtask
 task automatic send_report(input bit visible=1,input int u=60,input bit locked=1,input int kind=0);
   advance(10);@(negedge clk);frame++;rpt='0;
   rpt.requestTag=dut.requestTag;rpt.frameId=16'(frame);rpt.captureStartUs=timeUs;
   rpt.configVersion=status.activeCfgVersion;rpt.markerType=MARKER_BAY;rpt.digit=dut.selectedDigit;
   rpt.targetSelected=1;rpt.frameGood=1;rpt.observed=visible;rpt.locked=visible&&locked;
   rpt.quality=visible?200:0;rpt.centreU=8'(u);rpt.centreV=160;rpt.boxWidth=40;rpt.boxHeight=50;
   rpt.reason=visible?(locked?REPORT_OK:REPORT_ACQUIRING):REPORT_NOT_FOUND;
   case(kind)
     1:rpt.requestTag=rpt.requestTag+1'b1;
     2:rpt.configVersion=rpt.configVersion+1'b1;
     3:begin rpt.ambiguous=1;rpt.reason=REPORT_DUPLICATE_ID;end
     4:begin rpt.frameGood=0;rpt.observed=0;rpt.locked=0;rpt.reason=REPORT_FRAME_BAD;end
     5:rpt.captureStartUs=timeUs+100;
     6:rpt.captureStartUs=timeUs-150001;
     7:rpt.digit=6;
     8:rpt.reason=REPORT_LOW_QUALITY;
     9:rpt.frameId=dut.frameId;
     10:rpt.markerType=MARKER_FUNCTION;
     11:rpt.targetSelected=0;
     12:rpt.centreU=250;
     13:begin rpt.frameGood=0;rpt.observed=0;rpt.locked=0;rpt.reason=REPORT_RESOURCE_DROP;end
     14:rpt.quality=0;
   endcase
   rv=1;#1;
   if(kind!=0)begin
     ck(!dut.sourceHealthyFresh,"invalid public report immediately revokes qualified source");
     stopped("invalid identity/shape/age/health immediately gates wheel requests");
   end
   tick();ck(rr,"real adapter consumes report");@(negedge clk);rv=0;tick(3);
 endtask
 task automatic fresh(input int u=60);repeat(3)send_report(1,u,1);endtask
 task automatic stop_task;
   @(negedge clk);debugStop=1;#1;stopped("STOP immediate");tick();
   @(negedge clk);debugStop=0;tick(3);wait(zeroSent && !uartBusy);
 endtask
 task automatic restart(input int pulse_ms=200);
   stop_task();@(negedge clk);reset=1;rv=0;debugStart=0;power_frame=0;estop_frame=0;
   selection=1;mode=2;modeChanged=0;rawMode=0;injectLeaseValid=1;
   distance_valid=1;distance_mm=1000;cameraFifoFault=0;cameraAbandonEvent=0;
   status='0;status.perceptionReady=1;status.activeCfgVersion=1;
   alignTimingWord={14'd0,4'd6,5'(pulse_ms/10),5'(pulse_ms/10),4'd6};
   tick(3);@(negedge clk);reset=0;advance(1000);tick(15);samples();fresh();
   ck(motionTargetValid,"fresh selected identity is qualified before START");
 endtask
 task automatic arm;
   @(negedge clk);debugStart=1;tick();@(negedge clk);debugStart=0;tick(3);
 endtask
 task automatic start_turn(input int u=60,input int pulse_ms=200);
   restart(pulse_ms);if(u!=60)fresh(u);arm();
   ck(state==2 && permit && motionTargetValid,"fresh locked out-of-corridor target starts ALIGN");
 endtask
 task automatic keep_to(input logic[31:0] origin,input int unsigned until_us,
                       input bit visible=0,input int u=60,input bit locked=0);
   while(timeUs-origin+40010<until_us)begin advance(40000);send_report(visible,u,locked);end
   if(timeUs-origin<until_us)advance(until_us-(timeUs-origin));
 endtask
 function automatic string wheel_json(input int logicalL,input int logicalR);
   int ml,mr;string a,b;ml=-logicalL;mr=-logicalR;
   a=$sformatf("0.0%0d",ml<0?-ml:ml);b=$sformatf("0.0%0d",mr<0?-mr:mr);
   if(ml<0)a={"-",a};if(mr<0)b={"-",b};
   return {"{\"T\":1,\"L\":",a,",\"R\":",b,"}\n"};
 endfunction
 task automatic read_line;
   logic [7:0] ch;string line;line="";
   for(int n=0;n<29;n++)begin
     @(negedge tx);#40;if(tx!==0)$fatal(1,"UART start bit");
     for(int b=0;b<8;b++)begin #80;ch[b]=tx;end
     #80;if(tx!==1)$fatal(1,"UART stop bit");line={line,ch};
     if(ch==10)begin
       ck(lineCount<512,"bounded UART line capture");lines[lineCount++]=line;
       if(line==wheel_json(0,0))zeroLines++;
       else if(line==wheel_json(6,-6)||line==wheel_json(-6,6))kickLines++;
       else if(line==wheel_json(4,-4)||line==wheel_json(-4,4))cruiseLines++;
       else if(line==wheel_json(5,5))forwardLines++;
       else $fatal(1,"unexpected UART JSON: %s",line);
       return;
     end
   end
   $fatal(1,"UART missing newline");
 endtask
 initial forever read_line();
 initial begin
   logic[31:0] origin,taskOrigin,scanOrigin,settle;
   int beforeKick,beforeCruise,beforeZero,beforeForward;
   status='0;status.perceptionReady=1;status.activeCfgVersion=1;rpt='0;
   tick(3);@(negedge clk);uartReset=0;reset=0;tick(20);
   // The exact 200 ms ceiling, NF and same-identity acquiring in both phases.
   start_turn();origin=dut.motion.stateStartUs;taskOrigin=dut.motion.taskStartUs;scanOrigin=dut.scanElapsedUs;
   beforeKick=kickLines;tick(2000);ck(kickLines>beforeKick,"complete kick UART decoded");
   advance(20000);send_report(0);ck(dut.sourceHealthyFresh && !motionTargetValid && permit,"healthy NF keeps only entry-qualified pulse");
   ck(strictL==0 && strictR==0 && strictState==5,"default-disabled instance remains strict on NF");
   send_report(1,60,0);ck(dut.sourceHealthyFresh && dut.targetObserved && !motionTargetValid && permit,"same-ID acquiring may finish same pulse");
   ck(dut.motion.stateStartUs==origin && dut.motion.alignKickUs==60000,"NF/acquiring cannot reset origin or kick");
   keep_to(origin,59999);ck(l==LOW_KICK_L && r==-LOW_KICK_L,"kick sign/phase retained until original60ms boundary");
   advance(1);ck(l==LOW_CRUISE_L && r==-LOW_CRUISE_L,"original60ms boundary switches to cruise without re-kick");
   beforeCruise=cruiseLines;tick(2000);ck(cruiseLines>beforeCruise,"complete cruise UART decoded after kick");
   keep_to(origin,199999);ck(state==2 && permit,"healthy NF remains bounded immediately before200ms");
   beforeZero=zeroLines;advance(1);stopped("original200ms deadline forces zero with target still absent");
   ck(state==6 && dut.motion.stationaryRecoveryRequired,"expired gap always enters mandatory stationary ACQUIRE");
   ck(dut.motion.taskStartUs==taskOrigin && dut.scanElapsedUs==scanOrigin,"gap does not refund task/scan budget");
   tick(2000);ck(zeroSent && zeroLines>beforeZero,"full zero JSON completes after bounded pulse");
   ck(dut.motion.acquirePhase==1,"stationary dwell begins only after completed zero");settle=dut.motion.settleStartUs;
   while(timeUs-settle+40010<1500000)begin advance(40000);send_report(1,120,1);stopped("pre-fence target cannot resume movement during1.5s dwell");end
   advance(1499999-(timeUs-settle));ck(dut.motion.acquirePhase==1,"full production1.5s dwell is not shortened");
   advance(1);tick(3);ck(dut.motion.acquirePhase==2 && !motionTargetValid,"capture fence clears prior lock after full dwell");
   send_report(1,120);stopped("first post-fence frame cannot move");
   send_report(1,120);stopped("second post-fence frame cannot move");
   send_report(1,120);ck(state==3 && l==5 && r==5,"third fresh post-fence frame permits forward");
   beforeForward=forwardLines;tick(2000);ck(forwardLines>beforeForward,"complete forward UART follows qualified stationary reacquisition");
   send_report(0);stopped("APPROACH still stops immediately on healthy target loss");ck(state==5,"APPROACH loss remains LOST");

   start_turn(180);origin=dut.motion.stateStartUs;send_report(0);
   ck(l==-LOW_KICK_L && r==LOW_KICK_L,"opposite-side gap retains opposite latched direction");
   keep_to(origin,60000);ck(l==-LOW_CRUISE_L && r==LOW_CRUISE_L,"opposite-side cruise uses unchanged sign");
   send_report(1,120,0);stopped("fresh same-ID acquiring crossing stops immediately before third-frame lock");
   ck(state==6,"crossing uses complete stationary acquisition, never reverses in flight");
   fresh(60);stopped("opposite fresh reports during dwell cannot revive old pulse");

   start_turn(60,300);ck(!dut.motion.alignGapEligible,"pulse longer than200ms never qualifies for exception");
   send_report(0);stopped("300ms profile retains strict target-loss stop");ck(state==5,"long profile loss is LOST");
   restart();send_report(0);repeat(3)send_report(1,60,0);arm();
   ck(state==6 && !dut.motion.alignGapEligible,"unlocked entry cannot acquire a bounded-turn exception");stopped("unlocked entry remains stationary");

   // Every invalid public-report family goes through the real adapter.
   for(int kind=1;kind<=14;kind++)begin
     start_turn();advance(10000);send_report(1,60,1,kind);
     ck(state==5 && !dut.motion.alignGapEligible,"invalid report permanently revokes this pulse");
     fresh();stopped("restoring valid reports cannot replay invalidated pulse before ACQUIRE");
   end
   start_turn();advance(150001);stopped("age limit stops even without receiving another report");
   ck(state==5 && !dut.motion.alignGapEligible,"stale source revokes gap eligibility");fresh();stopped("freshness restoration does not revive old pulse");

   // Independent physical and task boundaries while NF continuation is active.
   for(int hazard=0;hazard<9;hazard++)begin
     start_turn();send_report(0);ck(permit,"qualified gap active before hazard");
     @(negedge clk);
     case(hazard)
       0:estop_frame=1;
       1:distance_mm=250;
       2:distance_valid=0;
       3:selection=2;
       4:begin mode=1;modeChanged=1;end
       5:debugStop=1;
       6:injectLeaseValid=0;
       7:status.perceptionReady=0;
       8:status.interactionBusy=1;
     endcase
     #1;stopped("IR/J3/selection/mode/STOP/lease/source immediately dominate bounded gap");tick(3);
     @(negedge clk);estop_frame=0;distance_mm=1000;distance_valid=1;selection=1;
     mode=2;modeChanged=0;debugStop=0;injectLeaseValid=1;status.perceptionReady=1;status.interactionBusy=0;
     samples();tick(20);fresh();stopped("restoring hazard cannot replay original bounded pulse");
   end
   // Unsigned subtraction must preserve the same deadline across time wrap.
   stop_task();@(negedge clk);timeUs=32'hfffe0000;restart();arm();origin=dut.motion.stateStartUs;
   send_report(0);keep_to(origin,199999);ck(permit,"gap stays bounded correctly across32-bit wrap");
   advance(1);stopped("wrapped original200ms deadline still stops");ck(state==6,"wrapped expiry enters ACQUIRE");
   stop_task();ck(zeroSent && zeroLines>0 && kickLines>0 && cruiseLines>0 && forwardLines>0,"all complete UART stages covered");
   $display("PASS tb_align_continuity sign=%0d checks=%0d UART=%0d kick=%0d cruise=%0d zero=%0d forward=%0d",TURN_SIGN,checks,lineCount,kickLines,cruiseLines,zeroLines,forwardLines);
   $finish;
 end
 initial begin #50000000;$fatal(1,"bounded continuity watchdog");end
endmodule
