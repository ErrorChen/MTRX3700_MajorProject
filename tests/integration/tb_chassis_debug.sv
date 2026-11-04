`timescale 1ns/1ps
module tb_chassis_debug;
 import perception_pkg::*;
 logic clk=0,reset=1;always #10 clk=~clk;
 logic [31:0] timeUs=0;always @(posedge clk)if(!reset)timeUs<=timeUs+1;
 logic [511:0] statusWords='0;
 wire [1:0] mode;
 wire modeChanged,debugStart,debugStop,injectLeaseValid,scanCalibrated,templateValid;
 wire [31:0] leaseAgeUs,scanBudgetUs,observation0,observation1,tuningWord,alignTimingWord,motionPolicyWord;
 chassisDebug #(.LEASE_US(500),.RUNTIME_MOTION_POLICY(1)) dut(.*);
 wire [1:0] bootMode;
 wire bootStart,bootCalibrated;
 wire [31:0] bootScanBudget,bootTuning,bootTiming,bootPolicy;
 chassisDebug #(.RUNTIME_MOTION_POLICY(1),.INITIAL_SCAN_CALIBRATED(1),
   .INITIAL_SCAN_BUDGET_US(15100000),.INITIAL_TUNING_WORD(32'h001e4543),
   .INITIAL_ALIGN_TIMING_WORD(32'h0001a946)) productionBoot(
   .clk(clk),.reset(reset),.timeUs(timeUs),.statusWords(statusWords),
   .mode(bootMode),.modeChanged(),.debugStart(bootStart),.debugStop(),
   .injectLeaseValid(),.leaseAgeUs(),.scanCalibrated(bootCalibrated),.scanBudgetUs(bootScanBudget),
   .tuningWord(bootTuning),.alignTimingWord(bootTiming),.motionPolicyWord(bootPolicy),
   .observation0(),.observation1(),.templateValid());
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
 function automatic logic [31:0] pulseWord(input int kick,minTotal,maxTotal,kickSpeed);
  return 32'(kick)|(32'(minTotal)<<4)|(32'(maxTotal)<<9)|(32'(kickSpeed)<<14);
 endfunction
 initial begin
  tick(4);reset=0;tick(12);
  check(mode==0&&!injectLeaseValid&&starts==0,"safe integrated reset");
  check(bootMode==0 && !bootStart && bootCalibrated && bootScanBudget==15100000,
    "production boot is disarmed integrated with historical 15.1s scan qualification");
  check(bootTuning==32'h001e4543 && bootTiming==32'h0001a946 && bootPolicy==32'h00000af9,
    "production boot retains E12 tested speed/pulse and unchanged policy defaults");
  check(tuningWord==32'h001e3544,"runtime tuning reset defaults");
  check(alignTimingWord==32'h00015420,"ALIGN timing reset defaults preserve old motion");
  command(12,pulseWord(6,8,20,4),5);check(alignTimingWord==32'h00015420,"integrated pulse write rejected");
  command(11,32'h00284855,5);check(tuningWord==32'h001e3544,"integrated tuning rejected");
  command(1,1);command(3,0,3);check(starts==0,"vision must never arm");
  command(11,32'h00284855,5);check(tuningWord==32'h001e3544,"zeroSent required");
  statusWords[8*32+15]=1;
  command(10,1);command(11,32'h001e3554);
  check(tuningWord==32'h001e3554&&scanCalibrated&&starts==0&&!injectLeaseValid,
    "stationary atomic change preserves calibration and cannot arm");
  command(2);check(dut.frozenWords[13*32+:32]==32'ha11e3554,"tuning capability and frozen readback");
  command(11,32'h00284855);
  check(tuningWord==32'h00284855&&!scanCalibrated,"search speed invalidates scan calibration");
  check(dut.frozenWords[13*32+:32]==32'ha11e3554,"prior snapshot immutable across tuning commit");
  command(2);check(dut.frozenWords[13*32+:32]==32'ha1284855,"new snapshot shows complete tuning word");
  // Each invalid field must reject the whole transaction, not partially write.
  command(11,32'h005e3544,2); // reserved bit22
  command(11,32'h001e3542,2);command(11,32'h001e3546,2);
  command(11,32'h001e3524,2);command(11,32'h001e3564,2);
  command(11,32'h001e3344,2);command(11,32'h001e3944,2);
  command(11,32'h001e2544,2);command(11,32'h001e5544,2);
  command(11,32'h001e4444,2); // approach must exceed fine
  command(11,32'h00093544,2);command(11,32'h00293544,2);
  check(tuningWord==32'h00284855,"invalid payloads leave all parameters unchanged");
  statusWords[20]=1;command(11,32'h001e3544,5);statusWords[20]=0;
  statusWords[28]=1;command(11,32'h001e3544,5);statusWords[28]=0;
  statusWords[7*32+:7]=3;command(11,32'h001e3544,5);statusWords[7*32+:7]=0;
  statusWords[7*32+8+:7]=7'h7d;command(11,32'h001e3544,5);statusWords[7*32+8+:7]=0;
  statusWords[8*32+15]=0;command(11,32'h001e3544,5);statusWords[8*32+15]=1;
  check(tuningWord==32'h00284855&&starts==0,"each motion boundary rejects tuning without ARM");
  command(1,2);command(11,32'h001e3544,5);
  command(1,1);command(11,32'h000a3433);
  check(tuningWord==32'h000a3433,"minimum runtime field boundaries accepted");
  command(11,32'h001e3544);
  command(10,1);command(2);
  check(dut.frozenWords[15*32+20+:8]==8'ha2 &&
        dut.frozenWords[15*32+2+:18]==18'h15420 &&
        dut.frozenWords[15*32+28+:4]==4'b0010 && dut.frozenWords[15*32+:2]==1,
        "pulse capability/payload preserve upper flags and mode");
  command(12,pulseWord(6,8,20,4));
  check(alignTimingWord==pulseWord(6,8,20,4) && tuningWord==32'h001e3544 &&
        scanCalibrated && scanBudgetUs==10000000 && starts==0 && !injectLeaseValid,
        "atomic pulse commit preserves speed/scan and does not ARM or lease");
  check(dut.frozenWords[15*32+2+:18]==18'h15420,"pulse snapshot remains immutable after commit");
  command(2);check(dut.frozenWords[15*32+2+:18]==pulseWord(6,8,20,4),"new snapshot has entire pulse word");
  command(12,32'h00055420,2); // reserved bit18
  command(12,32'h80015420,2); // high reserved bit
  command(12,pulseWord(11,2,10,5),2);
  command(12,pulseWord(0,1,10,5),2);command(12,pulseWord(0,31,31,5),2);
  command(12,pulseWord(0,2,31,5),2);command(12,pulseWord(0,10,9,5),2);
  command(12,pulseWord(0,2,10,2),2);command(12,pulseWord(0,2,10,9),2);
  check(alignTimingWord==pulseWord(6,8,20,4),"invalid pulse field rejects the whole word");
  statusWords[20]=1;command(12,32'h00015420,5);statusWords[20]=0;
  statusWords[28]=1;command(12,32'h00015420,5);statusWords[28]=0;
  statusWords[7*32+:7]=3;command(12,32'h00015420,5);statusWords[7*32+:7]=0;
  statusWords[7*32+8+:7]=7'h7d;command(12,32'h00015420,5);statusWords[7*32+8+:7]=0;
  statusWords[8*32+15]=0;command(12,32'h00015420,5);statusWords[8*32+15]=1;
  command(1,2);command(12,32'h00015420,5);command(1,1);
  check(alignTimingWord==pulseWord(6,8,20,4) && starts==0,"every pulse stationary boundary rejects without ARM");
  statusWords[29]=1;statusWords[30]=1;
  command(12,pulseWord(0,2,2,3));check(alignTimingWord==pulseWord(0,2,2,3),"minimum pulse boundaries accepted");
  command(12,pulseWord(10,30,30,8));check(alignTimingWord==pulseWord(10,30,30,8),"maximum pulse boundaries accepted");
  command(12,pulseWord(10,2,2,8));check(alignTimingWord==pulseWord(10,2,2,8),"longer kick accepted for controller total-time truncation");
  check(statusWords[29]&&statusWords[30]&&scanCalibrated&&starts==0,"pulse write retains latched safety inputs/calibration");
  command(12,32'h00015420);
  check(motionPolicyWord==32'h00000af9,"policy default preserves corridor/dwell/dock/slow");
  statusWords[10*32+:9]=9'h1d5;command(2);
  check(dut.frozenWords[10*32+:32]=={6'h2d,17'h00af9,9'h1d5},"policy capability/readback preserves all low nine flags");
  command(13,32'h00014b4e);
  check(motionPolicyWord==32'h00014b4e && scanCalibrated && scanBudgetUs==10000000 &&
    tuningWord==32'h001e3544 && alignTimingWord==32'h00015420 && starts==0 && !injectLeaseValid,
    "atomic policy write preserves other settings, safety and task authorization");
  check(dut.frozenWords[10*32+9+:17]==17'h00af9,"old policy snapshot remains immutable");
  command(2);check(dut.frozenWords[10*32+9+:17]==17'h14b4e,"new policy snapshot is the complete word");
  // Every field and high reserved bit must reject atomically.
  command(13,32'h00020af9,2);command(13,32'h80000af9,2);
  command(13,32'h00000af8,2);command(13,32'h00000aff,2);
  command(13,32'h00000a49,2);command(13,32'h00000b59,2);
  command(13,32'h000016f9,2);command(13,32'h000160f9,2);
  check(motionPolicyWord==32'h00014b4e,"invalid policy leaves old complete word");
  statusWords[20]=1;command(13,32'h00000af9,5);statusWords[20]=0;
  statusWords[28]=1;command(13,32'h00000af9,5);statusWords[28]=0;
  statusWords[7*32+:7]=3;command(13,32'h00000af9,5);statusWords[7*32+:7]=0;
  statusWords[7*32+8+:7]=7'h7d;command(13,32'h00000af9,5);statusWords[7*32+8+:7]=0;
  statusWords[8*32+15]=0;command(13,32'h00000af9,5);statusWords[8*32+15]=1;
  command(1,0);command(13,32'h00000af9,5);command(1,2);command(13,32'h00000af9,5);command(1,1);
  check(motionPolicyWord==32'h00014b4e && starts==0,"every policy stationary boundary rejects without ARM");
  command(13,32'h00000059);check(motionPolicyWord==32'h00000059,"minimum policy fields accepted");
  command(13,32'h0001554e);check(motionPolicyWord==32'h0001554e,"maximum policy fields accepted");
  command(13,32'h00000af9);statusWords='0;
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
   check(starts==prior,"old JTAG ARM not replayed after reset");
   check(tuningWord==32'h001e3544&&!scanCalibrated,"reset restores tuning defaults and clears calibration");end
  check(alignTimingWord==32'h00015420,"reset restores kick disabled and old pulse duration");
  check(motionPolicyWord==32'h00000af9,"reset restores policy defaults");
  check(bootMode==0 && !bootStart && bootCalibrated && bootScanBudget==15100000 &&
    bootTuning==32'h001e4543 && bootTiming==32'h0001a946 && bootPolicy==32'h00000af9,
    "KEY0 restores declared production profile without replaying a START");
  $display("PASS tb_chassis_debug checks=%0d reports=%0d",checks,reports);$finish;
 end
 initial begin #1000000;$fatal(1,"CCTL watchdog");end
endmodule
