`timescale 1ns/1ps
// Full production contour/label/diagnostic path: the previous SOP must reach
// the last metadata consumer before another packet can replace frameDebug.
module memberBVgaPipeline_tb;
    import perception_pkg::*;
    logic clk=0,reset=1,showCandidates=0,showCentre=0;
    logic [perception_pkg::DEBUG_WORD_COUNT*32-1:0] debugWords=0;
    logic [29:0] inData=0,outData;
    logic inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=0;
    int cycles=0,accepted=0,presented=0,consumed=0;
    logic [15:0] expectedConfig[0:99];
    logic stalled=0;
    logic [31:0] heldPayload;
    perceptionStatus_t status;
    always #5 clk=~clk;
    memberBVgaOverlay dut(.*);
    always @(negedge clk)begin cycles++;outReady=!reset&&cycles%11>=4;end
    always @(posedge clk)if(!reset)begin
        if(stalled&&(!outValid||heldPayload!=={outSop,outEop,outData}))$fatal(1,"FAIL linked VGA stall");
        stalled=outValid&&!outReady;heldPayload={outSop,outEop,outData};
        if(inValid&&inReady)begin
            expectedConfig[accepted]=debugWords[10*32+16+:16];
            accepted++;
        end
        if(outValid&&outReady)begin
            if(!outSop||!outEop)$fatal(1,"FAIL truncated packet boundary");
            consumed++;
        end
        if(dut.labelValid&&dut.labelReady&&dut.labelSop)begin
            // Nonblocking display registers become visible after this edge.
            #1;
            if(dut.withDiagnostics.diagnostics.displayStatus.activeCfgVersion!==16'(presented+1))
                $fatal(1,"FAIL linked VGA metadata overwrite packet=%0d actual=%0d",presented,
                    dut.withDiagnostics.diagnostics.displayStatus.activeCfgVersion);
            presented++;
        end
    end
    initial begin
        repeat(4)@(negedge clk);reset=0;
        for(int frame=1;frame<=64;frame++)begin
            @(negedge clk);#1;
            status='0;status.activeCfgVersion=16'(frame);
            debugWords=0;debugWords[10*32+:76]=status;
            inValid=1;inSop=1;inEop=1;inData=30'(frame);
            @(posedge clk);while(!inReady)@(posedge clk);
        end
        @(negedge clk);#1;inValid=0;inSop=0;inEop=0;
        repeat(30)@(negedge clk);
        if(accepted!=64||presented!=64||consumed!=64||outValid)$fatal(1,"FAIL linked VGA accounting");
        $display("PASS memberBVgaPipeline_tb 64 back-to-back packets, all three production stages, metadata and output stalls");
        $finish;
    end
    initial begin #100000;$fatal(1,"FAIL linked VGA timeout");end
endmodule
