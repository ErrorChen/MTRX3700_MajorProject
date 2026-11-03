`timescale 1ns/1ps
module memberBVgaDiagnostics_tb;
    import perception_pkg::*;
    logic clk=0,reset=1,showCandidates=1,showCentre=1;
    logic [perception_pkg::DEBUG_WORD_COUNT*32-1:0] debugWords=0,rawDebugWords=0,fixtureWords;
    logic [29:0] rawData=0,inData=0,outData;
    logic rawSop,rawEop,rawAccept,inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=0;
    integer cycles=0,written=0,read=0,frameNumber=0,sampleChecks=0,outputX=0,outputY=0;
    logic combinationTest=0;
    logic expectedCandidates,expectedCentre;
    integer candidateTextChecks=0,centreTextChecks=0,compactUiChecks=0,overflowTextChecks=0;
    integer roiTagChecks=0,allBlueChecks=0,blueOverflowTextChecks=0;
    logic overflowUiTest=0,allBlueUiTest=0,blueOverflowUiTest=0;
    logic stalled=0;
    logic [31:0] heldPayload;
    perceptionStatus_t status;
    logic [23:0] hueBoundaryRgb=0;
    logic [1:0] oldHueClass,newHueClass;
    always #5 clk=~clk;
    assign rawSop=inSop;assign rawEop=inEop;assign rawAccept=inValid&&inReady;
    memberBVgaDiagnostics dut(.*);
    hsvColourGate #(.BLUE_HUE_UPPER(250)) oldGate(.rgb(hueBoundaryRgb),.redMinimum(8'd48),.blueMinimum(8'd20),.colourMask(oldHueClass));
    hsvColourGate #(.BLUE_HUE_UPPER(260)) newGate(.rgb(hueBoundaryRgb),.redMinimum(8'd48),.blueMinimum(8'd20),.colourMask(newHueClass));
    function automatic logic [29:0] samplePixel(input int x,y);
        if(x>=180&&x<190&&y>=75&&y<86)return {10'd768,10'd0,10'd0};
        return {10'd0,10'd348,10'd736};
    endfunction
    always @(negedge clk)begin cycles++;outReady=!reset&&cycles%5!=0&&cycles%7!=0;end
    always @(posedge clk)if(!reset)begin
        if(stalled&&(!outValid||{outSop,outEop,outData}!==heldPayload))$fatal(1,"FAIL diagnostic stalled payload changed");
        stalled=outValid&&!outReady;heldPayload={outSop,outEop,outData};
        if(inValid&&inReady)begin
            written++;
            if(inSop)frameNumber++;
            if(frameNumber==2&&dut.pixelX==10&&dut.pixelY==80&&dut.character!="1")
                $fatal(1,"FAIL displayed red hundreds digit must be 1 (raw sample 192)");
            if(frameNumber==2&&dut.pixelX==510&&dut.pixelY==90&&dut.character!="2")
                $fatal(1,"FAIL displayed hue hundreds digit must be 2 (212 degrees)");
            if(frameNumber==2)begin
                if(dut.pixelX==28&&dut.pixelY==70)begin
                    if(!dut.textActive||dut.character!="A")$fatal(1,"FAIL red presentation tag A");
                    compactUiChecks++;
                end
                if(dut.pixelX==528&&dut.pixelY==70)begin
                    if(!dut.textActive||dut.character!="0")$fatal(1,"FAIL blue presentation tag0");
                    compactUiChecks++;
                end
                if(dut.pixelX==10&&dut.pixelY==346)begin
                    if(!dut.textActive||dut.character!="J")$fatal(1,"FAIL confirmed reference panel must say BJ");
                    compactUiChecks++;
                end
                if(dut.pixelX==510&&dut.pixelY==116)begin
                    if(!dut.textActive||dut.character!="6")$fatal(1,"FAIL blue6 ID replaced by presentation tag");
                    compactUiChecks++;
                end
                if(dut.pixelX==4&&dut.pixelY==116)begin
                    if(dut.textActive)$fatal(1,"FAIL rejected/empty red slot produced a panel");
                    compactUiChecks++;
                end
                if(dut.pixelX==504&&dut.pixelY==162)begin
                    if(dut.textActive)$fatal(1,"FAIL empty blue slot produced a panel");
                    compactUiChecks++;
                end
                for(int slot=0;slot<18;slot++)if(dut.displayUiVisible[slot])begin
                    if(int'(dut.pixelY)==int'(dut.displayRecords[slot][63:55])-3 &&
                       int'(dut.pixelX)==int'(dut.displayRecords[slot][72:64])+3)begin
                        if(!dut.textActive||dut.character!==(slot==17?8'd66:8'd35))$fatal(1,"FAIL ROI display tag prefix");
                        roiTagChecks++;
                    end
                    if(int'(dut.pixelY)==int'(dut.displayRecords[slot][63:55])-3 &&
                       int'(dut.pixelX)==int'(dut.displayRecords[slot][72:64])+9)begin
                        if(!dut.textActive||dut.character!==(slot==17?8'd74:dut.hexCharacter(dut.displayUiTags[slot])))
                            $fatal(1,"FAIL ROI/panel display tag mismatch");
                        roiTagChecks++;
                    end
                end
            end
            if(overflowUiTest&&dut.pixelX==4&&dut.pixelY==430)begin
                if(!dut.textActive||dut.character!="R")$fatal(1,"FAIL red display overflow not disclosed");
                overflowTextChecks++;
            end
            if(blueOverflowUiTest&&dut.pixelX==504&&dut.pixelY==430)begin
                if(!dut.textActive||dut.character!="B")$fatal(1,"FAIL blue display overflow not disclosed");
                blueOverflowTextChecks++;
            end
            if(allBlueUiTest)for(int row=0;row<8;row++)begin
                if(dut.pixelX==510&&dut.pixelY==70+row*46)begin
                    if(!dut.textActive||dut.character!==8'(48+(row<6?row+1:row-5)))
                        $fatal(1,"FAIL recognised blue1..6 must remain distinct from tag row%0d",row);
                    allBlueChecks++;
                end
                if(dut.pixelX==528&&dut.pixelY==70+row*46)begin
                    if(!dut.textActive||dut.character!==8'(48+row))$fatal(1,"FAIL complete blue #0..7 presentation range");
                    allBlueChecks++;
                end
            end
            if(combinationTest&&dut.pixelX==4&&dut.pixelY==80)begin
                if(dut.textActive!==expectedCandidates||
                   (expectedCandidates&&dut.character!="R"))$fatal(1,"FAIL SW0 panel enable/character");
                candidateTextChecks++;
            end
            if(combinationTest&&dut.pixelX==0&&dut.pixelY==448)begin
                if(dut.textActive!==expectedCentre||
                   (expectedCentre&&dut.character!="C"))$fatal(1,"FAIL SW1 centre panel enable/character");
                centreTextChecks++;
            end
        end
        if(outValid&&outReady)begin
            read++;
            if(outSop)begin outputX=0;outputY=0;end
            if(outputX==350&&outputY==300&&outData!={10'd0,10'd900,10'd0})
                $fatal(1,"FAIL diagnostic changed unmarked source pixel");
            if(outputX==639)begin outputX=0;outputY++;end else outputX++;
        end
    end
    task automatic sendFrame(input int count,input bit mutate);
        for(int i=0;i<count;i++)begin
            @(negedge clk);#1;
            inValid=1;inSop=i==0;inEop=i==count-1;
            rawData=samplePixel(i%640,i/640);
            // Sampling must use rawData, not the already modified downstream image.
            inData={10'd0,10'd900,10'd0};
            if(mutate&&i==1000)begin debugWords=0;rawDebugWords=0;showCandidates=0;showCentre=0;end
            @(posedge clk);while(!inReady)@(posedge clk);
        end
        @(negedge clk);#1;inValid=0;inSop=0;inEop=0;
        repeat(1000)@(negedge clk);
    endtask
    task automatic checkRecord(input int slot,r,g,b,h,s,v,digit,input bit blue);
        logic [79:0] record;
        record=dut.publishedRecords[slot];
        if(!record[79]||record[54:31]!=={8'(r),8'(g),8'(b)}||record[30:22]!=h||record[21:14]!=s||record[13:6]!=v)
            $fatal(1,"FAIL sampled RGB/HSV slot%0d record%h",slot,record);
        if(!record[78]||record[77]!==blue||record[76:73]!=digit)$fatal(1,"FAIL association metadata slot%0d",slot);
        sampleChecks++;
    endtask
    initial begin
        repeat(3)@(negedge clk);reset=0;
        hueBoundaryRgb={8'd60,8'd0,8'd180};#1;
        if(oldHueClass!=0||newHueClass!=2)$fatal(1,"FAIL exact H260 boundary / historical H250 profile");
        hueBoundaryRgb={8'd61,8'd0,8'd180};#1;
        if(newHueClass!=0)$fatal(1,"FAIL H above260 must reject");
        status='0;status.calibrated=1;status.activeCfgVersion=5;status.speechArmed=1;status.state=INTERACTION_SPEECH_ARMED;
        debugWords[0+:32]=32'h45425031;debugWords[1*32+:32]={16'(perception_pkg::DEBUG_SCHEMA_VERSION),16'(perception_pkg::PERCEPTION_CONTRACT_VERSION)};
        debugWords[3*32+:16]=99;debugWords[7*32+:16]=16'h3020;
        debugWords[9*32+:10]={5'd14,5'd2};debugWords[10*32+:76]=status;debugWords[(DEBUG_TAIL_BASE+1)*32+:4]=8;debugWords[(DEBUG_TAIL_BASE+3)*32]=1;
        debugWords[24*32+:32]=32'h81000000;debugWords[25*32+:32]={7'd0,9'd250,7'd0,9'd280};debugWords[26*32+:32]={8'd0,8'd10,8'd0,8'd50};
        debugWords[32*32+:32]=32'hc3000000;debugWords[33*32+:32]={7'd0,9'd100,7'd0,9'd220};debugWords[34*32+:32]={8'd0,8'd90,8'd0,8'd150};
        // Rejected red slot1 must not consume a sample or an empty panel row.
        debugWords[28*32+:32]=32'h0f000000;debugWords[29*32+:32]={7'd0,9'd40,7'd0,9'd60};debugWords[30*32+:32]={8'd0,8'd20,8'd0,8'd40};
        // Shared blue slot14 is BJ only because the schema7 pairing flag names it.
        debugWords[80*32+:32]=32'h4f000000;debugWords[81*32+:32]={7'd0,9'd50,7'd0,9'd90};debugWords[82*32+:32]={8'd0,8'd60,8'd0,8'd80};
        debugWords[84*32+:32]=32'hc6000000;debugWords[85*32+:32]={7'd0,9'd130,7'd0,9'd170};debugWords[86*32+:32]={8'd0,8'd170,8'd0,8'd190};
        debugWords[(DEBUG_TAIL_BASE+2)*32+3]=1;debugWords[(DEBUG_TAIL_BASE+2)*32+4+:4]=14;
        fixtureWords=debugWords;
        rawDebugWords=debugWords;
        // Invalid metadata must suppress every candidate UI/sample slot.
        rawDebugWords[(DEBUG_TAIL_BASE+3)*32]=0;rawDebugWords[9*32+:10]=0;#1;
        if(dut.nextMeta[0][24]||dut.nextMeta[8][24]||dut.nextMeta[17][24]||dut.nextMeta[16][23])
            $fatal(1,"FAIL bad-frame candidate/ID suppression");
        rawDebugWords[2*32+:32]=32'd150001;#1;
        if(dut.nextMeta[0][24]||dut.nextMeta[8][24]||dut.nextMeta[16][23])$fatal(1,"FAIL stale metadata kept ROI/ID");
        rawDebugWords=debugWords;
        #1;if(!dut.nextReference[17]||dut.nextReference[8]||dut.nextReference[9])$fatal(1,"FAIL unique paired reference index");
        rawDebugWords[1*32+16+:16]=5;#1;if(dut.nextReference!=0||dut.nextMeta[0][24])$fatal(1,"FAIL old schema accepted as capacity16 metadata");
        rawDebugWords=debugWords;
        rawDebugWords[(DEBUG_TAIL_BASE+2)*32+3]=0;#1;if(dut.nextReference!=0)$fatal(1,"FAIL no-digit blue guessed as reference");
        rawDebugWords=debugWords;rawDebugWords[(DEBUG_TAIL_BASE+3)*32]=0;#1;if(dut.nextReference!=0)$fatal(1,"FAIL bad frame kept BJ proof");
        rawDebugWords=debugWords;rawDebugWords[2*32+:32]=150001;#1;if(dut.nextReference!=0)$fatal(1,"FAIL stale frame kept BJ proof");
        rawDebugWords=debugWords;
        sendFrame(640*480,0);
        if(dut.sampleCount[0]!=16||dut.sampleCount[8]!=16||dut.sampleCount[16]!=64)$fatal(1,"FAIL exact ROI sample counts");
        checkRecord(0,192,0,0,0,255,192,1,0);
        checkRecord(8,0,87,184,212,255,184,3,1);
        checkRecord(16,0,87,184,212,255,184,3,1);
        if(!dut.publishedRecords[17][79]||!dut.publishedRecords[17][0]||dut.publishedRecords[17][78])
            $fatal(1,"FAIL BJ proof not bound through completed raw sample");
        sendFrame(640*480,1);
        if(!dut.heldShowCandidates||!dut.heldShowCentre||dut.displayStatus.activeCfgVersion!=5||dut.displaySampleCount!=8)
            $fatal(1,"FAIL mid-frame switch/status mutation escaped SOP freeze");
        sendFrame(10,0);
        if(dut.publishedRecords[16][79])$fatal(1,"FAIL truncated frame reused a valid centre sample");
        sendFrame(1,0);
        if(dut.displayRecords[16][79]||dut.heldShowCentre||dut.heldShowCandidates)$fatal(1,"FAIL invalid samples or switch disable did not latch");
        debugWords=fixtureWords;rawDebugWords=fixtureWords;
        showCandidates=0;showCentre=0;
        sendFrame(640*480,0);
        combinationTest=1;
        for(int mode=0;mode<4;mode++)begin
            expectedCandidates=mode[0];expectedCentre=mode[1];
            showCandidates=mode[0];showCentre=mode[1];
            sendFrame(640*480,0);
            if(dut.heldShowCandidates!==mode[0]||dut.heldShowCentre!==mode[1])
                $fatal(1,"FAIL switch combination %0d",mode);
        end
        if(candidateTextChecks!=4||centreTextChecks!=4)$fatal(1,"FAIL incomplete four-combination coverage");
        combinationTest=0;
        if(compactUiChecks!=6||roiTagChecks!=8||dut.displayRedRows!=1||dut.displayBlueRows!=2||dut.displayUiVisible[1]||
           dut.displayUiTags[0]!=10||dut.displayUiTags[8]!=0||dut.displayUiTags[9]!=1||!dut.displayUiVisible[17])
            $fatal(1,"FAIL recognised-only compact mapping/tag coverage");
        debugWords[(DEBUG_TAIL_BASE+2)*32+3]=0;#1;
        if(dut.nextUiVisible[17]||!dut.nextUiVisible[8]||!dut.nextUiVisible[9])$fatal(1,"FAIL BJ row survived missing current proof");
        debugWords=fixtureWords;debugWords[(DEBUG_TAIL_BASE+2)*32+4+:4]=8;#1;
        if(dut.nextUiVisible[17])$fatal(1,"FAIL BJ RGB sample reused for a different reference index");
        debugWords=fixtureWords;debugWords[(DEBUG_TAIL_BASE+3)*32]=0;#1;
        if(dut.nextUiVisible!=0)$fatal(1,"FAIL bad metadata left visible rows");
        debugWords=fixtureWords;debugWords[2*32+:32]=150001;#1;
        if(dut.nextUiVisible!=0)$fatal(1,"FAIL stale metadata left visible rows");
        debugWords=fixtureWords;
        debugWords[9*32+:10]={5'd9,5'd7};
        for(int i=1;i<7;i++)begin
            debugWords[(24+4*i)*32+:32]=32'h81000000;
            debugWords[(25+4*i)*32+:32]={7'd0,9'd250,7'd0,9'd280};
            debugWords[(26+4*i)*32+:32]={8'd0,8'd10,8'd0,8'd50};
        end
        rawDebugWords=debugWords;showCandidates=1;showCentre=1;
        sendFrame(640*480,0);
        overflowUiTest=1;sendFrame(640*438,0);overflowUiTest=0;
        if(!dut.displayRedOverflow||dut.displayRedRows!=6||dut.displayUiVisible[6]||dut.displayUiTags[5]!=15||overflowTextChecks!=1)
            $fatal(1,"FAIL red #A..F limit/explicit overflow");
        debugWords=fixtureWords;debugWords[3*32+:16]=100;debugWords[9*32+:10]={5'd16,5'd0};
        for(int i=0;i<16;i++)begin
            debugWords[(24+4*i)*32+:128]=0;
            debugWords[(24+4*i)*32+:32]=32'h4f000000;
        end
        debugWords[(DEBUG_TAIL_BASE+2)*32+4+:4]=15;
        for(int i=0;i<8;i++)begin
            debugWords[(24+4*i)*32+:32]=32'hc0000000|(32'(i<6?i+1:i-5)<<24);
            debugWords[(25+4*i)*32+:32]={7'd0,9'd50,7'd0,9'd90};
            debugWords[(26+4*i)*32+:32]={8'd0,8'd60,8'd0,8'd80};
        end
        debugWords[84*32+:32]=32'h4f000000;
        debugWords[85*32+:32]={7'd0,9'd50,7'd0,9'd90};
        debugWords[86*32+:32]={8'd0,8'd60,8'd0,8'd80};
        rawDebugWords=debugWords;
        sendFrame(640*480,0);
        allBlueUiTest=1;sendFrame(640*480,0);allBlueUiTest=0;
        if(allBlueChecks!=16||dut.displayBlueRows!=8||!dut.displayUiVisible[17]||dut.displayBlueOverflow)$fatal(1,"FAIL blue display mapping coverage");
        // Nine accepted blue bays exceed the eight presentation tags, while
        // capacity16 still carries all of them. BJ must remain independently
        // visible and cannot be mistaken for the ninth bay or consume tag7.
        debugWords[3*32+:16]=101;
        debugWords[80*32+:32]=32'hc5000000;
        debugWords[81*32+:32]={7'd0,9'd50,7'd0,9'd90};
        debugWords[82*32+:32]={8'd0,8'd60,8'd0,8'd80};
        rawDebugWords=debugWords;
        sendFrame(640*480,0);
        blueOverflowUiTest=1;sendFrame(640*438,0);blueOverflowUiTest=0;
        if(!dut.displayBlueOverflow||dut.displayBlueRows!=8||dut.displayUiTags[15]!=7||
           !dut.displayUiVisible[17]||blueOverflowTextChecks!=1)$fatal(1,"FAIL blue #0..7 limit/BJ/explicit overflow");
        if(read!=written||outValid)$fatal(1,"FAIL stream did not drain");
        $display("PASS memberBVgaDiagnostics_tb: %0d pixels, exact 4x4/8x8 RGB/HSV, association, status/switch freeze, partial-frame rejection, backpressure",read);
        $finish;
    end
    initial begin #100000000;$fatal(1,"FAIL diagnostic timeout");end
endmodule
