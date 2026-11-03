`timescale 1ns/1ps
// Exercise the actual latest-value mailbox at the schema6 display width.
// This proves logical payload ownership/coalescing, not analogue metastability
// or the physical bundled-data delay: those remain Quartus timing obligations.
module memberBDisplayCdc_tb;
    import perception_pkg::*;
    logic sourceClk=0,destinationClk=0,sourceReset=1,destinationReset=1;
    logic [DEBUG_WORD_COUNT*32-1:0] sourceData=0,destinationData;
    logic destinationValid;
    logic [DEBUG_WORD_COUNT*32-1:0] previousHeld=0;
    logic previousBusy=0;
    int updates=0,received=0,holdingChecks=0;
    logic [31:0] lastIdentity=0;
    // Deliberately unrelated clocks and phase; source updates frequently arrive
    // while a previous payload is still waiting for its acknowledgement.
    always #10 sourceClk=~sourceClk;
    initial begin #3;forever #19 destinationClk=~destinationClk;end
    heldBusCdc #(.WIDTH(DEBUG_WORD_COUNT*32)) dut(.*);

    function automatic logic [DEBUG_WORD_COUNT*32-1:0] packet(input logic [31:0] identity);
        logic [DEBUG_WORD_COUNT*32-1:0] value;
        value=0;
        for(int wordIndex=0;wordIndex<DEBUG_WORD_COUNT;wordIndex++)
            value[wordIndex*32+:32]=(identity*32'h9e3779b9)^32'(wordIndex*65537)^32'h81abce55;
        value[31:0]=identity;
        value[1*32+:32]={16'(DEBUG_SCHEMA_VERSION),16'(PERCEPTION_CONTRACT_VERSION)};
        // These metadata fields cross the wrap within this test. Every other
        // word depends on the identity too, exposing mixed old/new payloads.
        value[3*32+:32]={16'd0,16'(16'hfff0+identity)};
        value[4*32+:32]=32'hfffffff0+identity;
        return value;
    endfunction

    always @(posedge sourceClk)begin
        if(sourceReset)begin previousBusy=0;previousHeld=0;end
        else begin
            if(previousBusy)begin
                if(dut.heldData!==previousHeld)$fatal(1,"FAIL bundled data changed before acknowledgement");
                holdingChecks++;
            end
            previousBusy=dut.acknowledgeSync[1]!=dut.requestToggle;
            previousHeld=dut.heldData;
        end
    end
    always @(posedge destinationClk)begin
        #1;
        if(!destinationReset&&destinationValid)begin
            if(destinationData!==packet(destinationData[31:0]))$fatal(1,"FAIL torn schema6 display payload");
            if(destinationData[31:0]<=lastIdentity)$fatal(1,"FAIL duplicate/out-of-order mailbox update");
            lastIdentity=destinationData[31:0];received++;
        end
    end
    initial begin
        repeat(4)@(negedge sourceClk);sourceReset=0;
        @(negedge destinationClk);destinationReset=0;
        for(int identity=1;identity<=300;identity++)begin
            @(negedge sourceClk);sourceData=packet(32'(identity));updates++;
            if(identity%7==0)repeat(3)@(negedge sourceClk);
        end
        repeat(20)@(negedge destinationClk);
        if(lastIdentity!=300||received<20||received>=updates||holdingChecks<50)
            $fatal(1,"FAIL latest-value/coalescing coverage received=%0d held=%0d latest=%0d",received,holdingChecks,lastIdentity);
        // Reset both ownership endpoints, then accept a clean new transaction.
        sourceReset=1;destinationReset=1;sourceData=0;
        repeat(4)@(negedge sourceClk);
        @(negedge destinationClk);lastIdentity=0;destinationReset=0;
        @(negedge sourceClk);sourceReset=0;sourceData=packet(32'd901);
        repeat(20)@(negedge destinationClk);
        if(lastIdentity!=901)$fatal(1,"FAIL mailbox did not recover after common reset");
        $display("PASS memberBDisplayCdc_tb width=%0d updates=%0d received=%0d holdingChecks=%0d",DEBUG_WORD_COUNT*32,updates,received,holdingChecks);
        $finish;
    end
    initial begin #200000;$fatal(1,"FAIL display CDC timeout");end
endmodule
