`timescale 1ns/1ps
// Production clocks, TRIG/ECHO pins, unchanged sonar_range, real CDC mailbox.
// No forced measurements, driver state, clocks, valid bits or sample pulses.
// Default: complete boundary suite. +R6_REPRESENTATIVE: six real transactions
// covering normal/near/FAR/no-rise/stuck-high/late-fall/recovery at full clocks.
module tb_sonar_guard;
 logic clk50=0,reset=1,echo=0;
 always #10 clk50=~clk50;
 wire trig,distance_valid,sample_pulse;
 wire [11:0] distance_mm;
 sonar_guard dut(.*);
 int checks=0,samples=0,triggers=0;
 bit representative=0;
 time last_trigger=0,trigger_end=0;
 logic previous_sample=0;
 always @(posedge clk50) begin
   if(!reset) begin
     if(sample_pulse && previous_sample)$fatal(1,"sample_pulse wider than one clk50");
     if(sample_pulse)samples++;
   end
   previous_sample<=sample_pulse;
 end
 always @(posedge trig) begin
   if(last_trigger!=0 && ($time-last_trigger<99900000 || $time-last_trigger>100100000))
     $fatal(1,"trigger cadence changed from 100 ms");
   last_trigger=$time;triggers++;
 end
 always @(negedge trig) if(!reset) trigger_end=$time;
 task automatic ck(input bit ok,input string why);
   checks++;if(!ok)$fatal(1,"%s at %0t mm=%0d valid=%0b",why,$time,distance_mm,distance_valid);
 endtask
 task automatic begin_transaction;
   @(negedge trig);#450000;
 endtask
 task automatic completed_echo(input time width_ns,input bit expect_valid,
                               input int min_mm,max_mm,input string label);
   int before_samples;
   begin
     begin_transaction();before_samples=samples;echo=1;
     #(width_ns);
     ck(samples==before_samples,{label,": no result before actual ECHO fall"});
     echo=0;
     @(posedge sample_pulse);#1;
     ck(distance_valid==expect_valid,{label,": validity"});
     ck(distance_mm>=min_mm && distance_mm<=max_mm,{label,": distance/FAR sentinel"});
     #1000;
     ck(samples==before_samples+1,{label,": one completed sample"});
   end
 endtask
 initial begin
   representative=$test$plusargs("R6_REPRESENTATIVE");
   #1000;reset=0;
   ck(!distance_valid,"power-up invalid until actual sensor response");
   completed_echo(5830904,1,999,1000,"1000 mm measured");
   completed_echo(1166181,1,199,200,"200 mm remains valid near obstacle");
   if(!representative)begin
     completed_echo(58309,0,9,10,"10 mm below sensor minimum is invalid");
     completed_echo(23317884,1,3998,3999,"3999 mm stays measured, not FAR");
     completed_echo(24000000,1,4000,4000,"24 ms over-range pulse is FAR");
   end
   completed_echo(39000000,1,4000,4000,"39 ms normal no-reflection pulse is FAR");
   if(!representative)completed_echo(75000000,1,4000,4000,"75 ms bounded long pulse is also FAR");
   // No rising edge after a real trigger must not inherit the prior FAR.
   begin_transaction();
   @(posedge sample_pulse);#1;
   ck(!distance_valid,"stuck-low/no rise is invalid");
   ck($time-trigger_end>79000000 && $time-trigger_end<81000000,"no-rise watchdog bounded near 80 ms");
   // High pulse survives the range cap and old 30 ms timeout, then fails at
   // the real watchdog. A subsequent late fall cannot produce a second sample.
   begin_transaction();echo=1;
   @(posedge sample_pulse);#1;
   ck(!distance_valid && distance_mm==4000,"stuck-high at watchdog is invalid, not FAR");
   ck($time-trigger_end>79000000 && $time-trigger_end<81000000,"stuck-high watchdog bounded near 80 ms");
   begin
     int prior;#1000;prior=samples;
     #5000000;echo=0;#1000000;
     ck(samples==prior,"late falling edge cannot republish timed-out transaction");
     ck(!distance_valid,"late fall cannot recover stale validity");
   end
   if(!representative)completed_echo(39000000,1,4000,4000,"new completed FAR recovers after fault");
   completed_echo(1749271,1,299,300,"300 mm measured recovery remains distinct from FAR");
   // A line already high before the next transaction prevents TRIG. Even
   // falling within that transaction's deadline must not fabricate FAR.
   if(!representative)begin
     echo=1;#150000000;echo=0;
     @(posedge sample_pulse);#1;
     ck(!distance_valid,"pre-existing high then low without TRIG is invalid");
   end
   #1000;
   ck(triggers==(representative?6:11),"expected physical transaction count");
   ck(samples==(representative?6:12),"expected complete and fault sample count");
   $display("PASS tb_sonar_guard scope=%s checks=%0d samples=%0d triggers=%0d real-pins FAR/near/invalid/recovery",
     representative?"R6_REPRESENTATIVE":"FULL_BOUNDARIES",checks,samples,triggers);
   $finish;
 end
 initial begin #1400000000;$fatal(1,"sonar guard watchdog");end
endmodule
