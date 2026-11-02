`timescale 1ns/1ps
module fixedSheetInteraction_tb;
    import perception_pkg::*;
    logic clk=0,reset=1;
    always #10 clk=~clk;
    logic [31:0] timeUs=0;
    logic enable=1,permit=1,debugCalArm=0,debugSpeechArm=0;
    logic frameValid=0,frameGood=1,red1Paired=1,red2Seen=1;
    logic [15:0] frameId=0,configVersion=0,activeCfgVersion=0;
    logic sampleResultValid=0,sampleGood=1,commitAck=0;
    logic [15:0] commitVersion=0;
    logic collectEnable,commitRequest,calibrationAttempt;
    logic [3:0] sampleCount;
    logic calibrated,speechArmed,busy,eventOverflow;
    interactionKind_t kind;
    interactionState_t state;
    logic [15:0] interactionId;
    userEvent_t userEvent,savedEvent;
    logic userEventValid,userEventReady=1;
    integer attempts=0,eventTotal=0;
    userEvent_t events[0:31];
    fixedSheetInteraction #(.WAIT_TIMEOUT_US(100),.SAMPLE_TIMEOUT_US(100),.COMMIT_TIMEOUT_US(100)) dut(.*);
    always @(posedge clk) begin
        if(!reset) begin
            if(calibrationAttempt) attempts++;
            if(userEventValid && userEventReady) begin events[eventTotal]=userEvent;eventTotal++;end
        end
    end
    task automatic tick;
        @(posedge clk);#1;
    endtask
    task automatic frame(input bit sample);
        @(negedge clk);frameId=frameId+1;frameValid=1;sampleResultValid=sample;
        tick();
        @(negedge clk);frameValid=0;sampleResultValid=0;
    endtask
    task automatic arm;
        @(negedge clk);debugCalArm=1;
        tick();
        @(negedge clk);debugCalArm=0;
    endtask
    task automatic beginAttempt;
        frame(0);frame(0);frame(0);
        if(!busy || !collectEnable || kind!=KIND_CALIBRATION) $fatal(1,"three real red1+own-blue frames start sampling");
    endtask
    task automatic samples;
        for(int n=1;n<=8;n++) begin
            frame(1);
            if(sampleCount!=n) $fatal(1,"sampling count %0d",n);
        end
        tick();
        if(!commitRequest || state!=INTERACTION_CAL_COMMIT) $fatal(1,"shadow profile not requested after eight samples");
    endtask
    task automatic flushEvent;
        repeat(4) tick();
    endtask
    initial begin
        repeat(3) tick();
        if(userEventValid || speechArmed || calibrated) $fatal(1,"reset state");
        @(negedge clk);reset=0;
        beginAttempt();
        if(speechArmed) $fatal(1,"red2 must not preempt calibration");
        samples();
        @(negedge clk);activeCfgVersion=1;configVersion=1;commitVersion=1;commitAck=1;
        tick();
        @(negedge clk);commitAck=0;
        flushEvent();
        if(!calibrated || busy || eventTotal!=1 || events[0].eventType!=EVENT_CALIBRATION_DONE ||
           events[0].eventId!=1 || events[0].configVersion!=1 || events[0].interactionId!=1)
            $fatal(1,"one committed calibration event");
        frame(0);frame(0);frame(0);
        if(!speechArmed || busy || kind!=KIND_NONE || state!=INTERACTION_SPEECH_ARMED)
            $fatal(1,"red2 in new config should arm without busy");
        repeat(10) frame(0);
        timeUs=5000;repeat(20) tick();
        if(attempts!=1 || eventTotal!=1 || busy || !speechArmed) $fatal(1,"stationary cards/silence must not repeat transactions");
        // Physical disappearance is an input condition; no computer flip is implied.
        red1Paired=0;red2Seen=0;frame(0);
        if(!speechArmed || !calibrated) $fatal(1,"leaving red cards must preserve committed state");
        @(negedge clk);permit=0;tick();
        if(!speechArmed || busy || eventTotal!=1) $fatal(1,"idle permit revoke is not cancellation");
        @(negedge clk);enable=0;tick();
        if(speechArmed || !calibrated) $fatal(1,"enable revoke clears only speech arm");
        @(negedge clk);enable=1;permit=1;red1Paired=1;red2Seen=1;
        frame(0);frame(0);frame(0);
        if(!speechArmed || attempts!=1) $fatal(1,"reenable requires red2, not another calibration");
        // Recalibration failure leaves the old committed profile and ends once.
        arm();beginAttempt();sampleGood=0;frame(1);sampleGood=1;flushEvent();
        if(!calibrated || eventTotal!=2 || events[1].eventType!=EVENT_CALIBRATION_FAILED ||
           events[1].configVersion!=1 || sampleCount!=0) $fatal(1,"failed sample changed committed state");
        repeat(6) frame(0);
        if(attempts!=2 || eventTotal!=2) $fatal(1,"failed stationary card repeatedly retried");
        // Permit withdrawal during sampling generates exactly one cancellation.
        arm();beginAttempt();frame(1);
        @(negedge clk);permit=0;#1;
        if(collectEnable) $fatal(1,"revoked sampling still enabled");
        tick();flushEvent();
        if(eventTotal!=3 || events[2].eventType!=EVENT_INTERACTION_CANCELLED ||
           events[2].reason!=REASON_PERMIT_REVOKED || !calibrated)
            $fatal(1,"sample cancellation");
        @(negedge clk);permit=1;
        // An already committed acknowledgement wins over a later same-cycle revoke.
        arm();beginAttempt();samples();
        @(negedge clk);permit=0;commitAck=1;commitVersion=2;activeCfgVersion=2;configVersion=2;
        tick();
        @(negedge clk);commitAck=0;
        flushEvent();
        if(eventTotal!=4 || events[3].eventType!=EVENT_CALIBRATION_DONE || events[3].configVersion!=2)
            $fatal(1,"acknowledged commit incorrectly rolled back");
        @(negedge clk);permit=1;
        // Duplicate sample frame IDs are not counted as eight independent samples.
        arm();beginAttempt();frame(1);
        @(negedge clk);sampleResultValid=1; // deliberately reuse current frameId
        tick();
        @(negedge clk);sampleResultValid=0;
        flushEvent();
        if(eventTotal!=5 || events[4].eventType!=EVENT_CALIBRATION_FAILED)
            $fatal(1,"same sample reused");
        // Four full events include the visible stalled head. No fifth attempt starts.
        userEventReady=0;
        for(int n=0;n<4;n++) begin
            arm();beginAttempt();sampleGood=0;frame(1);sampleGood=1;flushEvent();
            if(n==0) savedEvent=userEvent;
            if(!userEventValid || userEvent!==savedEvent) $fatal(1,"stalled event payload changed");
        end
        arm();frame(0);frame(0);frame(0);tick();
        if(!eventOverflow || busy || collectEnable) $fatal(1,"full FIFO must prevent new transaction");
        @(negedge clk);enable=0;userEventReady=1;
        flushEvent();
        if(eventTotal!=9) $fatal(1,"FIFO silently dropped events %0d",eventTotal);
        for(int n=0;n<eventTotal;n++)
            if(events[n].eventId!=n+1) $fatal(1,"event ids not contiguous");
        // WAIT_PERMIT is finite, whereas idle silence above never times out.
        @(negedge clk);enable=1;permit=0;timeUs=6000;
        arm();frame(0);frame(0);frame(0);
        if(state!=INTERACTION_WAIT_PERMIT || !busy) $fatal(1,"wait permit state");
        timeUs=6101;tick();flushEvent();
        if(eventTotal!=10 || events[9].eventType!=EVENT_INTERACTION_TIMEOUT ||
           events[9].reason!=REASON_WAIT_TIMEOUT) $fatal(1,"bounded wait timeout");
        $display("PASS fixedSheetInteraction_tb");
        $finish;
    end
    initial begin #200000; $fatal(1,"timeout fixedSheetInteraction_tb");end
endmodule
