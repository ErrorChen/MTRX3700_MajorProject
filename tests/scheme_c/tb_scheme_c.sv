`timescale 1ns/1ps
module tb_scheme_c;
 import perception_pkg::*;
 logic clk=0,reset=1,power_frame=0,estop_frame=0;
 logic fifoFault=0,abandonEvent=0;
 always #10 clk=~clk;
 logic [2:0] selection=1;
 logic [31:0] timeUs=1000;
 perceptionStatus_t status;
 targetRequest_t req,held;
 targetReport_t rpt;
 wire qv,rr;logic qr=0,rv=0;
 logic distance_valid=1;logic [11:0] distance_mm=1000;
 wire signed [6:0] l,r;
 wire permit,used,estop,sonar_stop,motionTargetValid;
 wire [2:0] state,reason;
 int frame=0,checks=0;
 member_c_control dut(
   .motionPolicyWord(32'h00000af9),.chassisInitSent(1'b1),.clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),
 .cameraFifoFault(fifoFault),.cameraAbandonEvent(abandonEvent),.selection(selection),.timeUs(timeUs),.status(status),.targetRequest(req),.targetRequestValid(qv),
 .targetRequestReady(qr),.targetReport(rpt),.targetReportValid(rv),.targetReportReady(rr),
 .distance_valid(distance_valid),.distance_mm(distance_mm),.left_cm_s(l),.right_cm_s(r),
 .permit(permit),.used(used),.estop(estop),.sonar_stop(sonar_stop),.motionTargetValid(motionTargetValid),
 .motionState(state),.stop_reason(reason));
 wire signed [6:0] flipL,flipR;wire [2:0] flipState;
 motion_fsm #(.TURN_SIGN(-1)) flipped(
   .motionPolicyWord(32'h00000af9),.clk(clk),.reset(reset),.taskActive(dut.taskActive),
 .safetyHalt(estop_frame||estop||sonar_stop),.motionTargetValid(motionTargetValid),
 .distance_valid(distance_valid),.distance_mm(distance_mm),.centreU(dut.centreU),
 .left_cm_s(flipL),.right_cm_s(flipR),.state(flipState));
 task automatic ck(input bit c,input string msg);checks++;if(!c)$fatal(1,"%s",msg);endtask
 task automatic step(input int n=1);repeat(n)begin @(posedge clk);#1;end endtask
 task automatic clear;
 @(negedge clk);reset=1;power_frame=0;estop_frame=0;rv=0;qr=0;selection=1;
 fifoFault=0;abandonEvent=0;distance_valid=1;distance_mm=1000;status='0;status.perceptionReady=1;status.activeCfgVersion=1;
 step(3);@(negedge clk);reset=0;timeUs+=1000;step(3);
 endtask
 task automatic power;@(negedge clk);power_frame=1;step();@(negedge clk);power_frame=0;step(3);endtask
 task automatic select_target;
 power();ck(qv,"SELECT queued");held=req;
 ck(req.operation==TARGET_SELECT && req.markerType==MARKER_BAY && req.digit==selection,"typed identity");
 step(5);ck(req==held && qv,"request stable while backpressured");
 @(negedge clk);qr=1;step();@(negedge clk);qr=0;step(3);
 ck(!qv && state==1 && !permit,"SEARCH stationary");
 endtask
 task automatic build(input int u);
 timeUs+=1000;frame++;rpt='0;rpt.requestTag=req.requestTag;rpt.frameId=16'(frame);
 rpt.captureStartUs=timeUs-10;rpt.configVersion=status.activeCfgVersion;rpt.markerType=MARKER_BAY;
 rpt.digit=req.digit;rpt.frameGood=1;rpt.observed=1;rpt.locked=1;rpt.targetSelected=1;
 rpt.centreU=8'(u);rpt.quality=200;rpt.reason=REPORT_OK;
 endtask
 task automatic send;
 @(negedge clk);rv=1;step();ck(rr,"report handshake");@(negedge clk);rv=0;step(4);
 endtask
 task automatic report(input int u);build(u);send();endtask
 task automatic stopped(input string why);ck(!permit && l==0 && r==0,why);endtask
 task automatic abandon;
 @(negedge clk);timeUs+=100;abandonEvent=1;#1;
 ck(!motionTargetValid&&!permit,"abandon revokes combinational permission immediately");
 step();@(negedge clk);abandonEvent=0;status.faultFlags|=16'h0001;step(2);
 ck(!motionTargetValid&&!permit,"cache remains revoked after event");
 endtask
 task automatic recover;
 build(120);rpt.locked=0;rpt.reason=REPORT_ACQUIRING;send();
 ck(!motionTargetValid&&!permit,"recovery frame one cannot move");
 build(120);rpt.locked=0;rpt.reason=REPORT_ACQUIRING;send();
 ck(!motionTargetValid&&!permit,"recovery frame two cannot move");
 report(120);ck(motionTargetValid&&permit,"third fresh adjacent locked report recovers");
 endtask
 initial begin
 ck($bits(targetRequest_t)==24&&$bits(targetReport_t)==141,"public widths unchanged");
 clear();select_target();report(120);ck(permit,"normal movement");
 abandon();rv=1;step();rv=0;step(3);stopped("pre-event report rejected");recover();
 abandon();recover();ck(status.faultFlags==1,"history preserved after repeated recovery");
 // An already locked report is still insufficient for the first two frames.
 abandon();report(120);stopped("locked first recovery report insufficient");
 report(120);stopped("locked second recovery report insufficient");
 report(120);ck(permit,"three fresh locked reports recover");
 // Same-cycle handshake must lose to the event even with a fresh good payload.
 build(120);@(negedge clk);rv=1;abandonEvent=1;#1;
 ck(rr&&!motionTargetValid&&!permit,"event wins simultaneous valid/ready handshake");
 step();@(negedge clk);rv=0;abandonEvent=0;step(3);
 ck(!dut.adapter.haveMeasurement,"same-edge good report cannot refill cache");recover();
 // Hold an old valid report across the event and then release backpressure.
 @(negedge clk);force dut.adapter.targetReportReady=1'b0;rv=1;
 abandon();step(4);ck(!rr&&!motionTargetValid,"event observed while report channel stalled");
 @(negedge clk);release dut.adapter.targetReportReady;step();
 @(negedge clk);rv=0;step(3);stopped("held pre-fault report rejected after backpressure");recover();
 // Invalid frames reset recovery progress; all existing gates remain active.
 for(int bad=0;bad<12;bad++)begin
 abandon();report(120);report(120);build(120);
 case(bad)
 0:rpt.frameGood=0;
 1:rpt.ambiguous=1;
 2:rpt.digit=6;
 3:rpt.requestTag++;
 4:rpt.configVersion++;
 5:rpt.captureStartUs=timeUs-150001;
 6:rpt.markerType=MARKER_FUNCTION;
 7:rpt.quality=0;
 8:rpt.targetSelected=0;
 9:rpt.observed=0;
 10:rpt.centreU=240;
 11:rpt.captureStartUs=timeUs+1;
 endcase
 send();stopped("invalid recovery report cannot release motion");recover();
 end
 abandon();report(120);report(120);build(120);rpt.locked=0;rpt.reason=REPORT_ACQUIRING;
 send();stopped("third frame without tracker lock cannot release motion");
 report(120);ck(permit,"later locked report with consecutive evidence recovers");
 abandon();report(120);report(120);rv=1;step();rv=0;step(3);
 stopped("duplicate resets recovery sequence");recover();
 abandon();report(120);frame+=2;report(120);report(120);stopped("frame gap restarts three-frame count");
 report(120);ck(permit,"three adjacent frames after gap recover");
 abandon();report(120);report(120);status.activeCfgVersion++;step(3);
 stopped("configuration change revokes recovery progress");recover();
 abandon();report(120);report(120);status.interactionBusy=1;step(3);report(120);
 stopped("interaction busy prohibits recovery");status.interactionBusy=0;recover();
 timeUs=rpt.captureStartUs+150001;#1;stopped("150 ms cache age unchanged");
 abandon();report(120);report(120);timeUs=rpt.captureStartUs+150001;step(3);recover();
 // No false camera fault classification: bit zero with no witnessed event fails closed.
 clear();select_target();report(120);status.faultFlags=1;step(2);report(120);
 stopped("unclassified camera history remains fatal");
 // Other faults remain blocking even after an abandon recovery.
 for(int bitn=1;bitn<16;bitn++)begin
 clear();select_target();report(120);abandon();recover();
 status.faultFlags|=16'(1<<bitn);step(2);report(120);
 if(bitn==FAULT_AUDIO_CAPTURE)ck(permit,"audio exception unchanged");
 else stopped("other fault remains blocking");
 end
 clear();select_target();report(120);abandon();recover();
 @(negedge clk);fifoFault=1;#1;stopped("FIFO fault immediately stops after recovery");step(3);
 fifoFault=0;abandon();report(120);report(120);report(120);
 ck(dut.adapter.fifoFatal&&!permit&&!motionTargetValid,"FIFO fatal latch cannot recover even if input falls");
 // POWER, A and J3 cannot be bypassed by three good reports.
 clear();select_target();held=req;abandon();selection=6;power();
 ck(req==held&&!qv,"repeated POWER does not replace target or restart");recover();
 estop_frame=1;distance_mm=250;#1;stopped("A and J3 immediate stop");step();
 ck(estop&&reason==1,"A retains highest priority");estop_frame=0;distance_mm=1000;
 abandon();report(120);report(120);report(120);power();stopped("vision recovery cannot clear A latch");
 clear();select_target();report(120);distance_mm=250;step(2);distance_mm=1000;
 abandon();report(120);report(120);report(120);stopped("vision recovery cannot clear 250mm J3 latch");
 clear();select_target();report(120);distance_valid=0;step(2);distance_valid=1;
 abandon();report(120);report(120);report(120);stopped("vision recovery cannot clear invalid J3 latch");
 clear();build(120);send();stopped("reset cannot start from reports without POWER");
 ck(!dut.taskActive&&!dut.adapter.fifoFatal&&!dut.adapter.abandonSeen,"reset clears private state only");
 select_target();report(120);abandon();
 // Conservative fence works across 32-bit microsecond wrap.
 timeUs=32'hffff_ff00;abandon();timeUs=32'hffff_fff0;recover();
 $display("PASS: tb_scheme_c %0d checks",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
