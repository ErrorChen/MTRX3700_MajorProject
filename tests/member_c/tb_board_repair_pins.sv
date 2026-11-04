`timescale 1ns/1ps
// Pin-level board verification. No force of NEC, sonar or controller internals.
module tb_board_repair_pins;
 import perception_pkg::*;
 logic clk=0,reset=1,ir=1;always #10 clk=~clk;
 logic [5:0] divUs=0;logic[31:0]timeUs=0;
 always @(posedge clk)begin
   if(reset)begin divUs<=0;timeUs<=0;end
   else if(divUs==49)begin divUs<=0;timeUs<=timeUs+1;end
   else divUs<=divUs+1;
 end
 wire trig,echo,tx;wire[9:0]led;wire[6:0]h0,h1,h2,h3,h4,h5;
 wire[511:0]words;targetRequest_t req;targetReport_t rpt;perceptionStatus_t status;
 wire qv,qr,rv,rr;
 int wall=1000,measurements,errors,notes,lastEcho,initialErrors;
 int checks=0,moves=0,zeros=0;
 string line="";logic[7:0]ch;
 memberCBoard #(.SELECTION_STABLE_CLKS(8)) dut(
   .motionPolicyWord(32'h00000af9),
   .CLOCK_50(clk),.reset50(reset),.KEY(2'b11),.IRDA_RXD(ir),.SW(6'b1),
   .mode(2'd2),.visualStart(1'b0),.debugStart(1'b0),.debugStop(1'b0),.modeChanged(1'b0),.rawMode(1'b0),
   .injectLeaseValid(1'b1),.scanCalibrated(1'b0),.scanBudgetUs(32'd10000000),.statusWords(words),
   .timeUs(timeUs),.cameraFifoFault(1'b0),.cameraAbandonEvent(1'b0),.perceptionStatus(status),
   .targetRequest(req),.targetRequestValid(qv),.targetRequestReady(qr),
   .targetReport(rpt),.targetReportValid(rv),.targetReportReady(rr),
   .SONAR_ECHO(echo),.SONAR_TRIG(trig),.CHASSIS_RX(1'b1),.CHASSIS_TX(tx),.LEDR(led),
   .HEX0(h0),.HEX1(h1),.HEX2(h2),.HEX3(h3),.HEX4(h4),.HEX5(h5));
 syntheticPerception source(
   .clk(clk),.reset(reset),.enabled(1'b1),.sourceChanged(1'b0),.leaseValid(1'b1),.templateValid(1'b1),
   .timeUs(timeUs),.observation0(32'hff1aa078),.observation1(32'h00003228),
   .targetRequest(req),.targetRequestValid(qv),.targetRequestReady(qr),
   .targetReport(rpt),.targetReportValid(rv),.targetReportReady(rr),.status(status));
 hcsr04_model #(.VERBOSE(0)) sensor(.trig(trig),.echo(echo),.distance_mm(wall),.object_present(1'b1),
   .measurements(measurements),.errors(errors),.notes(notes),.last_echo_us(lastEcho));
 task automatic ck(input bit ok,input string why);checks++;if(!ok)$fatal(1,"%s at %0d us",why,timeUs);endtask
 task automatic tick(input int n=1);repeat(n)@(negedge clk);endtask
 task automatic nec(input logic[31:0]code);
   ir=0;#9000000;ir=1;#4500000;
   for(int b=0;b<32;b++)begin ir=0;#562500;ir=1;if(code[b])#1687500;else #562500;end
   ir=0;#562500;ir=1;#1000;
 endtask
 task automatic necRepeat;
   ir=0;#9000000;ir=1;#2250000;ir=0;#562500;ir=1;#1000;
 endtask
 initial forever begin
   @(negedge tx);#4340;ck(tx===0,"UART start bit");
   for(int b=0;b<8;b++)begin #8680;ch[b]=tx;end
   #8680;ck(tx===1,"UART stop bit");line={line,ch};
   if(ch==10)begin
     if(line=="{\"T\":1,\"L\":0.00,\"R\":0.00}\n")zeros++;
     else if(line=="{\"T\":1,\"L\":-0.05,\"R\":-0.05}\n")moves++;
     else $fatal(1,"unexpected UART line %s",line);
     line="";
   end
 end
 initial begin
   tick(10);initialErrors=errors;reset=0;
   wait(!dut.sonar_stop);tick(10);
   ck(measurements>=3,"three actual sonar samples release initial HOLD");
   ck(dut.distance_mm>=998 && dut.distance_mm<=1001,"actual J3 echo widths yield 1000mm");
   ck(dut.motionTargetValid && !dut.running,"tracking remains active before POWER");
   nec(32'hed12ff00);tick(10);ck(dut.running,"physical POWER starts locked target task");wait(moves>0);
   nec(32'hf00fff00);tick(10);ck(dut.estop && !dut.running,"physical A latches stop");
   nec(32'hed12ff00);tick(10);ck(!dut.estop && !dut.control_u.taskActive,"first POWER releases only");
   necRepeat();tick(10);ck(!dut.control_u.taskActive,"NEC repeat cannot start");
   nec(32'hed12ff00);tick(10);ck(!dut.control_u.taskActive,"full-frame long hold cannot start");
   #200000000;nec(32'hed12ff00);tick(10);ck(dut.running,"new POWER after release starts");
   wall=200;wait(dut.sonar_stop);tick(10);ck(!dut.running && dut.motionState==7,"physical hazardous J3 enters HOLD");
   wait(dut.zeroSent);ck(zeros>0,"physical UART completed zero JSON");
   ck(errors==initialErrors,"sonar trigger protocol preserved");
   $display("PASS: tb_board_repair_pins checks=%0d sonar=%0d UART move=%0d zero=%0d",checks,measurements,moves,zeros);$finish;
 end
 initial begin #1500000000;$fatal(1,"board pin watchdog");end
endmodule
