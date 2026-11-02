`timescale 1ns/1ps
module memberBVgaContour_tb;
    logic clk=0;always #20 clk=~clk;
    logic reset=1;
    logic [7:0] redMinimum=48,blueMinimum=32;
    logic [29:0] inData=0,outData;
    logic inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=0;
    logic [31:0] inputWords[0:940000],expectedWords[0:940000],profiles[0:940000],lengthWords[0:0];
    logic [31:0] randomState=32'h15407ca3,priorPayload;
    logic priorStall=0,scoreboardActive=1,forceStall=0;
    integer cycleCount=0,writeCount=0,readCount=0,stallCycles=0,inputBubbles=0;
    string vectors;
    memberBVgaContour dut(.*);
    always @(negedge clk)begin
        randomState=randomState^(randomState<<13);
        randomState=randomState^(randomState>>17);
        randomState=randomState^(randomState<<5);
        cycleCount=cycleCount+1;
        outReady=!reset && !forceStall && (randomState[0]||randomState[4]) && cycleCount%113>=7;
    end
    always @(posedge clk)begin
        if(reset)begin priorStall=0;writeCount=0;readCount=0;end
        else if(scoreboardActive)begin
            if(priorStall && (!outValid || {outSop,outEop,outData}!==priorPayload))$fatal(1,"Contour payload changed while stalled");
            priorStall=outValid&&!outReady;priorPayload={outSop,outEop,outData};
            if(priorStall)stallCycles=stallCycles+1;
            if(inValid&&inReady)writeCount=writeCount+1;
            if(outValid&&outReady)begin
                if(readCount>=writeCount)$fatal(1,"Contour output without accepted input");
                if({outSop,outEop,outData}!==expectedWords[readCount])
                    $fatal(1,"Contour oracle mismatch pixel%0d expected%08x actual%08x",readCount,expectedWords[readCount],{outSop,outEop,outData});
                readCount=readCount+1;
            end
        end
    end
    task automatic send(input integer index);
        begin
            @(negedge clk);#1;
            if(index%11==0)begin
                inValid=0;inputBubbles=inputBubbles+1;
                @(negedge clk);#1;
            end
            inValid=1;{inSop,inEop,inData}=inputWords[index];
            redMinimum=profiles[index][15:8];blueMinimum=profiles[index][7:0];
            @(posedge clk);while(!inReady)@(posedge clk);
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"Missing vector directory");
        $readmemh({vectors,"/contour_vector_count.hex"},lengthWords);
        $readmemh({vectors,"/contour_input.hex"},inputWords,0,lengthWords[0]-1);
        $readmemh({vectors,"/contour_expected.hex"},expectedWords,0,lengthWords[0]-1);
        $readmemh({vectors,"/contour_profile.hex"},profiles,0,lengthWords[0]-1);
        repeat(4)@(negedge clk);#1;reset=0;
        for(int index=0;index<lengthWords[0];index++)send(index);
        @(negedge clk);#1;inValid=0;
        wait(readCount==lengthWords[0]);repeat(4)@(negedge clk);
        if(outValid || stallCycles<10000)$fatal(1,"Coverage/drain failure");
        // Reset with a live pixel in flight, then start a fresh first row. Old
        // row RAM content must not leak into the new frame; no RAM reset loop.
        scoreboardActive=0;forceStall=1;send(0);send(1);
        @(negedge clk);#1;
        if(!dut.stageValid || !outValid)$fatal(1,"Reset test did not fill both elastic slots");
        reset=1;inValid=0;
        repeat(3)@(negedge clk);#1;
        if(outValid)$fatal(1,"Reset retained pending contour output");
        scoreboardActive=1;forceStall=0;reset=0;
        for(int index=0;index<640;index++)send(index);
        @(negedge clk);#1;inValid=0;
        wait(readCount==640);repeat(3)@(negedge clk);
        if(outValid)$fatal(1,"Post-reset stream did not drain");
        $display("PASS memberBVgaContour_tb pixels=%0d plusresetrow640 stalls=%0d bubbles=%0d",lengthWords[0],stallCycles,inputBubbles);
        $finish;
    end
    initial begin #100000000;$fatal(1,"Global timeout");end
endmodule
