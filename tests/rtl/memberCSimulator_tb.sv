`timescale 1ns/1ps
module memberCSimulator_tb;
    import perception_pkg::*;
    logic clk=0,reset=1;
    always #10 clk=~clk;
    logic [31:0] timeUs=1000;
    logic commandValid=0,commandReady,commandClear=0;
    logic [3:0] commandBayId=3;
    logic autoCycle=0,interactionEnable=1,interactionPermit=1;
    perceptionStatus_t status;
    targetRequest_t targetRequest,currentRequest,savedRequest;
    logic targetRequestValid,targetRequestReady=1;
    targetReport_t targetReport,cachedReport;
    logic targetReportValid=0,targetReportReady,measurementUsable;
    userEvent_t userEvent;
    logic userEventValid=0,userEventReady,acceptedEventPulse,rejectedEventPulse;
    memberCSimulator #(.MAX_AGE_US(100),.EVENT_MAX_AGE_US(1000),.CYCLE_PERIOD_US(2000)) dut(.*);
    task automatic tick;
        @(posedge clk); #1;
    endtask
    task automatic command(input integer bay);
        @(negedge clk); commandBayId=bay; commandValid=1;
        tick();
        @(negedge clk); commandValid=0;
        tick();
    endtask
    task automatic report(input integer id,input integer tag,input integer cfg,input bit seen);
        @(negedge clk); targetReport='0;
        targetReport.requestTag=tag; targetReport.frameId=id; targetReport.configVersion=cfg;
        targetReport.captureStartUs=timeUs; targetReport.bayId=currentRequest.bayId;
        targetReport.frameGood=1; targetReport.observed=seen; targetReport.locked=seen;
        targetReport.targetSelected=1; targetReport.centreU=22; targetReport.centreV=307;
        targetReportValid=1;
        tick();
        @(negedge clk); targetReportValid=0;
    endtask
    task automatic eventProposal(input integer id,input integer interaction,input integer issued);
        @(negedge clk); userEvent='0; userEvent.eventId=id;
        userEvent.eventType=EVENT_SPEECH_BAY_REQUEST; userEvent.bayId=5;
        userEvent.quality=200; userEvent.issuedAtUs=issued;
        userEvent.configVersion=status.activeCfgVersion; userEvent.interactionId=interaction;
        userEventValid=1;
        tick();
        @(negedge clk); userEventValid=0;
    endtask
    initial begin
        status='0; targetReport='0; userEvent='0;
        status.perceptionReady=1;
        tick();
        if(targetReportReady || userEventReady || targetRequestValid) $fatal(1,"C reset handshake");
        @(negedge clk); reset=0;
        tick(); command(3);
        if(currentRequest.bayId!=3 || currentRequest.requestTag!=1) $fatal(1,"C SELECT");
        report(1,1,0,1);
        if(!measurementUsable) $fatal(1,"valid current measurement");
        // Old tags/configs/duplicate or reverse frame packets cannot replace good cache.
        report(2,0,0,0); report(2,1,9,0); report(1,1,0,0); report(65535,1,0,0);
        if(!measurementUsable || cachedReport.frameId!=1) $fatal(1,"stale packet corrupted cache");
        timeUs=1101; #1;
        if(measurementUsable) $fatal(1,"cache expires without receiving another packet");
        timeUs=1102;
        report(2,1,0,1);
        if(!measurementUsable) $fatal(1,"new good measurement");
        report(3,1,0,0);
        if(measurementUsable) $fatal(1,"missing current report clears cache");
        report(4,1,0,1);
        status.interactionBusy=1; #1;
        if(measurementUsable) $fatal(1,"busy gates use");
        status.interactionBusy=0;status.speechArmed=1;status.state=INTERACTION_SPEECH_ARMED;#1;
        if(!measurementUsable) $fatal(1,"idle speech armed must allow observations");
        status.activeCfgVersion=1; tick();
        if(measurementUsable) $fatal(1,"config switch invalidates cache");
        // Request valid and payload remain stable while receiver refuses it.
        targetRequestReady=0;
        @(negedge clk);commandValid=1;commandBayId=4;
        tick(); savedRequest=targetRequest;
        @(negedge clk);commandValid=0;
        repeat(5) begin tick();if(!targetRequestValid || targetRequest!==savedRequest) $fatal(1,"request stall");end
        @(negedge clk);targetRequestReady=1;
        tick();
        if(currentRequest.bayId!=4 || measurementUsable) $fatal(1,"new request resets cache");
        // A speech event is only a proposal; C emits a separate SELECT transaction.
        status.interactionId=9;timeUs=2000;
        eventProposal(1,9,2000);
        if(!acceptedEventPulse || !targetRequestValid || targetRequest.bayId!=5) $fatal(1,"proposal-to-SELECT");
        tick();
        eventProposal(1,9,2000);
        if(!rejectedEventPulse || targetRequestValid) $fatal(1,"duplicate event");
        // Revoke during interaction: old queued and subsequently formed cancelled
        // interaction proposals are both rejected after permission is restored.
        status.interactionBusy=1;status.interactionId=10;timeUs=2100;
        @(negedge clk);interactionPermit=0;
        tick();
        @(negedge clk);interactionPermit=1;
        tick();
        status.interactionBusy=0;
        eventProposal(2,10,2101);
        if(!rejectedEventPulse) $fatal(1,"cancelled interaction revived");
        status.interactionId=11;
        eventProposal(3,11,2100);
        if(!rejectedEventPulse) $fatal(1,"pre-cancel queue result revived");
        timeUs=2200;
        eventProposal(4,11,2200);
        if(!acceptedEventPulse) $fatal(1,"fresh post-cancel interaction rejected");
        tick();
        // After old transactions have drained and a different session completed,
        // a legal interaction-ID reuse must not inherit an eternal cancel mark.
        status.interactionId=10;timeUs=2300;
        eventProposal(5,10,2300);
        if(!acceptedEventPulse) $fatal(1,"cancel tombstone prevented legal ID reuse");
        tick();
        // Counter wrap uses modular subtraction, never signed comparison of stamps.
        timeUs=32'hfffffff0;
        report(65535,currentRequest.requestTag,1,1);
        timeUs=32'h20; #1;
        if(!measurementUsable) $fatal(1,"valid time wrap");
        report(0,currentRequest.requestTag,1,1);
        if(!measurementUsable || cachedReport.frameId!=0) $fatal(1,"C frame wrap");
        @(negedge clk); targetReport.captureStartUs=32'h100;targetReport.frameId=1;targetReportValid=1;
        tick();
        if(measurementUsable) $fatal(1,"future timestamp accepted");
        $display("PASS memberCSimulator_tb");
        $finish;
    end
    initial begin #200000; $fatal(1,"timeout memberCSimulator_tb"); end
endmodule
