`timescale 1ns/1ps
// True independent clocks exercise payload coherence and FIFO ordering. This is
// functional CDC verification; physical metastability/Gray-bus skew require STA.
module cdcTransport_tb;
    import perception_pkg::*;
    logic clk=0,pclk=0,reset=1;
    always #10 clk=~clk;
    initial begin #7; forever #17 pclk=~pclk; end
    logic [23:0] sourceData=0,destinationData;
    logic destinationValid;
    // These resets model the same external reset reaching two clock-domain
    // synchronisers on different edges. The FIFO/bridge keep their original
    // reset, so the mailbox recovery exercise cannot restart their scoreboards.
    logic mailboxSourceReset=1,mailboxDestinationReset=1;
    heldBusCdc #(.WIDTH(24)) mailbox(clk,mailboxSourceReset,sourceData,
        pclk,mailboxDestinationReset,destinationData,destinationValid);
    logic writeValid=0,readEnable=0,full,empty,readValid;
    logic [15:0] writeData=0,readData;
    asyncPixelFifo #(.WIDTH(16),.ADDRESS_BITS(3)) fifo(pclk,reset,writeValid,writeData,full,
        clk,reset,readEnable,readData,readValid,empty);
    logic frameStart=0,pixelValid=0,streamReady=0,streamValid,transportFault;
    logic [15:0] pixel=0;
    logic [9:0] pixelX=0;
    logic [8:0] pixelY=0;
    logic [31:0] timeUs=0;
    targetRequest_t activeRequest;
    logic [79:0] streamData;
    cameraStreamBridge bridge(.pclk(pclk),.resetPclk(reset),.frameStart(frameStart),
        .pixelValid(pixelValid),.pixel(pixel),.pixelX(pixelX),.pixelY(pixelY),
        .clk(clk),.reset(reset),.timeUs(timeUs),.activeRequest(activeRequest),
        .streamReady(streamReady),.streamValid(streamValid),.streamData(streamData),.transportFault(transportFault));
    logic [15:0] expected[0:4095];
    integer written=0,received=0,fullAttempts=0;
    integer streamCount=0,sofCount=0,pixelCount=0;
    logic [79:0] streamRecords[0:1023];
    logic mailboxChecking=0;
    integer mailboxAcceptedWords=0,mailboxHeldChecks=0,mailboxResetCases=0;
    logic [23:0] mailboxPreviousHeld;
    logic mailboxWasPending;

    // Sample the condition used by the source FSM before its nonblocking
    // updates, then compare after them. A pending word must remain unchanged
    // even when sourceData changes on every source cycle. Reset deliberately
    // cancels a transaction and is outside this normal-operation assertion.
    always @(posedge clk) begin
        mailboxPreviousHeld=mailbox.heldData;
        mailboxWasPending=mailbox.acknowledgeSync[1]!=mailbox.requestToggle;
        #1;
        if(mailboxChecking && !mailboxSourceReset && !mailboxDestinationReset && mailboxWasPending) begin
            if(mailbox.heldData!==mailboxPreviousHeld)
                $fatal(1,"mailbox payload changed before acknowledgement");
            mailboxHeldChecks++;
        end
    end
    always @(posedge pclk) begin
        #1;
        if(mailboxChecking && !mailboxSourceReset && !mailboxDestinationReset && destinationValid) begin
            if(destinationData[11:0] !== (destinationData[23:12] ^ 12'h5a5))
                $fatal(1,"held-bus word tore across clock domains");
            mailboxAcceptedWords++;
        end
    end
    always @(posedge pclk) begin
        if(!reset && writeValid) begin
            if(!full) begin expected[written]=writeData;written++;end
            else fullAttempts++;
        end
    end
    always @(posedge clk) begin
        if(reset) timeUs<=0;
        else begin
            timeUs<=timeUs+1;
            if(readValid) begin
                if(received>=written || readData!==expected[received])
                    $fatal(1,"FIFO ordering at %0d got=%0h expected=%0h",received,readData,expected[received]);
                received++;
            end
            // streamReady grants a registered FIFO pop. The returned token is
            // consumed even if streamReady drops before this edge.
            if(streamValid) begin
                streamRecords[streamCount]=streamData;streamCount++;
                if(streamData[79]) sofCount++; else pixelCount++;
            end
        end
    end
    task automatic sourceFrame;
        @(negedge pclk);frameStart=1;
        @(negedge pclk);frameStart=0;
    endtask
    task automatic sourcePixel(input integer x,input integer y,input integer value);
        @(negedge pclk);pixelX=x;pixelY=y;pixel=value;pixelValid=1;
        @(negedge pclk);pixelValid=0;
    endtask
    task automatic skewedCommonReset(input integer caseNumber,input bit sourceFirst,
        input bit releaseSourceFirst,input integer phaseNs);
        integer acceptedBefore;
        // Interrupt a real launched transaction before its acknowledgement.
        // The phase sweep moves the shared reset request around both clocks.
        @(negedge clk);sourceData={12'(100+caseNumber),12'((100+caseNumber)^12'h5a5)};
        @(posedge clk);#1;
        if(mailbox.acknowledgeSync[1]==mailbox.requestToggle)
            $fatal(1,"reset test did not start with an outstanding word");
        #(phaseNs);
        // No delivery promise applies while only one domain has reached reset.
        // Consumers cancel that transaction rather than accepting its contents.
        mailboxChecking=0;
        if(sourceFirst)mailboxSourceReset=1;
        else mailboxDestinationReset=1;
        #(11+caseNumber%9);
        mailboxSourceReset=1;mailboxDestinationReset=1;sourceData=0;
        repeat(6) @(negedge pclk);
        if(mailbox.heldData!==0 || mailbox.requestToggle!==0 || mailbox.acknowledgeSync!==0 ||
            destinationData!==0 || destinationValid!==0 || mailbox.requestSync!==0 || mailbox.acknowledgeToggle!==0)
            $fatal(1,"common reset did not clear both mailbox endpoints, case=%0d",caseNumber);
        if(releaseSourceFirst)mailboxSourceReset=0;
        else mailboxDestinationReset=0;
        #19;
        mailboxSourceReset=0;mailboxDestinationReset=0;
        // Keep the zero reset value until both endpoints have left reset. This
        // does not claim support for arbitrary independent endpoint resets.
        repeat(4) @(negedge pclk);
        if(destinationData!==0 || destinationValid!==0 || mailbox.requestToggle!==mailbox.acknowledgeSync[1])
            $fatal(1,"mailbox failed reset quiescence, case=%0d",caseNumber);
        mailboxChecking=1;acceptedBefore=mailboxAcceptedWords;
        @(negedge clk);sourceData={12'(1000+caseNumber),12'((1000+caseNumber)^12'h5a5)};
        repeat(12) @(negedge pclk);
        if(destinationData!==sourceData || mailboxAcceptedWords!=acceptedBefore+1)
            $fatal(1,"fresh post-reset word not delivered exactly once, case=%0d",caseNumber);
        mailboxResetCases++;
    endtask
    initial begin
        activeRequest='0;
        repeat(6) @(negedge pclk);
        reset=0;mailboxSourceReset=0;mailboxDestinationReset=0;
        // Latest-value coalescing may skip intermediate requests, but every
        // received word must be one complete source word and final value arrives.
        mailboxChecking=1;
        for(int n=1;n<=40;n++) begin
            @(negedge clk);sourceData={12'(n),12'(n^12'h5a5)};
        end
        repeat(20) @(negedge pclk);
        if(destinationData!==sourceData) $fatal(1,"mailbox failed eventual delivery");
        // Both assertion orders, both release orders, and sixteen reset phases
        // retain the existing 20 ns / 34 ns independent clocks. This tests
        // functional recovery, not metastability or physical hold margins.
        for(int caseNumber=0;caseNumber<16;caseNumber++)
            skewedCommonReset(caseNumber,bit'(caseNumber&1),bit'((caseNumber>>1)&1),1+caseNumber%8);
        if(mailboxResetCases!=16 || mailboxHeldChecks<100)
            $fatal(1,"mailbox reset/stability coverage missing");
        $display("PASS mailbox skewed common reset: cases=%0d heldChecks=%0d acceptedWords=%0d",
            mailboxResetCases,mailboxHeldChecks,mailboxAcceptedWords);
        // Fill all eight entries, refuse further writes, then drain exactly once.
        for(int n=1;n<=18;n++) begin
            @(negedge pclk);writeData=n;writeValid=1;
        end
        @(negedge pclk);writeValid=0;
        if(!full || written!=8 || fullAttempts!=10) $fatal(1,"FIFO full capacity");
        @(negedge clk);readEnable=1;
        repeat(20) @(negedge clk);
        if(!empty || received!=8) $fatal(1,"FIFO drain");
        for(int n=0;n<100;n++) begin
            @(negedge pclk);writeData=100+n;writeValid=(n%3)!=0;
        end
        @(negedge pclk);writeValid=0;
        repeat(20) @(negedge clk);
        if(written!=received || !empty) $fatal(1,"FIFO concurrent ordering/drain");
        // The bridge snapshots the held request at SOF, not at pixel completion.
        activeRequest.operation=TARGET_SELECT;activeRequest.markerType=MARKER_BAY;activeRequest.requestTag=16'h1234;activeRequest.digit=3;
        streamReady=1;
        repeat(20) @(negedge pclk);
        sourceFrame();
        activeRequest.requestTag=16'h5678;activeRequest.markerType=MARKER_FUNCTION;activeRequest.digit=2;
        sourcePixel(20,40,16'hf81f);
        sourcePixel(21,40,16'hffff); // odd X is excluded by the native reduction
        sourcePixel(22,41,16'hffff); // odd Y is excluded
        sourcePixel(22,40,16'h1234);
        repeat(20) @(negedge clk);
        if(streamCount!=3 || sofCount!=1 || pixelCount!=2) $fatal(1,"bridge token count");
        if(streamRecords[0][73:50]!=={TARGET_SELECT,16'h1234,MARKER_BAY,4'd3} || streamRecords[0][49:34]!=1)
            $fatal(1,"SOF request ownership");
        if(streamRecords[1][32:24]!=10 || streamRecords[1][23:16]!=20 || streamRecords[1][15:0]!=16'hf81f)
            $fatal(1,"native pixel mapping");
        repeat(15) @(negedge pclk);
        sourceFrame();
        repeat(20) @(negedge clk);
        if(streamRecords[3][73:50]!=={TARGET_SELECT,16'h5678,MARKER_FUNCTION,4'd2} || streamRecords[3][49:34]!=2)
            $fatal(1,"next SOF did not use coherent updated request");
        if(streamRecords[3][33:2]<=streamRecords[0][33:2] || streamRecords[3][33:2]>timeUs)
            $fatal(1,"capture timestamp order");
        // Registered return stays valid after a pop grant has been withdrawn.
        streamReady=0;
        sourcePixel(24,40,16'hbeef);
        repeat(5) @(negedge clk);
        streamReady=1;
        @(negedge clk);streamReady=0;
        repeat(5) @(negedge clk);
        if(streamCount!=5 || streamRecords[4][15:0]!=16'hbeef) $fatal(1,"in-flight FIFO return lost");
        // No receiver service: explicit overflow; no overwrite of unread words.
        for(int n=0;n<270;n++) sourcePixel(2*(n%320),0,n);
        repeat(5) @(negedge clk);
        if(!transportFault) $fatal(1,"bridge overflow not reported");
        streamReady=1;
        repeat(600) @(negedge clk);
        if(streamCount!=261) $fatal(1,"overflow must retain first 256 tokens only, count=%0d",streamCount);
        for(int n=0;n<256;n++)
            if(streamRecords[5+n][15:0]!=n) $fatal(1,"overflow overwrote FIFO contents");
        sourceFrame();
        repeat(10) @(negedge clk);
        if(!streamRecords[261][78]) $fatal(1,"fault provenance absent from SOF");
        sourceFrame();
        repeat(10) @(negedge clk);
        if(streamRecords[262][78] || !transportFault)
            $fatal(1,"complete-frame recovery must clear transient fault and preserve sticky diagnostic");
        $display("PASS cdcTransport_tb");
        $finish;
    end
    initial begin #2000000; $fatal(1,"timeout cdcTransport_tb"); end
endmodule
