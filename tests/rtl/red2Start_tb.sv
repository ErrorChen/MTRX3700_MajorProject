`timescale 1ns/1ps
module red2Start_tb;
 import perception_pkg::*;
 logic red2Reset=0;
    logic clk=0,reset=1;always #10 clk=~clk;
 logic [31:0] timeUs=0;
 logic enable=1,permit=1,debugCalArm=0,debugSpeechArm=0;
 logic frameValid=0,frameGood=1,red1Paired=0,red2Seen=1,red2Present=1;
 logic [15:0] frameId=0,configVersion=0,activeCfgVersion=0,commitVersion=0;
 logic sampleResultValid=0,sampleGood=1,commitAck=0;
 wire collectEnable,commitRequest,calibrationAttempt,calibrated,speechArmed,busy,eventOverflow;
 wire [3:0] sampleCount;wire [15:0] interactionId;
 interactionKind_t kind;interactionState_t state;
 userEvent_t userEvent,held;wire userEventValid;logic userEventReady=1;
 integer starts=0,allEvents=0;
 fixedSheetInteraction #(.SAMPLE_TIMEOUT_US(1000)) dut(.*);
 always @(posedge clk)if(!reset)begin
   timeUs<=timeUs+1;
   if(speechArmed)$fatal(1,"red2 revived reserved speech state");
   if(userEventValid&&userEventReady)begin
     allEvents++;
     if(userEvent.eventType==EVENT_START_REQUEST)begin
       starts++;
       if(userEvent.bayId!=INVALID_BAY_ID||userEvent.configVersion!=activeCfgVersion)
         $fatal(1,"red2 must request physical selection, never a guessed bay");
     end
   end
 end
 task automatic tick(input integer n=1);repeat(n)@(negedge clk);endtask
 task automatic frame(input bit uniqueRed2,input bit present,input bit good=1,input bit increment=1);
   @(negedge clk);red2Seen=uniqueRed2;red2Present=present;frameGood=good;
   if(increment)frameId++;frameValid=1;
   @(negedge clk);frameValid=0;tick(5);
 endtask
 task automatic restart;
   reset=1;enable=1;permit=1;frameValid=0;frameGood=1;red1Paired=0;
   debugCalArm=0;configVersion=0;activeCfgVersion=0;userEventReady=1;
   sampleResultValid=0;commitAck=0;frameId=0;starts=0;allEvents=0;
   tick(3);reset=0;tick(3);repeat(3)frame(0,0);
 endtask
 initial begin
   tick(3);reset=0;
   repeat(4)frame(1,1);
   if(starts)$fatal(1,"resident red2 at power-up armed a task");
   repeat(3)frame(0,0);
   frame(1,1);frame(1,1);if(starts)$fatal(1,"red2 started before three independent frames");
   frame(1,1);if(starts!=1||busy||kind!=KIND_NONE)$fatal(1,"red2 start event absent or claimed calibration busy");
   repeat(5)frame(1,1);
   if(starts!=1)$fatal(1,"resident red2 repeatedly started");
   // Duplicate red2 cannot stand in for physical removal.
   repeat(4)frame(0,1);repeat(3)frame(1,1);
   if(starts!=1)$fatal(1,"duplicate red2 falsely rearmed start");
   frame(0,0);frame(0,0);repeat(3)frame(1,1);
   if(starts!=1)$fatal(1,"two absent frames rearmed too early");
   repeat(3)frame(0,0);frame(1,1);frame(1,1);
   if(starts!=1)$fatal(1,"rearm reused old confirmation");
   frame(1,1);if(starts!=2)$fatal(1,"physical removal/reappearance failed");
   restart();frame(1,1);frame(1,1,1,0);frame(1,1,1,0);
   if(starts)$fatal(1,"duplicate frame IDs counted as independent");
   frame(1,1);frame(1,1,0);frame(1,1);frame(1,1);
   if(starts)$fatal(1,"bad frame did not break red2 confirmation");
   configVersion=1;frame(1,1);configVersion=0;frame(1,1);frame(1,1);
   if(starts)$fatal(1,"old-config frame did not break confirmation");
   // Freeze the event head under backpressure; state remains non-calibration.
   userEventReady=0;frame(1,1);held=userEvent;
   if(!userEventValid||busy||held.eventType!=EVENT_START_REQUEST)$fatal(1,"start event queue readiness");
   repeat(4)frame(1,1);
   if(userEvent!==held||!userEventValid||starts)$fatal(1,"held red2 event changed or consumed early");
   userEventReady=1;tick(5);if(starts!=1)$fatal(1,"start event delivered more than once");
   red2Reset=1;tick(2);red2Reset=0;
   if(userEventValid)$fatal(1,"already-consumed event revived on visual boundary");
   repeat(3)frame(1,1);if(starts!=1)$fatal(1,"red2 boundary did not require a new presentation");
   // Reset can cancel a prepared start before its FIFO insertion, without
   // modifying an already presented ready/valid head.
   restart();frame(1,1);frame(1,1);
   @(negedge clk);frameId++;frameValid=1;red2Seen=1;red2Present=1;
   @(negedge clk);frameValid=0;red2Reset=1;tick(2);red2Reset=0;tick(4);
   if(userEventValid||starts)$fatal(1,"visual boundary queued an old pending start");
   // Red1 wins a simultaneous confirmation. Red2 shown during calibration is
   // consumed as a presence episode and needs removal after commit/cancellation.
   restart();red1Paired=1;
   repeat(3)frame(1,1);
   if(!busy||!collectEnable||starts)$fatal(1,"red1 did not take priority over red2");
   red2Reset=1;tick(2);red2Reset=0;
   if(!busy||!collectEnable)$fatal(1,"red2 boundary reset cancelled calibration");
   repeat(3)frame(1,1);permit=0;tick(5);permit=1;red1Paired=0;
   repeat(4)frame(1,1);
   if(starts)$fatal(1,"busy/cancelled calibration queued a latent start");
   repeat(3)frame(0,0);repeat(3)frame(1,1);
   if(starts!=1||speechArmed)$fatal(1,"fresh red2 after calibration cancellation failed");
   $display("PASS red2Start_tb three-frame unique event, resident latch, physical rearm, backpressure, calibration exclusion, no speech");
   $finish;
 end
 initial begin #200000;$fatal(1,"red2 start watchdog");end
endmodule
