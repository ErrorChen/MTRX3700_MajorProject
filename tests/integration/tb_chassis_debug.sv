`timescale 1ns/1ps
module tb_chassis_debug;
 import perception_pkg::*;
 logic clk=0,reset=1;always #10 clk=~clk;
 logic [31:0] timeUs=0;always @(posedge clk)if(!reset)timeUs<=timeUs+1;
 logic [511:0] statusWords='0;
 wire [1:0] mode;
 wire modeChanged,debugStart,debugStop,injectLeaseValid,scanCalibrated,templateValid;
 wire [31:0] leaseAgeUs,scanBudgetUs,observation0,observation1;
 chassisDebug #(.LEASE_US(500)) dut(.*);
 targetRequest_t targetRequest;
 logic targetRequestValid=0;
 wire targetRequestReady,targetReportValid;
 logic targetReportReady=1;
 targetReport_t targetReport,heldReport;
 perceptionStatus_t status;
 syntheticPerception #(.FRAME_PERIOD_US(40)) source(
  .clk(clk),.reset(reset),.enabled(mode==2),.sourceChanged(modeChanged),
  .leaseValid(injectLeaseValid),.templateValid(templateValid),.timeUs(timeUs),
  .observation0(observation0),.observation1(observation1),.targetRequest(targetRequest),
  .targetRequestValid(targetRequestValid),.targetRequestReady(targetRequestReady),
  .targetReport(targetReport),.targetReportValid(targetReportValid),.targetReportReady(targetReportReady),.status(status));
 int starts=0,stops=0,reports=0,checks=0;
 logic [15:0] lastFrame=0;
 logic [31:0] fence;
 always @(posedge clk)begin
  if(debugStart)starts++;
  if(debugStop)stops++;
  if(targetReportValid&&targetReportReady)begin
   reports++;
   if(targetReport.requestTag!=7 || targetReport.digit!=3 || targetReport.markerType!=MARKER_BAY ||
      targetReport.configVersion!=1 || targetReport.captureStartUs<=fence || targetReport.frameId<=lastFrame)
     $fatal(1,"synthetic request/frame provenance");
   lastFrame=targetReport.frameId;
  end
 end
 task automatic tick(input int n=1);repeat(n)@(negedge clk);endtask
 task automatic check(input bit ok,input string why);
  if(!ok)$fatal(1,"CCTL: %s",why);checks++;
 endtask
 task automatic command(input int op,input logic [31:0] payload=0,input int expectedError=0);
  logic toggle;
  toggle=!dut.ackToggle;
  dut.probes.src_jtag={toggle,3'd0,4'(op),8'd0,16'd0,payload};tick(12);
  check(dut.ackToggle==toggle,"ACK timeout");
  check(dut.errorCode==expectedError,"unexpected error code");
 endtask
 initial begin
  tick(4);reset=0;tick(12);
  check(mode==0&&!injectLeaseValid&&starts==0,"safe integrated reset");
  command(1,1);command(3,0,3);check(starts==0,"vision must never arm");
  command(1,2);command(7,0,4);
  command(5,(200<<24)|(1<<20)|(1<<19)|(1<<17)|(160<<8)|80);
  command(7,0,4);check(!templateValid,"half template cannot commit");
  command(6,(40<<8)|30);command(7);
  check(templateValid&&observation0[7:0]==80,"atomic observation commit");
  command(3,0,3);command(8);check(injectLeaseValid&&starts==0,"heartbeat never arms");
  targetRequest='0;targetRequest.operation=TARGET_SELECT;targetRequest.requestTag=7;
  targetRequest.markerType=MARKER_BAY;targetRequest.digit=3;
  targetRequestValid=1;tick();fence=timeUs-1;targetRequestValid=0;
  command(3);check(starts==1,"explicit start");tick(150);
  check(reports>=3&&targetReport.locked,"continuous independent three frame lock");
  targetReportReady=0;wait(targetReportValid);tick();heldReport=targetReport;
  tick(50);check(targetReport==heldReport,"ready/valid immutable stalled report");
  command(8);check(targetReport==heldReport,"heartbeat cannot refresh held timestamp");
  targetReportReady=1;tick(2);
  command(4);check(stops>=3,"stop pulse");
  tick(510);check(!injectLeaseValid&&!status.perceptionReady,"hard lease expiry");
  begin int beforeCount;beforeCount=reports;tick(100);check(reports==beforeCount,"expired lease stops generation");end
  command(8);check(starts==1,"renewal cannot arm");
  statusWords[31:0]=32'h12345678;command(2);statusWords[31:0]=0;tick();
  check(dut.selectedWord==32'h12345678,"status frozen");
  command(9,0,2);command(9,2000000);check(scanBudgetUs==2000000&&!scanCalibrated,"scan bounds");
  command(10,1);check(scanCalibrated,"explicit calibration acknowledgement");
  command(1,0);check(!templateValid&&!injectLeaseValid,"mode flush");
  command(3);begin int prior;prior=starts;reset=1;tick(5);reset=0;tick(15);
   check(starts==prior,"old JTAG ARM not replayed after reset");end
  $display("PASS tb_chassis_debug checks=%0d reports=%0d",checks,reports);$finish;
 end
 initial begin #1000000;$fatal(1,"CCTL watchdog");end
endmodule
