`timescale 1ns/1ps
// Independent integer-homography/model vectors include source-labelled real
// captures and synthetic counterfactuals. Candidate extraction is outside this
// bench; the complete core replay separately exercises the real CAP8 pipeline.
module projectiveMarkerReader_tb;
    import candidate_pkg::*;
    import vision_pkg::*;
    logic clk=0;
    always #10 clk=~clk;
    logic reset=1,start=0,busy,done,readWhite,readStrongWhite,readColour;
    logic [1:0] orientationProfile;
    logic [16:0] readAddress;
    logic [4:0] acceptedCount;
    candidate_array_t redCandidates,blueCandidates;
    markerArray_t markers;
    logic whiteBank[0:76799],strongWhiteBank[0:76799],colourBank[0:76799];
    logic [68:0] candidateWords[0:15];
    logic [31:0] expectedWords[0:15];
    logic [19:0] mapWords[0:20479];
    logic [31:0] countWord[0:0];
    logic [1:0] orientationWord[0:0];
    string vectorsPath,filename;
    integer expectedCount,cycles,currentVector=0,coordinateChecks=0,maxCycles=0;
    logic compareMap=0;
    candidate_t expectedBox;
    marker_t actualMarker;
    logic [31:0] actualWord;
    logic [19:0] actualCoordinate;
    logic testMultiplyStart=0,testMultiplyDone;
    logic signed [24:0] testOperandA=0;
    logic signed [11:0] testOperandB=0;
    logic signed [36:0] testProduct;
    projectiveSerialMultiply multiplyBoundaryDut(.clk(clk),.reset(reset),.start(testMultiplyStart),
        .operandA(testOperandA),.operandB(testOperandB),.result(testProduct),.done(testMultiplyDone));
    projectiveMarkerReader dut(.*);
    always_ff @(posedge clk)begin
        readWhite<=whiteBank[readAddress];
        readStrongWhite<=strongWhiteBank[readAddress];
        readColour<=colourBank[readAddress];
    end
    always @(posedge clk)begin
        if(!reset&&compareMap&&dut.state==dut.GRID_SAMPLE)begin
            actualCoordinate={2'b0,dut.quotientY,dut.quotientX};
            if(actualCoordinate!==mapWords[int'(dut.index)*1280+int'(dut.gridY)*32+int'(dut.gridX)])
                $fatal(1,"Homography coordinate mismatch vector=%0d slot=%0d grid=%0d,%0d actual=%05h expected=%05h",
                    currentVector,dut.index,dut.gridX,dut.gridY,actualCoordinate,
                    mapWords[int'(dut.index)*1280+int'(dut.gridY)*32+int'(dut.gridX)]);
            coordinateChecks++;
        end
    end
    task automatic requireFile(input string path);
        integer handle;
        begin handle=$fopen(path,"r");if(handle==0)$fatal(1,"Missing vector file: %s",path);$fclose(handle);end
    endtask
    task automatic checkSignedProduct(input integer a,input integer b);
        longint expectedProduct;
        integer waitCycles;
        begin
            expectedProduct=longint'(a)*longint'(b);
            @(negedge clk);testOperandA=25'(a);testOperandB=12'(b);testMultiplyStart=1;
            @(negedge clk);testMultiplyStart=0;
            waitCycles=0;
            while(!testMultiplyDone&&waitCycles<20)begin @(negedge clk);waitCycles++;end
            if(!testMultiplyDone||longint'(testProduct)!=expectedProduct)
                $fatal(1,"Serial signed product a=%0d b=%0d actual=%0d expected=%0d",a,b,testProduct,expectedProduct);
            @(negedge clk);if(testMultiplyDone)$fatal(1,"Multiplier done must pulse once");
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectorsPath))$fatal(1,"Missing +VECTORS path");
        filename={vectorsPath,"/projective_count.hex"};requireFile(filename);$readmemh(filename,countWord);
        if($isunknown(countWord[0])||countWord[0]<1||countWord[0]>256)$fatal(1,"Invalid projective vector count");
        redCandidates='0;blueCandidates='0;orientationProfile=0;
        repeat(3)@(negedge clk);reset=0;
        checkSignedProduct(-16777216,-2048);checkSignedProduct(-16777216,2047);
        checkSignedProduct(16777215,-2048);checkSignedProduct(16777215,2047);
        checkSignedProduct(0,-2048);checkSignedProduct(-1,-2048);
        checkSignedProduct(1,-1);checkSignedProduct(-1,1);
        checkSignedProduct(614400,-640);checkSignedProduct(-614400,640);
        for(int vectorIndex=0;vectorIndex<countWord[0];vectorIndex++)begin
            currentVector=vectorIndex;
            filename=$sformatf("%s/projective_%0d_white.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,whiteBank);
            filename=$sformatf("%s/projective_%0d_strong_white.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,strongWhiteBank);
            filename=$sformatf("%s/projective_%0d_colour.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,colourBank);
            filename=$sformatf("%s/projective_%0d_candidates.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,candidateWords);
            filename=$sformatf("%s/projective_%0d_expected.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,expectedWords);
            filename=$sformatf("%s/projective_%0d_orientation.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,orientationWord);
            filename=$sformatf("%s/projective_%0d_map.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,mapWords);
            for(int slot=0;slot<8;slot++)begin redCandidates[slot]=candidateWords[slot];blueCandidates[slot]=candidateWords[slot+8];end
            orientationProfile=orientationWord[0];compareMap=1;
            @(negedge clk);start=1;
            @(negedge clk);start=0;
            redCandidates='0;blueCandidates='0;orientationProfile=orientationWord[0]+2'd1;
            cycles=0;
            while(!done&&cycles<2000000)begin @(negedge clk);cycles++;end
            if(!done)$fatal(1,"Reader exceeds 40 ms frame budget vector=%0d",vectorIndex);
            if(cycles>maxCycles)maxCycles=cycles;
            compareMap=0;expectedCount=0;
            for(int slot=0;slot<16;slot++)begin
                actualMarker=markers[slot];expectedBox=candidateWords[slot];
                actualWord={7'd0,actualMarker.accepted,4'd0,actualMarker.digit,actualMarker.quality,actualMarker.reason};
                if(actualWord!==expectedWords[slot])
                    $fatal(1,"Classification mismatch vector=%0d slot=%0d expected=%08h actual=%08h segments=%07b",
                        vectorIndex,slot,expectedWords[slot],actualWord,actualMarker.segments);
                if(actualMarker.orientation!==orientationWord[0]||actualMarker.isBlue!==(slot>=8))
                    $fatal(1,"Latched orientation/type mismatch vector=%0d slot=%0d",vectorIndex,slot);
                if({actualMarker.xMin,actualMarker.xMax,actualMarker.yMin,actualMarker.yMax}!==
                    {expectedBox.xmin,expectedBox.xmax,expectedBox.ymin,expectedBox.ymax})
                    $fatal(1,"Canonical rectification changed external native bbox");
                if(actualMarker.accepted)expectedCount++;
            end
            if(acceptedCount!==expectedCount)$fatal(1,"Accepted count mismatch");
            $display("PROJECTIVE_MATCH vector=%0d accepted=%0d cycles=%0d latencyUs=%0d",vectorIndex,expectedCount,cycles,cycles/50);
            @(negedge clk);if(done)$fatal(1,"done must be one cycle");
        end
        redCandidates[0]='0;redCandidates[0].valid=1;
        redCandidates[0].xmin=0;redCandidates[0].xmax=53;redCandidates[0].ymin=0;redCandidates[0].ymax=60;
        @(negedge clk);start=1;@(negedge clk);start=0;
        repeat(100)@(negedge clk);reset=1;
        @(negedge clk);if(busy||done||acceptedCount||markers!='0)$fatal(1,"Reset failed to abandon projective scan");
        $display("PASS projectiveMarkerReader_tb vectors=%0d coordinateChecks=%0d maxCycles=%0d",countWord[0],coordinateChecks,maxCycles);
        $finish;
    end
    initial begin #2000000000;$fatal(1,"Global projective reader timeout");end
endmodule
