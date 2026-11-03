`timescale 1ns/1ps
module colourSampler_tb;
    import candidate_pkg::*;
    import vision_pkg::*;
    logic clk=0,reset=1,sof=0,pixelValid=0,eop=0,collectEnable=1,roiValid=1;
    always #10 clk=~clk;
    logic [8:0] x=0;
    logic [7:0] y=0;
    logic [23:0] rgb=0;
    logic useProjective=0,sampledUseProjective;
    samplePolygon_t redPolygon,bluePolygon,sampledRedPolygon,sampledBluePolygon;
    logic [1:0] orientation=0;
    candidate_t redBox,blueBox,sampledRedBox,sampledBlueBox;
    logic frameSampleGood;
    logic [7:0] redMinimum,blueMinimum;
    logic [16:0] redSamples,blueSamples;
    integer cycles=0,projectiveCases=0,pixelChecks=0;
    logic eopDelayed=0;
    logic [7:0] committedRed=64,committedBlue=32;
    logic [23:0] recordedPixels[0:76799];
    logic [31:0] recordedMetadata[0:20];
    string sampleVectorDir;
    colourSampler dut(.*);
    // Small consumer model, explicitly separate from the production core: an
    // EOP publishes diagnostic minima, but only a good sample may replace the
    // last accepted profile. A bad frame may change the diagnostic proposals.
    always @(posedge clk)begin
        cycles++;
        if(reset)begin eopDelayed<=0;committedRed<=64;committedBlue<=32;end
        else begin
            eopDelayed<=eop;
            if(eopDelayed&&frameSampleGood)begin committedRed<=redMinimum;committedBlue<=blueMinimum;end
        end
    end
    function automatic samplePolygon_t rectangle(input integer left,top,right,bottom);
        samplePolygon_t value;
        value='0;value.valid=1;
        value.x[0]=13'(left*16);value.y[0]=13'(top*16);
        value.x[1]=13'(right*16);value.y[1]=13'(top*16);
        value.x[2]=13'(right*16);value.y[2]=13'(bottom*16);
        value.x[3]=13'(left*16);value.y[3]=13'(bottom*16);
        return value;
    endfunction
    function automatic samplePolygon_t rotatePolygon(input samplePolygon_t original,input integer rotation);
        samplePolygon_t value;
        integer px,py;
        value=original;
        for(int vertex=0;vertex<4;vertex++)begin
            px=int'(original.x[vertex]);py=int'(original.y[vertex]);
            // Physical quarter turns about native(100,100), retaining positive
            // cyclic vertex order. Fractional Q4 coordinates are not rounded.
            case(rotation)
                0:begin value.x[vertex]=13'(px);value.y[vertex]=13'(py);end
                1:begin value.x[vertex]=13'(3200-py);value.y[vertex]=13'(px);end
                2:begin value.x[vertex]=13'(3200-px);value.y[vertex]=13'(3200-py);end
                default:begin value.x[vertex]=13'(py);value.y[vertex]=13'(3200-px);end
            endcase
        end
        return value;
    endfunction
    function automatic bit oracleInside(input samplePolygon_t polygon,input integer px,py);
        // Independent even/odd horizontal-ray oracle, with signed64-bit exact
        // comparisons. It does not use the DUT's convex half-plane reduction,
        // bounded signed products, hit flags or geometry-valid calculation.
        longint qx,qy,ax,ay,bx,by,lhs,rhs;
        bit boundary,odd;
        qx=longint'(px)*16;qy=longint'(py)*16;boundary=0;odd=0;
        for(int vertex=0;vertex<4;vertex++)begin
            ax=longint'(polygon.x[vertex]);ay=longint'(polygon.y[vertex]);
            bx=longint'(polygon.x[(vertex+1)%4]);by=longint'(polygon.y[(vertex+1)%4]);
            lhs=(qx-ax)*(by-ay);rhs=(qy-ay)*(bx-ax);
            if(lhs==rhs&&qx>=(ax<bx?ax:bx)&&qx<=(ax>bx?ax:bx)&&
               qy>=(ay<by?ay:by)&&qy<=(ay>by?ay:by))boundary=1;
            if((ay>qy)!=(by>qy))begin
                if((by>ay&&lhs<rhs)||(by<ay&&lhs>rhs))odd=!odd;
            end
        end
        return boundary||odd;
    endfunction
    task automatic projectiveScene(input integer mode,input bit geometryAccepted,expectedGood,
        input bit mutateInputs,input bit combineEop,input bit useRecorded);
        samplePolygon_t savedRed,savedBlue,previousSampledRed,previousSampledBlue;
        candidate_t savedRedBox,savedBlueBox;
        bit enabled,redHere,blueHere,polluted,oldPublishedMode;
        integer expectedRedCount,expectedBlueCount,redLowExpected,blueLowExpected;
        integer startCycles;
        logic [7:0] previousCommittedRed,previousCommittedBlue;
        begin
            savedRed=redPolygon;savedBlue=bluePolygon;savedRedBox=redBox;savedBlueBox=blueBox;
            previousSampledRed=sampledRedPolygon;previousSampledBlue=sampledBluePolygon;
            oldPublishedMode=sampledUseProjective;
            enabled=geometryAccepted&&collectEnable&&roiValid;polluted=0;
            expectedRedCount=0;expectedBlueCount=0;redLowExpected=255;blueLowExpected=255;
            previousCommittedRed=committedRed;previousCommittedBlue=committedBlue;
            useProjective=1;startCycles=cycles;
            @(negedge clk);sof=1;
            @(negedge clk);sof=0;
            if(dut.collecting!==enabled)$fatal(1,"Projective SOP admission mismatch case=%0d",projectiveCases);
            if(mutateInputs)begin
                // Deliberately hostile live inputs after the atomic SOP. The
                // complete frame must continue using the original geometry.
                redPolygon='0;bluePolygon='0;redBox='0;blueBox='0;
                useProjective=0;orientation=3;collectEnable=0;roiValid=0;
            end
            for(int py=0;py<240;py++)for(int px=0;px<320;px++)begin
                x=9'(px);y=8'(py);pixelValid=1;
                redHere=oracleInside(savedRed,px,py);blueHere=oracleInside(savedBlue,px,py);
                rgb=24'h080808;
                if(redHere)rgb=mode==1?24'h300a0a:mode==2?24'h0a0808:
                    mode==4?24'hff1410:mode==7?(px[0]?24'h880808:24'h280808):24'h781410;
                if(blueHere)rgb=mode==1?24'h0a0a1c:mode==5?24'h0a14ff:
                    mode==6?(py[0]?24'h081429:24'h081431):mode==8?24'h181820:24'h0a1440;
                if(mode==3&&redHere&&!polluted)begin rgb=24'hffffff;polluted=1;end
                if(useRecorded)rgb=recordedPixels[py*320+px];
                eop=combineEop&&py==239&&px==319;
                #1;
                if(enabled)begin
                    if(dut.redHit!==redHere||dut.blueHit!==blueHere)
                        $fatal(1,"Projective ray/edge membership mismatch case=%0d xy=%0d,%0d",projectiveCases,px,py);
                    pixelChecks++;
                    if(redHere)begin expectedRedCount++;if(int'(rgb[23:16])<redLowExpected)redLowExpected=int'(rgb[23:16]);end
                    if(blueHere)begin expectedBlueCount++;if(int'(rgb[7:0])<blueLowExpected)blueLowExpected=int'(rgb[7:0]);end
                end
                if(py==0&&px==32&&(sampledRedPolygon!==previousSampledRed||
                   sampledBluePolygon!==previousSampledBlue||sampledUseProjective!==oldPublishedMode))
                    $fatal(1,"SOP exposed incomplete frame metadata before EOP");
                @(negedge clk);
            end
            pixelValid=0;
            if(!combineEop)begin eop=1;@(negedge clk);end
            eop=0;repeat(2)@(negedge clk);
            if(frameSampleGood!==expectedGood||redSamples!=expectedRedCount||blueSamples!=expectedBlueCount||
               redMinimum!=(redLowExpected>>1)||blueMinimum!=(blueLowExpected>>1))
                $fatal(1,"Projective raw statistics case=%0d good=%0d expected=%0d red=%0d/%0d blue=%0d/%0d floor=%0d,%0d expected=%0d,%0d",
                    projectiveCases,frameSampleGood,expectedGood,redSamples,expectedRedCount,blueSamples,expectedBlueCount,
                    redMinimum,blueMinimum,redLowExpected>>1,blueLowExpected>>1);
            if(!sampledUseProjective||sampledRedPolygon!==savedRed||sampledBluePolygon!==savedBlue||
               sampledRedBox!==savedRedBox||sampledBlueBox!==savedBlueBox)
                $fatal(1,"Projective completed frame mixed old/live polygon or box metadata");
            if(expectedGood)begin
                if(committedRed!=redMinimum||committedBlue!=blueMinimum)$fatal(1,"Good sample consumer did not accept proposals");
            end else if(committedRed!=previousCommittedRed||committedBlue!=previousCommittedBlue)
                $fatal(1,"Failed sample contaminated the consumer's retained thresholds");
            if(useRecorded&&(redSamples!=recordedMetadata[16]||blueSamples!=recordedMetadata[17]||
               redMinimum!=recordedMetadata[18]||blueMinimum!=recordedMetadata[19]||
               frameSampleGood!=recordedMetadata[20]))$fatal(1,"Recorded image differs from independent exact Python oracle");
            $display("SAMPLER_PROJECTIVE case=%0d mode=%0d good=%0d redSamples=%0d blueSamples=%0d minima=%0d,%0d cycles=%0d recorded=%0d",
                projectiveCases,mode,frameSampleGood,redSamples,blueSamples,redMinimum,blueMinimum,cycles-startCycles,useRecorded);
            projectiveCases++;
            redPolygon=savedRed;bluePolygon=savedBlue;redBox=savedRedBox;blueBox=savedBlueBox;
            collectEnable=1;roiValid=1;useProjective=1;
        end
    endtask
    task automatic scene(input integer mode);
        @(negedge clk);sof=1;
        @(negedge clk);sof=0;
        for(int py=0;py<130;py++) for(int px=0;px<170;px++) begin
            x=px;y=py;pixelValid=1;rgb=0;
            if(px>=20&&px<=119&&py>=20&&py<=119)
                rgb=mode==1 ? 24'h300a0a : mode==2 ? 24'h0a0808 : 24'h781410;
            if(px>=130&&px<=159&&py>=20&&py<=119)
                rgb=mode==1 ? 24'h0a0a1c : 24'h0a1440;
            if(mode==3&&px==30&&py==60)rgb=24'hffffff;
            if(mode==4&&px>=20&&px<=119&&py>=20&&py<=119)rgb=24'hff1410;
            if(mode==5&&px>=130&&px<=159&&py>=20&&py<=119)rgb=24'h0a14ff;
            if(mode==6&&px>=130&&px<=159&&py>=20&&py<=119)
                rgb=py<70?24'h081429:24'h081431;
            @(negedge clk);
        end
        pixelValid=0;eop=1;
        @(negedge clk);eop=0;
    endtask
    initial begin
        samplePolygon_t baseRed,baseBlue,goodRed,goodBlue,invalidPolygon;
        integer firstRotatedRedCount,firstRotatedBlueCount;
        redPolygon='0;bluePolygon='0;
        redBox='0;blueBox='0;
        redBox.valid=1;redBox.xmin=20;redBox.xmax=119;redBox.ymin=20;redBox.ymax=119;
        blueBox.valid=1;blueBox.xmin=130;blueBox.xmax=159;blueBox.ymin=20;blueBox.ymax=119;
        repeat(3)@(negedge clk);reset=0;
        scene(0);
        if(!frameSampleGood || redSamples!=400 || blueSamples!=1080 || redMinimum!=60 || blueMinimum!=32)
            $fatal(1,"inset raw RGB statistics r=%0d b=%0d",redSamples,blueSamples);
        scene(1);
        if(!frameSampleGood || redMinimum!=24 || blueMinimum!=14)
            $fatal(1,"samples below old segmentation threshold must still be collected");
        scene(2);if(frameSampleGood)$fatal(1,"dark reference accepted");
        scene(3);if(frameSampleGood)$fatal(1,"white pollution accepted");
        scene(4);if(frameSampleGood)$fatal(1,"clipped dominant red accepted");
        scene(5);if(frameSampleGood)$fatal(1,"clipped dominant blue accepted");
        scene(6);if(!frameSampleGood||blueMinimum!=20)
            $fatal(1,"V floor must use raw darkest validated reference, not midrange");
        orientation=1;scene(0);
        if(!frameSampleGood || redSamples!=400)$fatal(1,"rotated inset sample");
        collectEnable=0;scene(0);if(frameSampleGood)$fatal(1,"disabled collection accepted");
        collectEnable=1;roiValid=0;scene(0);if(frameSampleGood)$fatal(1,"invalid pairing accepted");
        roiValid=1;orientation=0;redBox.xmax=29;redBox.ymax=29;
        scene(0);if(frameSampleGood || redSamples>=16)$fatal(1,"insufficient sample size accepted");
        if(sampledUseProjective)$fatal(1,"Legacy path unexpectedly advertised projective samples");
        // Oblique, non-rectangular fixtures include fractional Q4 vertices.
        // Painting and expected inclusion use the independent ray oracle.
        baseRed=rectangle(20,20,42,44);
        baseRed.y[1]=13'(22*16+3);baseRed.x[2]=13'(38*16+5);
        baseRed.x[3]=13'(18*16+2);baseRed.y[3]=13'(40*16+7);
        baseBlue=rectangle(54,25,80,43);
        baseBlue.y[1]=13'(29*16+1);baseBlue.x[2]=13'(76*16+9);
        baseBlue.x[3]=13'(52*16+3);baseBlue.y[3]=13'(40*16+5);
        for(int rotation=0;rotation<4;rotation++)begin
            redPolygon=rotatePolygon(baseRed,rotation);bluePolygon=rotatePolygon(baseBlue,rotation);
            orientation=2'(rotation);
            projectiveScene(0,1,1,0,0,0);
            if(rotation==0)begin firstRotatedRedCount=redSamples;firstRotatedBlueCount=blueSamples;end
            else if(redSamples!=firstRotatedRedCount||blueSamples!=firstRotatedBlueCount)
                $fatal(1,"Quarter-turn Q4 sampling changed the exact native lattice population");
        end
        goodRed=rectangle(8,8,11,11);goodBlue=rectangle(20,20,23,23);
        redPolygon=goodRed;bluePolygon=goodBlue;
        projectiveScene(0,1,1,0,0,0);
        if(redSamples!=16||blueSamples!=16)$fatal(1,"Inclusive corners/edges must provide exactly16 samples");
        redPolygon=rectangle(8,8,10,12);
        projectiveScene(0,1,0,0,0,0);
        if(redSamples!=15)$fatal(1,"Exactly15 samples must remain below the unchanged minimum16");
        redPolygon=goodRed;bluePolygon=goodBlue;
        for(int mode=1;mode<=8;mode++)projectiveScene(mode,1,mode==1||mode==6,0,0,0);
        redPolygon=baseRed;bluePolygon=baseBlue;
        projectiveScene(0,1,1,1,0,0);
        collectEnable=0;projectiveScene(0,1,0,0,0,0);
        roiValid=0;projectiveScene(0,1,0,0,0,0);
        // Every malformed shape is explicitly classified by construction, not
        // by copying the DUT's convexity predicate into an expected-good test.
        for(int malformed=0;malformed<8;malformed++)begin
            redPolygon=goodRed;bluePolygon=goodBlue;invalidPolygon=goodRed;
            case(malformed)
                0:invalidPolygon.valid=0;
                1:invalidPolygon.x[1]=13'd5120;
                2:invalidPolygon.y[2]=13'd3840;
                3:begin // Reversed cyclic order: convex but negative orientation.
                    for(int vertex=0;vertex<4;vertex++)begin
                        invalidPolygon.x[vertex]=goodRed.x[3-vertex];
                        invalidPolygon.y[vertex]=goodRed.y[3-vertex];
                    end
                end
                4:begin invalidPolygon.x[2]=invalidPolygon.x[1];invalidPolygon.y[2]=invalidPolygon.y[1];end
                5:begin // Bow tie.
                    invalidPolygon.x[1]=goodRed.x[2];invalidPolygon.y[1]=goodRed.y[2];
                    invalidPolygon.x[2]=goodRed.x[1];invalidPolygon.y[2]=goodRed.y[1];
                end
                6:begin invalidPolygon.x[1]=13'(9*16);invalidPolygon.y[1]=13'(10*16);end // Concave.
                7:begin invalidPolygon.x[0]=13'd8191;invalidPolygon.y[0]=13'd8191;end
            endcase
            // Rejecting either colour invalidates the entire paired sample.
            if(malformed[0])bluePolygon=invalidPolygon;else redPolygon=invalidPolygon;
            projectiveScene(0,0,0,0,0,0);
            if(redSamples||blueSamples)$fatal(1,"Malformed paired ROI still collected raw samples");
        end
        // Both image borders and the final pixel are valid sample centres.
        // Omitting the simultaneous EOP pixel would yield15 blue samples/fail.
        redPolygon=rectangle(0,0,3,3);bluePolygon=rectangle(316,236,319,239);
        projectiveScene(0,1,1,0,1,0);
        if(redSamples!=16||blueSamples!=16)$fatal(1,"Bottom-right simultaneous EOP sample was omitted");
        // Maximum legal fractional vertices exercise large signed products and
        // the17-bit count. Overlapping blue raw pixels must pollute the red
        // sample rather than being filtered away by a colour classification.
        redPolygon=rectangle(0,0,319,239);
        redPolygon.x[1]=5119;redPolygon.x[2]=5119;
        redPolygon.y[2]=3839;redPolygon.y[3]=3839;
        bluePolygon=rectangle(150,100,153,103);
        projectiveScene(0,1,0,0,1,0);
        if(redSamples!=76800||blueSamples!=16)$fatal(1,"Full-frame Q4 population/count width changed");
        // Reset an in-flight collection, including an asserted EOP. No old
        // polygon/mode/statistic may survive and complete under the next SOF.
        redPolygon=goodRed;bluePolygon=goodBlue;
        @(negedge clk);sof=1;@(negedge clk);sof=0;
        x=8;y=8;rgb=24'h781410;pixelValid=1;repeat(4)@(negedge clk);
        reset=1;eop=1;repeat(2)@(negedge clk);pixelValid=0;eop=0;
        if(frameSampleGood||redSamples||blueSamples||sampledUseProjective||
           sampledRedPolygon!=='0||sampledBluePolygon!=='0||redMinimum!=64||blueMinimum!=32)
            $fatal(1,"Reset retained a partial projective sample");
        reset=0;projectiveScene(0,1,1,0,0,0);
        if($value$plusargs("SAMPLE_VECTOR_DIR=%s",sampleVectorDir))begin
            $readmemh({sampleVectorDir,"/frame15078_rgb888.hex"},recordedPixels);
            $readmemh({sampleVectorDir,"/frame15078_expected.hex"},recordedMetadata);
            redPolygon='0;bluePolygon='0;redPolygon.valid=1;bluePolygon.valid=1;
            for(int vertex=0;vertex<4;vertex++)begin
                redPolygon.x[vertex]=13'(recordedMetadata[2*vertex]);redPolygon.y[vertex]=13'(recordedMetadata[2*vertex+1]);
                bluePolygon.x[vertex]=13'(recordedMetadata[8+2*vertex]);bluePolygon.y[vertex]=13'(recordedMetadata[9+2*vertex]);
            end
            projectiveScene(0,1,1,0,1,1);
        end
        // A real following SOP returns to the original SW8/axis path. Invalid
        // polygons are deliberately present and must not gate legacy sampling.
        useProjective=0;redPolygon='1;bluePolygon='1;
        redBox='0;blueBox='0;redBox.valid=1;blueBox.valid=1;
        redBox.xmin=20;redBox.xmax=119;redBox.ymin=20;redBox.ymax=119;
        blueBox.xmin=130;blueBox.xmax=159;blueBox.ymin=20;blueBox.ymax=119;
        for(int rotation=2;rotation<4;rotation++)begin
            orientation=2'(rotation);scene(0);
            if(!frameSampleGood||redSamples!=400||blueSamples!=1080||
               redMinimum!=60||blueMinimum!=32||sampledUseProjective)
                $fatal(1,"Returning to legacy axis mode changed rotation%0d statistics",rotation);
        end
        $display("PASS colourSampler_tb projectiveCases=%0d membershipChecks=%0d cycles=%0d recorded=%0d legacyRetained=1",
            projectiveCases,pixelChecks,cycles,sampleVectorDir!="");$finish;
    end
    // At most32 native-frame projective cases plus the original inset scenes
    // require less than55 ms at50 MHz; keep a bounded60 ms simulation guard.
    initial begin #60000000;$fatal(1,"timeout colourSampler_tb");end
endmodule
