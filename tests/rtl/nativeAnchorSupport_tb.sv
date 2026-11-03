`timescale 1ns/1ps
// Component-level reader9 proof. Digit IDs are intentionally absent from this
// module and these inputs. Full glyph/caller ordering is tested separately.
module nativeAnchorSupport_tb;
    logic clk=0;always #10 clk=~clk;
    logic reset=1,start=0,busy,done,readWhite,readWeakWhite,weakSupportMode=0;
    logic signed [10:0] pointX[0:3],pointY[0:3];
    logic [8:0] ownerXMin=0,ownerXMax=0,seedXMin=0,seedXMax=0,thinSeedXMin,thinSeedXMax;
    logic [7:0] ownerYMin=0,ownerYMax=0,seedYMin=0,seedYMax=0,thinSeedYMin,thinSeedYMax;
    logic [16:0] seedStrongCount=0,thinSeedStrongCount,readAddress,anchorCount;
    logic [8:0] anchorWidth;
    logic [7:0] anchorHeight;
    logic ambiguous,overflow,thinSeedHazard,supportAccepted;
    logic [3:0] allocationPeak;
    logic [15:0] componentCount;
    logic [1:0] thinSeedCount;
    logic strongBank[0:76799],weakBank[0:76799];
    logic [31:0] metadata[0:40*512-1],caseCount[0:0];
    string inputs,path;
    integer checks=0,cycles=0,maxCycles=0,supports=0,rejected=0,thinCases=0,overflows=0,ambiguities=0;
    nativeAnchorReader dut(.*);
    always_ff @(posedge clk)begin
        readWhite<=strongBank[readAddress];readWeakWhite<=weakBank[readAddress];
    end
    task automatic bindCase(input integer index);
        for(int k=0;k<4;k++)begin pointX[k]=11'(metadata[40*index+1+2*k]);pointY[k]=11'(metadata[40*index+2+2*k]);end
        weakSupportMode=1'(metadata[40*index]);
        ownerXMin=9'(metadata[40*index+9]);ownerYMin=8'(metadata[40*index+10]);
        ownerXMax=9'(metadata[40*index+11]);ownerYMax=8'(metadata[40*index+12]);
        seedXMin=9'(metadata[40*index+13]);seedYMin=8'(metadata[40*index+14]);
        seedXMax=9'(metadata[40*index+15]);seedYMax=8'(metadata[40*index+16]);seedStrongCount=17'(metadata[40*index+17]);
    endtask
    task automatic checkCleared;
        if(anchorCount!==0||anchorWidth!==0||anchorHeight!==0||thinSeedCount!==0||thinSeedStrongCount!==0||
            thinSeedXMin!==0||thinSeedXMax!==0||thinSeedYMin!==0||thinSeedYMax!==0||supportAccepted!==0||
            thinSeedHazard!==0||ambiguous!==0||overflow!==0)$fatal(1,"Reset/start failed to clear previous result");
        checks++;
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",inputs))$fatal(1,"Missing support vectors");
        $readmemh({inputs,"/support_count.hex"},caseCount);
        if($isunknown(caseCount[0])||caseCount[0]<1||caseCount[0]>512)$fatal(1,"Invalid vector count");
        $readmemh({inputs,"/support_meta.hex"},metadata);
        repeat(3)@(negedge clk);reset=0;checkCleared();
        for(int index=0;index<caseCount[0];index++)begin
            path=$sformatf("%s/support_%0d_strong.hex",inputs,index);$readmemh(path,strongBank);
            path=$sformatf("%s/support_%0d_weak.hex",inputs,index);$readmemh(path,weakBank);
            @(negedge clk);bindCase(index);start=1;
            @(negedge clk);start=0;checkCleared();
            // Destroy all captured controls. Busy start pulses must not accept
            // new ports or change the selected pixel plane mid-scan.
            weakSupportMode=~weakSupportMode;
            seedXMin=319;seedXMax=0;seedYMin=239;seedYMax=0;seedStrongCount=17'h1ffff;
            ownerXMin=319;ownerXMax=0;ownerYMin=239;ownerYMax=0;
            for(int k=0;k<4;k++)begin pointX[k]=-11'sd1;pointY[k]=-11'sd1;end
            cycles=0;
            while(!done&&cycles<400000)begin @(negedge clk);cycles++;start=cycles==5;end
            start=0;
            if(!done)$fatal(1,"Support timeout case%0d",index);
            if(cycles>maxCycles)maxCycles=cycles;
            if(anchorCount!==17'(metadata[40*index+18])||anchorWidth!==9'(metadata[40*index+19])||anchorHeight!==8'(metadata[40*index+20])||
                ambiguous!==1'(metadata[40*index+21])||overflow!==1'(metadata[40*index+22])||thinSeedCount!==2'(metadata[40*index+23])||
                thinSeedXMin!==9'(metadata[40*index+24])||thinSeedYMin!==8'(metadata[40*index+25])||
                thinSeedXMax!==9'(metadata[40*index+26])||thinSeedYMax!==8'(metadata[40*index+27])||
                thinSeedStrongCount!==17'(metadata[40*index+28])||thinSeedHazard!==1'(metadata[40*index+29])||supportAccepted!==1'(metadata[40*index+30]))
                $fatal(1,"Support mismatch case%0d got anchor%0d %0dx%0d amb%0d over%0d thin%0d box%0d,%0d,%0d,%0d count%0d hazard%0d accepted%0d expected anchor%0d %0dx%0d amb%0d over%0d thin%0d box%0d,%0d,%0d,%0d count%0d hazard%0d accepted%0d",
                    index,anchorCount,anchorWidth,anchorHeight,ambiguous,overflow,thinSeedCount,thinSeedXMin,thinSeedYMin,thinSeedXMax,thinSeedYMax,thinSeedStrongCount,thinSeedHazard,supportAccepted,
                    metadata[40*index+18],metadata[40*index+19],metadata[40*index+20],metadata[40*index+21],metadata[40*index+22],metadata[40*index+23],metadata[40*index+24],metadata[40*index+25],metadata[40*index+26],metadata[40*index+27],metadata[40*index+28],metadata[40*index+29],metadata[40*index+30]);
            if(dut.roiXMin!==9'(metadata[40*index+31])||dut.roiYMin!==8'(metadata[40*index+32])||
                dut.roiXMax!==9'(metadata[40*index+33])||dut.roiYMax!==8'(metadata[40*index+34]))$fatal(1,"Support ROI mismatch case%0d",index);
            checks+=14;
            if(supportAccepted)supports++;
            else if(metadata[40*index][0])rejected++;
            if(thinSeedCount!=0)thinCases++;
            if(overflow)overflows++;
            if(ambiguous)ambiguities++;
            @(negedge clk);if(done||busy)$fatal(1,"Done must pulse once and return idle");checks++;
        end
        // Reset both preparation and pixel/retirement phases in each mode.
        for(int mode=0;mode<2;mode++)for(int delayCycles=1;delayCycles<=80;delayCycles+=7)begin
            @(negedge clk);bindCase(mode);weakSupportMode=1'(mode);start=1;
            @(negedge clk);start=0;
            repeat(delayCycles)@(negedge clk);reset=1;
            @(negedge clk);if(busy||done)$fatal(1,"Reset failed to abandon support scan");checkCleared();reset=0;
        end
        if(supports<10||rejected<10||thinCases<10||overflows<2||ambiguities<1)$fatal(1,"Support coverage missing");
        $display("PASS nativeAnchorSupport_tb cases=%0d checks=%0d supports=%0d rejected=%0d thinCases=%0d overflows=%0d ambiguous=%0d maxCycles=%0d",caseCount[0],checks,supports,rejected,thinCases,overflows,ambiguities,maxCycles);
        $finish;
    end
    initial begin #500000000;$fatal(1,"Support global watchdog");end
endmodule
