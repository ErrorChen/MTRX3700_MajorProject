`timescale 1ns/1ps
module markerQueryStore_tb;
    import perception_pkg::*;
    logic clk=0,reset=1;
    always #5 clk=~clk;
    logic [31:0] timeUs=32'd1000;
    logic [15:0] activeConfigVersion=1;
    logic perceptionReady=1;
    logic beginFrame=0,inputFrameGood=1,writeValid=0,writeAccepted=0;
    logic [15:0] inputFrameId=0,inputConfigVersion=1;
    logic [31:0] inputCaptureStartUs=1000;
    logic [3:0] writeIndex=0,writeDigit=0;
    markerType_t writeType=MARKER_NONE;
    logic [7:0] writeQuality=0,writeYMin=0,writeYMax=0;
    logic [8:0] writeXMin=0,writeXMax=0;
    logic commitFrame=0,cancelFrame=0,publishBad=0;
    logic [15:0] badFrameId=0,badConfigVersion=1;
    logic [31:0] badCaptureStartUs=1000;
    targetRequest_t queryRequest;
    logic queryRequestValid=0,queryRequestReady;
    queryResult_t queryResult;
    logic queryResultValid,queryResultReady=0,queryBusy;
    integer checks=0,packets=0,queries=0,nextTag=1;
    logic [15:0] currentTag;
    logic wasStalled=0;
    queryResult_t stalledPayload;

    markerQueryStore dut(.*);

    // This monitor is independent of the query tasks. Every held beat must
    // remain stable even while all three bank roles rotate underneath it.
    always @(posedge clk) begin
        if(reset) wasStalled<=0;
        else begin
            if(wasStalled) begin
                assert(queryResultValid&&queryResult===stalledPayload)
                    else $fatal(1,"Stalled query payload changed");
            end
            wasStalled<=queryResultValid&&!queryResultReady;
            stalledPayload<=queryResult;
            if(queryBusy) assert(!queryRequestReady)
                else $fatal(1,"Outstanding query accepted another query");
        end
    end

    task automatic step;
        @(posedge clk);#1;
    endtask
    task automatic check(input logic condition,input string message);
        checks++;
        if(condition!==1'b1) $fatal(1,"%s (check %0d, time %0t)",message,checks,$time);
    endtask
    task automatic resetStore;
        @(negedge clk);reset=1;beginFrame=0;writeValid=0;commitFrame=0;
        cancelFrame=0;publishBad=0;queryRequestValid=0;queryResultReady=0;
        repeat(2) step();
        @(negedge clk);reset=0;
        step();
        check(queryRequestReady&&!queryResultValid&&!queryBusy,"Reset did not clear ownership/query state");
    endtask
    task automatic startFrame(input integer frameNumber,input logic [31:0] stamp,
            input integer version,input logic good=1);
        @(negedge clk);
        inputFrameId=16'(frameNumber);inputCaptureStartUs=stamp;
        inputConfigVersion=16'(version);inputFrameGood=good;beginFrame=1;
        step();@(negedge clk);beginFrame=0;
    endtask
    // Pattern0 is empty; pattern1 has five recognised items (including two
    // distinct blue1 positions and red1); pattern2 fills all sixteen slots.
    // Slot15 in pattern1 is initially unknown blue, then explicitly BJ-patched.
    task automatic setDescriptor(input integer slot,input integer pattern,input integer offset);
        writeIndex=4'(slot);writeAccepted=0;writeType=MARKER_BAY;writeDigit=4'd6;
        writeQuality=8'(150+slot);writeXMin=9'(10+slot*12+offset);
        writeXMax=writeXMin+9'd3;writeYMin=8'(20+slot*5);writeYMax=writeYMin+8'd4;
        if(pattern==2) begin writeAccepted=1;writeDigit=4'(slot%6+1);end
        if(pattern==1) begin
            case(slot)
                0: begin writeAccepted=1;writeDigit=1;writeQuality=180;end
                1: begin writeAccepted=1;writeType=MARKER_FUNCTION;writeDigit=1;writeQuality=200;end
                2: begin writeAccepted=1;writeDigit=1;writeQuality=210;end
                3: begin writeAccepted=1;writeDigit=2;writeQuality=220;end
                // No digit is accepted merely because a blue candidate exists.
                default: begin writeAccepted=0;writeDigit=4'hf;end
            endcase
        end
    endtask
    task automatic writeOne(input integer slot,input integer pattern,input integer offset);
        @(negedge clk);setDescriptor(slot,pattern,offset);writeValid=1;
        step();@(negedge clk);writeValid=0;
    endtask
    task automatic finishFrame;
        @(negedge clk);commitFrame=1;step();@(negedge clk);commitFrame=0;
    endtask
    task automatic fillFrame(input integer frameNumber,input logic [31:0] stamp,
            input integer version,input integer pattern,input integer offset=0,input logic good=1);
        startFrame(frameNumber,stamp,version,good);
        for(integer slot=0;slot<16;slot++) writeOne(slot,pattern,offset);
        if(pattern==1) begin
            // The producer may replace the rejected reference candidate on the
            // exact commit edge, after the unique same-frame red1 pairing.
            @(negedge clk);setDescriptor(15,pattern,offset);
            writeAccepted=1;writeType=MARKER_REFERENCE;writeDigit=4'hf;writeQuality=200;
            writeValid=1;commitFrame=1;step();
            @(negedge clk);writeValid=0;commitFrame=0;
        end else finishFrame();
    endtask
    task automatic sendQuery(input targetOperation_t operation,input markerType_t kind,input logic [3:0] digit);
        @(negedge clk);
        check(queryRequestReady,"Query channel unexpectedly busy");
        currentTag=16'(nextTag);nextTag++;queries++;
        queryRequest.operation=operation;queryRequest.requestTag=currentTag;
        queryRequest.markerType=kind;queryRequest.digit=digit;queryRequestValid=1;
        step();@(negedge clk);queryRequestValid=0;
    endtask
    task automatic awaitPacket;
        integer waited;
        waited=0;
        while(!queryResultValid&&waited<150) begin step();waited++;end
        check(queryResultValid,"Query did not finish bounded synchronous scan");
        check(queryBusy&&!queryRequestReady,"Presented query did not retain ownership");
        check(queryResult.requestTag==currentTag,"Query tag changed");
    endtask
    task automatic consumePacket;
        @(negedge clk);queryResultReady=1;step();packets++;
        @(negedge clk);queryResultReady=0;
    endtask
    task automatic checkHeader(input integer frameNumber,input logic [31:0] stamp,input integer version);
        check(queryResult.frameId==16'(frameNumber),"Wrong snapshot frame");
        check(queryResult.captureStartUs==stamp,"Capture timestamp was replaced or mixed");
        check(queryResult.configVersion==16'(version),"Configuration mixed across query");
    endtask
    task automatic expectEmpty(input queryReason_t reason,input integer frameNumber,
            input logic [31:0] stamp,input integer version);
        awaitPacket();checkHeader(frameNumber,stamp,version);
        check(queryResult.reason==reason,"Wrong empty/error reason");
        check(queryResult.count==0&&queryResult.index==0&&queryResult.last,"Invalid empty packet framing");
        check(queryResult.markerType==MARKER_NONE&&queryResult.digit==4'hf,"Empty packet exposed identity");
        check({queryResult.centreU,queryResult.centreV,queryResult.boxWidth,
               queryResult.boxHeight,queryResult.quality}=='0,"Empty packet exposed geometry");
        consumePacket();check(queryRequestReady&&!queryBusy,"Empty transaction did not release reader");
    endtask
    task automatic expectItem(input integer frameNumber,input logic [31:0] stamp,input integer version,
            input integer count,input integer index,input integer slot,input integer pattern,
            input integer offset,input queryReason_t reason);
        integer xLo,xHi,yLo,yHi,expectedQuality,expectedDigit;
        markerType_t expectedType;
        xLo=10+slot*12+offset;xHi=xLo+3;yLo=20+slot*5;yHi=yLo+4;
        expectedType=MARKER_BAY;expectedDigit=slot%6+1;expectedQuality=150+slot;
        if(pattern==1) case(slot)
            0: begin expectedDigit=1;expectedQuality=180;end
            1: begin expectedType=MARKER_FUNCTION;expectedDigit=1;expectedQuality=200;end
            2: begin expectedDigit=1;expectedQuality=210;end
            3: begin expectedDigit=2;expectedQuality=220;end
            15: begin expectedType=MARKER_REFERENCE;expectedDigit=15;expectedQuality=200;end
            default: $fatal(1,"Test requested a rejected pattern1 slot");
        endcase
        awaitPacket();checkHeader(frameNumber,stamp,version);
        check(queryResult.reason==reason,"Wrong nonempty reason");
        check(queryResult.count==count&&queryResult.index==index&&queryResult.last==(index==count-1),
              "Incorrect count/index/last");
        check(queryResult.markerType==expectedType&&queryResult.digit==expectedDigit,"Wrong type/digit");
        // Arithmetic oracle uses integer transformed endpoints, including an
        // even native width whose rounded native centre would give the wrong V.
        check(queryResult.centreU==(yLo+yHi)/2&&queryResult.centreV==(638-xLo-xHi)/2,
              "Native bbox was not transformed before floor-centre");
        check(queryResult.boxWidth==yHi-yLo+1&&queryResult.boxHeight==xHi-xLo+1,"Wrong inclusive dimensions");
        check(queryResult.quality==expectedQuality,"Quality mixed or lost");
        consumePacket();
    endtask
    task automatic expectSmallList(input integer frameNumber,input logic [31:0] stamp,input integer version,
            input integer offset=0);
        for(integer item=0;item<5;item++)
            expectItem(frameNumber,stamp,version,5,item,item==4?15:item,1,offset,QUERY_OK);
    endtask
    task automatic badFrame(input integer frameNumber,input logic [31:0] stamp,input integer version);
        @(negedge clk);publishBad=1;badFrameId=16'(frameNumber);
        badCaptureStartUs=stamp;badConfigVersion=16'(version);step();@(negedge clk);publishBad=0;
    endtask

    initial begin
        queryRequest='0;
        check($bits(targetRequest_t)==24&&$bits(targetReport_t)==141&&$bits(queryResult_t)==141&&
              $bits(userEvent_t)==104&&$bits(perceptionStatus_t)==76,"Public v3 widths differ");
        resetStore();
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_NOT_READY,0,0,1);
        sendQuery(TARGET_GET,MARKER_BAY,0);expectEmpty(QUERY_INVALID_REQUEST,0,0,1);
        sendQuery(TARGET_SELECT,MARKER_BAY,1);expectEmpty(QUERY_INVALID_REQUEST,0,0,1);
        sendQuery(TARGET_CLEAR,MARKER_NONE,4'hf);expectEmpty(QUERY_INVALID_REQUEST,0,0,1);

        fillFrame(1,1000,1,1);
        sendQuery(TARGET_GET,MARKER_BAY,1);
        expectItem(1,1000,1,2,0,0,1,0,QUERY_MULTIPLE);
        expectItem(1,1000,1,2,1,2,1,0,QUERY_MULTIPLE);
        sendQuery(TARGET_GET,MARKER_FUNCTION,1);expectItem(1,1000,1,1,0,1,1,0,QUERY_OK);
        sendQuery(TARGET_GET,MARKER_REFERENCE,4'hf);expectItem(1,1000,1,1,0,15,1,0,QUERY_OK);
        sendQuery(TARGET_GET,MARKER_BAY,6);expectEmpty(QUERY_NOT_FOUND,1,1000,1);
        sendQuery(TARGET_GET,MARKER_REFERENCE,1);expectEmpty(QUERY_INVALID_REQUEST,1,1000,1);
        sendQuery(TARGET_GET,MARKER_FUNCTION,3);expectEmpty(QUERY_INVALID_REQUEST,1,1000,1);
        sendQuery(TARGET_GET,MARKER_NONE,4'hf);expectEmpty(QUERY_INVALID_REQUEST,1,1000,1);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectSmallList(1,1000,1);

        fillFrame(2,1000,1,2);
        sendQuery(TARGET_LIST,MARKER_NONE,0);
        for(integer slot=0;slot<16;slot++) expectItem(2,1000,1,16,slot,slot,2,0,QUERY_OK);
        fillFrame(3,1000,1,0);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_NOT_FOUND,3,1000,1);

        // Hold the first beat through twenty fully published frames and a
        // readiness/config/time change; release must return the old whole list.
        fillFrame(4,1000,1,1);
        sendQuery(TARGET_LIST,MARKER_NONE,0);awaitPacket();
        activeConfigVersion=2;perceptionReady=0;timeUs=500000;
        for(integer frameNumber=5;frameNumber<=24;frameNumber++) fillFrame(frameNumber,500000,2,2,frameNumber);
        expectSmallList(4,1000,1);
        perceptionReady=1;
        sendQuery(TARGET_GET,MARKER_BAY,6);
        expectItem(24,500000,2,2,0,5,2,24,QUERY_MULTIPLE);
        expectItem(24,500000,2,2,1,11,2,24,QUERY_MULTIPLE);

        // Query accepts the pre-edge latest despite a concurrent good commit.
        startFrame(25,500000,2);
        for(integer slot=0;slot<16;slot++) writeOne(slot,0,0);
        @(negedge clk);commitFrame=1;
        currentTag=16'(nextTag);nextTag++;queries++;
        queryRequest='{TARGET_GET,currentTag,MARKER_BAY,4'd6};queryRequestValid=1;
        step();@(negedge clk);commitFrame=0;queryRequestValid=0;
        expectItem(24,500000,2,2,0,5,2,24,QUERY_MULTIPLE);
        expectItem(24,500000,2,2,1,11,2,24,QUERY_MULTIPLE);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_NOT_FOUND,25,500000,2);

        // Same contract for query acceptance coincident with a bad publication.
        fillFrame(26,500000,2,1);
        @(negedge clk);publishBad=1;badFrameId=27;badCaptureStartUs=500000;badConfigVersion=2;
        currentTag=16'(nextTag);nextTag++;queries++;
        queryRequest='{TARGET_LIST,currentTag,MARKER_NONE,4'hf};queryRequestValid=1;
        step();@(negedge clk);publishBad=0;queryRequestValid=0;
        expectSmallList(26,500000,2);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,27,500000,2);

        // A newer bad capture cancels an older completion, both same edge and
        // delayed; equal frame good commits never resurrect a known bad frame.
        startFrame(28,500000,2);
        for(integer slot=0;slot<16;slot++) writeOne(slot,2,0);
        @(negedge clk);commitFrame=1;publishBad=1;badFrameId=29;step();
        @(negedge clk);commitFrame=0;publishBad=0;
        finishFrame();
        fillFrame(29,500000,2,2);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,29,500000,2);

        // Conversely, an older bad event must preserve the newer writer and
        // its same-cycle descriptor write. The three-bank fallback is exercised
        // with an old query held, a newer latest and an active writer.
        fillFrame(30,500000,2,1);sendQuery(TARGET_LIST,MARKER_NONE,0);awaitPacket();
        fillFrame(31,500000,2,2);
        startFrame(33,500000,2);
        for(integer slot=0;slot<8;slot++) writeOne(slot,2,33);
        @(negedge clk);setDescriptor(8,2,33);writeValid=1;publishBad=1;badFrameId=32;
        step();@(negedge clk);writeValid=0;publishBad=0;
        for(integer slot=9;slot<16;slot++) writeOne(slot,2,33);
        finishFrame();expectSmallList(30,500000,2);
        sendQuery(TARGET_LIST,MARKER_NONE,0);
        for(integer slot=0;slot<16;slot++) expectItem(33,500000,2,16,slot,slot,2,33,QUERY_OK);

        // A final writer beat+commit can also coincide with an older bad event.
        startFrame(35,500000,2);
        for(integer slot=0;slot<15;slot++) writeOne(slot,2,35);
        @(negedge clk);setDescriptor(15,2,35);writeValid=1;commitFrame=1;publishBad=1;badFrameId=34;
        step();@(negedge clk);writeValid=0;commitFrame=0;publishBad=0;
        sendQuery(TARGET_LIST,MARKER_NONE,0);
        for(integer slot=0;slot<16;slot++) expectItem(35,500000,2,16,slot,slot,2,35,QUERY_OK);
        badFrame(34,1,1);
        sendQuery(TARGET_GET,MARKER_BAY,6);
        expectItem(35,500000,2,2,0,5,2,35,QUERY_MULTIPLE);
        expectItem(35,500000,2,2,1,11,2,35,QUERY_MULTIPLE);
        badFrame(35,500000,2);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,35,500000,2);

        // Missing a slot invalidates the whole frame, irrespective of old RAM
        // contents. Explicit bad candidate frames and cancelled writes likewise
        // cannot expose stale accepted entries.
        startFrame(36,500000,2);
        for(integer slot=0;slot<15;slot++) writeOne(slot,2,0);
        finishFrame();sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,36,500000,2);
        fillFrame(37,500000,2,2,0,0);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,37,500000,2);
        startFrame(38,500000,2);writeOne(0,2,0);
        @(negedge clk);cancelFrame=1;step();@(negedge clk);cancelFrame=0;finishFrame();
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,37,500000,2);

        // Error priority and exact age boundaries, including time/frame wrap.
        perceptionReady=0;activeConfigVersion=3;timeUs=900000;
        sendQuery(TARGET_GET,MARKER_BAY,0);expectEmpty(QUERY_INVALID_REQUEST,37,500000,2);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_NOT_READY,37,500000,2);
        perceptionReady=1;
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,37,500000,2);
        fillFrame(38,800000,2,1);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_STALE,38,800000,2);
        activeConfigVersion=2;timeUs=950000;
        sendQuery(TARGET_GET,MARKER_FUNCTION,1);expectItem(38,800000,2,1,0,1,1,0,QUERY_OK);
        timeUs=950001;
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_STALE,38,800000,2);
        timeUs=799999;
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_STALE,38,800000,2);

        resetStore();activeConfigVersion=4;timeUs=32'h20;
        fillFrame(65535,32'hfffffff0,4,1);
        sendQuery(TARGET_GET,MARKER_FUNCTION,1);expectItem(65535,32'hfffffff0,4,1,0,1,1,0,QUERY_OK);
        fillFrame(0,32'h10,4,1,4);
        sendQuery(TARGET_GET,MARKER_FUNCTION,1);expectItem(0,32'h10,4,1,0,1,1,4,QUERY_OK);
        badFrame(65535,32'hfffffff0,4);badFrame(32768,32'h10,4);
        sendQuery(TARGET_GET,MARKER_FUNCTION,1);expectItem(0,32'h10,4,1,0,1,1,4,QUERY_OK);
        badFrame(1,32'h20,4);
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_FRAME_BAD,1,32'h20,4);

        fillFrame(2,32'h20,4,1);sendQuery(TARGET_LIST,MARKER_NONE,0);awaitPacket();
        resetStore();
        sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_NOT_READY,0,0,4);

        // Defence at the descriptor boundary: an upstream acceptance bit alone
        // cannot publish zero quality, illegal identity or malformed geometry.
        startFrame(3,32'h20,4);
        for(integer slot=0;slot<16;slot++) begin
            @(negedge clk);setDescriptor(slot,0,0);writeValid=1;
            case(slot)
                0: begin writeAccepted=1;writeQuality=0;end
                1: begin writeAccepted=1;writeXMin=50;writeXMax=49;end
                2: begin writeAccepted=1;writeXMax=320;end
                3: begin writeAccepted=1;writeYMax=240;end
                4: begin writeAccepted=1;writeYMin=60;writeYMax=59;end
                5: begin writeAccepted=1;writeType=MARKER_NONE;end
                6: begin writeAccepted=1;writeDigit=7;end
                7: begin writeAccepted=1;writeType=MARKER_FUNCTION;writeDigit=6;end
                default: begin end
            endcase
            step();@(negedge clk);writeValid=0;
        end
        finishFrame();sendQuery(TARGET_LIST,MARKER_NONE,0);expectEmpty(QUERY_NOT_FOUND,3,32'h20,4);
        $display("PASS markerQueryStore_tb checks=%0d queries=%0d consumedPackets=%0d banks=3 slots=16 v3=1",checks,queries,packets);
        $finish;
    end
    initial begin #2000000;$fatal(1,"markerQueryStore_tb timeout");end
endmodule
