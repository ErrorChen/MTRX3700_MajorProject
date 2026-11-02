`timescale 1ns/1ps
// PROTOCOL_CONFIG_INJECTION: drive completed-frame statistics and interaction
// controls at their module boundaries. No pixel, camera or calibration-quality
// claim is made here. The core's currentSample/sampleGood/applyCommit decisions,
// shadow registers, active profile and bank metadata are never forced.
module perceptionCoreCalibration_tb;
    import candidate_pkg::*;
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
    logic [1:0] orientationProfile=0;
    targetRequest_t targetRequest='0;
    logic targetRequestValid=0,targetRequestReady;
    targetReport_t targetReport;
    logic targetReportValid,targetReportReady=1;
    userEvent_t userEvent;
    logic userEventValid,userEventReady=1;
    perceptionStatus_t status;
    logic [3071:0] debugWords;
    logic completedFrame;
    logic [15:0] completedFrameId;
    logic [79:0] sofDrive=0;
    logic aggregateDrive=0,collectDrive=1,attemptDrive=0,commitDrive=0,pairedDrive=1;
    logic [15:0] interactionDrive=1;
    logic [3:0] sampleCountDrive=0;
    frameObservation_t completionDrive;
    candidate_t redBoxDrive,blueBoxDrive;
    integer checks=0,acceptedSamples=0,rejectedSamples=0,ignoredSamples=0;
    integer expectedRedMin=255,expectedBlueMin=255,expectedRedMax=0,expectedBlueMax=0;
    perceptionCore dut(.*);
    always @(posedge clk) if(!reset)timeUs<=timeUs+1;

    task automatic tick;
        @(posedge clk);#1;
    endtask
    task automatic checkWindow;
        if(dut.shadowRedMinimum!=expectedRedMin || dut.shadowBlueMinimum!=expectedBlueMin ||
           dut.windowRedMaximum!=expectedRedMax || dut.windowBlueMaximum!=expectedBlueMax)
            $fatal(1,"Sampling window changed incorrectly min=%0d/%0d max=%0d/%0d expected=%0d/%0d %0d/%0d",
                dut.shadowRedMinimum,dut.shadowBlueMinimum,dut.windowRedMaximum,dut.windowBlueMaximum,
                expectedRedMin,expectedBlueMin,expectedRedMax,expectedBlueMax);
        checks++;
    endtask
    task automatic newWindow;
        @(negedge clk);attemptDrive=1;sampleCountDrive=0;
        tick();
        expectedRedMin=255;expectedBlueMin=255;expectedRedMax=0;expectedBlueMax=0;
        checkWindow();
        @(negedge clk);attemptDrive=0;
    endtask
    task automatic sample(input integer redFloor,blueFloor,input bit expectCurrent,expectGood);
        @(negedge clk);
        completionDrive.frameId=completionDrive.frameId+1;
        dut.bankSampleRedMin[0]=8'(redFloor);dut.bankSampleBlueMin[0]=8'(blueFloor);
        aggregateDrive=1;
        #1;
        if(dut.currentSample!==expectCurrent || dut.sampleGood!==expectGood)
            $fatal(1,"Sample guards current/good=%b/%b expected=%b/%b floor=%0d/%0d",
                dut.currentSample,dut.sampleGood,expectCurrent,expectGood,redFloor,blueFloor);
        if(expectCurrent && expectGood && !attemptDrive)begin
            if(redFloor<expectedRedMin)expectedRedMin=redFloor;
            if(blueFloor<expectedBlueMin)expectedBlueMin=blueFloor;
            if(redFloor>expectedRedMax)expectedRedMax=redFloor;
            if(blueFloor>expectedBlueMax)expectedBlueMax=blueFloor;
            acceptedSamples++;
        end else if(expectCurrent) rejectedSamples++;
        else ignoredSamples++;
        if(attemptDrive)begin
            expectedRedMin=255;expectedBlueMin=255;expectedRedMax=0;expectedBlueMax=0;
        end
        tick();checkWindow();
        @(negedge clk);aggregateDrive=0;
        if(expectCurrent && expectGood && !attemptDrive)sampleCountDrive=sampleCountDrive+1;
    endtask
    task automatic sof(input integer id);
        @(negedge clk);sofDrive='0;sofDrive[79]=1;
        sofDrive[49:34]=16'(id);sofDrive[33:2]=timeUs;
        tick();
    endtask
    task automatic checkActive(input integer version,redFloor,blueFloor,input bit ack);
        if(dut.configVersion!=version || dut.activeRedMinimum!=redFloor ||
           dut.activeBlueMinimum!=blueFloor || dut.commitAck!==ack)
            $fatal(1,"Atomic commit mismatch cfg=%0d floor=%0d/%0d ack=%b expected=%0d %0d/%0d %b",
                dut.configVersion,dut.activeRedMinimum,dut.activeBlueMinimum,dut.commitAck,
                version,redFloor,blueFloor,ack);
        if(sofDrive[79] && (dut.captureMeta.configVersion!=version ||
           dut.bankRedMinimum[dut.writeBank]!=redFloor || dut.bankBlueMinimum[dut.writeBank]!=blueFloor))
            $fatal(1,"SOF bank metadata/profile disagrees with effective commit");
        checks++;
    endtask
    initial begin
        completionDrive='0;completionDrive.frameGood=1;
        redBoxDrive='0;redBoxDrive.valid=1;redBoxDrive.xmin=20;redBoxDrive.xmax=80;
        redBoxDrive.ymin=30;redBoxDrive.ymax=100;
        blueBoxDrive=redBoxDrive;blueBoxDrive.ymin=105;blueBoxDrive.ymax=120;
        repeat(5)@(negedge clk);reset=0;resetPclk=0;
        force dut.streamData=sofDrive;
        force dut.sof=sofDrive[79];
        force dut.readerBusy=1'b1;
        force dut.readerDone=1'b0;
        force dut.aggregateDone=aggregateDrive;
        force dut.readBank=1'b0;
        force dut.processedObservation=completionDrive;
        force dut.collectEnable=collectDrive;
        force dut.calibrationAttempt=attemptDrive;
        force dut.interactionId=interactionDrive;
        force dut.sampleCount=sampleCountDrive;
        force dut.commitRequest=commitDrive;
        force dut.red1Paired=pairedDrive;
        force dut.pairRed=redBoxDrive;
        force dut.pairBlue=blueBoxDrive;
        @(negedge clk);
        dut.bankSampling[0]=1;dut.bankInteractionId[0]=1;dut.bankSampleGood[0]=1;
        dut.bankSampleRed[0]=redBoxDrive;dut.bankSampleBlue[0]=blueBoxDrive;
        checkWindow();

        // The full-window maximum prevents a gradual downward ratchet from
        // passing the former comparison against only the running minimum.
        newWindow();sample(100,90,1,1);sample(80,70,1,1);sample(60,50,1,0);
        sample(76,66,1,1); // inclusive 24-unit full-window span
        sample(75,66,1,0);sample(76,65,1,0); // red and blue checked independently
        sample(101,90,1,0);sample(100,91,1,0); // upward full-window span

        // Valid-looking old or cancelled work cannot contaminate the current
        // window. Returning the ownership/configuration gates restores access.
        collectDrive=0;sample(78,68,0,1);collectDrive=1;
        @(negedge clk);dut.bankSampling[0]=0;
        sample(78,68,0,1);
        @(negedge clk);dut.bankSampling[0]=1;dut.bankInteractionId[0]=0;
        sample(78,68,0,1);
        @(negedge clk);dut.bankInteractionId[0]=1;completionDrive.configVersion=16'hffff;
        sample(78,68,0,1);
        @(negedge clk);completionDrive.configVersion=0;
        sample(78,68,1,1);
        pairedDrive=0;sample(78,68,1,0);pairedDrive=1;
        @(negedge clk);dut.bankSampleGood[0]=0;
        sample(78,68,1,0);
        @(negedge clk);dut.bankSampleGood[0]=1;completionDrive.frameGood=0;
        sample(78,68,1,0);
        @(negedge clk);completionDrive.frameGood=1;dut.bankSampleRed[0].xmin=24;
        sample(78,68,1,0);
        @(negedge clk);dut.bankSampleRed[0]=redBoxDrive;dut.bankSampleBlue[0].ymax=124;
        sample(78,68,1,0);
        @(negedge clk);dut.bankSampleBlue[0]=blueBoxDrive;

        // A reset pulse for a new attempt wins over even an otherwise eligible
        // completion on that edge; no stale minimum survives the reset.
        attemptDrive=1;sampleCountDrive=0;sample(50,40,1,1);
        @(negedge clk);attemptDrive=0;interactionDrive=2;
        sample(50,40,0,1);
        @(negedge clk);dut.bankInteractionId[0]=2;
        sample(50,40,1,1);sample(44,34,1,1);
        checkActive(0,48,20,0);

        // Revocation is already visible in the commit domain. It wins even
        // while the request is held high; the entire active profile stays old.
        collectDrive=0;commitDrive=1;interactionPermit=0;
        sof(1);checkActive(0,48,20,0);
        if(dut.commitConsumed)$fatal(1,"revoked commit consumed pending request");
        interactionPermit=1;interactionEnable=0;
        sof(2);checkActive(0,48,20,0);
        interactionEnable=1;
        sof(3);checkActive(1,44,34,1);
        if(!dut.commitConsumed)$fatal(1,"successful commit was not consumed");
        // No low request cycle and no gap between SOF pulses: only the first
        // edge commits. This stresses the ack-consumption race deliberately.
        sof(4);checkActive(1,44,34,0);
        sof(5);checkActive(1,44,34,0);
        @(negedge clk);sofDrive=0;commitDrive=0;
        tick();
        if(dut.commitConsumed)$fatal(1,"new transaction cannot reopen after request drops");

        // A distinct transaction may commit, and SOF must latch the collecting
        // attempt identity on both initial allocation and truncated-bank reuse.
        newWindow();collectDrive=1;interactionDrive=3;
        @(negedge clk);dut.bankSampling[0]=1;dut.bankInteractionId[0]=3;completionDrive.configVersion=1;
        sample(42,32,1,1);sample(40,30,1,1);
        commitDrive=1;
        sof(6);checkActive(2,40,30,1);
        if(dut.bankInteractionId[dut.writeBank]!=3 || !dut.bankSampling[dut.writeBank])
            $fatal(1,"SOF lost sampling attempt ownership");
        interactionDrive=4;sof(7);checkActive(2,40,30,0);
        if(dut.bankInteractionId[dut.writeBank]!=4)
            $fatal(1,"reclaimed capture retained previous attempt identity");
        $display("PASS perceptionCoreCalibration_tb checks=%0d accepted=%0d rejected=%0d ignored=%0d source=PROTOCOL_CONFIG_INJECTION",
            checks,acceptedSamples,rejectedSamples,ignoredSamples);
        $finish;
    end
    initial begin #1000000;$fatal(1,"Calibration protocol regression timeout");end
endmodule
