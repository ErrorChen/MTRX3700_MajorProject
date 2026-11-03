`timescale 1ns/1ps
// Executes the production pairing FSM against independent host geometry
// vectors. Source images establish measured corners only, never pair answers.
module calibrationGeometry_tb;
    import vision_pkg::*;
    import candidate_pkg::*;
    logic clk=0;
    always #10 clk=~clk;
    logic reset=1,start=0,blueIsBay=0,busy,done,pairValid;
    logic [3:0] reason;
    colourQuad_t redQuad,blueQuad;
    candidate_t redBox;
    samplePolygon_t redPolygon,bluePolygon;
    calibrationGeometry dut(.*);

    localparam int RECORD_WORDS=64,MAX_CASES=4096,MAX_CYCLES=4096;
    logic [31:0] countWords[0:0],formatWords[0:0];
    logic [31:0] words[0:MAX_CASES*RECORD_WORDS-1];
    string vectors,fileName;
    integer checks=0,casesRun=0,maximumCycles=0,validCases=0,invalidCases=0;
    integer reasonCoverage[0:15];
    integer rotationCoverage[0:3];
    bit priorDone=0;

    always @(posedge clk)begin
        #2;
        if(reset)priorDone=0;
        else begin
            if(done&&priorDone)$fatal(1,"geometry done lasted more than one cycle");
            if(done&&busy)$fatal(1,"geometry done asserted while busy");
            priorDone=done;
        end
    end

    task automatic loadCase(input integer index);
        integer offset;
        begin
            offset=index*RECORD_WORDS;
            redBox='0;redQuad='0;blueQuad='0;
            redBox.xmin=9'(words[offset]);redBox.ymin=8'(words[offset+1]);
            redBox.xmax=9'(words[offset+2]);redBox.ymax=8'(words[offset+3]);
            for(int corner=0;corner<4;corner++)begin
                redQuad.x[corner]=11'(words[offset+4+2*corner]);
                redQuad.y[corner]=11'(words[offset+5+2*corner]);
                blueQuad.x[corner]=11'(words[offset+12+2*corner]);
                blueQuad.y[corner]=11'(words[offset+13+2*corner]);
            end
            blueIsBay=1'(words[offset+20]);
            redQuad.valid=1'(words[offset+56]);
            blueQuad.valid=1'(words[offset+57]);
            redBox.valid=1'(words[offset+58]);
        end
    endtask

    task automatic runCase(input integer index,input bit disturbInputs);
        integer cycles,offset;
        samplePolygon_t heldRed,heldBlue;
        logic heldValid;
        logic [3:0] heldReason;
        begin
            @(negedge clk);loadCase(index);start=1;
            @(negedge clk);start=0;cycles=0;
            if(pairValid||redPolygon!='0||bluePolygon!='0)
                $fatal(1,"new geometry request retained prior result case=%0d",index);
            while(!done)begin
                @(negedge clk);cycles++;
                if(disturbInputs&&cycles==3)begin
                    // Competing work and changing input buses during busy
                    // must have no effect on the transaction already accepted.
                    redQuad='1;blueQuad='1;redBox='1;blueIsBay=1;start=1;
                end
                if(cycles==4)start=0;
                if(cycles>MAX_CYCLES)
                    $fatal(1,"geometry timeout case=%0d state=%0d",index,dut.state);
            end
            start=0;offset=index*RECORD_WORDS;checks+=4;
            if(pairValid!==1'(words[offset+21]))
                $fatal(1,"geometry verdict case=%0d valid=%0d reason=%0d expected=%0d matches=%0d mapperValid=%0d mapperReason=%0d expectedInside=%0d vLinesGood=%0d x0=%0d y0=%0d",index,pairValid,reason,words[offset+21],dut.matchCount,dut.mapperValid,dut.mapperReason,dut.expectedInside,dut.vLinesGood,$signed(dut.mappedX[0]),$signed(dut.mappedY[0]));
            if(redPolygon.valid!==pairValid||bluePolygon.valid!==pairValid)
                $fatal(1,"geometry polygon valid disagreement case=%0d",index);
            if((pairValid&&reason!=0)||(!pairValid&&reason==0))
                $fatal(1,"geometry reason inconsistent case=%0d valid=%0d reason=%0d",index,pairValid,reason);
            for(int corner=0;corner<4;corner++)begin
                checks+=4;
                if(redPolygon.x[corner]!==13'(words[offset+22+2*corner])||
                   redPolygon.y[corner]!==13'(words[offset+23+2*corner])||
                   bluePolygon.x[corner]!==13'(words[offset+30+2*corner])||
                   bluePolygon.y[corner]!==13'(words[offset+31+2*corner]))
                    $fatal(1,"geometry polygon case=%0d corner=%0d red=%0d,%0d expectedRed=%0d,%0d blue=%0d,%0d expectedBlue=%0d,%0d",index,corner,redPolygon.x[corner],redPolygon.y[corner],words[offset+22+2*corner],words[offset+23+2*corner],bluePolygon.x[corner],bluePolygon.y[corner],words[offset+30+2*corner],words[offset+31+2*corner]);
            end
            if(!pairValid&&(redPolygon!='0||bluePolygon!='0))
                $fatal(1,"invalid geometry retained partial polygon case=%0d",index);
            if(cycles>maximumCycles)maximumCycles=cycles;
            casesRun++;reasonCoverage[reason]++;
            if(pairValid)begin
                validCases++;rotationCoverage[dut.winningRotation]++;checks++;
                if(dut.winningRotation!==2'(words[offset+39]))
                    $fatal(1,"geometry cyclic correspondence case=%0d got=%0d expected=%0d",index,dut.winningRotation,words[offset+39]);
            end else invalidCases++;
            heldRed=redPolygon;heldBlue=bluePolygon;heldReason=reason;heldValid=pairValid;
            repeat(3)begin
                @(negedge clk);checks++;
                if(done||busy||redPolygon!==heldRed||bluePolygon!==heldBlue||reason!==heldReason||pairValid!==heldValid)
                    $fatal(1,"idle geometry output changed case=%0d",index);
            end
        end
    endtask

    initial begin
        redQuad='0;blueQuad='0;redBox='0;
        for(int index=0;index<16;index++)reasonCoverage[index]=0;
        for(int index=0;index<4;index++)rotationCoverage[index]=0;
        if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"VECTORS directory required");
        fileName={vectors,"/calibration_geometry_count.hex"};$readmemh(fileName,countWords);
        fileName={vectors,"/calibration_geometry_record_words.hex"};$readmemh(fileName,formatWords);
        if(formatWords[0]!=RECORD_WORDS||countWords[0]<1||countWords[0]>MAX_CASES)
            $fatal(1,"invalid geometry vector schema/count");
        fileName={vectors,"/calibration_geometry_meta.hex"};$readmemh(fileName,words,0,countWords[0]*RECORD_WORDS-1);
        repeat(4)@(negedge clk);reset=0;
        for(int index=0;index<countWords[0];index++)
            runCase(index,words[index*RECORD_WORDS+21]&&index%2==0);

        // Abort after the mapper has actually begun, then require a clean
        // response to a complete replay. No partial polygon can survive reset.
        @(negedge clk);loadCase(0);start=1;
        @(negedge clk);start=0;
        repeat(100)@(negedge clk);
        if(!busy)$fatal(1,"geometry reset test did not reach busy work");
        reset=1;@(negedge clk);checks++;
        if(busy||done||pairValid||reason!=0||redPolygon!='0||bluePolygon!='0)
            $fatal(1,"geometry reset retained output");
        reset=0;runCase(0,1);
        $display("PASS calibrationGeometry_tb cases=%0d checks=%0d valid=%0d invalid=%0d maximumCycles=%0d inputReject=%0d redRoiReject=%0d referenceReject=%0d pairingReject=%0d blueRoiReject=%0d shapeReject=%0d cyclic0=%0d cyclic1=%0d cyclic2=%0d cyclic3=%0d",casesRun,checks,validCases,invalidCases,maximumCycles,reasonCoverage[1],reasonCoverage[2],reasonCoverage[3],reasonCoverage[4],reasonCoverage[5],reasonCoverage[6],rotationCoverage[0],rotationCoverage[1],rotationCoverage[2],rotationCoverage[3]);
        $finish;
    end
    initial begin #1000000000;$fatal(1,"global geometry timeout");end
endmodule
