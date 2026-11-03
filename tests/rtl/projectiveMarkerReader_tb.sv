`timescale 1ns/1ps
// Independent integer-homography/model vectors include source-labelled real
// captures and synthetic counterfactuals. Candidate extraction is outside this
// bench; the complete core replay separately exercises the candidate pipeline.
module projectiveMarkerReader_tb #(
    // reader8:1/1/1; reader7:1/1/0; reader6:1/0/0; reader5:0/0/0.
    parameter bit ENFORCE_OWNER_BOUNDS=1'b1,
    parameter bit ENFORCE_MAIN_COMPONENT=1'b1,
    parameter bit EMIT_CALIBRATION_QUADS=1'b1,
    parameter bit ENABLE_THIN_ANCHOR_SUPPORT=1'b1
);
    logic bypassPerspective=0;
    bit bypassMode=0;
    import candidate_pkg::*;
    import vision_pkg::*;
    logic clk=0;
    always #10 clk=~clk;
    logic reset=1,start=0,busy,done,readWhite,readStrongWhite,readColour;
    logic [1:0] orientationProfile;
    logic [16:0] readAddress;
    logic [4:0] acceptedCount;
    candidate_array_t sharedCandidates;
    logic [15:0] sharedColours;
    markerArray_t markers;
    logic [3:0] geometryReadIndex=0;
    colourQuad_t geometryReadQuad;
    logic whiteBank[0:76799],strongWhiteBank[0:76799],colourBank[0:76799];
    logic [68:0] candidateWords[0:15];
    logic candidateColours[0:15];
    logic [31:0] expectedWords[0:15];
    logic expectedThinSupport[0:15];
    // Nine signed32-bit file words per slot: valid,x0,y0,...,x3,y3.
    // Do not infer file packing from the packed SystemVerilog struct order.
    logic [31:0] expectedColourQuadWords[0:143];
    logic [1:0] expectedOrientations[0:15];
    logic [19:0] mapWords[0:20479];
    logic [31:0] countWord[0:0];
    logic [31:0] slotCountWord[0:0];
    logic sharedPoolWord[0:0];
    logic [1:0] orientationWord[0:0];
    string vectorsPath,filename;
    integer expectedCount,cycles,currentVector=0,coordinateChecks=0,maxCycles=0;
    integer mainCalls=0,expectedMainCalls=0,mainCycles=0,maxMainCycles=0,totalMainCycles=0;
    integer maxMainAllocationPeak=0,mainOverflowCalls=0,mainCycleBaseline=0,maxVectorMainCycles=0;
    integer readerClockCount=0,vectorStartCycle=0,geometryReadChecks=0,negativeGeometryCoordinates=0;
    integer lastValidGeometrySlot=-1;
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
    projectiveMarkerReader #(.ENFORCE_OWNER_BOUNDS(ENFORCE_OWNER_BOUNDS),
        .ENFORCE_MAIN_COMPONENT(ENFORCE_MAIN_COMPONENT),
        .EMIT_CALIBRATION_QUADS(EMIT_CALIBRATION_QUADS),
        .ENABLE_THIN_ANCHOR_SUPPORT(ENABLE_THIN_ANCHOR_SUPPORT)) dut(.*);
    always_ff @(posedge clk)begin
        readWhite<=whiteBank[readAddress];
        readStrongWhite<=strongWhiteBank[readAddress];
        readColour<=colourBank[readAddress];
    end
    always @(posedge clk)begin
        if(!reset&&compareMap&&dut.state==dut.DECIDE)begin
            if(ENABLE_THIN_ANCHOR_SUPPORT&&dut.selectedFallback!==expectedThinSupport[dut.index])
                $fatal(1,"Thin support mismatch vector=%0d slot=%0d",currentVector,dut.index);
            if(dut.selectedFallback&&dut.decision.quality>192)
                $fatal(1,"Weak support must not claim strongest quality");
        end
        readerClockCount++;
        if(!reset&&dut.state==dut.MAIN_START)begin
            if(bypassMode||!ENFORCE_MAIN_COMPONENT)
                $fatal(1,"Historical/SW8 bypass unexpectedly invoked main-component geometry");
            mainCalls++;mainCycles=0;
        end
        if(!reset&&(dut.state==dut.MAIN_START||dut.state==dut.MAIN_WAIT))begin
            totalMainCycles++;mainCycles++;
            if(dut.state==dut.MAIN_WAIT&&dut.mainDone)begin
                if(mainCycles>maxMainCycles)maxMainCycles=mainCycles;
                if(dut.mainAllocationPeak>maxMainAllocationPeak)maxMainAllocationPeak=dut.mainAllocationPeak;
                if(dut.mainOverflow)mainOverflowCalls++;
            end
        end
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
    task automatic checkGeometryRead(input integer slot,input bit requireInvalid);
        colourQuad_t previousOutput;
        integer expectedX,expectedY,actualX,actualY;
        begin
            @(negedge clk);previousOutput=geometryReadQuad;geometryReadIndex=4'(slot);
            #1;
            if(geometryReadQuad!==previousOutput)$fatal(1,"Geometry address caused asynchronous read-through");
            @(posedge clk);#1;
            geometryReadChecks++;
            if(requireInvalid||!EMIT_CALIBRATION_QUADS)begin
                if(geometryReadQuad!=='0)$fatal(1,"Stale/disabled colour geometry leaked slot=%0d",slot);
            end else begin
                if(expectedColourQuadWords[slot*9]>1||$isunknown(expectedColourQuadWords[slot*9]))
                    $fatal(1,"Invalid expected colour-quad validity word slot=%0d",slot);
                if(geometryReadQuad.valid!==expectedColourQuadWords[slot*9][0])
                    $fatal(1,"Colour quad validity mismatch vector=%0d slot=%0d actual=%0d expected=%0d",
                        currentVector,slot,geometryReadQuad.valid,expectedColourQuadWords[slot*9]);
                if(!geometryReadQuad.valid)begin
                    if(geometryReadQuad!=='0)$fatal(1,"Invalid geometry exposed stale coordinates slot=%0d",slot);
                end else begin
                    lastValidGeometrySlot=slot;
                    for(int corner=0;corner<4;corner++)begin
                        expectedX=$signed(expectedColourQuadWords[slot*9+1+corner*2]);
                        expectedY=$signed(expectedColourQuadWords[slot*9+2+corner*2]);
                        actualX=int'($signed(geometryReadQuad.x[corner]));
                        actualY=int'($signed(geometryReadQuad.y[corner]));
                        if(expectedX< -1024||expectedX>1023||expectedY< -1024||expectedY>1023)
                            $fatal(1,"Expected half-pixel coordinate exceeds the signed11 interface");
                        if(actualX!=expectedX||actualY!=expectedY)
                            $fatal(1,"Colour quad coordinate mismatch vector=%0d slot=%0d corner=%0d actual=%0d,%0d expected=%0d,%0d",
                                currentVector,slot,corner,actualX,actualY,expectedX,expectedY);
                        if(actualX<0)negativeGeometryCoordinates++;
                        if(actualY<0)negativeGeometryCoordinates++;
                    end
                end
            end
            @(negedge clk);
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectorsPath))$fatal(1,"Missing +VECTORS path");
        bypassMode=$test$plusargs("BYPASS");
        if(bypassMode)begin
            // Full-suite exports keep a nested bypass directory. Targeted
            // source-bound exports may explicitly name an independent folder.
            if($value$plusargs("BYPASS_VECTORS=%s",filename))vectorsPath=filename;
            else vectorsPath={vectorsPath,"/bypass"};
        end
        filename={vectorsPath,"/projective_count.hex"};requireFile(filename);$readmemh(filename,countWord);
        filename={vectorsPath,"/projective_slot_count.hex"};requireFile(filename);$readmemh(filename,slotCountWord);
        filename={vectorsPath,"/projective_shared_pool.hex"};requireFile(filename);$readmemh(filename,sharedPoolWord);
        if(slotCountWord[0]!==32'd16||sharedPoolWord[0]!==1'b1)
            $fatal(1,"Current reader RTL requires explicit shared16 vectors; historical split replay needs its historical source");
        if($isunknown(countWord[0])||countWord[0]<1||countWord[0]>512)$fatal(1,"Invalid projective vector count");
        sharedCandidates='0;sharedColours=0;orientationProfile=0;
        repeat(3)@(negedge clk);reset=0;
        for(int slot=0;slot<16;slot++)checkGeometryRead(slot,1);
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
            filename=$sformatf("%s/projective_%0d_candidate_colours.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,candidateColours);
            filename=$sformatf("%s/projective_%0d_expected.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,expectedWords);
            if(ENABLE_THIN_ANCHOR_SUPPORT)begin
                filename=$sformatf("%s/projective_%0d_expected_thin_support.hex",vectorsPath,vectorIndex);
                requireFile(filename);$readmemh(filename,expectedThinSupport);
            end
            filename=$sformatf("%s/projective_%0d_orientation.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,orientationWord);
            filename=$sformatf("%s/projective_%0d_expected_orientation.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,expectedOrientations);
            filename=$sformatf("%s/projective_%0d_map.hex",vectorsPath,vectorIndex);requireFile(filename);$readmemh(filename,mapWords);
            for(int wordIndex=0;wordIndex<144;wordIndex++)expectedColourQuadWords[wordIndex]=0;
            if(EMIT_CALIBRATION_QUADS)begin
                filename=$sformatf("%s/projective_%0d_expected_colour_quads.hex",vectorsPath,vectorIndex);
                requireFile(filename);$readmemh(filename,expectedColourQuadWords);
            end
            for(int slot=0;slot<16;slot++)begin
                integer minimumScanDimension;
                sharedCandidates[slot]=candidateWords[slot];sharedColours[slot]=candidateColours[slot];
                expectedBox=candidateWords[slot];
                minimumScanDimension=EMIT_CALIBRATION_QUADS&&candidateColours[slot]?4:24;
                if(ENFORCE_MAIN_COMPONENT&&!bypassMode&&expectedBox.valid&&
                    expectedBox.xmin<=expectedBox.xmax&&expectedBox.ymin<=expectedBox.ymax&&
                    expectedBox.xmax<320&&expectedBox.ymax<240&&
                    int'(expectedBox.xmax)-int'(expectedBox.xmin)+1>=minimumScanDimension&&
                    int'(expectedBox.ymax)-int'(expectedBox.ymin)+1>=minimumScanDimension)expectedMainCalls++;
            end
            orientationProfile=orientationWord[0];bypassPerspective=bypassMode;compareMap=1;
            mainCycleBaseline=totalMainCycles;
            @(negedge clk);start=1;vectorStartCycle=readerClockCount+1;
            @(negedge clk);start=0;
            // The preceding vector deliberately leaves a real valid geometry
            // read pending. A new start must clear every validity bit and the
            // registered read-valid output, without resetting the RAM contents.
            if(dut.geometryValid!=='0||geometryReadQuad!=='0)
                $fatal(1,"New start leaked previous-frame geometry before a new write");
            sharedCandidates='0;sharedColours=~sharedColours;orientationProfile=orientationWord[0]+2'd1;bypassPerspective=!bypassMode;
            for(int slot=0;slot<16;slot++)checkGeometryRead(slot,1);
            while(!done&&readerClockCount-vectorStartCycle<2000000)@(negedge clk);
            cycles=readerClockCount-vectorStartCycle;
            if(!done)$fatal(1,"Reader exceeds 40 ms frame budget vector=%0d",vectorIndex);
            if(cycles>maxCycles)maxCycles=cycles;
            if(totalMainCycles-mainCycleBaseline>maxVectorMainCycles)maxVectorMainCycles=totalMainCycles-mainCycleBaseline;
            compareMap=0;expectedCount=0;
            for(int slot=0;slot<16;slot++)begin
                actualMarker=markers[slot];expectedBox=candidateWords[slot];
                actualWord={7'd0,actualMarker.accepted,4'd0,actualMarker.digit,actualMarker.quality,actualMarker.reason};
                if(actualWord!==expectedWords[slot])
                    $fatal(1,"Classification mismatch vector=%0d slot=%0d expected=%08h actual=%08h segments=%07b",
                        vectorIndex,slot,expectedWords[slot],actualWord,actualMarker.segments);
                if(actualMarker.orientation!==expectedOrientations[slot]||actualMarker.isBlue!==candidateColours[slot])
                    $fatal(1,"Pixel-derived orientation/type mismatch vector=%0d slot=%0d actual=%0d expected=%0d",
                        vectorIndex,slot,actualMarker.orientation,expectedOrientations[slot]);
                if({actualMarker.xMin,actualMarker.xMax,actualMarker.yMin,actualMarker.yMax}!==
                    {expectedBox.xmin,expectedBox.xmax,expectedBox.ymin,expectedBox.ymax})
                    $fatal(1,"Canonical rectification changed external native bbox");
                if(actualMarker.accepted)expectedCount++;
            end
            if(acceptedCount!==expectedCount)$fatal(1,"Accepted count mismatch");
            lastValidGeometrySlot=-1;
            for(int slot=0;slot<16;slot++)checkGeometryRead(slot,0);
            // Real previous-frame data, not an injected/fabricated quad, tests
            // clearing the one-cycle registered read token at the next start.
            if(lastValidGeometrySlot>=0)checkGeometryRead(lastValidGeometrySlot,0);
            $display("PROJECTIVE_MATCH vector=%0d accepted=%0d cycles=%0d latencyUs=%0d",vectorIndex,expectedCount,cycles,cycles/50);
            @(negedge clk);if(done)$fatal(1,"done must be one cycle");
        end
        if(mainCalls!=expectedMainCalls)$fatal(1,"Main-component invocation count actual=%0d expected=%0d",mainCalls,expectedMainCalls);
        sharedCandidates[0]='0;sharedCandidates[0].valid=1;sharedColours=0;
        sharedCandidates[0].xmin=0;sharedCandidates[0].xmax=53;sharedCandidates[0].ymin=0;sharedCandidates[0].ymax=60;
        // The earlier start-capture check deliberately changed caller ports.
        // Bind the requested mode again for this independent reset scenario.
        bypassPerspective=bypassMode;
        @(negedge clk);start=1;@(negedge clk);start=0;
        repeat(100)@(negedge clk);reset=1;
        @(negedge clk);if(busy||done||acceptedCount||markers!='0)$fatal(1,"Reset failed to abandon projective scan");
        if(geometryReadQuad!=='0||dut.geometryValid!=='0)$fatal(1,"Reset retained completed geometry validity");
        for(int slot=0;slot<16;slot++)checkGeometryRead(slot,1);
        if(dut.mainBusy||dut.mainDone||dut.mainGeometryValid)$fatal(1,"Reset did not abort/clear main-component reader");
        if(mainCalls-expectedMainCalls!=(ENFORCE_MAIN_COMPONENT&&!bypassMode?1:0))
            $fatal(1,"Reset scenario did not exercise the intended mode");
        if($test$plusargs("REQUIRE_NEGATIVE_GEOMETRY")&&negativeGeometryCoordinates==0)
            $fatal(1,"Requested signed half-pixel boundary coverage was not exercised");
        $display("PASS projectiveMarkerReader_tb vectors=%0d coordinateChecks=%0d maxCycles=%0d mainCalls=%0d resetMainCalls=%0d maxMainCycles=%0d maxVectorMainCycles=%0d maxMainAllocationPeak=%0d mainOverflowCalls=%0d geometryReadChecks=%0d negativeGeometryCoordinates=%0d emitQuads=%0d",
            countWord[0],coordinateChecks,maxCycles,expectedMainCalls,mainCalls-expectedMainCalls,maxMainCycles,maxVectorMainCycles,maxMainAllocationPeak,mainOverflowCalls,
            geometryReadChecks,negativeGeometryCoordinates,EMIT_CALIBRATION_QUADS);
        $finish;
    end
    // Up to512 declared vectors, each retaining its40ms budget above, need
    // 20.48s simulated time plus file/start overhead. This is a suite guard,
    // not permission to extend the per-frame algorithm budget.
    initial begin #(64'd22000000000);$fatal(1,"Global projective reader timeout");end
endmodule
