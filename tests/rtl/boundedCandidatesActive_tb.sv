`timescale 1ns/1ps
// Same pixels into active8/output8 and active12/output8. The camera mask is
// derived independently from retained frame30507; expected geometry is BFS.
module boundedCandidatesActive_tb;
    import candidate_pkg::*;
    candidate_array_t red_candidates,blue_candidates,oldRed,oldBlue;

    // Legacy geometry oracles consume per-colour views. This adapter is test
    // code only; the DUT has one physical completed pool and a colour bitmap.
    candidate_array_t sharedCandidates,oldSharedCandidates;
    logic [15:0] sharedColours,oldSharedColours;
    logic [4:0] sharedCount;
    function automatic candidate_array_t colourView(input candidate_array_t values,input logic [15:0] colours,input logic blue);
        candidate_array_t result;
        integer count;
        result='0;count=0;
        for(int slot=0;slot<16;slot++)if(values[slot].valid&&colours[slot]==blue)begin
            result[count]=values[slot];count++;
        end
        return result;
    endfunction
    always_comb begin
        red_candidates=colourView(sharedCandidates,sharedColours,0);
        blue_candidates=colourView(sharedCandidates,sharedColours,1);
        oldRed=colourView(oldSharedCandidates,oldSharedColours,0);
        oldBlue=colourView(oldSharedCandidates,oldSharedColours,1);
    end

    logic clk=0,reset=1,in_valid=0,in_sop=0,in_eop=0;
    always #5 clk=~clk;
    logic [1:0] in_mask=0;
    logic [8:0] in_x=0;
    logic [7:0] in_y=0;
    logic [4:0] red_count,blue_count;
    logic [3:0] allocationPeakRed,allocationPeakBlue;
    logic out_valid,frame_valid,overflow,frame_error,overrun;
    logic oldValid,oldGood,oldOverflow,oldSeen,oldBad;
    logic [1:0] mask[0:76799];
    logic [31:0] expected[0:127];
    string vectorDir;
    integer checks=0;
    boundedCandidates #(.SHARED_POOL(0),.CAP(8),.ACTIVE_CAP(12),.PRUNE_UNUSABLE(1)) dut(
        .clk(clk),.reset(reset),.in_valid(in_valid),.in_sop(in_sop),.in_eop(in_eop),
        .in_mask(in_mask),.in_x(in_x),.in_y(in_y),.sharedCandidates(sharedCandidates),.sharedColours(sharedColours),.sharedCount(sharedCount),
        .red_count(red_count),.blue_count(blue_count),.out_valid(out_valid),.frame_valid(frame_valid),
        .overflow(overflow),.frame_error(frame_error),.overrun(overrun),.red_overflow(),.blue_overflow(),
        .frame_id(),.busy(),.allocationPeakRed(allocationPeakRed),.allocationPeakBlue(allocationPeakBlue));
    boundedCandidates #(.SHARED_POOL(0),.CAP(8),.PRUNE_UNUSABLE(1)) oldDut(
        .clk(clk),.reset(reset),.in_valid(in_valid),.in_sop(in_sop),.in_eop(in_eop),
        .in_mask(in_mask),.in_x(in_x),.in_y(in_y),.sharedCandidates(oldSharedCandidates),.sharedColours(oldSharedColours),.sharedCount(),
        .red_count(),.blue_count(),.out_valid(oldValid),.frame_valid(oldGood),
        .overflow(oldOverflow),.frame_error(),.overrun(),.red_overflow(),.blue_overflow(),
        .frame_id(),.busy(),.allocationPeakRed(),.allocationPeakBlue());
    always @(negedge clk)if(!reset&&oldValid)begin oldSeen=1;oldBad=oldOverflow;end
    // Every allocated handle must remain a one-hop canonical root, including
    // when nine aliases merge in a row and are reclaimed at its boundary.
    always @(negedge clk)if(!reset)for(int c=0;c<2;c++)for(int slot=0;slot<12;slot++)begin
        if(!dut.free_slots[c][slot])begin
            if(dut.parent[c][slot]<1||dut.parent[c][slot]>12||
               dut.parent[c][dut.parent[c][slot]-1]!=dut.parent[c][slot])
                $fatal(1,"FAIL active12 parent invariant");
        end
    end
    function automatic logic [1:0] pixelAt(input int scenario,x,y);
        int seeds;
        logic [1:0] value;
        value=0;seeds=scenario==0?9:13;
        if(scenario<2)begin
            if(y>=10&&y<=34&&x>=10&&x<=10+4*(seeds-1)&&
               ((x-10)%4==0||y==34))value=1;
        end else if(scenario==2)begin
            for(int i=0;i<9;i++)if(x>=10+40*(i%3)&&x<34+40*(i%3)&&
                y>=10+40*(i/3)&&y<34+40*(i/3))value=1;
        end else if(scenario==3)value=mask[y*320+x];
        return value;
    endfunction
    task automatic idle;
        @(negedge clk);in_valid=0;in_sop=0;in_eop=0;
        @(posedge clk);#1;
    endtask
    task automatic sendFrame(input int scenario,gap=332);
        bit publicationSeen;
        oldSeen=0;oldBad=0;
        publicationSeen=0;
        for(int y=0;y<240;y++)begin
            if(y!=0)repeat(gap)idle();
            for(int x=0;x<320;x++)begin
                @(negedge clk);in_valid=1;in_x=9'(x);in_y=8'(y);
                in_sop=x==0&&y==0;in_eop=x==319&&y==239;in_mask=pixelAt(scenario,x,y);
                @(posedge clk);#1;
            end
        end
        repeat(332)begin
            idle();
            if(out_valid)begin
                publicationSeen=1;
                if(gap==332)$fatal(1,"FAIL early active12 publication");
            end
        end
        idle();publicationSeen=publicationSeen||out_valid;
        if(!publicationSeen||!oldSeen||(gap==332&&!out_valid))
            $fatal(1,"FAIL missing bounded publication (legal frames exactly333 clocks)");
        if(gap==332&&(frame_error||overrun))$fatal(1,"FAIL legal row gap rejected");
        checks++;
    endtask
    task automatic checkRecordedBoxes;
        candidate_t box;
        int base;
        bit found;
        for(int c=0;c<2;c++)for(int item=0;item<(c==0?2:7);item++)begin
            base=(c*8+item)*8;found=0;
            for(int slot=0;slot<8;slot++)begin
                box=c==0?red_candidates[slot]:blue_candidates[slot];
                if(box.valid&&box.xmin==expected[base+1]&&box.xmax==expected[base+2]&&
                   box.ymin==expected[base+3]&&box.ymax==expected[base+4]&&box.area==expected[base+5]&&
                   box.cx==expected[base+6]&&box.cy==expected[base+7])found=1;
            end
            if(!found)$fatal(1,"FAIL real frame BFS descriptor mismatch colour%0d item%0d",c,item);
            checks++;
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectorDir))$fatal(1,"FAIL missing vector directory");
        $readmemh({vectorDir,"/capacity_mask.hex"},mask);
        $readmemh({vectorDir,"/capacity_expected.hex"},expected);
        repeat(3)@(negedge clk);reset=0;
        sendFrame(0);
        if(!frame_valid||overflow||red_count!=1||allocationPeakRed!=9||!oldBad)
            $fatal(1,"FAIL nine temporary handles merging into one output");
        sendFrame(1);
        if(frame_valid||!overflow||red_count!=0||allocationPeakRed!=12)
            $fatal(1,"FAIL thirteen handles must still reject whole frame");
        sendFrame(2);
        if(frame_valid||!overflow||red_count!=0||allocationPeakRed!=3)
            $fatal(1,"FAIL completed capacity must remain eight");
        sendFrame(3);
        if(!frame_valid||overflow||red_count!=2||blue_count!=7||allocationPeakRed!=9||allocationPeakBlue!=5||!oldBad)
            $fatal(1,"FAIL recorded failure does not match independent active12 oracle");
        checkRecordedBoxes();
        sendFrame(4,331);
        if(frame_valid||!frame_error||!overrun)$fatal(1,"FAIL short row gap accepted");
        sendFrame(0);
        if(!frame_valid||overflow)$fatal(1,"FAIL recovery after scheduling overrun");
        $display("PASS boundedCandidatesActive_tb: six frames, %0d checks, exact332/333 clocks, real frame30507",checks);
        $finish;
    end
    initial begin #20000000;$fatal(1,"FAIL active capacity timeout");end
endmodule
