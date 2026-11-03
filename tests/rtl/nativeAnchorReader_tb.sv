`timescale 1ns/1ps
module nativeAnchorReader_tb;
    logic clk=0;always #10 clk=~clk;
    logic reset=1,start=0,busy,done,readWhite;
    logic weakSupportMode=0,readWeakWhite;
    logic [8:0] seedXMin=0,seedXMax=0,thinSeedXMin,thinSeedXMax;
    logic [7:0] seedYMin=0,seedYMax=0,thinSeedYMin,thinSeedYMax;
    logic [16:0] seedStrongCount=0,thinSeedStrongCount;
    logic [1:0] thinSeedCount;
    logic thinSeedHazard,supportAccepted;
    logic signed [10:0] pointX[0:3],pointY[0:3];
    logic [8:0] ownerXMin=0,ownerXMax=319;
    logic [7:0] ownerYMin=0,ownerYMax=239;
    logic [16:0] readAddress,anchorCount;
    logic [8:0] anchorWidth;
    logic [7:0] anchorHeight;
    logic ambiguous,overflow;
    logic [3:0] allocationPeak;
    logic [15:0] componentCount;
    logic whiteBank[0:76799];
    // Reader5 evaluates four native anchor hypotheses before glyph decoding.
    // Include rejected hypotheses, so ambiguity/overflow cases are not lost.
    // This is testbench storage only; the synthesised reader is unchanged.
    localparam int MAX_NATIVE_CASES=4096, MAX_RECORD_WORDS=24;
    logic [31:0] metadata[0:MAX_NATIVE_CASES*MAX_RECORD_WORDS-1],count[0:0],recordSizeWord[0:0];
    string inputs,fileName;
    integer previousSource=-1,currentCase=0,cycles,maxCycles=0,overflowCases=0,ambiguousCases=0,validAnchors=0;
    integer recordWords,ownershipChecks=0;
    logic dividerStart=0,dividerDone;
    logic [16:0] dividerNumerator[0:3],dividerQuotient[0:3];
    integer dividerChecks=0,boundaryChecks=0,inputMutationChecks=0;
    nativeAnchorReader dut(.*);
    nativeAnchorDivide40 dividerDut(.clk(clk),.reset(reset),.start(dividerStart),
        .numerator(dividerNumerator),.quotient(dividerQuotient),.done(dividerDone));
    always_ff @(posedge clk)begin readWhite<=whiteBank[readAddress];readWeakWhite<=whiteBank[readAddress];end
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
    task automatic setQuad(input integer x0,y0,x1,y1);
        pointX[0]=11'(2*x0);pointY[0]=11'(2*y0);
        pointX[1]=11'(2*x1);pointY[1]=11'(2*y0);
        pointX[2]=11'(2*x1);pointY[2]=11'(2*y1);
        pointX[3]=11'(2*x0);pointY[3]=11'(2*y1);
    endtask
    task automatic clearWhite;
        for(integer pixel=0;pixel<76800;pixel++)whiteBank[pixel]=0;
    endtask
    task automatic whiteRectangle(input integer x0,y0,x1,y1);
        for(integer y=y0;y<=y1;y++)for(integer x=x0;x<=x1;x++)whiteBank[y*320+x]=1;
    endtask
    task automatic ownershipCase(input integer x0,y0,x1,y1,expectedCount,expectedWidth,expectedHeight,
            input logic expectedAmbiguous);
        integer waited;
        @(negedge clk);ownerXMin=9'(x0);ownerYMin=8'(y0);ownerXMax=9'(x1);ownerYMax=8'(y1);start=1;
        @(negedge clk);start=0;
        // Every ownership limit must be captured on start, not reread while
        // calculating the ROI or retiring a component many cycles later.
        ownerXMin=319;ownerXMax=0;ownerYMin=239;ownerYMax=0;
        waited=0;
        while(!done&&waited<400000)begin @(negedge clk);waited++;end
        if(!done||anchorCount!=expectedCount||anchorWidth!=expectedWidth||anchorHeight!=expectedHeight||
           ambiguous!=expectedAmbiguous||overflow)
            $fatal(1,"Ownership case%0d bbox%0d,%0d,%0d,%0d got count%0d %0dx%0d ambiguous%0d overflow%0d",
                ownershipChecks,x0,y0,x1,y1,anchorCount,anchorWidth,anchorHeight,ambiguous,overflow);
        ownershipChecks++;
        @(negedge clk);if(done)$fatal(1,"Ownership case done must pulse once");
    endtask
    task automatic checkOwnership;
        // Inclusive boundaries retain an anchor whose full component extends
        // beyond a quantised colour edge. These are direct component-level
        // stimuli, independent of candidate/digit/orientation reference models.
        clearWhite();setQuad(100,80,200,180);whiteRectangle(106,86,108,88);
        ownershipCase(100,80,200,180,9,3,3,0);
        ownershipCase(107,87,107,87,9,3,3,0); // exact centre on all four limits
        ownershipCase(108,80,200,180,0,0,0,0); // overlap alone is insufficient
        ownershipCase(100,80,106,180,0,0,0,0);
        ownershipCase(100,88,200,180,0,0,0,0);
        ownershipCase(100,80,200,86,0,0,0,0);
        ownershipCase(200,80,100,180,0,0,0,0); // inverted owner cannot accept
        // Half-integer centres must never be rounded before comparison.
        clearWhite();whiteRectangle(106,86,107,87);
        ownershipCase(100,80,200,180,4,2,2,0);
        ownershipCase(100,80,106,180,0,0,0,0); // X centre106.5 exceeds106
        ownershipCase(107,80,200,180,0,0,0,0);
        ownershipCase(100,80,200,86,0,0,0,0); // Y centre86.5 exceeds86
        ownershipCase(100,87,200,180,0,0,0,0);
        // Broad ROI sees both own and neighbouring closed components. Retire
        // both normally, but only an owned component may affect uniqueness.
        clearWhite();whiteRectangle(106,86,108,88);whiteRectangle(120,86,122,88);
        ownershipCase(100,80,115,180,9,3,3,0);
        ownershipCase(100,80,200,180,0,0,0,1); // two OWNED anchors still reject
        ownershipCase(150,80,200,180,0,0,0,0);
        // Exercise sums beyond an unsigned9-bit X range and8-bit Y range.
        clearWhite();setQuad(270,200,319,239);whiteRectangle(278,204,280,206);
        ownershipCase(270,200,319,239,9,3,3,0);
        ownershipCase(279,205,279,205,9,3,3,0);
        ownershipCase(280,200,319,239,0,0,0,0);
        clearWhite();previousSource=-1;
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",inputs))
            $fatal(1,"Missing vector paths");
        $readmemh({inputs,"/anchor_count.hex"},count);
        if($isunknown(count[0])||count[0]<1||count[0]>MAX_NATIVE_CASES)
            $fatal(1,"Invalid native anchor vector count (bounded testbench capacity=%0d)",MAX_NATIVE_CASES);
        $readmemh({inputs,"/anchor_meta.hex"},metadata);
        $readmemh({inputs,"/anchor_record_words.hex"},recordSizeWord);
        if(recordSizeWord[0]!==20&&recordSizeWord[0]!==24)$fatal(1,"Unsupported native anchor record width");
        recordWords=int'(recordSizeWord[0]);
        for(int i=0;i<4;i++)begin pointX[i]=0;pointY[i]=0;dividerNumerator[i]=0;end
        repeat(3)@(negedge clk);reset=0;
        checkDividerAndClipping();
        checkOwnership();
        for(int test=0;test<count[0];test++)begin
            currentCase=test;
            if(metadata[test*recordWords]!=previousSource)begin
                fileName=$sformatf("%s/projective_%0d_strong_white.hex",inputs,metadata[test*recordWords]);
                $readmemh(fileName,whiteBank);previousSource=metadata[test*recordWords];
            end
            for(int i=0;i<4;i++)begin pointX[i]=11'(metadata[test*recordWords+1+2*i]);pointY[i]=11'(metadata[test*recordWords+2+2*i]);end
            ownerXMin=recordWords==24?9'(metadata[test*24+20]):9'd0;
            ownerYMin=recordWords==24?8'(metadata[test*24+21]):8'd0;
            ownerXMax=recordWords==24?9'(metadata[test*24+22]):9'd319;
            ownerYMax=recordWords==24?8'(metadata[test*24+23]):8'd239;
            @(negedge clk);start=1;@(negedge clk);start=0;
            // Inputs are deliberately destroyed immediately after the accepted
            // start, before any vertex calculation. Busy-period data and start
            // pulses must not replace the captured quad.
            for(int i=0;i<4;i++)begin pointX[i]=11'sd639-11'(i);pointY[i]=-11'sd1+11'(i);end
            ownerXMin=319;ownerXMax=0;ownerYMin=239;ownerYMax=0;
            inputMutationChecks++;
            cycles=0;
            while(!done&&cycles<400000)begin
                @(negedge clk);cycles++;
                start=cycles==4; // ignored while the captured quad is busy
            end
            start=0;
            if(!done)$fatal(1,"Native anchor timeout case%0d",test);
            if(cycles>maxCycles)maxCycles=cycles;
            if(dut.roiXMin!==9'(metadata[test*recordWords+9])||dut.roiYMin!==8'(metadata[test*recordWords+10])||
               dut.roiXMax!==9'(metadata[test*recordWords+11])||dut.roiYMax!==8'(metadata[test*recordWords+12]))
                $fatal(1,"Native ROI mismatch case%0d got%0d,%0d,%0d,%0d expected%0d,%0d,%0d,%0d",test,
                    dut.roiXMin,dut.roiYMin,dut.roiXMax,dut.roiYMax,metadata[test*recordWords+9],metadata[test*recordWords+10],metadata[test*recordWords+11],metadata[test*recordWords+12]);
            if(anchorCount!==17'(metadata[test*recordWords+13])||anchorWidth!==9'(metadata[test*recordWords+14])||anchorHeight!==8'(metadata[test*recordWords+15])||
                ambiguous!==1'(metadata[test*recordWords+16])||overflow!==1'(metadata[test*recordWords+17]))
                $fatal(1,"Native anchor result mismatch case%0d got count%0d width%0d height%0d ambiguous%0d overflow%0d; expected count%0d width%0d height%0d ambiguous%0d overflow%0d",test,
                    anchorCount,anchorWidth,anchorHeight,ambiguous,overflow,metadata[test*recordWords+13],metadata[test*recordWords+14],metadata[test*recordWords+15],metadata[test*recordWords+16],metadata[test*recordWords+17]);
            if(allocationPeak!==4'(metadata[test*recordWords+18]))$fatal(1,"Native active peak mismatch case%0d got%0d expected%0d",test,allocationPeak,metadata[test*recordWords+18]);
            if(metadata[test*recordWords+19]!=32'hffffffff&&componentCount!==16'(metadata[test*recordWords+19]))
                $fatal(1,"Native retired count mismatch case%0d got%0d expected%0d",test,componentCount,metadata[test*recordWords+19]);
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
        $display("PASS nativeAnchorReader_tb rois=%0d valid=%0d ambiguous=%0d overflow=%0d maxCycles=%0d dividerChecks=%0d boundaryChecks=%0d inputMutationChecks=%0d ownershipChecks=%0d recordWords=%0d",
            count[0],validAnchors,ambiguousCases,overflowCases,maxCycles,dividerChecks,boundaryChecks,inputMutationChecks,ownershipChecks,recordWords);
        $finish;
    end
    initial begin #500000000;$fatal(1,"Native anchor global watchdog");end
endmodule
