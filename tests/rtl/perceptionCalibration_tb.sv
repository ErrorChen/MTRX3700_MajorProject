`timescale 1ns/1ps
// One hash-bound recorded native image drives the real colour/candidate/glyph,
// quad ownership, polygon sampling and interaction pipeline. Repetition is RTL
// stimulus from one acquisition, never additional CAMERA_HW evidence.
// Frames wait for their preceding report; this checks transaction sequencing.
// Independent continuous/overload benches check an unstalled source cadence.
module perceptionCalibration_tb;
    import perception_pkg::*;
    logic clk=0,pclk=0,reset=1,resetPclk=1;
    always #10 clk=~clk;
    initial begin #7;forever #25 pclk=~pclk;end
    logic cameraFrameStart=0,cameraPixelValid=0;
    logic [15:0] cameraPixel=0;
    logic [9:0] cameraX=0;
    logic [8:0] cameraY=0;
    logic [31:0] timeUs=0;
    logic interactionEnable=1,interactionPermit=1,debugCalArm=0,debugSpeechArm=0;
    logic [1:0] orientationProfile=0;
    logic bypassPerspective=0,processingEnable=1,debugInteractionArmReady;
    targetRequest_t targetRequest;
    logic targetRequestValid=0,targetRequestReady;
    targetReport_t targetReport,lastReport;
    logic targetReportValid,targetReportReady=1;
    userEvent_t userEvent;
    logic userEventValid,userEventReady=1;
    queryResult_t queryResult;
    logic queryResultValid,queryResultReady=1,queryBusy;
    perceptionStatus_t status;
    logic [DEBUG_WORD_COUNT*32-1:0] debugWords;
    logic completedFrame;
    logic [15:0] completedFrameId;
    perceptionCore dut(.*);
    logic [15:0] pixels[0:76799];
    string vectorDir,sceneFile;
    integer microDivider=0,reportCount=0,frameNumber=0,eventCount=0;
    integer commitCount=0,acceptedSamples=0,samplingFrames=0,checks=0;
    integer expectedEvent=EVENT_INTERACTION_CANCELLED;
    logic priorSof=0,priorCommit=0;
    logic [15:0] priorVersion=0;
    logic [7:0] priorRedShadow=0,priorBlueShadow=0;
    logic [31:0] sourceTime[1:64];
    logic [15:0] sourceVersion[1:64];
    logic sourceBypass[1:64];

    always @(posedge clk)begin
        if(reset)begin
            microDivider<=0;timeUs<=0;priorSof=0;priorCommit=0;priorVersion=0;
        end else begin
            if(microDivider==49)begin microDivider<=0;timeUs<=timeUs+1;end
            else microDivider<=microDivider+1;
            if(dut.configVersion!=priorVersion)begin
                checks++;
                if(!priorSof||dut.configVersion!=priorVersion+16'd1)
                    $fatal(1,"configuration changed away from SOP or skipped version");
            end
            if(dut.commitAck)begin
                commitCount++;checks++;
                if(!priorSof||!priorCommit||dut.activeRedMinimum!=priorRedShadow||
                   dut.activeBlueMinimum!=priorBlueShadow)
                    $fatal(1,"profile commit was not atomic at SOP");
            end
            if(dut.sof)begin
                integer id;
                id=int'(dut.streamData[49:34]);
                if(id<1||id>64)$fatal(1,"unexpected source frame identity");
                sourceTime[id]=dut.streamData[33:2];
                sourceVersion[id]=dut.configVersion+16'(dut.applyCommit||dut.activeBypass!=bypassPerspective||dut.activeOrientation!=orientationProfile||dut.processingModeChange);
                sourceBypass[id]=bypassPerspective;
                if(dut.applyCommit||dut.activeBypass!=bypassPerspective||dut.activeOrientation!=orientationProfile)begin
                    checks++;
                    if(dut.sampleRoiAvailable)$fatal(1,"old polygon accepted at profile-changing SOP");
                end
                if(dut.collectEnable&&dut.sampleRoiAvailable)samplingFrames++;
            end
            if(dut.currentSample)begin
                checks++;
                if(dut.bankMeta[dut.readBank].configVersion!=dut.configVersion||
                   dut.bankInteractionId[dut.readBank]!=dut.interactionId)
                    $fatal(1,"sample result crossed configuration or interaction ownership");
                if(dut.sampleGood)begin
                    acceptedSamples++;checks++;
                    if(dut.bankSampleProjective[dut.readBank]!==!dut.bankBypass[dut.readBank]||
                       (!dut.bankBypass[dut.readBank]&&(!dut.bankRedPolygon[dut.readBank].valid||!dut.bankBluePolygon[dut.readBank].valid)))
                        $fatal(1,"accepted sample lacks matching projective geometry");
                end
                $display("CAL_SAMPLE frame=%0d cfg=%0d good=%0d countBefore=%0d red=%0d blue=%0d checks=%b projective=%0d redMinimum=%0d blueMinimum=%0d",
                    dut.processedObservation.frameId,dut.processedObservation.configVersion,dut.sampleGood,dut.sampleCount,
                    dut.bankRedSamples[dut.readBank],dut.bankBlueSamples[dut.readBank],
                    {dut.sampleWindowGood,dut.sampleGeometryGood,dut.red1Paired,dut.processedObservation.frameGood,dut.bankSampleGood[dut.readBank]},
                    dut.bankSampleProjective[dut.readBank],dut.bankSampleRedMin[dut.readBank],dut.bankSampleBlueMin[dut.readBank]);
            end
            if(targetReportValid&&targetReportReady)begin
                lastReport=targetReport;reportCount++;checks++;
                if(targetReport.frameId<1||targetReport.frameId>64||
                   targetReport.captureStartUs!=sourceTime[targetReport.frameId]||
                   targetReport.configVersion!=sourceVersion[targetReport.frameId])
                    $fatal(1,"report lost source frame/time/config identity");
                $display("CAL_FRAME id=%0d cfg=%0d observed=%0d locked=%0d samples=%0d state=%0d pair=%0d tag=%0d digit=%0d centreU=%0d centreV=%0d redMinimum=%0d blueMinimum=%0d",
                    targetReport.frameId,targetReport.configVersion,targetReport.observed,targetReport.locked,
                    dut.sampleCount,status.state,dut.red1Paired,targetReport.requestTag,targetReport.digit,
                    targetReport.centreU,targetReport.centreV,dut.activeRedMinimum,dut.activeBlueMinimum);
            end
            if(userEventValid&&userEventReady)begin
                eventCount++;checks++;
                if(userEvent.eventType!=expectedEvent)
                    $fatal(1,"unexpected calibration event type=%0d reason=%0d wanted=%0d",userEvent.eventType,userEvent.reason,expectedEvent);
                if(expectedEvent==EVENT_INTERACTION_CANCELLED&&userEvent.reason!=REASON_PERMIT_REVOKED)
                    $fatal(1,"permit cancellation reason missing");
                if(expectedEvent==EVENT_CALIBRATION_FAILED&&userEvent.reason!=REASON_CAL_SAMPLES_INVALID)
                    $fatal(1,"profile-switch failure reason missing");
                $display("CAL_EVENT type=%0d reason=%0d cfg=%0d interaction=%0d",userEvent.eventType,userEvent.reason,userEvent.configVersion,userEvent.interactionId);
            end
            priorSof=dut.sof;priorCommit=dut.applyCommit;
            priorVersion=dut.configVersion;priorRedShadow=dut.shadowRedMinimum;priorBlueShadow=dut.shadowBlueMinimum;
        end
    end

    task automatic selectBay(input integer bay,input integer tag);
        @(negedge clk);targetRequest.operation=TARGET_SELECT;targetRequest.markerType=MARKER_BAY;
        targetRequest.digit=4'(bay);targetRequest.requestTag=16'(tag);targetRequestValid=1;
        do @(posedge clk);while(!targetRequestReady);
        @(negedge clk);targetRequestValid=0;repeat(20)@(negedge pclk);
    endtask
    task automatic frame(input bit switchDuringCapture=0);
        integer wantedReports,waitCycles;
        begin
            wantedReports=reportCount+1;frameNumber++;
            @(negedge pclk);cameraFrameStart=1;
            @(negedge pclk);cameraFrameStart=0;repeat(8)@(negedge pclk);
            for(int py=0;py<240;py++)begin
                if(switchDuringCapture&&py==100)bypassPerspective=1;
                for(int px=0;px<320;px++)begin
                    cameraX=10'(2*px);cameraY=9'(2*py);cameraPixel=pixels[py*320+px];cameraPixelValid=1;
                    @(negedge pclk);cameraPixelValid=0;repeat(3)@(negedge pclk);
                end
                // Explicit sensor-like maintenance time, not a zero-gap fake stream.
                repeat(150)@(negedge pclk);
            end
            waitCycles=0;
            while((reportCount<wantedReports||lastReport.frameId!=frameNumber)&&waitCycles<2000000)begin
                @(negedge clk);waitCycles++;
            end
            if(reportCount<wantedReports||lastReport.frameId!=frameNumber||!lastReport.frameGood)
                $fatal(1,"calibration core frame timeout/bad frame=%0d",frameNumber);
            if(dut.bufferDropCount||dut.candidateOverflow||dut.candidateOverrun||dut.transportFault)
                $fatal(1,"calibration replay violated source/candidate/bank capacity");
            repeat(20)@(negedge clk);
        end
    endtask
    task automatic armCalibration;
        if(!debugInteractionArmReady)$fatal(1,"calibration rearm not accepted in idle");
        @(negedge clk);debugCalArm=1;
        @(negedge clk);debugCalArm=0;repeat(5)@(negedge clk);
    endtask
    task automatic awaitEvents(input integer count);
        integer waitCycles;
        begin
            waitCycles=0;
            while(eventCount<count&&waitCycles<100)begin @(negedge clk);waitCycles++;end
            if(eventCount!=count)$fatal(1,"missing or duplicate terminal event wanted=%0d got=%0d",count,eventCount);
        end
    endtask

    initial begin
        targetRequest='0;lastReport='0;
        if(!$value$plusargs("VECTOR_DIR=%s",vectorDir))vectorDir="vectors";
        if(!$value$plusargs("SCENE_FILE=%s",sceneFile))sceneFile={vectorDir,"/calibration_scene_rgb565.hex"};
        $readmemh(sceneFile,pixels);
        repeat(10)@(negedge pclk);reset=0;resetPclk=0;selectBay(3,1);

        // A real eight-frame sample window reaches commit intent, then permit
        // is revoked before the next SOP. Neither threshold may change.
        for(int n=0;n<11;n++)frame();
        if(dut.sampleCount!=8||!dut.commitRequest||dut.configVersion!=0)
            $fatal(1,"eight real sample frames did not reach uncommitted intent");
        @(negedge clk);interactionPermit=0;awaitEvents(1);
        frame();
        if(dut.configVersion!=0||dut.activeRedMinimum!=48||dut.activeBlueMinimum!=20||status.calibrated||commitCount)
            $fatal(1,"permit revoke committed or contaminated reset profile");

        // A mid-frame SW8 change cannot relabel the current polygon sample.
        // The next SOP changes version and suppresses the old sampling ROI.
        interactionPermit=1;expectedEvent=EVENT_CALIBRATION_FAILED;armCalibration();
        for(int n=0;n<3;n++)frame();
        frame();
        if(dut.sampleCount!=1)$fatal(1,"second attempt did not collect first sample");
        frame(1);
        if(dut.configVersion!=0||dut.sampleCount!=2)
            $fatal(1,"mid-frame profile switch changed current-frame metadata");
        frame();awaitEvents(2);
        if(dut.configVersion!=1||dut.activeRedMinimum!=48||dut.activeBlueMinimum!=20||commitCount)
            $fatal(1,"mixed profile sample polluted calibration thresholds");
        bypassPerspective=0;expectedEvent=EVENT_NONE;frame();
        if(dut.configVersion!=2)$fatal(1,"normal profile restore not versioned at SOP");

        // Reopen through the real command, recognise red1 again, collect eight
        // new observations, commit at SOP and recognise red2 under that profile.
        expectedEvent=EVENT_CALIBRATION_DONE;armCalibration();
        for(int n=0;n<11;n++)frame();
        if(dut.sampleCount!=8||!dut.commitRequest||dut.configVersion!=2)
            $fatal(1,"fresh normal-profile calibration did not reach commit");
        frame();awaitEvents(3);
        if(dut.configVersion!=3||commitCount!=1||!status.calibrated||lastReport.locked)
            $fatal(1,"new calibration version did not commit/unlock tracking");
        for(int n=0;n<3;n++)frame();
        if(!lastReport.observed||!lastReport.locked||!status.speechArmed||status.interactionBusy||eventCount!=3)
            $fatal(1,"post-commit tracking/idle arming did not recover");
        if(acceptedSamples!=18||commitCount!=1)
            $fatal(1,"sample/commit accounting mismatch samples=%0d commits=%0d",acceptedSamples,commitCount);
        // Exercise the real C request channel for every enabled bay. No input
        // command supplies a pixel label; three distinct newly streamed frame
        // IDs must confirm each selected blue digit after the request changes.
        expectedEvent=EVENT_NONE;
        for(int bay=1;bay<=6;bay++)begin
            selectBay(bay,10+bay);
            for(int n=1;n<=3;n++)begin
                frame();checks++;
                if(!lastReport.observed||lastReport.digit!=bay||lastReport.markerType!=MARKER_BAY||
                   lastReport.requestTag!=10+bay||lastReport.configVersion!=3||lastReport.locked!=(n==3))
                    $fatal(1,"recorded pixel-to-report bay selection bay=%0d confirmation=%0d",bay,n);
            end
        end
        if(eventCount!=3||commitCount!=1||!status.speechArmed||status.interactionBusy)
            $fatal(1,"stationary red cards retriggered calibration or blocked observations");
        $display("PASS perceptionCalibration_tb frames=%0d checks=%0d acceptedSamples=%0d samplingFrames=%0d commits=%0d events=%0d source=ONE_RECORDED_FRAME_REPEATED_IN_RTL",frameNumber,checks,acceptedSamples,samplingFrames,commitCount,eventCount);
        $finish;
    end
    initial begin #4000000000;$fatal(1,"perception calibration global timeout");end
endmodule
