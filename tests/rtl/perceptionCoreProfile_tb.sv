`timescale 1ns/1ps
// Protocol/configuration injection only. This bench does not claim pixel or
// CAMERA_HW recognition. It uses real SOF/bank metadata logic and controls the
// completion edge to reproduce configuration changes around a held old bank.
module perceptionCoreProfile_tb;
 logic red2Reset=0; // No mode change in this pixel fixture.
    logic bypassPerspective=0;
    logic processingEnable=1;
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
    logic [DEBUG_WORD_COUNT*32-1:0] debugWords;
    logic completedFrame;
    logic [15:0] completedFrameId;
    logic [79:0] sofDrive=0;
    logic commitDrive=0,aggregateDrive=0,candidateDrive=0,readBankDrive=0;
    logic [7:0] shadowRedDrive=37,shadowBlueDrive=30;
    frameObservation_t completionDrive;
    integer capturedBank=0,checks=0,completions=0,reusedBank;
    logic debugInteractionArmReady;
    queryResult_t queryResult;
    logic queryResultValid,queryResultReady=1,queryBusy;
    perceptionCore dut(.*);
    always @(posedge clk) if(!reset)timeUs<=timeUs+1;

    task automatic checkProfile(input integer id,cfg,orientation,redFloor,blueFloor,liveCfg);
        begin
            if(debugWords[3*32+:16]!=id||debugWords[6*32+:32]!=cfg||
               debugWords[7*32+18+:2]!=orientation||debugWords[7*32+8+:8]!=redFloor||
               debugWords[7*32+:8]!=blueFloor||status.activeCfgVersion!=liveCfg)
                $fatal(1,"Frame/profile binding mismatch expected frame=%0d cfg=%0d ori=%0d floors=%0d/%0d live=%0d actual frame=%0d cfg=%0d ori=%0d floors=%0d/%0d live=%0d",
                    id,cfg,orientation,redFloor,blueFloor,liveCfg,
                    debugWords[3*32+:16],debugWords[6*32+:32],debugWords[7*32+18+:2],
                    debugWords[7*32+8+:8],debugWords[7*32+:8],status.activeCfgVersion);
            checks++;
        end
    endtask
    task automatic pulseSof(input integer id,orientation,input bit commit,
        input bit completeTogether,input integer completedBank);
        begin
            @(negedge clk);
            orientationProfile=2'(orientation);commitDrive=commit;
            sofDrive='0;sofDrive[79]=1;sofDrive[49:34]=16'(id);sofDrive[33:2]=timeUs;
            if(completeTogether)begin
                readBankDrive=1'(completedBank);completionDrive=dut.bankMeta[completedBank];aggregateDrive=1;
            end
            @(posedge clk);#1;
            if(!dut.haveWriteBank)$fatal(1,"SOF did not own a write bank");
            capturedBank=dut.writeBank;
            if(completeTogether)begin
                if(!completedFrame)$fatal(1,"Coincident valid completion was lost");
                completions++;
            end
            @(negedge clk);sofDrive=0;commitDrive=0;aggregateDrive=0;
        end
    endtask
    task automatic sealCapturedBank;
        begin
            @(negedge clk);candidateDrive=1;
            @(posedge clk);#1;
            if(dut.bankState[capturedBank]!=dut.READY)$fatal(1,"Candidate publication did not seal writing bank");
            @(negedge clk);candidateDrive=0;
            // Simulate the reader ownership transfer without waiting for image
            // processing: the test's deliberately empty image is not evidence.
            dut.bankState[capturedBank]=dut.READING;
        end
    endtask
    task automatic completeBank(input integer bank);
        begin
            @(negedge clk);readBankDrive=1'(bank);completionDrive=dut.bankMeta[bank];aggregateDrive=1;
            @(posedge clk);#1;
            if(!completedFrame||dut.bankState[bank]!=dut.FREE)$fatal(1,"Accepted completion did not publish/release");
            completions++;
            @(negedge clk);aggregateDrive=0;
        end
    endtask
    initial begin
        completionDrive='0;
        repeat(5)@(negedge clk);reset=0;resetPclk=0;
        force dut.streamData=sofDrive;
        force dut.sof=sofDrive[79];
        force dut.commitRequest=commitDrive;
        force dut.shadowRedMinimum=shadowRedDrive;
        force dut.shadowBlueMinimum=shadowBlueDrive;
        force dut.candidateValid=candidateDrive;
        force dut.candidateGood=1'b1;
        force dut.candidateOverflow=1'b0;
        force dut.readerBusy=1'b1;
        force dut.readerDone=1'b0;
        force dut.aggregateDone=aggregateDrive;
        force dut.readBank=readBankDrive;
        force dut.processedObservation=completionDrive;
        checkProfile(0,0,0,48,20,0);

        // A new-profile SOF arrives while the old-profile bank is READING.
        pulseSof(1,0,0,0,0);sealCapturedBank();
        pulseSof(2,0,1,0,0);
        if(status.activeCfgVersion!=1)$fatal(1,"Commit did not advance the live profile");
        sealCapturedBank();
        completeBank(0);checkProfile(1,0,0,48,20,1);
        completeBank(1);checkProfile(2,1,0,37,30,1);

        // A profile commit just after aggregation must not alter the completed
        // result during the wrapper's delayed held-word snapshot capture.
        pulseSof(3,0,0,0,0);sealCapturedBank();completeBank(capturedBank);
        checkProfile(3,1,0,37,30,1);
        shadowRedDrive=44;shadowBlueDrive=31;
        pulseSof(4,0,1,0,0);
        repeat(3)begin @(negedge clk);checkProfile(3,1,0,37,30,2);end
        sealCapturedBank();completeBank(capturedBank);checkProfile(4,2,0,44,31,2);

        // Orientation-only changes advance config but retain intensity floors.
        pulseSof(5,1,0,0,0);checkProfile(4,2,0,44,31,3);
        sealCapturedBank();completeBank(capturedBank);checkProfile(5,3,1,44,31,3);

        // Reclaiming an incomplete WRITING bank must bind the replacement SOF's
        // committed profile, not the abandoned frame's earlier thresholds.
        pulseSof(6,1,0,0,0);reusedBank=capturedBank;
        shadowRedDrive=40;shadowBlueDrive=28;
        pulseSof(7,2,1,0,0);
        if(capturedBank!=reusedBank||dut.bufferDropCount!=1)$fatal(1,"Truncated bank not reclaimed once");
        checkProfile(5,3,1,44,31,4);
        sealCapturedBank();completeBank(capturedBank);checkProfile(7,4,2,40,28,4);

        // A revoked permission means shadow values never become the frame's
        // effective segmentation profile, even when commitRequest remains high.
        interactionPermit=0;shadowRedDrive=99;shadowBlueDrive=98;
        pulseSof(8,2,1,0,0);sealCapturedBank();completeBank(capturedBank);
        checkProfile(8,4,2,40,28,4);interactionPermit=1;

        // Simultaneous old completion/new SOF exercises independent read and
        // write bank indices plus combined orientation and threshold commit.
        pulseSof(9,2,0,0,0);sealCapturedBank();
        shadowRedDrive=50;shadowBlueDrive=35;
        pulseSof(10,3,1,1,0);checkProfile(9,4,2,40,28,5);
        if(capturedBank!=1)$fatal(1,"Coincident SOF should claim the other free bank");
        sealCapturedBank();completeBank(capturedBank);checkProfile(10,5,3,50,35,5);
        if(completions!=9||dut.completionDiscardCount!=0)$fatal(1,"Profile regression completion accounting");
        // SW9's already-synchronised core input may change mid-frame. Only a
        // subsequent SOF applies it; the old owned bank retains its own mode.
        pulseSof(11,3,0,0,0);sealCapturedBank();
        bypassPerspective=1;
        repeat(3)@(negedge clk);
        if(dut.activeBypass||status.activeCfgVersion!=5)$fatal(1,"Bypass applied before SOF");
        pulseSof(12,3,0,0,0);sealCapturedBank();
        completeBank(0);
        if(debugWords[7*32+20]||debugWords[6*32+:16]!=5)$fatal(1,"Old bank relabelled as bypass");
        completeBank(1);
        if(!debugWords[7*32+20]||debugWords[6*32+:16]!=6)$fatal(1,"Bypass mode/version not bound to bank");
        pulseSof(13,3,0,0,0);sealCapturedBank();completeBank(capturedBank);
        if(status.activeCfgVersion!=6)$fatal(1,"Held SW9 repeatedly changed configuration");
        bypassPerspective=0;pulseSof(14,3,0,0,0);sealCapturedBank();completeBank(capturedBank);
        if(debugWords[7*32+20]||status.activeCfgVersion!=7)$fatal(1,"Normal mode did not resume atomically");
        $display("PASS perceptionCoreProfile_tb checks=%0d acceptedCompletions=%0d source=PROTOCOL_CONFIG_INJECTION",checks,completions);
        $finish;
    end
    initial begin #1000000;$fatal(1,"Profile binding regression timeout");end
endmodule
