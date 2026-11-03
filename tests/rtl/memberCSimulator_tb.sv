`timescale 1ns/1ps
module memberCSimulator_tb;
    import perception_pkg::*;
    logic clk=0,reset=1;
    always #10 clk=~clk;
    logic [31:0] timeUs=1000;
    logic commandValid=0,commandReady;
    targetOperation_t commandOperation=TARGET_SELECT;
    markerType_t commandMarkerType=MARKER_BAY;
    logic [3:0] commandDigit=3;
    logic autoCycle=0,interactionEnable=1,interactionPermit=1;
    perceptionStatus_t status;
    targetRequest_t targetRequest,currentRequest,savedRequest,savedCurrent;
    logic targetRequestValid,targetRequestReady=1;
    targetReport_t targetReport,cachedReport,savedReport;
    logic targetReportValid=0,targetReportReady,measurementUsable;
    userEvent_t userEvent;
    logic userEventValid=0,userEventReady,acceptedEventPulse,rejectedEventPulse;
    memberCSimulator #(.MAX_AGE_US(100),.EVENT_MAX_AGE_US(1000),.CYCLE_PERIOD_US(2000)) dut(.*);
    task automatic tick;
        @(posedge clk); #1;
    endtask
    task automatic typedCommand(input targetOperation_t op,input markerType_t kind,input integer digit);
        @(negedge clk);commandOperation=op;commandMarkerType=kind;commandDigit=4'(digit);commandValid=1;
        tick();
        @(negedge clk); commandValid=0;
        tick();
    endtask
    task automatic command(input integer bay);
        typedCommand(TARGET_SELECT,MARKER_BAY,bay);
    endtask
    task automatic report(input integer id,input integer tag,input integer cfg,input bit seen);
        @(negedge clk); targetReport='0;
        targetReport.requestTag=tag; targetReport.frameId=id; targetReport.configVersion=cfg;
        targetReport.captureStartUs=timeUs; targetReport.markerType=currentRequest.markerType;
        targetReport.digit=currentRequest.digit;
        targetReport.frameGood=1; targetReport.observed=seen; targetReport.locked=seen;
        targetReport.targetSelected=1;
        if(seen) begin
            targetReport.centreU=22;targetReport.centreV=307;
            targetReport.boxWidth=5;targetReport.boxHeight=4;targetReport.quality=220;
        end
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
        if(currentRequest.markerType!=MARKER_BAY || currentRequest.digit!=3 || currentRequest.requestTag!=1) $fatal(1,"C SELECT");
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
        @(negedge clk);commandValid=1;commandDigit=4;
        tick(); savedRequest=targetRequest;
        @(negedge clk);commandValid=0;
        repeat(5) begin tick();if(!targetRequestValid || targetRequest!==savedRequest) $fatal(1,"request stall");end
        @(negedge clk);targetRequestReady=1;
        tick();
        if(currentRequest.digit!=4 || measurementUsable) $fatal(1,"new request resets cache");
        // A speech event is only a proposal; C emits a separate SELECT transaction.
        status.interactionId=9;timeUs=2000;
        eventProposal(1,9,2000);
        if(!acceptedEventPulse || !targetRequestValid || targetRequest.markerType!=MARKER_BAY || targetRequest.digit!=5) $fatal(1,"proposal-to-SELECT");
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
        @(negedge clk);targetReportValid=0;
        for(int typed=1;typed<=3;typed++) begin
            typedCommand(TARGET_SELECT,typed==3?MARKER_REFERENCE:MARKER_FUNCTION,typed==3?15:typed);
            report(1,currentRequest.requestTag,status.activeCfgVersion,1);
            if(!measurementUsable || cachedReport.markerType!=currentRequest.markerType)
                $fatal(1,"typed red/reference usable observation");
        end
        // An unrelated query never changes the live target or its valid cache.
        savedCurrent=currentRequest;savedReport=cachedReport;
        typedCommand(TARGET_GET,MARKER_BAY,1);
        if(currentRequest!==savedCurrent || cachedReport!==savedReport || !measurementUsable)
            $fatal(1,"GET changed tracking cache/tag");
        typedCommand(TARGET_LIST,MARKER_NONE,15);
        if(currentRequest!==savedCurrent || cachedReport!==savedReport || !measurementUsable)
            $fatal(1,"LIST changed tracking cache/tag");
        // A held query request is stable, while the current tracking report can
        // still refresh independently. Queries share no cache sequence counter.
        @(negedge clk);targetRequestReady=0;commandOperation=TARGET_GET;
        commandMarkerType=MARKER_FUNCTION;commandDigit=1;commandValid=1;
        tick();savedRequest=targetRequest;
        @(negedge clk);commandValid=0;
        report(2,currentRequest.requestTag,status.activeCfgVersion,1);
        repeat(3) begin
            tick();
            if(!targetRequestValid || targetRequest!==savedRequest || currentRequest!==savedCurrent ||
               cachedReport.frameId!=2 || !measurementUsable) $fatal(1,"query stall affected live tracking");
        end
        @(negedge clk);targetRequestReady=1;
        tick();
        if(currentRequest!==savedCurrent || !measurementUsable) $fatal(1,"query acceptance replaced target");
        // Equal digit/tag is insufficient: an opposite-colour packet is not the
        // requested observation and cannot poison an otherwise current cache.
        typedCommand(TARGET_SELECT,MARKER_FUNCTION,1);
        report(1,currentRequest.requestTag,status.activeCfgVersion,1);savedReport=cachedReport;
        @(negedge clk);targetReport.markerType=MARKER_BAY;targetReport.frameId=2;targetReportValid=1;
        tick();
        if(cachedReport!==savedReport || !measurementUsable) $fatal(1,"wrong typed identity corrupted cache");
        @(negedge clk);targetReportValid=0;
        report(2,currentRequest.requestTag,status.activeCfgVersion,0);
        if(measurementUsable) $fatal(1,"red missing observation remained usable");
        typedCommand(TARGET_CLEAR,MARKER_REFERENCE,15);
        if(currentRequest.operation!=TARGET_CLEAR || currentRequest.markerType!=MARKER_NONE ||
           currentRequest.digit!=15 || measurementUsable) $fatal(1,"typed CLEAR");
        // Automatic cycling and speech remain explicitly bay-only stimuli.
        @(negedge clk);timeUs=10000;autoCycle=1;
        tick();
        if(!targetRequestValid || targetRequest.operation!=TARGET_SELECT ||
           targetRequest.markerType!=MARKER_BAY || targetRequest.digit!=1) $fatal(1,"auto cycle identity");
        @(negedge clk);autoCycle=0;
        tick();
        $display("PASS memberCSimulator_tb");
        $finish;
    end
    initial begin #200000; $fatal(1,"timeout memberCSimulator_tb"); end
endmodule
