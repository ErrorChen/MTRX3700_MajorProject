`timescale 1ns/1ps
// PROTOCOL_CONFIG_INJECTION. Pixel classification is independently tested by
// replay benches. This bench controls SOF and reader completion boundaries to
// exercise raw-camera pause, bank cancellation, real tracker/FSM transactions,
// and three fresh confirmations after resumption. No camera accuracy claim.
module perceptionCorePause_tb;
 logic red2Reset=0; // No mode change in this pixel fixture.
    import perception_pkg::*;
    logic clk=0,pclk=0,reset=1,resetPclk=1;
    always #10 clk=~clk;
    always #25 pclk=~pclk;
    logic cameraFrameStart=0,cameraPixelValid=0;
    logic [15:0] cameraPixel=0;
    logic [9:0] cameraX=0;
    logic [8:0] cameraY=0;
    logic [31:0] timeUs=0;
    logic interactionEnable=1,interactionPermit=1,debugCalArm=0,debugSpeechArm=0;
    logic debugInteractionArmReady;
    logic [1:0] orientationProfile=0;
    logic bypassPerspective=0,processingEnable=1;
    targetRequest_t targetRequest='0;
    logic targetRequestValid=0,targetRequestReady;
    targetReport_t targetReport,heldReport;
    logic targetReportValid,targetReportReady=1;
    userEvent_t userEvent,heldEvent;
    logic userEventValid,userEventReady=0;
    perceptionStatus_t status;
    logic [DEBUG_WORD_COUNT*32-1:0] debugWords;
    logic completedFrame;
    logic [15:0] completedFrameId;
    logic [79:0] streamDrive=0;
    logic validDrive=0,candidateDrive=0,aggregateDrive=0,commitDrive=0,pairedDrive=1;
    logic readBankDrive=0;
    frameObservation_t completionDrive;
    integer capturedBank,checks=0;
    logic [31:0] rawCaptureUs;
    queryResult_t queryResult;
    logic queryResultValid,queryResultReady=1,queryBusy;
    perceptionCore dut(.*);
    always @(posedge clk)if(!reset)timeUs<=timeUs+1;

    task automatic tick;
        @(posedge clk);#1;
    endtask
    task automatic sendSof(input integer id);
        // The real PCLK-side counter must continue even while processing is
        // held reset. CLOCK_50 metadata is driven separately and explicitly.
        @(negedge pclk);cameraFrameStart=1;
        @(negedge pclk);cameraFrameStart=0;
        @(negedge clk);streamDrive='0;streamDrive[79]=1;validDrive=1;
        streamDrive[73:50]=dut.activeRequest;streamDrive[49:34]=16'(id);
        streamDrive[33:2]=timeUs;rawCaptureUs=timeUs;
        tick();capturedBank=dut.writeBank;
        @(negedge clk);validDrive=0;streamDrive=0;
    endtask
    task automatic completeNormal(input integer id,input bit expectedLocked);
        sendSof(id);
        if(!dut.haveWriteBank||!dut.activeProcessing)$fatal(1,"FAIL resume did not claim fresh writing bank");
        @(negedge clk);candidateDrive=1;
        tick();
        @(negedge clk);candidateDrive=0;
        dut.bankState[capturedBank]=dut.READING;
        completionDrive=dut.bankMeta[capturedBank];
        completionDrive.matchCount=1;completionDrive.xMin=100;completionDrive.xMax=150;
        completionDrive.yMin=60;completionDrive.yMax=120;completionDrive.quality=200;
        readBankDrive=1'(capturedBank);aggregateDrive=1;
        tick();
        if(!completedFrame||completedFrameId!=id||debugWords[7*32+21])
            $fatal(1,"FAIL normal completion metadata");
        @(negedge clk);aggregateDrive=0;
        tick();
        if(!targetReportValid||!targetReport.observed||targetReport.frameId!=id||
           targetReport.locked!==expectedLocked||!status.perceptionReady)
            $fatal(1,"FAIL three-frame resume confirmation frame%0d locked%0b reason%0d",id,targetReport.locked,targetReport.reason);
        checks++;
    endtask
    task automatic completeRaw(input integer id,input integer expectedConfig);
        @(negedge clk);streamDrive=0;validDrive=1;
        streamDrive[32:24]=319;streamDrive[23:16]=239;streamDrive[15:0]=16'hffff;
        tick();
        if(!completedFrame||completedFrameId!=id||debugWords[3*32+:16]!=id||
           debugWords[4*32+:32]!=rawCaptureUs||debugWords[6*32+:16]!=expectedConfig||
           !debugWords[7*32+21]||debugWords[(DEBUG_TAIL_BASE+3)*32+:32]!=0||debugWords[9*32+:32]!=0||
           dut.lastMarkers!='0||debugWords[(DEBUG_TAIL_BASE+2)*32+3+:5]!=0||status.perceptionReady||dut.haveWriteBank)
            $fatal(1,"FAIL raw same-frame empty metadata id%0d cfg%0d",id,expectedConfig);
        @(negedge clk);validDrive=0;streamDrive=0;
        repeat(3)tick();checks++;
    endtask
    initial begin
        completionDrive='0;
        repeat(5)@(negedge clk);reset=0;resetPclk=0;
        force dut.streamData=streamDrive;force dut.streamValid=validDrive;
        force dut.candidateValid=candidateDrive;force dut.candidateGood=1'b1;
        force dut.candidateOverflow=1'b0;
        force dut.readerBusy=1'b1;force dut.readerDone=1'b0;
        force dut.aggregateDone=aggregateDrive;force dut.processedObservation=completionDrive;
        force dut.readBank=readBankDrive;force dut.red1Paired=pairedDrive;
        force dut.pairReferenceIndex=4'd13;
        force dut.commitRequest=commitDrive;
        force dut.shadowRedMinimum=8'd90;force dut.shadowBlueMinimum=8'd91;
        @(negedge clk);targetRequest.operation=TARGET_SELECT;targetRequest.markerType=MARKER_BAY;targetRequest.digit=1;
        targetRequest.requestTag=16'h1234;targetRequestValid=1;
        tick();@(negedge clk);targetRequestValid=0;
        completeNormal(1,0);completeNormal(2,0);completeNormal(3,1);
        if(debugWords[(DEBUG_TAIL_BASE+2)*32+3+:5]!={4'd13,1'b1})
            $fatal(1,"FAIL setup did not publish reference annotation before pause");
        if(!dut.collectEnable)$fatal(1,"FAIL three real interaction observations did not start collection");
        @(negedge clk);targetReportReady=0;heldReport=targetReport;
        sendSof(4); // Truncated WRITING frame, plus an outstanding reader.
        dut.bankState[1-capturedBank]=dut.READING;
        @(negedge clk);processingEnable=0;commitDrive=1;aggregateDrive=1;
        #1;if(status.perceptionReady||dut.applyCommit||dut.debugInteractionArmReady)
            $fatal(1,"FAIL disable must immediately withdraw readiness and commit permission");
        sendSof(5);
        aggregateDrive=0;commitDrive=0;pairedDrive=0;
        if(dut.activeProcessing||dut.bankState[0]!=dut.FREE||dut.bankState[1]!=dut.FREE||
           dut.haveWriteBank||status.activeCfgVersion!=1||dut.activeRedMinimum!=48||dut.activeBlueMinimum!=20)
            $fatal(1,"FAIL pause ownership/profile/configuration boundary");
        completeRaw(5,1);
        if(!userEventValid||userEvent.eventType!=EVENT_INTERACTION_CANCELLED||userEvent.reason!=REASON_ENABLE_REVOKED)
            $fatal(1,"FAIL pause did not cancel pending calibration through existing event channel");
        heldEvent=userEvent;
        for(int sample=0;sample<12;sample++)begin
            @(negedge clk);validDrive=1;streamDrive=0;streamDrive[32:24]=9'(sample);
            streamDrive[23:16]=5;streamDrive[15:0]=sample[0]?16'hffff:16'hf800;
            tick();
            if(dut.rgb!=0||dut.runValid||dut.cleanValid||dut.readerStart||dut.glyphMemory.writeEnable||
               dut.collectEnable||dut.applyCommit||targetReport!==heldReport||!targetReportValid||
               userEvent!==heldEvent||!userEventValid)
                $fatal(1,"FAIL algorithms continued or stalled transaction changed in raw mode");
        end
        @(negedge clk);validDrive=0;streamDrive=0;
        sendSof(6);completeRaw(6,1);
        if(dut.cameraBridge.frameId!=6||dut.bufferDropCount!=0||dut.faults!=0)
            $fatal(1,"FAIL camera counter reset or intentional pause counted as transport failure");
        @(negedge clk);targetReportReady=1;
        repeat(4)tick();
        if(targetReport.frameId!=6||targetReport.observed||targetReport.locked||
           targetReport.centreU||targetReport.centreV||targetReport.boxWidth||targetReport.boxHeight||
           targetReport.quality||targetReport.reason!=REPORT_FRAME_BAD)
            $fatal(1,"FAIL disabled observation retained public measurements");
        @(negedge clk);processingEnable=1;
        #1;if(status.perceptionReady)$fatal(1,"FAIL readiness resumed before fresh SOF/completion");
        completeNormal(7,0);
        if(status.activeCfgVersion!=2||dut.activeRedMinimum!=48||dut.activeBlueMinimum!=20)
            $fatal(1,"FAIL resume must increment once and preserve complete calibration profile");
        completeNormal(8,0);completeNormal(9,1);
        if(status.activeCfgVersion!=2||dut.cameraBridge.frameId!=9||
           !userEventValid||userEvent!==heldEvent||debugWords[1*32+:32]!={16'(DEBUG_SCHEMA_VERSION),16'(PERCEPTION_CONTRACT_VERSION)})
            $fatal(1,"FAIL mode held/version/native identity/event preservation");
        $display("PASS perceptionCorePause_tb checks=%0d source=PROTOCOL_CONFIG_INJECTION",checks);
        $finish;
    end
    initial begin #2000000;$fatal(1,"FAIL raw-camera pause timeout");end
endmodule
