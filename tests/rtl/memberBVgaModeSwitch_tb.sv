`timescale 1ns/1ps
// Packet ownership test for the raw display switch. Raw checks compare all30
// camera bits and SOP/EOP. Processed checks compare a separate unchanged overlay
// instance fed on exactly the same clocks, including both diagnostic switches.
module memberBVgaModeSwitch_tb;
    logic clk=0, reset=1;
    logic [perception_pkg::DEBUG_WORD_COUNT*32-1:0] debugWords=0;
    logic showCandidates=1, showCentre=1;
    logic rawModeRequested=0, rawModeActive;
    logic [29:0] inData=0, outData;
    logic inSop=0, inEop=0, inValid=0, inReady;
    logic outSop, outEop, outValid, outReady=0;
    logic [29:0] referenceData;
    logic referenceSop, referenceEop, referenceValid, referenceReady;
    logic manualStall=0, toggleOnStall=0, expectedInputMode=0;
    logic [31:0] expectedPayload[0:63];
    logic expectedRaw[0:63];
    logic stalled=0, heldMode;
    logic [31:0] heldPayload;
    int writeIndex=0, readIndex=0, queued=0, cycles=0;
    int accepted=0, consumed=0, rawChecked=0, normalChecked=0;
    int normalChanged=0, stallToggles=0, rawBeforeReset=0, normalBeforeReset=0;

    always #5 clk=~clk;
    memberBVgaModeSwitch dut(.*);
    memberBVgaOverlay referenceOverlay(
        .clk(clk), .reset(reset || rawModeActive), .debugWords(debugWords),
        .showCandidates(showCandidates), .showCentre(showCentre),
        .inData(inData), .inSop(inSop), .inEop(inEop),
        .inValid(dut.overlayInValid), .inReady(referenceReady),
        .outData(referenceData), .outSop(referenceSop), .outEop(referenceEop),
        .outValid(referenceValid), .outReady(dut.overlayOutReady)
    );

    // Deterministic downstream stalls exercise both the processed EOP drain and
    // raw zero-latency path. Requests also change during an offered/stalled pixel.
    always @(negedge clk) begin
        cycles++;
        outReady=!reset && !manualStall && cycles%11>=3;
        if(!reset && toggleOnStall && outValid && !outReady) begin
            rawModeRequested=~rawModeRequested;
            toggleOnStall=0;
            stallToggles++;
        end
    end

    always @(posedge clk) begin
        if(reset) begin
            writeIndex=0; readIndex=0; queued=0;
            accepted=0; consumed=0; rawChecked=0; normalChecked=0;
            stalled=0; normalChanged=0;
        end else begin
            if(stalled && (!outValid || heldPayload!=={outSop,outEop,outData} || heldMode!==rawModeActive))
                $fatal(1,"FAIL mode switch changed offered payload/mode while stalled");
            stalled=outValid && !outReady;
            heldPayload={outSop,outEop,outData}; heldMode=rawModeActive;
            if(rawModeActive && (!dut.overlayReset || dut.overlayInValid || dut.overlayOutReady))
                $fatal(1,"FAIL raw mode did not hold overlay reset/inactive");
            if(!rawModeActive && dut.overlayInValid && referenceReady!==dut.overlayInReady)
                $fatal(1,"FAIL normal reference input handshake differs");
            if(inValid && inReady) begin
                if(rawModeActive!==expectedInputMode)$fatal(1,"FAIL selected wrong packet mode");
                if(queued==64)$fatal(1,"FAIL unexpected unbounded packet buffering");
                expectedPayload[writeIndex]={inSop,inEop,inData};
                expectedRaw[writeIndex]=expectedInputMode;
                writeIndex=(writeIndex+1)%64; queued++; accepted++;
            end
            if(outValid && outReady) begin
                if(queued==0)$fatal(1,"FAIL duplicate/output without input");
                if({outSop,outEop}!==expectedPayload[readIndex][31:30])
                    $fatal(1,"FAIL packet boundaries mixed/lost");
                if(rawModeActive!==expectedRaw[readIndex])$fatal(1,"FAIL packet mode changed before EOP drain");
                if(expectedRaw[readIndex]) begin
                    if({outSop,outEop,outData}!==expectedPayload[readIndex])
                        $fatal(1,"FAIL raw pixels changed with SW0/SW1 enabled");
                    rawChecked++;
                end else begin
                    if(!referenceValid || {outSop,outEop,outData}!=={referenceSop,referenceEop,referenceData})
                        $fatal(1,"FAIL processed output differs from original overlay");
                    normalChecked++;
                    if(outData!==expectedPayload[readIndex][29:0])normalChanged++;
                end
                readIndex=(readIndex+1)%64; queued--; consumed++;
            end
        end
    end

    function automatic logic [29:0] pixelValue(input int pixel, input int seed);
        logic [31:0] value;
        value=32'(pixel)*32'd1664525 ^ (32'(seed)*32'd1013904223);
        return value[29:0];
    endfunction

    task automatic sendPixel(input logic [29:0] value, input logic sop, input logic eop);
        @(negedge clk); #1;
        inData=value; inSop=sop; inEop=eop; inValid=1;
        @(posedge clk);
        while(!inReady)@(posedge clk);
    endtask

    task automatic sendPacket(input int length, input logic mode, input logic toggleMidPacket, input int seed);
        @(negedge clk); #1;
        rawModeRequested=mode; expectedInputMode=mode;
        for(int pixel=0;pixel<length;pixel++) begin
            if(pixel!=0)begin @(negedge clk); #1; end
            if(toggleMidPacket && pixel==17)toggleOnStall=1;
            inData=pixelValue(pixel,seed); inSop=pixel==0;
            inEop=pixel==length-1; inValid=1;
            @(posedge clk);
            while(!inReady)@(posedge clk);
        end
    endtask

    task automatic drain;
        @(negedge clk); #1;
        inValid=0; inSop=0; inEop=0;
        repeat(32)@(negedge clk);
        if(queued!=0 || outValid || accepted!=consumed)$fatal(1,"FAIL packet did not fully drain");
    endtask

    initial begin
        debugWords[31:0]=32'h45425031;
        debugWords[7*32+8+:8]=8'd48;
        debugWords[7*32+:8]=8'd20;
        repeat(4)@(negedge clk); #1; reset=0;

        // Normal -> raw -> normal; both switch changes happen inside stalled
        // packets and may only affect a subsequent packet. Raw covers every
        // pixel of a full640x480 display packet, with arbitrary low RGB bits.
        sendPacket(640*480,0,1,1);
        sendPacket(640*480,1,1,2);
        sendPacket(4096,0,0,3);
        sendPacket(4096,0,0,4);
        drain();
        if(stallToggles!=2 || rawChecked!=640*480 || normalChecked!=640*480+8192 || normalChanged==0)
            $fatal(1,"FAIL full packet coverage or expected normal overlays missing");

        // Back-to-back one-pixel packets stress SOP metadata and the processed
        // EOP drain, rather than depending on a full-frame blanking interval.
        for(int packet=0;packet<64;packet++)sendPacket(1,1'(packet%2),0,packet+10);
        drain();
        rawBeforeReset=rawChecked; normalBeforeReset=normalChecked;

        // Reset is the only permitted packet abort. Reset while a normal output
        // is offered under stall, then prove new raw/normal packets start cleanly.
        @(negedge clk); #1; rawModeRequested=0; expectedInputMode=0;
        for(int pixel=0;pixel<8;pixel++)sendPixel(pixelValue(pixel,99),pixel==0,0);
        @(negedge clk); #1; inValid=0; manualStall=1;
        wait(outValid); repeat(3)@(negedge clk);
        #1; reset=1; inValid=0; manualStall=0;
        repeat(4)@(negedge clk); #1; reset=0;
        for(int packet=0;packet<16;packet++)sendPacket(1,1'(packet%2),0,packet+100);
        drain();
        if(rawChecked!=8 || normalChecked!=8)$fatal(1,"FAIL post-reset accounting");
        $display("PASS memberBVgaModeSwitch_tb raw30-bit=%0d normal-reference=%0d plus reset/one-pixel/backpressure/mid-stall toggles",
            rawBeforeReset+rawChecked,normalBeforeReset+normalChecked);
        $finish;
    end
    initial begin #200000000; $fatal(1,"FAIL mode switch timeout"); end
endmodule
