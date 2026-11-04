`timescale 1ns/1ps
module tb_motion_policy;
 logic clk=0,reset=1,startPulse=0,cancel=0,taskActive=0,safetyHalt=0;
 always #10 clk=~clk;
 logic sourceHealthyFresh=1,targetObserved=1,motionTargetValid=1,distance_valid=1;
 logic scanAllowed=1,zeroSent=1,motionApplied=0;
 logic [31:0] timeUs=0,scanBudgetUs=15100000;
 logic [31:0] tuningWord=32'h001e4543,alignTimingWord=32'h0001a946,motionPolicyWord=32'h00000af9;
 logic [7:0] centreU=120;
 logic [11:0] distance_mm=700;
 wire signed [6:0] left_cm_s,right_cm_s,legacyL,legacyR;
 wire [3:0] state,legacyState;
 wire acquireFencePulse,taskDone;
 wire [31:0] scanElapsedUs,scanRemainingUs;
 wire [3:0] failureReason;
 int checks=0,tuples=0;
 motion_fsm #(.RUNTIME_TUNING(1),.RUNTIME_MOTION_POLICY(1),.ALLOW_BOUNDED_ALIGN_GAP(1)) dut(.*);
 motion_fsm #(.RUNTIME_TUNING(1),.ALLOW_BOUNDED_ALIGN_GAP(1)) legacy(
   .clk(clk),.reset(reset),.startPulse(startPulse),.cancel(cancel),.taskActive(taskActive),.safetyHalt(safetyHalt),
   .sourceHealthyFresh(sourceHealthyFresh),.targetObserved(targetObserved),.motionTargetValid(motionTargetValid),
   .distance_valid(distance_valid),.scanAllowed(scanAllowed),.zeroSent(zeroSent),.motionApplied(motionApplied),
   .timeUs(timeUs),.scanBudgetUs(scanBudgetUs),.tuningWord(tuningWord),.alignTimingWord(alignTimingWord),
   .motionPolicyWord(32'hffffffff),.centreU(centreU),.distance_mm(distance_mm),
   .left_cm_s(legacyL),.right_cm_s(legacyR),.state(legacyState),.acquireFencePulse(),.taskDone(),
   .scanElapsedUs(),.scanRemainingUs(),.failureReason());
 // This arbiter retains its fixed physical emergency limits for every policy.
 logic distanceSample=0,power_frame=0,estop_frame=0;
 wire permit,estop,sonar_stop;
 safety_arbiter guard(.clk(clk),.reset(reset),.power_frame(power_frame),.estop_frame(estop_frame),
   .motion_enable(left_cm_s!=0 || right_cm_s!=0),.taskArmed(taskActive),.cancel(cancel),.modePermit(1'b1),
   .distanceSample(distanceSample),.distance_valid(distance_valid),.distance_mm(distance_mm),
   .permit(permit),.taskEnabled(),.used(),.estop(estop),.sonar_stop(sonar_stop),.reason());
 task automatic ck(input bit ok,input string why);
   checks++;if(!ok)$fatal(1,"policy: %s state=%0d L=%0d R=%0d time=%0d",why,state,left_cm_s,right_cm_s,timeUs);
 endtask
 task automatic tick(input int n=1);
   repeat(n)begin @(negedge clk);timeUs++;@(posedge clk);#1;end
 endtask
 task automatic advance(input int us);
   @(negedge clk);timeUs=timeUs+32'(us);@(posedge clk);#1;
 endtask
 function automatic logic[31:0] packedPolicy(input int corridor,settle,stopMm,slowMm);
   return 32'(corridor/5)|(32'(settle/100)<<4)|(32'((stopMm-300)/10)<<9)|(32'((slowMm-500)/50)<<13);
 endfunction
 task automatic stopTask;
   cancel=1;taskActive=0;tick();cancel=0;tick();
 endtask
 task automatic beginTask;
   taskActive=1;startPulse=1;tick();startPulse=0;tick();
 endtask
 task automatic policy(input int corridor=45,settle=1500,stopMm=350,slowMm=500);
   stopTask();motionPolicyWord=packedPolicy(corridor,settle,stopMm,slowMm);tick();
 endtask
 task automatic clearSonar;
   repeat(3)begin distanceSample=1;tick();distanceSample=0;tick();end
 endtask
 initial begin
   tick(3);reset=0;tick();
   // Exhaust every accepted tuple against an independent integer reference.
   for(int c=45;c<=70;c+=5)for(int s=500;s<=2000;s+=100)
   for(int d=300;d<=400;d+=10)for(int f=500;f<=1000;f+=50)begin
     motionPolicyWord=packedPolicy(c,s,d,f);#1;
     ck(dut.motionPolicyValid && dut.approachCorridor==c && dut.acquireSettleUs==s*1000 &&
       dut.dockStopMm==d && dut.slowStartMm==f,"all four bounded shift/add decoders equal reference");tuples++;
   end
   policy();clearSonar();
   // Default policy must retain existing entry, steering and docking behavior.
   for(int u=45;u<=195;u+=15)begin
     stopTask();centreU=8'(u);distance_mm=700;beginTask();
     ck(state==legacyState && left_cm_s==legacyL && right_cm_s==legacyR,"default matches legacy at target positions");
   end
   policy(45);centreU=60;distance_mm=700;beginTask();ck(state==2,"45px corridor retains 60px error pivot");
   policy(70);centreU=60;beginTask();ck(state==3 && left_cm_s>0 && right_cm_s>0,"70px corridor permits continuous forward differential");
   centreU=50;tick();ck(state==3 && left_cm_s>0 && right_cm_s>0,"inclusive corridor edge remains forward");
   centreU=49;tick();ck(state==6 && left_cm_s==0 && right_cm_s==0,"outside corridor requires stationary reacquisition");
   policy(70,1500,400,800);centreU=120;distance_mm=801;beginTask();
   ck(state==3 && left_cm_s==5 && right_cm_s==5,"above configured slow distance uses drive speed");
   distance_mm=800;tick();ck(left_cm_s==4 && right_cm_s==4,"configured slow boundary uses fine speed");
   distance_mm=401;tick();ck(state==3 && left_cm_s==4 && right_cm_s==4,"above configured dock threshold approaches");
   distance_mm=400;#1;ck(left_cm_s==0 && right_cm_s==0,"dock boundary gates wheels without an extra state cycle");
   tick();ck(state==4 && taskDone,"configured dock boundary terminates task");
   distance_mm=700;tick(4);ck(state==4 && left_cm_s==0 && right_cm_s==0,"moving obstacle away cannot revive DOCKED");
   // Variable dwell never bypasses zero completion or the stationary frame fence.
   for(int ms=500;ms<=2000;ms+=500)begin
     policy(45,ms);centreU=120;distance_mm=700;targetObserved=0;motionTargetValid=0;beginTask();
     ck(state==1,"healthy no-target starts scan");targetObserved=1;tick();ck(state==6,"sighting enters acquisition");
     zeroSent=0;advance(ms*1000+100);ck(dut.acquirePhase==0 && !acquireFencePulse,"elapsed time alone cannot bypass completed zero");
     zeroSent=1;tick();ck(dut.acquirePhase==1,"zero completion starts dwell");
     advance(ms*1000-1);ck(dut.acquirePhase==1 && !acquireFencePulse,"new dwell has inclusive lower boundary");
     advance(1);ck(dut.acquirePhase==2 && acquireFencePulse,"configured dwell expiry requests new-frame fence");
     tick();ck(state==6,"observed but unconfirmed target cannot leave acquisition");
     motionTargetValid=1;tick();ck(state==3,"only current confirmed lock permits forward transition");
   end
   policy();centreU=120;distance_mm=700;targetObserved=1;motionTargetValid=1;clearSonar();beginTask();
   // Malformed words fail closed even if injected around a latched live task.
   begin logic[31:0] saved,bad;saved=motionPolicyWord;
     for(int k=0;k<8;k++)begin
       case(k)
         0:bad=saved|32'h00020000;1:bad=saved|32'h80000000;
         2:bad=(saved&~32'hf)|8;3:bad=(saved&~32'hf)|15;
         4:bad=(saved&~32'h1f0)|(4<<4);5:bad=(saved&~32'h1f0)|(21<<4);
         6:bad=(saved&~32'h1e00)|(11<<9);default:bad=(saved&~32'h1e000)|(11<<13);
       endcase
       motionPolicyWord=bad;#1;ck(!dut.motionPolicyValid && left_cm_s==0 && right_cm_s==0,"invalid policy immediately inhibits all wheel requests");
       motionPolicyWord=saved;#1;
     end
   end
   // Fixed physical safety remains 250/300mm, regardless of 400mm normal stop.
   policy(70,500,400,1000);distance_mm=700;beginTask();clearSonar();ck(permit,"motion authorized before physical near hazard");
   distance_mm=250;#1;ck(!permit,"250mm final safety gates immediately");tick();ck(sonar_stop,"near hazard latches HOLD");
   distance_mm=299;distanceSample=1;tick(4);distanceSample=0;ck(sonar_stop,"299mm cannot release physical hold");
   distance_mm=300;distanceSample=1;tick();distanceSample=0;tick();ck(sonar_stop,"first new 300mm sample remains held");
   distanceSample=1;tick();distanceSample=0;tick();ck(sonar_stop,"second new 300mm sample remains held");
   distanceSample=1;tick();distanceSample=0;tick();ck(!sonar_stop,"third new 300mm sample releases only physical hold");
   estop_frame=1;#1;ck(!permit,"IR A still overrides every policy");tick();estop_frame=0;tick();ck(estop,"IR stays latched");
   stopTask();power_frame=1;tick();power_frame=0;tick();ck(!estop && !permit,"POWER may clear IR but cannot itself grant this disarmed task");
   $display("PASS tb_motion_policy checks=%0d tuples=%0d",checks,tuples);$finish;
 end
 initial begin #5000000;$fatal(1,"motion policy watchdog");end
endmodule
