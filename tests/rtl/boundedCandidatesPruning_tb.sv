`timescale 1ns/1ps
// Synthetic pixel masks exercise the optional retirement-only necessary-size
// gate. Both DUTs consume identical native-sized frames with the actual 328
// invalid clocks between rows; no frame/candidate ID is injected as an answer.
module boundedCandidatesPruning_tb;
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

    localparam int W=320,H=240,CAP=8,ROW_GAP=W+CAP,FINAL_LATENCY=ROW_GAP+1;
    logic clk=0,reset=1,in_valid=0,in_sop=0,in_eop=0;
    always #5 clk=~clk;
    logic [1:0] in_mask=0;
    logic [8:0] in_x=0;
    logic [7:0] in_y=0;
    logic [4:0] red_count,blue_count,oldRedCount,oldBlueCount;
    logic [3:0] allocationPeakRed,allocationPeakBlue,oldPeakRed,oldPeakBlue;
    logic out_valid,frame_valid,red_overflow,blue_overflow,overflow,frame_error,overrun,busy;
    logic oldOutValid,oldFrameValid,oldRedOverflow,oldBlueOverflow,oldOverflow,oldError,oldOverrun;
    logic [15:0] frame_id;
    int cycles=0,lastPixelCycle,checks=0;
    always @(posedge clk)cycles++;
    boundedCandidates #(.SHARED_POOL(0),.W(W),.H(H),.CAP(CAP),.MIN_AREA(32),.PRUNE_UNUSABLE(1)) dut(.*);
    boundedCandidates #(.SHARED_POOL(0),.W(W),.H(H),.CAP(CAP),.MIN_AREA(32)) legacy(
        .clk(clk),.reset(reset),.in_valid(in_valid),.in_sop(in_sop),.in_eop(in_eop),
        .in_mask(in_mask),.in_x(in_x),.in_y(in_y),.sharedCandidates(oldSharedCandidates),.sharedColours(oldSharedColours),.sharedCount(),
        .red_count(oldRedCount),.blue_count(oldBlueCount),.out_valid(oldOutValid),.frame_valid(oldFrameValid),
        .red_overflow(oldRedOverflow),.blue_overflow(oldBlueOverflow),.overflow(oldOverflow),
        .frame_error(oldError),.overrun(oldOverrun),.frame_id(),.busy(),
        .allocationPeakRed(oldPeakRed),.allocationPeakBlue(oldPeakBlue));
    function automatic bit withinBox(input int x,y,x0,y0,width,height);
        return x>=x0&&x<x0+width&&y>=y0&&y<y0+height;
    endfunction
    function automatic logic [1:0] maskAt(input int scenario,x,y);
        logic [1:0] value;
        value=0;
        case(scenario)
            0:begin
                for(int i=0;i<12;i++)if(withinBox(x,y,10,2+5*i,20,2))value=2;
                if(withinBox(x,y,50,100,24,24))value=2;
            end
            1:begin
                if(withinBox(x,y,10,10,20,3)||withinBox(x,y,50,10,3,20))value=2;
                if(withinBox(x,y,100,10,24,24))value=1;
            end
            2:begin
                if(withinBox(x,y,10,10,23,24)||withinBox(x,y,50,10,24,23))value=1;
                if(withinBox(x,y,100,10,24,24))value=2;
            end
            3:for(int i=0;i<9;i++)if(withinBox(x,y,10+50*(i%3),10+50*(i/3),24,24))value=2;
            4:for(int i=0;i<9;i++)if(withinBox(x,y,10+10*i,10,4,8))value=2;
            5:for(int i=0;i<8;i++)if(withinBox(x,y,10,5+10*i,20,3))value=2;
            default:value=0;
        endcase
        return value;
    endfunction
    task automatic idleCycle;
        @(negedge clk);in_valid=0;in_sop=0;in_eop=0;in_mask=0;
        @(posedge clk);#1;
    endtask
    task automatic sendFrame(input int scenario);
        for(int y=0;y<H;y++)begin
            if(y!=0)repeat(ROW_GAP)idleCycle();
            for(int x=0;x<W;x++)begin
                @(negedge clk);in_valid=1;in_x=9'(x);in_y=8'(y);
                in_mask=maskAt(scenario,x,y);in_sop=x==0&&y==0;in_eop=x==W-1&&y==H-1;
                @(posedge clk);#1;
            end
        end
        lastPixelCycle=cycles;
        repeat(FINAL_LATENCY)idleCycle();
        if(!out_valid||!oldOutValid||cycles-lastPixelCycle!=FINAL_LATENCY)
            $fatal(1,"FAIL pruning changed publication timing case%0d",scenario);
        if(frame_error||overrun||oldError||oldOverrun)
            $fatal(1,"FAIL pruning normal frame has protocol error case%0d",scenario);
        if(allocationPeakRed!==oldPeakRed||allocationPeakBlue!==oldPeakBlue)
            $fatal(1,"FAIL retirement pruning changed active-label allocation case%0d",scenario);
    endtask
    task automatic expectCounts(input int redCount,blueCount);
        if(!frame_valid||overflow||int'(red_count)!=redCount||int'(blue_count)!=blueCount)
            $fatal(1,"FAIL pruned counts got%0d/%0d valid%0d overflow%0d expected%0d/%0d",red_count,blue_count,frame_valid,overflow,redCount,blueCount);
        checks++;
    endtask
    task automatic expectBox(input bit blue,input int x,y,width,height,area);
        candidate_t box;
        bit found;
        found=0;
        for(int i=0;i<8;i++)begin
            box=blue?blue_candidates[i]:red_candidates[i];
            if(box.valid&&box.xmin==x&&box.xmax==x+width-1&&box.ymin==y&&box.ymax==y+height-1&&
                box.area==area&&box.cx==(2*x+width-1)/2&&box.cy==(2*y+height-1)/2)found=1;
        end
        if(!found)$fatal(1,"FAIL retained descriptor geometry/area/centre changed");
        checks++;
    endtask
    initial begin
        repeat(3)@(posedge clk);
        @(negedge clk);reset=0;
        sendFrame(0);expectCounts(0,1);expectBox(1,50,100,24,24,576);
        if(!oldOverflow||!oldBlueOverflow||oldFrameValid)$fatal(1,"FAIL old fragment overflow control did not fire");
        sendFrame(1);expectCounts(1,2);expectBox(1,10,10,20,3,60);expectBox(1,50,10,3,20,60);expectBox(0,100,10,24,24,576);
        sendFrame(2);expectCounts(0,1);expectBox(1,100,10,24,24,576);
        if(oldRedCount!=2||oldBlueCount!=1||!oldFrameValid)$fatal(1,"FAIL red necessary-size negative control");
        sendFrame(3);
        if(!overflow||!blue_overflow||frame_valid||blue_count!=0||allocationPeakBlue>8)
            $fatal(1,"FAIL genuine ninth completed component must overflow");
        sendFrame(4);
        if(!overflow||!blue_overflow||!oldOverflow||frame_valid||allocationPeakBlue!=8)
            $fatal(1,"FAIL active-handle overflow was hidden");
        sendFrame(5);expectCounts(0,8);
        for(int i=0;i<8;i++)expectBox(1,10,5+10*i,20,3,60);
        $display("PASS boundedCandidatesPruning_tb: 6 native frames, %0d checks, unchanged 328-cycle row gap/329-cycle publication",checks);
        $finish;
    end
    initial begin #20000000;$fatal(1,"FAIL pruning test timed out");end
endmodule
