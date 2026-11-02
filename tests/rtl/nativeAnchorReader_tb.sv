`timescale 1ns/1ps
module nativeAnchorReader_tb;
    logic clk=0;always #10 clk=~clk;
    logic reset=1,start=0,busy,done,readWhite;
    logic signed [10:0] pointX[0:3],pointY[0:3];
    logic [16:0] readAddress,anchorCount;
    logic [8:0] anchorWidth;
    logic [7:0] anchorHeight;
    logic ambiguous,overflow;
    logic [3:0] allocationPeak;
    logic [15:0] componentCount;
    logic whiteBank[0:76799];
    logic [31:0] metadata[0:8191],count[0:0];
    string inputs,fileName;
    integer previousSource=-1,currentCase=0,cycles,maxCycles=0,overflowCases=0,ambiguousCases=0,validAnchors=0;
    logic dividerStart=0,dividerDone;
    logic [16:0] dividerNumerator[0:3],dividerQuotient[0:3];
    integer dividerChecks=0,boundaryChecks=0,inputMutationChecks=0;
    nativeAnchorReader dut(.*);
    nativeAnchorDivide40 dividerDut(.clk(clk),.reset(reset),.start(dividerStart),
        .numerator(dividerNumerator),.quotient(dividerQuotient),.done(dividerDone));
    always_ff @(posedge clk)readWhite<=whiteBank[readAddress];
    always @(posedge clk)begin
        #2;
        if(!reset)begin
            for(int slot=0;slot<8;slot++)if(!dut.freeSlots[slot])begin
                if(dut.parents[slot]<1||dut.parents[slot]>8||dut.parents[dut.parents[slot]-1]!=dut.parents[slot])
                    $fatal(1,"Native anchor parent not canonical case%0d slot%0d",currentCase,slot);
            end
        end
    end
    task automatic checkDividerAndClipping;
        integer waitCycles,signedValue,limitValue,lowerExpected,upperExpected,lowerQuotient,upperQuotient;
        begin
            // Independent builtin integer arithmetic is the oracle. Four lanes
            // cover EVERY unsigned-17 dividend and EVERY signed-17 numerator,
            // including all floor/ceil and image-clipping boundaries.
            for(int base=0;base<131072;base+=4)begin
                @(negedge clk);dividerStart=1;
                for(int lane=0;lane<4;lane++)dividerNumerator[lane]=17'(base+lane);
                @(negedge clk);dividerStart=0;
                for(int lane=0;lane<4;lane++)dividerNumerator[lane]=17'h1ffff^17'(base+lane);
                waitCycles=0;
                while(!dividerDone&&waitCycles<19)begin @(negedge clk);waitCycles++;end
                if(!dividerDone||waitCycles!=17)$fatal(1,"Divider latency mismatch base%0d cycles%0d",base,waitCycles);
                for(int lane=0;lane<4;lane++)begin
                    if(dividerQuotient[lane]!==17'((base+lane)/40))
                        $fatal(1,"Exact divide mismatch numerator%0d quotient%0d",base+lane,dividerQuotient[lane]);
                    dividerChecks++;
                    signedValue=base+lane;if(signedValue>=65536)signedValue-=131072;
                    lowerQuotient=signedValue>0?signedValue/40:0;
                    upperQuotient=signedValue<0?0:(signedValue+39)/40;
                    for(int axis=0;axis<2;axis++)begin
                        limitValue=axis==0?319:239;
                        lowerExpected=lowerQuotient==0?0:lowerQuotient-1;
                        if(lowerExpected>limitValue)lowerExpected=limitValue;
                        upperExpected=signedValue<0?0:upperQuotient+1;
                        if(upperExpected>limitValue)upperExpected=limitValue;
                        if(dut.lowerBoundaryFromQuotient(17'(lowerQuotient),limitValue)!==9'(lowerExpected)||
                            dut.upperBoundaryFromQuotient(17'(upperQuotient),signedValue<0,limitValue)!==9'(upperExpected))
                            $fatal(1,"ROI clip mismatch numerator%0d limit%0d",signedValue,limitValue);
                        boundaryChecks+=2;
                    end
                end
                @(negedge clk);if(dividerDone)$fatal(1,"Divider done must pulse once");
            end
            // Reset during restoring division cancels the complete transaction.
            @(negedge clk);dividerStart=1;@(negedge clk);dividerStart=0;
            repeat(5)@(negedge clk);reset=1;
            @(negedge clk);if(dividerDone||dividerDut.working)$fatal(1,"Divider reset failed");
            reset=0;
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",inputs))
            $fatal(1,"Missing vector paths");
        $readmemh({inputs,"/anchor_count.hex"},count);$readmemh({inputs,"/anchor_meta.hex"},metadata);
        for(int i=0;i<4;i++)begin pointX[i]=0;pointY[i]=0;dividerNumerator[i]=0;end
        repeat(3)@(negedge clk);reset=0;
        checkDividerAndClipping();
        for(int test=0;test<count[0];test++)begin
            currentCase=test;
            if(metadata[test*20]!=previousSource)begin
                fileName=$sformatf("%s/projective_%0d_strong_white.hex",inputs,metadata[test*20]);
                $readmemh(fileName,whiteBank);previousSource=metadata[test*20];
            end
            for(int i=0;i<4;i++)begin pointX[i]=11'(metadata[test*20+1+2*i]);pointY[i]=11'(metadata[test*20+2+2*i]);end
            @(negedge clk);start=1;@(negedge clk);start=0;
            // Inputs are deliberately destroyed immediately after the accepted
            // start, before any vertex calculation. Busy-period data and start
            // pulses must not replace the captured quad.
            for(int i=0;i<4;i++)begin pointX[i]=11'sd639-11'(i);pointY[i]=-11'sd1+11'(i);end
            inputMutationChecks++;
            cycles=0;
            while(!done&&cycles<400000)begin
                @(negedge clk);cycles++;
                start=cycles==4; // ignored while the captured quad is busy
            end
            start=0;
            if(!done)$fatal(1,"Native anchor timeout case%0d",test);
            if(cycles>maxCycles)maxCycles=cycles;
            if(dut.roiXMin!==9'(metadata[test*20+9])||dut.roiYMin!==8'(metadata[test*20+10])||
               dut.roiXMax!==9'(metadata[test*20+11])||dut.roiYMax!==8'(metadata[test*20+12]))
                $fatal(1,"Native ROI mismatch case%0d got%0d,%0d,%0d,%0d expected%0d,%0d,%0d,%0d",test,
                    dut.roiXMin,dut.roiYMin,dut.roiXMax,dut.roiYMax,metadata[test*20+9],metadata[test*20+10],metadata[test*20+11],metadata[test*20+12]);
            if(anchorCount!==17'(metadata[test*20+13])||anchorWidth!==9'(metadata[test*20+14])||anchorHeight!==8'(metadata[test*20+15])||
                ambiguous!==1'(metadata[test*20+16])||overflow!==1'(metadata[test*20+17]))
                $fatal(1,"Native anchor result mismatch case%0d got count%0d width%0d height%0d ambiguous%0d overflow%0d; expected count%0d width%0d height%0d ambiguous%0d overflow%0d",test,
                    anchorCount,anchorWidth,anchorHeight,ambiguous,overflow,metadata[test*20+13],metadata[test*20+14],metadata[test*20+15],metadata[test*20+16],metadata[test*20+17]);
            if(allocationPeak!==4'(metadata[test*20+18]))$fatal(1,"Native active peak mismatch case%0d got%0d expected%0d",test,allocationPeak,metadata[test*20+18]);
            if(metadata[test*20+19]!=32'hffffffff&&componentCount!==16'(metadata[test*20+19]))
                $fatal(1,"Native retired count mismatch case%0d got%0d expected%0d",test,componentCount,metadata[test*20+19]);
            if(overflow)overflowCases++;if(ambiguous)ambiguousCases++;if(anchorCount!=0)validAnchors++;
            @(negedge clk);if(done)$fatal(1,"Native done must pulse once");
        end
        // Reset interrupts every preparation stage as well as an active scan,
        // without needing to clear the synchronous line RAM.
        for(int delayCycles=1;delayCycles<=28;delayCycles++)begin
            for(int i=0;i<4;i++)begin pointX[i]=11'(metadata[1+2*i]);pointY[i]=11'(metadata[2+2*i]);end
            @(negedge clk);start=1;@(negedge clk);start=0;
            repeat(delayCycles)@(negedge clk);reset=1;
            @(negedge clk);if(busy||done||anchorCount!=0||overflow)$fatal(1,"Native reset did not abandon stage delay%0d",delayCycles);
            reset=0;
        end
        if(overflowCases<1||ambiguousCases<1)$fatal(1,"Native negative branch coverage missing");
        $display("PASS nativeAnchorReader_tb rois=%0d valid=%0d ambiguous=%0d overflow=%0d maxCycles=%0d dividerChecks=%0d boundaryChecks=%0d inputMutationChecks=%0d",
            count[0],validAnchors,ambiguousCases,overflowCases,maxCycles,dividerChecks,boundaryChecks,inputMutationChecks);
        $finish;
    end
    initial begin #500000000;$fatal(1,"Native anchor global watchdog");end
endmodule
