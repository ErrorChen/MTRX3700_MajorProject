`timescale 1ns/1ps
module tb_chassis_init_gate;
 import perception_pkg::*;
 logic clk=0,reset=1,power_frame=0,estop_frame=0,chassisInitSent=0;
 always #10 clk=~clk;
 logic[31:0] timeUs=0;
 always @(posedge clk)if(reset)timeUs<=0;else timeUs<=timeUs+1;
 logic[5:0] selection=8;
 logic[1:0] mode=0;
 logic debugStart=0,debugStop=0,modeChanged=0,visualStart=0;
 logic distanceSample=0;
 perceptionStatus_t status;
 targetRequest_t req;
 targetReport_t rpt;
 logic rv=0;
 wire qv,rr,permit,estop,sonar_stop,locked;
 wire signed[6:0] l,r;
 wire[3:0] state;
 wire[511:0] words;
 int checks=0,frame=0;
 member_c_control #(.REQUIRE_CHASSIS_INIT(1),.SELECTION_STABLE_CLKS(3),.ACQUIRE_SETTLE_US(100),
   .ACQUIRE_TIMEOUT_US(1000),.LOST_WAIT_US(1000),.TASK_TIMEOUT_US(100000)) dut(
   .motionPolicyWord(32'h00000af9),
   .clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),.selection(selection),
   .mode(mode),.visualStart(visualStart),.debugStart(debugStart),.debugStop(debugStop),.modeChanged(modeChanged),
   .rawMode(1'b0),.injectLeaseValid(1'b1),.scanCalibrated(1'b1),.scanBudgetUs(32'd50000),.timeUs(timeUs),
   .tuningWord(32'h001e4543),.alignTimingWord(32'h0001a946),
   .cameraFifoFault(1'b0),.cameraAbandonEvent(1'b0),.status(status),
   .targetRequest(req),.targetRequestValid(qv),.targetRequestReady(1'b1),
   .targetReport(rpt),.targetReportValid(rv),.targetReportReady(rr),
   .distance_valid(1'b1),.distanceSample(distanceSample),.distance_mm(12'd1000),
   .zeroSent(1'b1),.uartBusy(1'b0),.chassisInitSent(chassisInitSent),.left_cm_s(l),.right_cm_s(r),
   .permit(permit),.used(),.estop(estop),.sonar_stop(sonar_stop),.motionTargetValid(locked),
   .motionState(state),.stop_reason(),.statusWords(words));
 task automatic ck(input bit ok,input string label);
   checks++;if(!ok)$fatal(1,"%s state=%0d armed=%0b ready=%0b",label,state,dut.taskActive,chassisInitSent);
 endtask
 task automatic tick(input int n=1);repeat(n)begin @(posedge clk);#1;end endtask
 task automatic fresh(input bit visible=0);
   repeat(3)begin
     tick(10);@(negedge clk);frame++;rpt='0;
     rpt.requestTag=dut.requestTag;rpt.frameId=16'(frame);rpt.captureStartUs=timeUs;
     rpt.configVersion=status.activeCfgVersion;rpt.markerType=MARKER_BAY;rpt.digit=dut.selectedDigit;
     rpt.targetSelected=1;rpt.frameGood=1;rpt.observed=visible;rpt.locked=visible;
     rpt.centreU=120;rpt.centreV=160;rpt.quality=200;
     rpt.reason=visible?REPORT_OK:REPORT_NOT_FOUND;rv=1;tick();ck(rr,"real adapter consumes report");
     @(negedge clk);rv=0;tick(3);
   end
 endtask
 task automatic keyPower;
   @(negedge clk);power_frame=1;tick();@(negedge clk);power_frame=0;tick(3);
 endtask
 task automatic hostStart;
   @(negedge clk);debugStart=1;tick();@(negedge clk);debugStart=0;tick(3);
 endtask
 task automatic red2;
   @(negedge clk);visualStart=1;tick();@(negedge clk);visualStart=0;tick(12);
 endtask
 task automatic stopTask;
   @(negedge clk);debugStop=1;tick();@(negedge clk);debugStop=0;tick(3);
 endtask
 task automatic estopA;
   @(negedge clk);estop_frame=1;#1;ck(l==0 && r==0,"A immediately gates final wheels");tick();
   @(negedge clk);estop_frame=0;tick(3);ck(estop && !dut.taskActive,"A latches and disarms independently of init");
 endtask
 initial begin
   logic[15:0] beforeTag;
   status='0;status.perceptionReady=1;status.activeCfgVersion=1;rpt='0;
   tick(3);@(negedge clk);reset=0;tick(20);
   repeat(3)begin distanceSample=1;tick();distanceSample=0;tick();end
   fresh(1);ck(locked && dut.sourceHealthyFresh,"read-only perception stays healthy while init pending");
   keyPower();ck(!dut.taskActive && !permit,"early POWER cannot ARM");
   hostStart();ck(!dut.taskActive && !permit,"early debug START cannot ARM");
   beforeTag=dut.requestTag;red2();fresh(1);
   ck(!dut.pendingVisualStart && !dut.taskActive && dut.requestTag==beforeTag,"early red2 cannot queue or refresh a task");
   estopA();keyPower();ck(!estop && !dut.taskActive,"POWER still clears IR while init pending, without ARM");
   chassisInitSent=1;tick(10);fresh(1);ck(!dut.taskActive,"readiness transition cannot replay any early START");
   hostStart();ck(dut.taskActive && permit && state==3,"new explicit START after local init can approach");
   chassisInitSent=0;tick(3);ck(dut.taskActive && permit,"readiness only qualifies NEW tasks, not active safety arbitration");
   estopA();keyPower();ck(!estop && !dut.taskActive,"IR clear-only remains separate after active-task stop");
   chassisInitSent=1;tick(5);fresh();beforeTag=dut.requestTag;red2();
   ck(dut.pendingVisualStart && !dut.taskActive,"new ready red2 waits for its refreshed report");
   fresh();ck(dut.requestTag!=beforeTag && dut.taskActive && state==1 && permit,"ready new red2 plus healthy NOT_FOUND starts calibrated SEARCH");
   stopTask();ck(!dut.taskActive && !permit,"STOP remains unconditional after initialization");
   fresh();red2();ck(dut.pendingVisualStart,"new pending red2 exists before readiness loss");
   chassisInitSent=0;tick(2);ck(!dut.pendingVisualStart,"readiness loss discards pending authorization");
   chassisInitSent=1;fresh();ck(!dut.taskActive,"restored readiness cannot revive old red2");
   mode=1;modeChanged=1;tick();modeChanged=0;tick(12);fresh(1);hostStart();keyPower();red2();fresh(1);
   ck(locked && !dut.taskActive && !permit,"VISION_ONLY remains zero and tracking despite ready/start events");
   $display("PASS tb_chassis_init_gate checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
