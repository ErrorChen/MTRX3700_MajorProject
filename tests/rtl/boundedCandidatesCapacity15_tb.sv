`timescale 1ns/1ps
// Historical active15/output8 boundary test versus the former active12 pool.
// Generated comb masks exercise every nonzero four-bit label and real overflow.
// Only scenario4 is recorded camera frame30507. Frame16493 motivated the new
// capacity, but its RGB pixels were not retained and are not recreated here.
module boundedCandidatesCapacity15_tb;
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
    boundedCandidates #(.SHARED_POOL(0),.CAP(8),.ACTIVE_CAP(15),.PRUNE_UNUSABLE(1)) dut(
        .clk(clk),.reset(reset),.in_valid(in_valid),.in_sop(in_sop),.in_eop(in_eop),
        .in_mask(in_mask),.in_x(in_x),.in_y(in_y),.sharedCandidates(sharedCandidates),.sharedColours(sharedColours),.sharedCount(sharedCount),
        .red_count(red_count),.blue_count(blue_count),.out_valid(out_valid),.frame_valid(frame_valid),
        .overflow(overflow),.frame_error(frame_error),.overrun(overrun),.red_overflow(),.blue_overflow(),
        .frame_id(),.busy(),.allocationPeakRed(allocationPeakRed),.allocationPeakBlue(allocationPeakBlue));
    boundedCandidates #(.SHARED_POOL(0),.CAP(8),.ACTIVE_CAP(12),.PRUNE_UNUSABLE(1)) oldDut(
        .clk(clk),.reset(reset),.in_valid(in_valid),.in_sop(in_sop),.in_eop(in_eop),
        .in_mask(in_mask),.in_x(in_x),.in_y(in_y),.sharedCandidates(oldSharedCandidates),.sharedColours(oldSharedColours),.sharedCount(),
        .red_count(),.blue_count(),.out_valid(oldValid),.frame_valid(oldGood),
        .overflow(oldOverflow),.frame_error(),.overrun(),.red_overflow(),.blue_overflow(),
        .frame_id(),.busy(),.allocationPeakRed(),.allocationPeakBlue());
    always @(negedge clk)if(!reset&&oldValid)begin oldSeen=1;oldBad=oldOverflow;end
    // Aliases stay allocated until row sealing. Even handle15 must point to a
    // nonzero canonical root, never wrap to the reserved background label0.
    always @(negedge clk)if(!reset)for(int colour=0;colour<2;colour++)for(int slot=0;slot<15;slot++)begin
        if(!dut.free_slots[colour][slot])begin
            if(dut.parent[colour][slot]<1||dut.parent[colour][slot]>15||
               dut.parent[colour][dut.parent[colour][slot]-1]!=dut.parent[colour][slot])
                $fatal(1,"FAIL active15 canonical parent invariant");
        end
    end
    function automatic logic [1:0] pixelAt(input int scenario,x,y);
        int seeds;
        logic [1:0] value;
        value=0;
        seeds=scenario==0?15:scenario==1?13:16;
        if(scenario<3)begin
            if(y>=10&&y<=34&&x>=10&&x<=10+4*(seeds-1)&&
               ((x-10)%4==0||y==34))value=1;
            // Both colours independently consume all fifteen handles.
            if(scenario==0&&y>=60&&y<=84&&x>=100&&x<=156&&
               ((x-100)%4==0||y==84))value=2;
        end else if(scenario==3)begin
            for(int item=0;item<9;item++)if(x>=10+40*(item%3)&&x<34+40*(item%3)&&
                y>=10+40*(item/3)&&y<34+40*(item/3))value=1;
        end else if(scenario==4)value=mask[y*320+x];
        return value;
    endfunction
    task automatic idle;
        @(negedge clk);in_valid=0;in_sop=0;in_eop=0;
        @(posedge clk);#1;
    endtask
    task automatic sendFrame(input int scenario,gap=335);
        bit publicationSeen;
        oldSeen=0;oldBad=0;publicationSeen=0;
        for(int y=0;y<240;y++)begin
            if(y!=0)repeat(gap)idle();
            for(int x=0;x<320;x++)begin
                @(negedge clk);in_valid=1;in_x=9'(x);in_y=8'(y);
                in_sop=x==0&&y==0;in_eop=x==319&&y==239;in_mask=pixelAt(scenario,x,y);
                @(posedge clk);#1;
            end
        end
        repeat(335)begin
            idle();
            if(out_valid)begin
                publicationSeen=1;
                if(gap==335)$fatal(1,"FAIL early active15 publication");
            end
        end
        idle();publicationSeen=publicationSeen||out_valid;
        if(!publicationSeen||!oldSeen||(gap==335&&!out_valid))
            $fatal(1,"FAIL missing publication (legal frames exactly336 clocks)");
        if(gap==335&&(frame_error||overrun))$fatal(1,"FAIL exact335 row gap rejected");
        checks++;
    endtask
    task automatic checkRecordedBoxes;
        candidate_t box;
        int base;
        bit found;
        for(int colour=0;colour<2;colour++)for(int item=0;item<(colour==0?2:7);item++)begin
            base=(colour*8+item)*8;found=0;
            for(int slot=0;slot<8;slot++)begin
                box=colour==0?red_candidates[slot]:blue_candidates[slot];
                if(box.valid&&box.xmin==expected[base+1]&&box.xmax==expected[base+2]&&
                   box.ymin==expected[base+3]&&box.ymax==expected[base+4]&&box.area==expected[base+5]&&
                   box.cx==expected[base+6]&&box.cy==expected[base+7])found=1;
            end
            if(!found)$fatal(1,"FAIL recorded BFS geometry colour%0d item%0d",colour,item);
            checks++;
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectorDir))$fatal(1,"FAIL missing vector directory");
        $readmemh({vectorDir,"/capacity_mask.hex"},mask);
        $readmemh({vectorDir,"/capacity_expected.hex"},expected);
        repeat(3)@(negedge clk);reset=0;
        sendFrame(0);
        if(!frame_valid||overflow||red_count!=1||blue_count!=1||
           allocationPeakRed!=15||allocationPeakBlue!=15||!oldBad)
            $fatal(1,"FAIL fifteen handles per colour did not merge into single outputs");
        if(red_candidates[0].area!=417||red_candidates[0].xmin!=10||red_candidates[0].xmax!=66||
           red_candidates[0].ymin!=10||red_candidates[0].ymax!=34||blue_candidates[0].area!=417)
            $fatal(1,"FAIL merged aliases lost or duplicated pixels");
        sendFrame(1);
        if(!frame_valid||overflow||red_count!=1||allocationPeakRed!=13||!oldBad)
            $fatal(1,"FAIL thirteen-label old12 counterexample");
        sendFrame(2);
        if(frame_valid||!overflow||red_count!=0||blue_count!=0||allocationPeakRed!=15||!oldBad)
            $fatal(1,"FAIL sixteenth label must invalidate whole frame without label0 wrap");
        sendFrame(3);
        if(frame_valid||!overflow||red_count!=0||allocationPeakRed!=3||!oldBad)
            $fatal(1,"FAIL output capacity must remain eight");
        sendFrame(4);
        if(!frame_valid||overflow||red_count!=2||blue_count!=7||allocationPeakRed!=9||allocationPeakBlue!=5||oldBad)
            $fatal(1,"FAIL retained frame30507 active15/active12 agreement");
        checkRecordedBoxes();
        sendFrame(5,334);
        if(frame_valid||!frame_error||!overrun)$fatal(1,"FAIL short334 row gap accepted");
        sendFrame(0);
        if(!frame_valid||overflow||red_count!=1||blue_count!=1)
            $fatal(1,"FAIL recovery after scheduling overrun");
        $display("PASS boundedCandidatesCapacity15_tb: seven frames, %0d checks, exact335/336 clocks",checks);
        $finish;
    end
    initial begin #20000000;$fatal(1,"FAIL capacity15 timeout");end
endmodule
