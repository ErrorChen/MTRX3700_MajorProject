`timescale 1ns/1ps
// PROTOCOL_CONFIG_INJECTION: drive completed-frame statistics and interaction
// controls at their module boundaries. No pixel, camera or calibration-quality
// claim is made here. The core's currentSample/sampleGood/applyCommit decisions,
// shadow registers, active profile and bank metadata are never forced.
module perceptionCoreCalibration_tb;
    logic bypassPerspective=0;
    logic processingEnable=1;
    import candidate_pkg::*;
    import perception_pkg::*;
    import vision_pkg::*;
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
    logic aggregateDrive=0,collectDrive=1,attemptDrive=0,commitDrive=0,pairedDrive=1;
    logic [15:0] interactionDrive=1;
    logic [3:0] sampleCountDrive=0;
    frameObservation_t completionDrive;
    candidate_t redBoxDrive,blueBoxDrive;
    markerArray_t pairingMarkers;
    logic pairingReaderDone=0;
    integer pairingFrame=100;
    integer checks=0,acceptedSamples=0,rejectedSamples=0,ignoredSamples=0;
    integer expectedRedMin=255,expectedBlueMin=255,expectedRedMax=0,expectedBlueMax=0;
    logic debugInteractionArmReady;
    perceptionCore dut(.*);
    always @(posedge clk) if(!reset)timeUs<=timeUs+1;

    task automatic tick;
        @(posedge clk);#1;
    endtask
    // Geometric unit vectors call the production function directly. The
    // controlled translations below keep all four configured rotations inside
    // native320x240; they are test geometry, never runtime sheet coordinates.
    function automatic candidate_t rotatedBox(input integer x0,y0,x1,y1,rotation);
        candidate_t value;
        begin
            value='0;value.valid=1;
            case(rotation)
                0:begin value.xmin=9'(20+x0);value.xmax=9'(20+x1);value.ymin=8'(10+y0);value.ymax=8'(10+y1);end
                1:begin value.xmin=9'(250-y1);value.xmax=9'(250-y0);value.ymin=8'(20+x0);value.ymax=8'(20+x1);end
                2:begin value.xmin=9'(220-x1);value.xmax=9'(220-x0);value.ymin=8'(235-y1);value.ymax=8'(235-y0);end
                default:begin value.xmin=9'(20+y0);value.xmax=9'(20+y1);value.ymin=8'(220-x1);value.ymax=8'(220-x0);end
            endcase
            return value;
        end
    endfunction
    task automatic checkPairGeometry(input integer width,height,left,right,top,bottom,rotation,input bit expected);
        candidate_t cardBox,referenceBox;
        marker_t card;
        begin
            cardBox=rotatedBox(0,0,width-1,height-1,rotation);
            referenceBox=rotatedBox(left,top,right,bottom,rotation);
            card='0;card.accepted=1;card.digit=1;
            card.xMin=cardBox.xmin;card.xMax=cardBox.xmax;card.yMin=cardBox.ymin;card.yMax=cardBox.ymax;
            if(dut.referencePaired(card,referenceBox,2'(rotation))!==expected)
                $fatal(1,"Scale-aware pair width=%0d height=%0d ref=%0d,%0d,%0d,%0d rot=%0d expected=%b",
                    width,height,left,top,right,bottom,rotation,expected);
            if(expected)begin
                if(dut.referencePaired(card,referenceBox,2'(rotation^2)))
                    $fatal(1,"Reference on the opposite configured side was paired");
                referenceBox.valid=0;
                if(dut.referencePaired(card,referenceBox,2'(rotation)))
                    $fatal(1,"Invalid reference descriptor was paired");
            end
            checks++;
        end
    endtask
    task automatic checkPairingBoundaries;
        integer width,height,refWidth,refHeight,tolerance,left,gap;
        begin
            for(int rotation=0;rotation<4;rotation++)begin
                // Frame30158: red bbox36,5..107,94 and strip41,96..108,116.
                // The old left-edge +/-4 rule rejected the actual5px edge
                // shift, although the centre moved only3px. Translation below
                // preserves those inclusive dimensions and half-pixel centres.
                checkPairGeometry(72,90,5,72,91,111,rotation,1);
                for(int scale=1;scale<=4;scale++)begin
                    width=24*scale;height=30*scale;refHeight=6*scale;
                    tolerance=(width+15)/16;gap=scale;
                    checkPairGeometry(width,height,2*scale,25*scale-1,height+gap,height+gap+refHeight-1,rotation,1);
                    // Inclusive centre boundary and first rejected pixel,
                    // independently on both sides at four different scales.
                    checkPairGeometry(width,height,tolerance,width-1+tolerance,height+gap,height+gap+refHeight-1,rotation,1);
                    checkPairGeometry(width,height,tolerance+1,width+tolerance,height+gap,height+gap+refHeight-1,rotation,0);
                    checkPairGeometry(width,height,-tolerance,width-1-tolerance,height+gap,height+gap+refHeight-1,rotation,1);
                    checkPairGeometry(width,height,-tolerance-1,width-2-tolerance,height+gap,height+gap+refHeight-1,rotation,0);
                    refWidth=(width*8+9)/10;left=(width-refWidth)/2;
                    checkPairGeometry(width,height,left,left+refWidth-1,height+gap,height+gap+refHeight-1,rotation,1);
                    checkPairGeometry(width,height,left,left+refWidth-2,height+gap,height+gap+refHeight-1,rotation,0);
                    refWidth=width*12/10;left=(width-refWidth)/2;
                    checkPairGeometry(width,height,left,left+refWidth-1,height+gap,height+gap+refHeight-1,rotation,1);
                    checkPairGeometry(width,height,left,left+refWidth,height+gap,height+gap+refHeight-1,rotation,0);
                    checkPairGeometry(width,height,0,width-1,height+height/8,height+height/8+refHeight-1,rotation,1);
                    checkPairGeometry(width,height,0,width-1,height+height/8+1,height+height/8+refHeight,rotation,0);
                    checkPairGeometry(width,height,0,width-1,height-1,height+refHeight-2,rotation,0);
                    checkPairGeometry(width,height,0,width-1,height+gap,height+gap+height/10-1,rotation,1);
                    checkPairGeometry(width,height,0,width-1,height+gap,height+gap+height/10-2,rotation,0);
                    checkPairGeometry(width,height,0,width-1,height+gap,height+gap+height*3/10-1,rotation,1);
                    checkPairGeometry(width,height,0,width-1,height+gap,height+gap+height*3/10,rotation,0);
                end
                // Do not floor each centre before comparing: odd strip width
                // can put its doubled centre one unit beyond the allowed limit.
                checkPairGeometry(72,90,8,74,91,111,rotation,0);
            end
        end
    endtask
    task automatic checkFullMarkerCapacity(input bit blue);
        bit seen;
        @(negedge clk);targetRequest.operation=TARGET_SELECT;targetRequest.bayId=1;
        targetRequest.requestTag=16'h3210;targetRequestValid=1;
        tick();@(negedge clk);targetRequestValid=0;
        pairingMarkers='0;
        for(int i=0;i<16;i++)begin
            pairingMarkers[i].accepted=1;pairingMarkers[i].isBlue=blue;
            pairingMarkers[i].digit=blue?4'd1:4'd2;pairingMarkers[i].quality=200;
            pairingMarkers[i].xMin=10;pairingMarkers[i].xMax=40;
            pairingMarkers[i].yMin=20;pairingMarkers[i].yMax=60;
        end
        dut.bankCandidates[0]='0;dut.bankColours[0]=blue?16'hffff:16'd0;
        dut.bankRedCount[0]=blue?0:16;dut.bankBlueCount[0]=blue?16:0;
        dut.bankMeta[0]='0;dut.bankMeta[0].boundRequest=dut.activeRequest;
        dut.bankMeta[0].frameId=16'(pairingFrame);dut.bankMeta[0].frameGood=1;
        dut.bankMeta[0].configVersion=dut.configVersion;dut.bankMeta[0].captureStartUs=timeUs;
        dut.bankState[0]=dut.READING;dut.bankState[1]=dut.FREE;dut.haveWriteBank=0;
        pairingReaderDone=1;tick();@(negedge clk);pairingReaderDone=0;seen=0;
        for(int cycle=0;cycle<200;cycle++)begin tick();if(completedFrame)begin seen=1;break;end end
        if(!seen||dut.processedObservation.matchCount!=(blue?16:0)||dut.red2Count!=(blue?0:16)||
           debugWords[9*32+:5]!=(blue?0:16)||debugWords[9*32+5+:5]!=(blue?16:0)||
           !debugWords[(24+15*4)*32+31]||debugWords[(24+15*4)*32+30]!==blue||
           debugWords[(24+15*4)*32+24+:4]!=(blue?1:2)||
           debugWords[DEBUG_TAIL_BASE*32+:22]!==dut.activeRequest||
           debugWords[1*32+16+:16]!=DEBUG_SCHEMA_VERSION||
           debugWords[(DEBUG_TAIL_BASE+5)*32+8+:24]!=24'h01100f)
            $fatal(1,"Shared16-marker/count16/debug-tail packing lost an upper slot");
        tick();
        if(!targetReportValid||targetReport.frameId!=pairingFrame||targetReport.ambiguous!==blue||
           targetReport.observed||targetReport.locked||targetReport.reason!=(blue?REPORT_DUPLICATE_ID:REPORT_NOT_FOUND))
            $fatal(1,"Sixteen shared observations lost colour/count/ambiguity");
        pairingFrame++;checks++;
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
        if(expectCurrent && (debugWords[(DEBUG_TAIL_BASE+1)*32+16+:16]!=completionDrive.frameId ||
            debugWords[(DEBUG_TAIL_BASE+1)*32+8+:5]!=={dut.sampleWindowGood,dut.sampleGeometryGood,
                dut.red1Paired,completionDrive.frameGood,dut.bankSampleGood[0]}))
            $fatal(1,"Persisted sample diagnostics are not bound to the completed sample frame");
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
    task automatic checkReferenceAnnotation(input integer firstIndex,secondIndex,
        input bit acceptedBlueBay,goodFrame,input integer expectedPairs,expectedIndex);
        bit seen;
        integer redIndex;
        @(negedge clk);
        redIndex=firstIndex==15||secondIndex==15?14:15;
        pairingMarkers='0;
        pairingMarkers[redIndex].accepted=1;pairingMarkers[redIndex].digit=1;
        pairingMarkers[redIndex].xMin=redBoxDrive.xmin;pairingMarkers[redIndex].xMax=redBoxDrive.xmax;
        pairingMarkers[redIndex].yMin=redBoxDrive.ymin;pairingMarkers[redIndex].yMax=redBoxDrive.ymax;
        dut.bankCandidates[0]='0;dut.bankColours[0]=0;dut.bankOrientation[0]=0;
        if(firstIndex>=0)begin
            dut.bankCandidates[0][firstIndex]=blueBoxDrive;dut.bankColours[0][firstIndex]=1;
            if(acceptedBlueBay)begin
                pairingMarkers[firstIndex].accepted=1;pairingMarkers[firstIndex].isBlue=1;
                pairingMarkers[firstIndex].digit=3;
            end
        end else begin
            // An unrelated unrecognised blue region must remain unknown.
            dut.bankCandidates[0][2]=blueBoxDrive;dut.bankColours[0][2]=1;
            dut.bankCandidates[0][2].xmin=200;dut.bankCandidates[0][2].xmax=260;
        end
        if(secondIndex>=0)begin dut.bankCandidates[0][secondIndex]=blueBoxDrive;dut.bankColours[0][secondIndex]=1;end
        dut.bankMeta[0]='0;dut.bankMeta[0].frameId=16'(pairingFrame);
        dut.bankMeta[0].frameGood=goodFrame;dut.bankMeta[0].configVersion=dut.configVersion;
        dut.bankMeta[0].captureStartUs=timeUs;
        dut.bankState[0]=dut.READING;dut.bankState[1]=dut.FREE;dut.haveWriteBank=0;
        pairingReaderDone=1;tick();
        @(negedge clk);pairingReaderDone=0;seen=0;
        for(int cycle=0;cycle<400;cycle++)begin
            tick();
            if(completedFrame)begin seen=1;break;end
        end
        if(!seen||completedFrameId!=pairingFrame||dut.pairCount!=expectedPairs||
           debugWords[(DEBUG_TAIL_BASE+2)*32+3]!==1'(expectedPairs==1&&goodFrame)||
           debugWords[(DEBUG_TAIL_BASE+2)*32+4+:4]!=expectedIndex)
            $fatal(1,"Reference annotation mismatches actual pair uniqueness frame=%0d pairs=%0d valid=%0b index=%0d",
                pairingFrame,dut.pairCount,debugWords[(DEBUG_TAIL_BASE+2)*32+3],debugWords[(DEBUG_TAIL_BASE+2)*32+4+:4]);
        pairingFrame++;checks++;
    endtask
    initial begin
        if(dut.candidates.CAP!=16||dut.candidates.ACTIVE_CAP!=15||!dut.candidates.SHARED_POOL||$bits(debugWords)!=DEBUG_WORD_COUNT*32)
            $fatal(1,"Production core must instantiate shared16/active15 and current schema width");
        completionDrive='0;completionDrive.frameGood=1;
        redBoxDrive='0;redBoxDrive.valid=1;redBoxDrive.xmin=20;redBoxDrive.xmax=80;
        redBoxDrive.ymin=30;redBoxDrive.ymax=100;
        blueBoxDrive=redBoxDrive;blueBoxDrive.ymin=105;blueBoxDrive.ymax=120;
        checkPairingBoundaries();
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

        // Exercise the actual bounded AG_REFERENCE geometry scan. These inputs
        // are candidate/reader boundary injections, not forced pair outcomes.
        @(negedge clk);sofDrive=0;commitDrive=0;collectDrive=0;aggregateDrive=0;
        release dut.aggregateDone;release dut.processedObservation;
        release dut.red1Paired;release dut.pairRed;release dut.pairBlue;
        release dut.readerDone;
        force dut.readerDone=pairingReaderDone;force dut.markers=pairingMarkers;
        force dut.candidateValid=1'b0;
        checkReferenceAnnotation(4,-1,0,1,1,4);
        checkReferenceAnnotation(1,6,0,1,2,0); // two geometric matches are ambiguous
        checkReferenceAnnotation(-1,-1,0,1,0,0); // unknown blue region is not BJ
        checkReferenceAnnotation(3,-1,1,1,0,0); // a recognised bay cannot be BJ
        checkReferenceAnnotation(7,-1,0,0,1,0); // bad frame clears a valid-looking pair
        checkReferenceAnnotation(0,-1,0,1,1,0); // index0 is distinguished by valid bit
        checkReferenceAnnotation(15,-1,0,1,1,15); // full four-bit reference index
        checkReferenceAnnotation(0,15,0,1,2,0); // upper-half match also destroys uniqueness
        checkReferenceAnnotation(15,-1,1,1,0,0); // accepted blue global slot15 cannot become BJ
        checkFullMarkerCapacity(1);checkFullMarkerCapacity(0);
        $display("PASS perceptionCoreCalibration_tb checks=%0d accepted=%0d rejected=%0d ignored=%0d source=PROTOCOL_CONFIG_INJECTION",
            checks,acceptedSamples,rejectedSamples,ignoredSamples);
        $finish;
    end
    initial begin #1000000;$fatal(1,"Calibration protocol regression timeout");end
endmodule
