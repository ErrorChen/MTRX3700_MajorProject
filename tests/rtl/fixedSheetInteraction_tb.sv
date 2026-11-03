`timescale 1ns/1ps
module fixedSheetInteraction_tb;
    import perception_pkg::*;
    logic clk=0,reset=1;
    always #10 clk=~clk;
    logic [31:0] timeUs=0;
    logic enable=1,permit=1,debugCalArm=0,debugSpeechArm=0;
    logic frameValid=0,frameGood=1,red1Paired=1,red2Seen=1;
    logic [15:0] frameId=0,configVersion=0,activeCfgVersion=0;
    // Models perceptionCore's nonblocking configuration update at input SOF.
    // The interaction sees the old version on that edge, then the new version
    // immediately afterwards; this is different from changing it at negedge.
    logic switchConfigAtSampleEdge=0;
    always @(posedge clk)
        if(switchConfigAtSampleEdge) activeCfgVersion<=activeCfgVersion+16'd1;
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
    fixedSheetInteraction #(.WAIT_TIMEOUT_US(100),.SAMPLE_TIMEOUT_US(100),.COMMIT_TIMEOUT_US(100),
        .RETRY_DELAY_US(40)) dut(.*);
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
    task automatic restart(input logic [31:0] startUs);
        @(negedge clk);reset=1;
        frameValid=0;sampleResultValid=0;commitAck=0;debugCalArm=0;debugSpeechArm=0;
        enable=1;permit=1;frameGood=1;red1Paired=1;red2Seen=1;sampleGood=1;
        userEventReady=1;frameId=0;configVersion=0;activeCfgVersion=0;commitVersion=0;
        timeUs=startUs;switchConfigAtSampleEdge=0;
        repeat(2) tick();
        @(negedge clk);reset=0;attempts=0;eventTotal=0;
    endtask
    task automatic expectConfigurationFailure;
        flushEvent();
        if(eventTotal!=1 || events[0].eventType!=EVENT_CALIBRATION_FAILED ||
           events[0].reason!=REASON_CAL_SAMPLES_INVALID ||
           events[0].configVersion!=activeCfgVersion || collectEnable ||
           commitRequest || calibrated || busy)
            $fatal(1,"configuration change did not cancel the uncommitted window");
        repeat(4)tick();
        if(eventTotal!=1)$fatal(1,"configuration change produced duplicate terminal events");
    endtask
    task automatic badSample;
        @(negedge clk);sampleGood=0;
        frame(1);
        @(negedge clk);sampleGood=1;
        flushEvent();
    endtask
    task automatic finishCommit;
        @(negedge clk);activeCfgVersion=activeCfgVersion+1;
        configVersion=activeCfgVersion;commitVersion=activeCfgVersion;commitAck=1;
        tick();
        if(commitRequest) $fatal(1,"acknowledged request remained asserted");
        // An acknowledgement may remain asserted for more than one cycle.
        // The interaction must consume it once and queue one success only.
        repeat(3) begin tick();if(commitRequest) $fatal(1,"duplicate commit request after ack");end
        @(negedge clk);commitAck=0;
        flushEvent();
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

        // The real startup failure occurred after four valid sampling frames.
        // A later stable image must recover without a debug command. Keep C
        // stalled throughout both failures to check event episode coalescing.
        restart(100);userEventReady=0;
        beginAttempt();repeat(4) frame(1);badSample();
        if(calibrated || busy || collectEnable || !userEventValid || attempts!=1 ||
           sampleCount!=4 || userEvent.reason!=REASON_CAL_SAMPLES_INVALID)
            $fatal(1,"initial sample failure diagnostic/cooldown");
        savedEvent=userEvent;
        repeat(5) frame(0);
        timeUs=139;tick();frame(0);
        if(attempts!=1 || busy || userEvent!==savedEvent) $fatal(1,"retry before complete cooldown");
        timeUs=140;tick();
        frame(0);frame(0);
        if(collectEnable || attempts!=1) $fatal(1,"cooldown reused earlier card confirmation");
        frame(0);
        if(!collectEnable) $fatal(1,"fresh post-cooldown card did not restart initial sampling");
        badSample();
        if(attempts!=2 || busy || userEvent!==savedEvent || eventOverflow)
            $fatal(1,"same automatic failure overwrote stalled diagnostic");
        timeUs=180;tick();beginAttempt();samples();finishCommit();
        if(!calibrated || attempts!=3 || userEvent!==savedEvent || eventOverflow)
            $fatal(1,"automatic startup recovery did not commit once");
        @(negedge clk);userEventReady=1;
        flushEvent();
        if(eventTotal!=2 || events[0].eventType!=EVENT_CALIBRATION_FAILED ||
           events[0].interactionId!=1 || events[1].eventType!=EVENT_CALIBRATION_DONE ||
           events[1].interactionId!=3 || events[1].eventId!=2)
            $fatal(1,"coalesced episode lost first failure/final success or attempt identity");
        timeUs=5000;repeat(12) frame(0);
        if(attempts!=3 || eventTotal!=2 || !speechArmed || busy)
            $fatal(1,"successful recovery repeated with resident cards");

        // Cooldown arithmetic wraps at 2^32 microseconds. Revoked permission
        // cannot start a retry; after permission returns, both a bad frame and
        // an old-configuration frame independently break the confirmation run.
        restart(32'hfffffff0);beginAttempt();badSample();
        timeUs=32'h00000017;repeat(4) frame(0);
        if(attempts!=1 || busy) $fatal(1,"wrapped cooldown expired too early");
        @(negedge clk);permit=0;timeUs=32'h00000018;
        repeat(5) frame(0);
        if(attempts!=1 || busy || collectEnable) $fatal(1,"retry started without permit");
        @(negedge clk);permit=1;tick();
        frame(0);frame(0);
        @(negedge clk);frameGood=0;frame(0);
        @(negedge clk);frameGood=1;frame(0);frame(0);
        if(collectEnable) $fatal(1,"bad frame did not clear retry confirmation");
        @(negedge clk);configVersion=1;frame(0);
        @(negedge clk);configVersion=0;frame(0);frame(0);
        if(collectEnable) $fatal(1,"old configuration did not clear retry confirmation");
        frame(0);
        if(!collectEnable) $fatal(1,"wrap-safe permitted retry failed to start");
        frame(1);
        @(negedge clk);permit=0;tick();flushEvent();
        if(eventTotal!=2 || events[1].eventType!=EVENT_INTERACTION_CANCELLED ||
           events[1].reason!=REASON_PERMIT_REVOKED || collectEnable || commitRequest)
            $fatal(1,"automatic retry cancellation was coalesced or kept active");

        // A changed failure reason is a new observable diagnostic episode.
        restart(10);beginAttempt();badSample();
        timeUs=50;tick();beginAttempt();timeUs=151;tick();flushEvent();
        if(eventTotal!=2 || events[1].eventType!=EVENT_INTERACTION_TIMEOUT ||
           events[1].reason!=REASON_CAPTURE_TIMEOUT) $fatal(1,"changed automatic failure was hidden");

        // An explicit rearm owns one attempt even if no calibration has ever
        // succeeded. It cannot silently turn into an automatic retry sequence.
        restart(0);arm();beginAttempt();badSample();
        timeUs=10000;repeat(12) frame(0);
        if(attempts!=1 || eventTotal!=1 || busy || calibrated)
            $fatal(1,"failed explicit startup rearm retried automatically");

        // A collection attempt owns one configuration, including its time spent
        // waiting for permission. Granting permission cannot revive old geometry.
        restart(0);arm();permit=0;frame(0);frame(0);frame(0);
        if(state!=INTERACTION_WAIT_PERMIT)$fatal(1,"configuration WAIT setup");
        @(negedge clk);activeCfgVersion=1;permit=1;#1;
        if(collectEnable || commitRequest)$fatal(1,"changed WAIT configuration was enabled");
        tick();expectConfigurationFailure();

        // Mid-window mode/configuration changes stop the raw collection gate
        // immediately and produce one failure even before another frame arrives.
        restart(0);arm();beginAttempt();repeat(4)frame(1);
        @(negedge clk);activeCfgVersion=1;#1;
        if(collectEnable || commitRequest)$fatal(1,"old collection gate survived configuration change");
        tick();expectConfigurationFailure();

        // Regression for the observed review counterexample: the eighth valid
        // old-config sample and SW8/SOF version increment share the same clock.
        // Accepting this sample on that edge is harmless only if validation can
        // never turn the obsolete eight-sample set into a commit request.
        restart(0);arm();beginAttempt();repeat(7)frame(1);
        @(negedge clk);frameId=frameId+1;frameValid=1;sampleResultValid=1;
        switchConfigAtSampleEdge=1;tick();
        if(activeCfgVersion!=1 || sampleCount!=8 || state!=INTERACTION_CAL_VALIDATE)
            $fatal(1,"same-edge eighth-sample configuration stimulus was not exercised");
        @(negedge clk);frameValid=0;sampleResultValid=0;switchConfigAtSampleEdge=0;
        tick();
        if(commitRequest)$fatal(1,"eighth old-config sample requested commit after same-edge switch");
        expectConfigurationFailure();

        // A mode change after the final sample, or while waiting for the next
        // SOF commit, is equally invalid. These cover distinct FSM branches.
        restart(0);arm();beginAttempt();repeat(8)frame(1);
        if(state!=INTERACTION_CAL_VALIDATE)$fatal(1,"configuration VALIDATE setup");
        activeCfgVersion=1;tick();expectConfigurationFailure();
        restart(0);arm();beginAttempt();samples();
        @(negedge clk);activeCfgVersion=1;#1;
        if(commitRequest)$fatal(1,"obsolete pending commit was not gated immediately");
        tick();expectConfigurationFailure();

        // Equality, rather than ordered comparison, owns the configuration.
        // Acknowledged commits remain final, including 0xffff -> 0 wrap and a
        // simultaneous permit withdrawal; this must not be mistaken for failure.
        restart(0);activeCfgVersion=16'hffff;configVersion=16'hffff;
        arm();beginAttempt();samples();
        @(negedge clk);activeCfgVersion=0;configVersion=0;commitVersion=0;
        commitAck=1;permit=0;tick();
        @(negedge clk);commitAck=0;flushEvent();
        if(eventTotal!=1 || events[0].eventType!=EVENT_CALIBRATION_DONE ||
           events[0].configVersion!=0 || !calibrated || commitRequest)
            $fatal(1,"acknowledged wrapped commit was rolled back by configuration guard");
        $display("PASS fixedSheetInteraction_tb");
        $finish;
    end
    initial begin #200000; $fatal(1,"timeout fixedSheetInteraction_tb");end
endmodule
