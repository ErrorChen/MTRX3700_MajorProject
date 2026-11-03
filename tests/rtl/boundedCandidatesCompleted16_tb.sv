`timescale 1ns/1ps
// One physical completed pool, shared by both colours. Independent real56554
// BFS vectors compare a geometry+colour multiset, never assumed hardware order.
module boundedCandidatesCompleted16_tb;
    import candidate_pkg::*;
    logic clk=0,reset=1,in_valid=0,in_sop=0,in_eop=0;
    always #5 clk=~clk;
    logic [1:0] in_mask=0;
    logic [8:0] in_x=0;
    logic [7:0] in_y=0;
    candidate_array_t sharedCandidates;
    logic [15:0] sharedColours;
    logic [4:0] sharedCount,red_count,blue_count;
    logic [3:0] allocationPeakRed,allocationPeakBlue;
    logic out_valid,frame_valid,overflow,frame_error,overrun,red_overflow,blue_overflow;
    logic [15:0] frame_id;
    logic busy;
    logic [1:0] mask[0:76799];
    logic [31:0] expected[0:257];
    string vectorDir;
    integer checks=0,frames=0,tieChecks=0;
    boundedCandidates #(.CAP(16),.SHARED_POOL(1),.ACTIVE_CAP(15),.PRUNE_UNUSABLE(1)) dut(.*);

    function automatic logic [1:0] pixelAt(input int scenario,x,y);
        logic [1:0] value;
        value=0;
        if(scenario==5)return mask[y*320+x];
        for(int item=0;item<16;item++)begin
            if((scenario!=0||item<11)&&(scenario!=4||item<15)&&
               x>=10+70*(item%4)&&x<34+70*(item%4)&&y>=10+45*(item/4)&&y<34+45*(item/4))begin
                case(scenario)
                    0:value=(item==0||item==10)?1:2; //2red+9blue
                    1:value=item==15?1:2; //1red+15blue
                    2:value=2; //16blue
                    3:value=1; //16red
                    default:value=2;
                endcase
            end
        end
        // Fifteen blue components have retired before two final components.
        // Both final roots use label1: their simultaneous retirement has only
        // one slot left. Red gets slot15; blue raises the shared-pool overflow.
        if(scenario==4&&y>=210&&y<234)begin
            if(x>=10&&x<34)value=1;
            if(x>=100&&x<124)value=2;
        end
        return value;
    endfunction
    always @(posedge clk)if(!reset&&dut.state==dut.RETIRE&&dut.workCount==15&&dut.retireCandidate==2'b11)begin
        if(dut.insertCandidate!==2'b01||dut.blueInsertSlot!=16)$fatal(1,"FAIL simultaneous retirement did not allocate red first");
        tieChecks++;
    end
    task automatic idle;
        @(negedge clk);in_valid=0;in_sop=0;in_eop=0;
        @(posedge clk);#1;
    endtask
    task automatic sendFrame(input int scenario,input int rowGap=335);
        for(int y=0;y<240;y++)begin
            if(y!=0)repeat(rowGap)idle();
            for(int x=0;x<320;x++)begin
                @(negedge clk);in_valid=1;in_x=9'(x);in_y=8'(y);
                in_sop=x==0&&y==0;in_eop=x==319&&y==239;in_mask=pixelAt(scenario,x,y);
                @(posedge clk);#1;
            end
        end
        repeat(335)begin idle();if(rowGap==335&&out_valid)$fatal(1,"FAIL shared16 early publication");end
        idle();frames++;
        if((rowGap==335&&!out_valid)||frame_id!=frames)$fatal(1,"FAIL exact335/336 scheduling/publication identity");
        if(rowGap==335&&(frame_error||overrun))$fatal(1,"FAIL legal335-clock row gap rejected");
        checks++;
    endtask
    task automatic checkSynthetic(input int scenario,input int redExpected,blueExpected);
        candidate_t box;
        int xStart,yStart,found,colour,count;
        count=redExpected+blueExpected;
        if(!frame_valid||overflow||sharedCount!=count||red_count!=redExpected||blue_count!=blueExpected)
            $fatal(1,"FAIL shared capacity counts scenario%0d shared%0d red%0d blue%0d",scenario,sharedCount,red_count,blue_count);
        for(int slot=0;slot<16;slot++)if(sharedCandidates[slot].valid!==(slot<count))
            $fatal(1,"FAIL non-dense shared output");
        for(int item=0;item<count;item++)begin
            xStart=10+70*(item%4);yStart=10+45*(item/4);found=0;
            colour=scenario==0?(item!=0&&item!=10):scenario==1?(item!=15):scenario==2;
            for(int slot=0;slot<16;slot++)begin
                box=sharedCandidates[slot];
                if(box.valid&&sharedColours[slot]==colour&&box.xmin==xStart&&box.xmax==xStart+23&&box.ymin==yStart&&box.ymax==yStart+23&&
                   box.area==576&&box.cx==xStart+11&&box.cy==yStart+11)found++;
            end
            if(found!=1)$fatal(1,"FAIL shared exact unique geometry/colour scenario%0d item%0d",scenario,item);
            checks++;
        end
    endtask
    task automatic checkRecorded;
        candidate_t box;
        int base,found;
        if(!frame_valid||overflow||red_count!=expected[0]||blue_count!=expected[1]||blue_count<9||sharedCount!=red_count+blue_count)
            $fatal(1,"FAIL actual scene56554 did not fit shared pool");
        for(int colour=0;colour<2;colour++)for(int item=0;item<int'(expected[colour]);item++)begin
            base=2+(colour*16+item)*8;found=0;
            for(int slot=0;slot<16;slot++)begin
                box=sharedCandidates[slot];
                if(box.valid&&sharedColours[slot]==colour&&box.xmin==expected[base+1]&&box.xmax==expected[base+2]&&
                   box.ymin==expected[base+3]&&box.ymax==expected[base+4]&&box.area==expected[base+5]&&
                   box.cx==expected[base+6]&&box.cy==expected[base+7])found++;
            end
            if(found!=1)$fatal(1,"FAIL real56554 independent BFS multiset colour%0d item%0d",colour,item);
            checks++;
        end
    endtask
    task automatic checkInvalid;
        if(frame_valid||sharedCount||red_count||blue_count||sharedColours)$fatal(1,"FAIL invalid frame published counts/colour");
        for(int slot=0;slot<16;slot++)if(sharedCandidates[slot].valid)$fatal(1,"FAIL invalid frame published candidate");
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectorDir))$fatal(1,"FAIL missing vector directory");
        $readmemh({vectorDir,"/completed16_mask.hex"},mask);
        $readmemh({vectorDir,"/completed16_expected.hex"},expected);
        repeat(3)@(negedge clk);reset=0;
        sendFrame(0);checkSynthetic(0,2,9);
        sendFrame(1);checkSynthetic(1,1,15);
        sendFrame(2);checkSynthetic(2,0,16);
        sendFrame(3);checkSynthetic(3,16,0);
        sendFrame(4);checkInvalid();
        if(!overflow||red_overflow||!blue_overflow||tieChecks!=1||allocationPeakBlue>4||allocationPeakRed!=1)
            $fatal(1,"FAIL seventeenth mixed completion/tie/overflow attribution");
        sendFrame(5);checkRecorded();
        sendFrame(0,334);checkInvalid();
        if(!frame_error||!overrun)$fatal(1,"FAIL335-clocks lower bound not enforced");
        sendFrame(0);checkSynthetic(0,2,9);
        $display("PASS boundedCandidatesCompleted16_tb shared16 frames=%0d checks=%0d 2R9B/1R15B/16same/17mixed real56554 multiset exact335/336",frames,checks);
        $finish;
    end
    initial begin #30000000;$fatal(1,"FAIL shared16 timeout");end
endmodule
