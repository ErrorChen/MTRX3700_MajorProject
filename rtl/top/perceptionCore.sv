// CLOCK_50 processing, native-pixel FIFO input, no motion outputs. A 334-clock
// row guard preserves CAP8's 328-cycle housekeeping plus run/cleanup latency.
module perceptionCore (
    input logic clk,reset,pclk,resetPclk,cameraFrameStart,cameraPixelValid,
    input logic [15:0] cameraPixel,
    input logic [9:0] cameraX,
    input logic [8:0] cameraY,
    input logic [31:0] timeUs,
    input logic interactionEnable,interactionPermit,debugCalArm,debugSpeechArm,
    input logic [1:0] orientationProfile,
    input perception_pkg::targetRequest_t targetRequest,
    input logic targetRequestValid,
    output logic targetRequestReady,
    output perception_pkg::targetReport_t targetReport,
    output logic targetReportValid,
    input logic targetReportReady,
    output perception_pkg::userEvent_t userEvent,
    output logic userEventValid,
    input logic userEventReady,
    output perception_pkg::perceptionStatus_t status,
    output logic [3071:0] debugWords,
    output logic completedFrame,
    output logic [15:0] completedFrameId
);
    import camera_pkg::*;
    import candidate_pkg::*;
    import perception_pkg::*;
    import vision_pkg::*;
    targetRequest_t activeRequest;
    logic streamValid,transportFault;
    logic [79:0] streamData;
    logic [8:0] rowGuard;
    wire sof=streamValid&&streamData[79];
    wire pixelValid=streamValid&&!streamData[79];
    wire [8:0] x=streamData[32:24];
    wire [7:0] y=streamData[23:16];
    wire pixelSop=pixelValid&&x==0&&y==0;
    wire pixelEop=pixelValid&&x==319&&y==239;
    wire [23:0] rgb=rgb565_to_rgb888(streamData[15:0]);
    wire [9:0] r={2'b0,rgb[23:16]},g={2'b0,rgb[15:8]},b={2'b0,rgb[7:0]};
    logic [7:0] activeRedMinimum,activeBlueMinimum,shadowRedMinimum,shadowBlueMinimum;
    logic [1:0] activeOrientation;
    logic [15:0] configVersion;
    wire [1:0] colourMask;
    hsvColourGate colourGate (.rgb(rgb),.redMinimum(activeRedMinimum),
        .blueMinimum(activeBlueMinimum),.colourMask(colourMask));
    // Reader algorithm 2 has a fixed camera-measured luma/spread white gate.
    // This is NOT automatic white calibration: red/blue calibration never
    // changes the fixed threshold. R+2G+B spans 0..1020 and fits ten bits.
    // Debug word95's white byte is quarter-luma units only for algorithm 2;
    // historical algorithm 1 keeps its minimum-channel interpretation.
    localparam int WHITE_LUMA_QUARTER=96;
    wire [9:0] whiteLumaSum=r+(g<<1)+b;
    wire whitePixel=whiteLumaSum>=10'(4*WHITE_LUMA_QUARTER)&&
        r<=g+64&&g<=r+64&&r<=b+64&&b<=r+64&&g<=b+64&&b<=g+64;
    cameraStreamBridge cameraBridge (
        .pclk(pclk),.resetPclk(resetPclk),.frameStart(cameraFrameStart),
        .pixelValid(cameraPixelValid),.pixel(cameraPixel),.pixelX(cameraX),.pixelY(cameraY),
        .clk(clk),.reset(reset),.timeUs(timeUs),.activeRequest(activeRequest),
        .streamReady(rowGuard==0),.streamValid(streamValid),.streamData(streamData),.transportFault(transportFault));
    logic cleanValid,cleanSop,cleanEop,abandonAtSof;
    logic [8:0] cleanX;
    logic [7:0] cleanY;
    logic [1:0] cleanMask;
    logic runValid,runSop,runEop;
    logic [8:0] runX;
    logic [7:0] runY;
    logic [1:0] runMask;
    // Keep complete >=3-pixel horizontal runs, including their first/last
    // pixels. This removes quantised orange speckles without eroding card
    // corners. The reader's foreground bank deliberately retains raw HSV bits.
    horizontalRunFilter runFilter (.clk(clk),.reset(reset||abandonAtSof),
        .in_valid(pixelValid),.in_sop(pixelSop),.in_eop(pixelEop),.in_x(x),.in_y(y),.in_mask(colourMask),
        .out_valid(runValid),.out_sop(runSop),.out_eop(runEop),.out_x(runX),.out_y(runY),.out_mask(runMask));
    causalMaskCleanup cleanup (.clk(clk),.reset(reset||abandonAtSof),.in_valid(runValid),.in_sop(runSop),.in_eop(runEop),
        .in_x(runX),.in_y(runY),.in_mask(runMask),.out_valid(cleanValid),.out_sop(cleanSop),
        .out_eop(cleanEop),.out_x(cleanX),.out_y(cleanY),.out_mask(cleanMask));
    candidate_array_t redCandidates,blueCandidates;
    logic [3:0] redCount,blueCount,allocationPeakRed,allocationPeakBlue;
    logic candidateValid,candidateGood,candidateOverflow,candidateError,candidateOverrun;
    logic [15:0] candidateSequence;
    boundedCandidates candidates (.clk(clk),.reset(reset||abandonAtSof),.in_valid(cleanValid),.in_sop(cleanSop),.in_eop(cleanEop),
        .in_mask(cleanMask),.in_x(cleanX),.in_y(cleanY),.red_candidates(redCandidates),.blue_candidates(blueCandidates),
        .red_count(redCount),.blue_count(blueCount),.out_valid(candidateValid),.frame_valid(candidateGood),
        .overflow(candidateOverflow),.red_overflow(),.blue_overflow(),.frame_error(candidateError),
        .overrun(candidateOverrun),.frame_id(candidateSequence),.busy(),
        .allocationPeakRed(allocationPeakRed),.allocationPeakBlue(allocationPeakBlue));
    typedef enum logic [1:0] {FREE,WRITING,READY,READING} bankState_t;
    bankState_t bankState[0:1];
    frameObservation_t bankMeta[0:1],captureMeta,observation,processedObservation;
    candidate_array_t bankRed[0:1],bankBlue[0:1];
    logic [1:0] bankOrientation[0:1];
    // The segmentation profile belongs to the captured bank, not the later
    // global profile when that bank finishes recognition.
    logic [7:0] bankRedMinimum[0:1],bankBlueMinimum[0:1];
    logic [3:0] bankRedCount[0:1],bankBlueCount[0:1],bankPeakRed[0:1],bankPeakBlue[0:1];
    logic [2:0] bankCandidateFaults[0:1];
    logic writeBank,haveWriteBank,readBank,readerStart,readerBusy,readerDone;
    // Part A intentionally publishes an aborted old frame on an overlapping SOP.
    // Discarding a partial capture here resets only the candidate/cleanup state,
    // so that old packet cannot be attached to the new frame's metadata.
    assign abandonAtSof=sof&&haveWriteBank&&bankState[writeBank]==WRITING&&!candidateValid;
    logic [16:0] glyphAddress;
    logic glyphWhite,glyphColour;
    markerArray_t markers,lastMarkers;
    logic [4:0] acceptedCount;
    logic observationValid;
    logic [15:0] bufferDropCount,reportDropCount;
    logic requestInvalidFault;
    glyphBanks glyphMemory (.clk(clk),.writeEnable(pixelValid&&haveWriteBank&&x<320&&y<240),
        .writeBank(writeBank),.writeAddress(17'(y)*17'd320+17'(x)),.writeWhite(whitePixel),.writeColour(colourMask!=0),
        .readBank(readBank),.readAddress(glyphAddress),.readWhite(glyphWhite),.readColour(glyphColour));
    projectiveMarkerReader reader (.clk(clk),.reset(reset),.start(readerStart),.redCandidates(bankRed[readBank]),
        .blueCandidates(bankBlue[readBank]),.orientationProfile(bankOrientation[readBank]),.busy(readerBusy),
        .done(readerDone),.readAddress(glyphAddress),.readWhite(glyphWhite),.readColour(glyphColour),
        .markers(markers),.acceptedCount(acceptedCount));
    targetTracker tracker (.clk(clk),.reset(reset),.timeUs(timeUs),.activeCfgVersion(configVersion),
        .perceptionReady(status.perceptionReady),.targetRequest(targetRequest),.targetRequestValid(targetRequestValid),
        .targetRequestReady(targetRequestReady),.frameObservation(observation),.frameValid(observationValid),
        .targetReport(targetReport),.targetReportValid(targetReportValid),.targetReportReady(targetReportReady),
        .activeRequest(activeRequest),.reportDropCount(reportDropCount),.requestInvalidFault(requestInvalidFault));

    // Pair using the red card's local geometry, never a sheet cell/known bay.
    function automatic logic referencePaired(input marker_t card,input candidate_t refBox,input logic [1:0] rotation);
        // Native extrema are at most 319; signed 15-bit intermediates cover
        // differences, +/-4 tolerance and the largest constant product (x12).
        logic signed [14:0] cw,ch,rw,rh,lo,hi,rl,rhEnd,gap;
        begin
            cw=rotation[0]?int'(card.yMax)-int'(card.yMin)+1:int'(card.xMax)-int'(card.xMin)+1;
            ch=rotation[0]?int'(card.xMax)-int'(card.xMin)+1:int'(card.yMax)-int'(card.yMin)+1;
            rw=rotation[0]?int'(refBox.ymax)-int'(refBox.ymin)+1:int'(refBox.xmax)-int'(refBox.xmin)+1;
            rh=rotation[0]?int'(refBox.xmax)-int'(refBox.xmin)+1:int'(refBox.ymax)-int'(refBox.ymin)+1;
            lo=rotation[0]?int'(card.yMin):int'(card.xMin);hi=rotation[0]?int'(card.yMax):int'(card.xMax);
            rl=rotation[0]?int'(refBox.ymin):int'(refBox.xmin);rhEnd=rotation[0]?int'(refBox.ymax):int'(refBox.xmax);
            case(rotation)
                0:gap=int'(refBox.ymin)-int'(card.yMax)-1;
                1:gap=int'(card.xMin)-int'(refBox.xmax)-1;
                2:gap=int'(card.yMin)-int'(refBox.ymax)-1;
                default:gap=int'(refBox.xmin)-int'(card.xMax)-1;
            endcase
            referencePaired=refBox.valid&&gap>=0&&gap*8<=ch&&rw*10>=cw*8&&rw*10<=cw*12&&
                rh*10>=ch&&rh*10<=ch*3&&rl>=lo-4&&rl<=lo+4&&rhEnd>=hi-4&&rhEnd<=hi+4;
        end
    endfunction
    function automatic logic stationary(input candidate_t a,input candidate_t c);
        stationary=a.valid&&c.valid&&int'(a.xmin)-int'(c.xmin)<=3&&int'(c.xmin)-int'(a.xmin)<=3&&
            int'(a.xmax)-int'(c.xmax)<=3&&int'(c.xmax)-int'(a.xmax)<=3&&
            int'(a.ymin)-int'(c.ymin)<=3&&int'(c.ymin)-int'(a.ymin)<=3&&
            int'(a.ymax)-int'(c.ymax)<=3&&int'(c.ymax)-int'(a.ymax)<=3;
    endfunction
    candidate_t pairRed,pairBlue,lastPairRed,lastPairBlue,sampledRed,sampledBlue;
    candidate_t bankSampleRed[0:1],bankSampleBlue[0:1];
    logic red1Paired,red2Seen,roiValid;
    logic [4:0] pairCount,red2Count;
    // One geometric comparator is shared across candidate pairs. The former
    // combinational 16x8 loop duplicated 128 arithmetic/priority paths and was
    // the largest contributor to the failed fit. Keep the READING bank owned
    // until this bounded scan completes, so all data still belongs to one frame.
    typedef enum logic [1:0] {AG_IDLE,AG_MARKER,AG_REFERENCE,AG_DONE} aggregateState_t;
    aggregateState_t aggregateState;
    logic [3:0] markerIndex;
    logic [2:0] referenceIndex;
    wire aggregateDone=aggregateState==AG_DONE;
    // Capture can report a newer truncated/dropped frame on the same clock as
    // an older owned bank finishes classification. The newer bad observation
    // must win: publishing the old good result would hide immediate lock loss.
    wire captureDropNow=abandonAtSof||(candidateValid&&!haveWriteBank);
    wire aggregateAccepted=aggregateDone&&!captureDropNow;
    logic [15:0] completionDiscardCount;
    assign red1Paired=pairCount==1;
    assign red2Seen=red2Count==1;
    always_ff @(posedge clk) begin
        if(reset) begin
            aggregateState<=AG_IDLE;markerIndex<=0;referenceIndex<=0;
            processedObservation<='0;pairRed<='0;pairBlue<='0;pairCount<=0;red2Count<=0;
        end else case(aggregateState)
            AG_IDLE: if(readerDone) begin
                processedObservation<=bankMeta[readBank];processedObservation.matchCount<=0;
                pairRed<='0;pairBlue<='0;pairCount<=0;red2Count<=0;
                markerIndex<=0;referenceIndex<=0;aggregateState<=AG_MARKER;
            end
            AG_MARKER: begin
                if(markers[markerIndex].accepted) begin
                    if(markers[markerIndex].isBlue &&
                        markers[markerIndex].digit==bankMeta[readBank].boundRequest.bayId) begin
                        processedObservation.matchCount<=processedObservation.matchCount+5'd1;
                        processedObservation.xMin<=markers[markerIndex].xMin;
                        processedObservation.xMax<=markers[markerIndex].xMax;
                        processedObservation.yMin<=markers[markerIndex].yMin;
                        processedObservation.yMax<=markers[markerIndex].yMax;
                        processedObservation.quality<=markers[markerIndex].quality;
                    end
                    if(!markers[markerIndex].isBlue && markers[markerIndex].digit==2)
                        red2Count<=red2Count+5'd1;
                end
                if(markers[markerIndex].accepted && !markers[markerIndex].isBlue && markers[markerIndex].digit==1) begin
                    referenceIndex<=0;aggregateState<=AG_REFERENCE;
                end else if(markerIndex==15) aggregateState<=AG_DONE;
                else markerIndex<=markerIndex+4'd1;
            end
            AG_REFERENCE: begin
                if(referencePaired(markers[markerIndex],bankBlue[readBank][referenceIndex],bankOrientation[readBank])) begin
                    // Saturating uniqueness must not wrap back to one.
                    if(pairCount<2) pairCount<=pairCount+5'd1;
                    pairRed.valid<=1;
                    pairRed.xmin<=markers[markerIndex].xMin;pairRed.xmax<=markers[markerIndex].xMax;
                    pairRed.ymin<=markers[markerIndex].yMin;pairRed.ymax<=markers[markerIndex].yMax;
                    pairBlue<=bankBlue[readBank][referenceIndex];
                end
                if(referenceIndex==7) begin
                    if(markerIndex==15) aggregateState<=AG_DONE;
                    else begin markerIndex<=markerIndex+4'd1;aggregateState<=AG_MARKER;end
                end else referenceIndex<=referenceIndex+3'd1;
            end
            AG_DONE: aggregateState<=AG_IDLE;
            default: aggregateState<=AG_IDLE;
        endcase
    end
    logic collectEnable,calibrationAttempt,commitRequest,commitAck,calibrated,speechArmed,interactionBusy;
    logic [3:0] sampleCount;
    logic [15:0] interactionId;
    interactionKind_t interactionKind;
    interactionState_t interactionState;
    logic eventOverflow,samplerGood;
    logic [7:0] sampleRedMinimum,sampleBlueMinimum;
    logic [16:0] redSamples,blueSamples;
    logic bankSampling[0:1],bankSampleGood[0:1];
    logic [7:0] bankSampleRedMin[0:1],bankSampleBlueMin[0:1];
    wire sampleGood=bankSampleGood[readBank]&&red1Paired&&processedObservation.frameGood&&
        stationary(pairRed,bankSampleRed[readBank])&&stationary(pairBlue,bankSampleBlue[readBank])&&
        (sampleCount==0||(int'(bankSampleRedMin[readBank])-int'(shadowRedMinimum)<=24&&
        int'(shadowRedMinimum)-int'(bankSampleRedMin[readBank])<=24&&
        int'(bankSampleBlueMin[readBank])-int'(shadowBlueMinimum)<=24&&
        int'(shadowBlueMinimum)-int'(bankSampleBlueMin[readBank])<=24));
    colourSampler sampler (.clk(clk),.reset(reset),.sof(sof),.pixelValid(pixelValid),.eop(pixelEop),
        .collectEnable(collectEnable),.roiValid(roiValid),.x(x),.y(y),.rgb(rgb),.orientation(activeOrientation),
        .redBox(lastPairRed),.blueBox(lastPairBlue),.frameSampleGood(samplerGood),.redMinimum(sampleRedMinimum),
        .blueMinimum(sampleBlueMinimum),.redSamples(redSamples),.blueSamples(blueSamples),
        .sampledRedBox(sampledRed),.sampledBlueBox(sampledBlue));
    fixedSheetInteraction interaction (.clk(clk),.reset(reset),.timeUs(timeUs),.enable(interactionEnable),
        .permit(interactionPermit),.debugCalArm(debugCalArm),.debugSpeechArm(debugSpeechArm),
        .frameValid(aggregateAccepted),.frameGood(processedObservation.frameGood),.frameId(processedObservation.frameId),
        .configVersion(processedObservation.configVersion),.activeCfgVersion(configVersion),.red1Paired(red1Paired),
        .red2Seen(red2Seen),.sampleResultValid(aggregateAccepted&&bankSampling[readBank]),.sampleGood(sampleGood),
        .commitAck(commitAck),.commitVersion(configVersion),.collectEnable(collectEnable),.commitRequest(commitRequest),
        .calibrationAttempt(calibrationAttempt),.sampleCount(sampleCount),.calibrated(calibrated),.speechArmed(speechArmed),
        .busy(interactionBusy),.kind(interactionKind),.state(interactionState),.interactionId(interactionId),
        .userEvent(userEvent),.userEventValid(userEventValid),.userEventReady(userEventReady),.eventOverflow(eventOverflow));
    logic [15:0] faults,lastFrameId,lastFrameConfigVersion;
    logic [1:0] lastFrameOrientation;
    logic [7:0] lastFrameRedMinimum,lastFrameBlueMinimum;
    logic haveFrame,lastFrameGood;
    logic [31:0] lastCompletionUs,lastCaptureUs;
    logic [3:0] lastRedCount,lastBlueCount,lastPeakRed,lastPeakBlue;
    logic [2:0] lastCandidateFaults;
    always_ff @(posedge clk) begin
        if(reset)begin
            rowGuard<=0;activeRedMinimum<=48;activeBlueMinimum<=32;shadowRedMinimum<=255;shadowBlueMinimum<=255;
            activeOrientation<=0;configVersion<=0;commitAck<=0;writeBank<=0;haveWriteBank<=0;readBank<=0;readerStart<=0;
            observationValid<=0;observation<='0;captureMeta<='0;bufferDropCount<=0;faults<=0;haveFrame<=0;lastCompletionUs<=0;
            lastMarkers<='0;lastFrameId<=0;lastCaptureUs<=0;lastRedCount<=0;lastBlueCount<=0;roiValid<=0;
            lastPairRed<='0;lastPairBlue<='0;completedFrame<=0;completedFrameId<=0;lastFrameGood<=0;
            lastPeakRed<=0;lastPeakBlue<=0;lastCandidateFaults<=0;
            lastFrameConfigVersion<=0;lastFrameOrientation<=0;
            lastFrameRedMinimum<=48;lastFrameBlueMinimum<=32;
            completionDiscardCount<=0;
            for(int i=0;i<2;i++)begin
                bankState[i]<=FREE;bankMeta[i]<='0;bankRed[i]<='0;bankBlue[i]<='0;bankOrientation[i]<=0;
                bankRedMinimum[i]<=48;bankBlueMinimum[i]<=32;
                bankRedCount[i]<=0;bankBlueCount[i]<=0;bankPeakRed[i]<=0;bankPeakBlue[i]<=0;bankCandidateFaults[i]<=0;
                bankSampling[i]<=0;bankSampleGood[i]<=0;bankSampleRedMin[i]<=0;bankSampleBlueMin[i]<=0;
                bankSampleRed[i]<='0;bankSampleBlue[i]<='0;
            end
        end else begin
            readerStart<=0;observationValid<=0;commitAck<=0;completedFrame<=0;
            if(rowGuard!=0)rowGuard<=rowGuard-9'd1;
            if(pixelValid&&x==319)rowGuard<=9'd334;
            if(transportFault)faults[FAULT_CAMERA_TRANSPORT]<=1;
            if(requestInvalidFault)faults[FAULT_REQUEST_INVALID]<=1;
            if(calibrationAttempt)begin shadowRedMinimum<=255;shadowBlueMinimum<=255;end
            if(aggregateAccepted&&bankSampling[readBank]&&sampleGood)begin
                if(bankSampleRedMin[readBank]<shadowRedMinimum)shadowRedMinimum<=bankSampleRedMin[readBank];
                if(bankSampleBlueMin[readBank]<shadowBlueMinimum)shadowBlueMinimum<=bankSampleBlueMin[readBank];
            end
            if(sof)begin
                // Revoke already visible in the commit domain wins this edge.
                if(commitRequest&&interactionEnable&&interactionPermit)begin
                    activeRedMinimum<=shadowRedMinimum;activeBlueMinimum<=shadowBlueMinimum;
                    configVersion<=configVersion+16'd1;commitAck<=1;
                end else if(activeOrientation!=orientationProfile)configVersion<=configVersion+16'd1;
                activeOrientation<=orientationProfile;captureMeta<='0;
                captureMeta.boundRequest<=targetRequest_t'(streamData[71:50]);captureMeta.frameId<=streamData[49:34];
                captureMeta.captureStartUs<=streamData[33:2];
                captureMeta.configVersion<=configVersion+16'((commitRequest&&interactionEnable&&interactionPermit)||activeOrientation!=orientationProfile);
                captureMeta.frameGood<=!streamData[78];
                if(abandonAtSof)begin
                    // A new SOF without a completed candidate packet abandons
                    // the truncated frame. Reclaim only its WRITING bank; READY
                    // and READING banks are never overwritten by this recovery.
                    observation<=captureMeta;observation.frameGood<=0;
                    observation.resourceDrop<=1;observationValid<=1;
                    bankOrientation[writeBank]<=orientationProfile;
                    bankRedMinimum[writeBank]<=(commitRequest&&interactionEnable&&interactionPermit)?shadowRedMinimum:activeRedMinimum;
                    bankBlueMinimum[writeBank]<=(commitRequest&&interactionEnable&&interactionPermit)?shadowBlueMinimum:activeBlueMinimum;
                    bankSampling[writeBank]<=collectEnable;
                    if(bufferDropCount!=16'hffff)bufferDropCount<=bufferDropCount+16'd1;
                    faults[FAULT_CAMERA_TRANSPORT]<=1;
                end else if(bankState[0]==FREE||bankState[1]==FREE)begin
                    writeBank<=bankState[0]==FREE?1'b0:1'b1;haveWriteBank<=1;
                    bankState[bankState[0]==FREE?0:1]<=WRITING;bankOrientation[bankState[0]==FREE?0:1]<=orientationProfile;
                    bankRedMinimum[bankState[0]==FREE?0:1]<=(commitRequest&&interactionEnable&&interactionPermit)?shadowRedMinimum:activeRedMinimum;
                    bankBlueMinimum[bankState[0]==FREE?0:1]<=(commitRequest&&interactionEnable&&interactionPermit)?shadowBlueMinimum:activeBlueMinimum;
                    bankSampling[bankState[0]==FREE?0:1]<=collectEnable;
                end else begin
                    haveWriteBank<=0;captureMeta.resourceDrop<=1;
                    if(bufferDropCount!=16'hffff)bufferDropCount<=bufferDropCount+16'd1;
                    faults[FAULT_MASK_BUFFER_OVERRUN]<=1;
                end
            end
            if(candidateValid)begin
                if(candidateOverflow)faults[FAULT_CANDIDATE_OVERFLOW]<=1;
                if(haveWriteBank)begin
                    bankMeta[writeBank]<=captureMeta;bankMeta[writeBank].frameGood<=captureMeta.frameGood&&candidateGood&&!candidateOverflow;
                    bankRed[writeBank]<=redCandidates;bankBlue[writeBank]<=blueCandidates;bankState[writeBank]<=READY;
                    // Diagnostics travel with the same owned bank as its image.
                    bankRedCount[writeBank]<=redCount;bankBlueCount[writeBank]<=blueCount;
                    bankPeakRed[writeBank]<=allocationPeakRed;bankPeakBlue[writeBank]<=allocationPeakBlue;
                    bankCandidateFaults[writeBank]<={candidateOverflow,candidateError,candidateOverrun};
                    // A simultaneous SOF may already have claimed the other bank.
                    if(!sof)haveWriteBank<=0;
                    bankSampleGood[writeBank]<=samplerGood;bankSampleRedMin[writeBank]<=sampleRedMinimum;
                    bankSampleBlueMin[writeBank]<=sampleBlueMinimum;bankSampleRed[writeBank]<=sampledRed;bankSampleBlue[writeBank]<=sampledBlue;
                end else begin
                    observation<=captureMeta;observation.resourceDrop<=1;observation.frameGood<=0;observationValid<=1;
                end
            end
            if(!readerBusy&&!readerStart&&!readerDone&&aggregateState==AG_IDLE&&(bankState[0]==READY||bankState[1]==READY))begin
                readBank<=bankState[0]==READY?1'b0:1'b1;bankState[bankState[0]==READY?0:1]<=READING;readerStart<=1;
            end
            if(aggregateDone)begin
                // Release the old reader even if its result loses arbitration.
                // Snapshot publication and calibration must use the same
                // accepted result as the report; never attach old good marker
                // words to the newer dropped frame's observation.
                bankState[readBank]<=FREE;
                if(captureDropNow&&completionDiscardCount!=16'hffff)
                    completionDiscardCount<=completionDiscardCount+16'd1;
            end
            if(aggregateAccepted)begin
                observation<=processedObservation;observationValid<=1;
                lastMarkers<=markers;lastFrameId<=processedObservation.frameId;lastCaptureUs<=processedObservation.captureStartUs;
                lastCompletionUs<=timeUs;haveFrame<=1;completedFrame<=1;completedFrameId<=processedObservation.frameId;
                lastFrameGood<=processedObservation.frameGood;
                lastFrameConfigVersion<=processedObservation.configVersion;
                lastFrameOrientation<=bankOrientation[readBank];
                lastFrameRedMinimum<=bankRedMinimum[readBank];lastFrameBlueMinimum<=bankBlueMinimum[readBank];
                lastRedCount<=bankRedCount[readBank];lastBlueCount<=bankBlueCount[readBank];
                lastPeakRed<=bankPeakRed[readBank];lastPeakBlue<=bankPeakBlue[readBank];
                lastCandidateFaults<=bankCandidateFaults[readBank];
                roiValid<=red1Paired&&processedObservation.frameGood;lastPairRed<=pairRed;lastPairBlue<=pairBlue;
            end
        end
    end
    always_comb begin
        status='0;status.interactionBusy=interactionBusy;status.kind=interactionKind;status.state=interactionState;
        status.calibrated=calibrated;status.audioReady=0;status.perceptionReady=haveFrame&&freshTime(timeUs,lastCompletionUs,32'd150000);
        status.activeCfgVersion=configVersion;status.reportDropCount=reportDropCount;status.eventOverflow=eventOverflow;
        status.faultFlags=faults;status.interactionId=interactionId;status.speechArmed=speechArmed;
        debugWords='0;
        debugWords[0*32+:32]=32'h45425031;debugWords[1*32+:32]=32'h00020002;
        debugWords[2*32+:32]=timeUs;debugWords[3*32+:32]={16'd0,lastFrameId};debugWords[4*32+:32]=lastCaptureUs;
        debugWords[5*32+:32]=lastCompletionUs;debugWords[6*32+:32]={16'd0,lastFrameConfigVersion};
        debugWords[7*32+:32]={12'd0,lastFrameOrientation,2'd0,lastFrameRedMinimum,lastFrameBlueMinimum};
        debugWords[8*32+:32]={16'd0,bufferDropCount};debugWords[9*32+:32]={24'd0,lastBlueCount,lastRedCount};
        debugWords[10*32+:76]=status;debugWords[13*32+:139]=targetReport;debugWords[18*32+:104]=userEvent;
        debugWords[22*32+:32]={15'd0,redSamples};debugWords[23*32+:32]={15'd0,blueSamples};
        for(int i=0;i<16;i++)begin
            debugWords[(24+i*4)*32+:32]={lastMarkers[i].accepted,lastMarkers[i].isBlue,lastMarkers[i].orientation,
                lastMarkers[i].digit,lastMarkers[i].quality,lastMarkers[i].reason,1'b0,lastMarkers[i].segments};
            debugWords[(25+i*4)*32+:32]={7'd0,lastMarkers[i].xMin,7'd0,lastMarkers[i].xMax};
            debugWords[(26+i*4)*32+:32]={8'd0,lastMarkers[i].yMin,8'd0,lastMarkers[i].yMax};
        end
        debugWords[88*32+:32]={10'd0,activeRequest};debugWords[89*32+:32]={28'd0,sampleCount};
        debugWords[90*32+:32]={30'd0,targetReportValid,userEventValid};
        debugWords[91*32+:32]={31'd0,lastFrameGood};
        debugWords[93*32+:32]={24'd0,lastPeakBlue,lastPeakRed};
        debugWords[94*32+:32]={completionDiscardCount,12'd0,transportFault,lastCandidateFaults};
        debugWords[95*32+:32]={8'd1,8'd2,8'(WHITE_LUMA_QUARTER),8'd64};
    end
endmodule
