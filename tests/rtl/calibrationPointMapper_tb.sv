`timescale 1ns/1ps
module calibrationPointMapper_tb;
    logic clk=0;always #10 clk=~clk;
    logic reset=1,start=0,busy,done,valid;
    logic signed [3:0][10:0] pointX,pointY;
    logic [3:0] pointCount,reason;
    logic signed [11:0][10:0] sampleU,sampleV;
    logic [11:0] requireInImage;
    logic signed [11:0][15:0] mappedX,mappedY;
    calibrationPointMapper dut(.*);
    logic multiplyStart=0,multiplyDone;
    logic signed [47:0] operandA;
    logic signed [11:0] operandB;
    logic signed [59:0] multiplyResult;
    calibrationSerialMultiply arithmetic(.clk(clk),.reset(reset),.start(multiplyStart),
        .operandA(operandA),.operandB(operandB),.result(multiplyResult),.done(multiplyDone));
    logic [31:0] countWords[0:0],words[0:2048*60-1];
    string vectors,fileName;
    integer checks=0,casesRun=0,maximumCycles=0,validCases=0,invalidCases=0;
    integer reasonCoverage[0:7];
    bit priorDone=0;
    always @(posedge clk)begin
        #2;
        if(reset)priorDone=0;
        else begin
            if(done&&priorDone)$fatal(1,"done lasted more than one cycle");
            if(done&&busy)$fatal(1,"done asserted while busy");
            priorDone=done;
        end
    end
    task automatic loadCase(input integer index);
        integer offset;
        begin
            offset=index*60;
            pointCount=4'(words[offset]);
            requireInImage=12'(words[offset+3]);
            for(int corner=0;corner<4;corner++)begin
                pointX[corner]=11'(words[offset+4+2*corner]);
                pointY[corner]=11'(words[offset+5+2*corner]);
            end
            for(int sampleIndex=0;sampleIndex<12;sampleIndex++)begin
                sampleU[sampleIndex]=11'(words[offset+12+sampleIndex]);
                sampleV[sampleIndex]=11'(words[offset+24+sampleIndex]);
            end
        end
    endtask
    task automatic runCase(input integer index,input bit disturbInputs);
        integer cycles,offset;
        logic signed [11:0][15:0] heldOutputX,heldOutputY;
        begin
            @(negedge clk);loadCase(index);start=1;
            @(negedge clk);start=0;cycles=0;
            while(!done)begin
                @(negedge clk);cycles++;
                if(disturbInputs&&cycles==3)begin
                    pointX='1;pointY='1;pointCount=0;sampleU='1;sampleV='1;requireInImage=~requireInImage;
                    start=1; // Busy requests and changing buses cannot replace held inputs.
                end
                if(cycles==4)start=0;
                if(cycles>4000)$fatal(1,"mapper timeout case=%0d state=%0d",index,dut.state);
            end
            start=0;offset=index*60;checks+=2;
            if(valid!==1'(words[offset+1]) || reason!==4'(words[offset+2]))
                $fatal(1,"mapper verdict case=%0d valid=%0d reason=%0d expected=%0d/%0d",index,valid,reason,words[offset+1],words[offset+2]);
            // Geometry/coefficient setup is340 clocks; each point is103 clocks.
            // This is a bounded arithmetic pipeline, with no data-dependent wait.
            if(valid&&cycles!=340+103*words[offset])
                $fatal(1,"mapper latency case=%0d cycles=%0d count=%0d",index,cycles,words[offset]);
            for(int sampleIndex=0;sampleIndex<12;sampleIndex++)begin
                checks+=2;
                if(mappedX[sampleIndex]!==16'(words[offset+36+sampleIndex]) ||
                   mappedY[sampleIndex]!==16'(words[offset+48+sampleIndex]))
                    $fatal(1,"mapper coordinate case=%0d sample=%0d got=%0d,%0d expected=%0d,%0d",index,sampleIndex,$signed(mappedX[sampleIndex]),$signed(mappedY[sampleIndex]),$signed(words[offset+36+sampleIndex]),$signed(words[offset+48+sampleIndex]));
            end
            if(cycles>maximumCycles)maximumCycles=cycles;
            casesRun++;reasonCoverage[reason]++;
            if(valid)validCases++;else invalidCases++;
            heldOutputX=mappedX;heldOutputY=mappedY;
            repeat(3)begin
                @(negedge clk);
                if(done||busy||mappedX!==heldOutputX||mappedY!==heldOutputY)$fatal(1,"idle outputs changed case=%0d",index);
            end
        end
    endtask
    task automatic checkMultiply(input logic signed [47:0] a,input logic signed [11:0] b);
        longint signed expected;
        integer cycles;
        begin
            expected=longint'(a)*longint'(b);
            @(negedge clk);operandA=a;operandB=b;multiplyStart=1;
            @(negedge clk);multiplyStart=0;cycles=0;
            while(!multiplyDone)begin
                @(negedge clk);cycles++;
                if(cycles>20)$fatal(1,"serial multiply timeout");
            end
            checks++;
            if(multiplyResult!==60'(expected))$fatal(1,"serial multiply sign/width a=%0d b=%0d result=%0d expected=%0d",a,b,multiplyResult,expected);
            @(negedge clk);
            if(multiplyDone)$fatal(1,"multiply done pulse");
        end
    endtask
    initial begin
        pointX='0;pointY='0;pointCount=0;sampleU='0;sampleV='0;requireInImage=0;operandA=0;operandB=0;
        for(int index=0;index<8;index++)reasonCoverage[index]=0;
        if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"VECTORS directory required");
        fileName={vectors,"/calibration_mapper_count.hex"};$readmemh(fileName,countWords);
        if(countWords[0]<1||countWords[0]>2048)$fatal(1,"invalid vector count");
        fileName={vectors,"/calibration_mapper_vectors.hex"};$readmemh(fileName,words,0,countWords[0]*60-1);
        repeat(4)@(negedge clk);reset=0;
        for(int index=0;index<countWords[0];index++)runCase(index,words[index*60+1]&&index%2==0);
        checkMultiply(48'sh7fffffffffff,12'sd2047);
        checkMultiply(48'sh800000000000,-12'sd2048);
        checkMultiply(48'sh800000000000,12'sd2047);
        checkMultiply(48'sh7fffffffffff,-12'sd2048);
        checkMultiply(-48'sd1,-12'sd2048);
        for(int index=0;index<512;index++)checkMultiply(48'({$urandom,$urandom}),12'($urandom));
        @(negedge clk);loadCase(0);start=1;
        @(negedge clk);start=0;
        repeat(100)@(negedge clk);
        if(!busy)$fatal(1,"reset test did not reach busy work");
        reset=1;@(negedge clk);
        if(busy||done||valid||mappedX!='0||mappedY!='0)$fatal(1,"mid-transaction reset retained output");
        reset=0;runCase(0,1);
        $display("PASS calibrationPointMapper_tb cases=%0d checks=%0d valid=%0d invalid=%0d maximumCycles=%0d countReject=%0d inputReject=%0d geometryReject=%0d denominatorReject=%0d outsideReject=%0d",casesRun,checks,validCases,invalidCases,maximumCycles,reasonCoverage[1],reasonCoverage[2],reasonCoverage[3],reasonCoverage[5],reasonCoverage[6]);
        $finish;
    end
    initial begin #100000000;$fatal(1,"global mapper timeout");end
endmodule
