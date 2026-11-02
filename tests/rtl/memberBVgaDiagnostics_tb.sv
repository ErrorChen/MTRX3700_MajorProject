`timescale 1ns/1ps
module memberBVgaDiagnostics_tb;
    import perception_pkg::*;
    logic clk=0,reset=1,showCandidates=1,showCentre=1;
    logic [3071:0] debugWords=0,rawDebugWords=0;
    logic [29:0] rawData=0,inData=0,outData;
    logic rawSop,rawEop,rawAccept,inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=0;
    integer cycles=0,written=0,read=0,frameNumber=0,sampleChecks=0,outputX=0,outputY=0;
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
        debugWords[0+:32]=32'h45425031;debugWords[3*32+:16]=99;debugWords[7*32+:16]=16'h3020;
        debugWords[9*32+:8]=8'h11;debugWords[10*32+:76]=status;debugWords[89*32+:4]=8;debugWords[91*32]=1;
        debugWords[24*32+:32]=32'h81000000;debugWords[25*32+:32]={7'd0,9'd250,7'd0,9'd280};debugWords[26*32+:32]={8'd0,8'd10,8'd0,8'd50};
        debugWords[56*32+:32]=32'hc3000000;debugWords[57*32+:32]={7'd0,9'd100,7'd0,9'd220};debugWords[58*32+:32]={8'd0,8'd90,8'd0,8'd150};
        rawDebugWords=debugWords;
        // Overflow clears the reliable count/ID, but retained nondegenerate
        // diagnostic bboxes must remain sampleable and explicitly bad-frame.
        rawDebugWords[91*32]=0;rawDebugWords[9*32+:8]=0;#1;
        if(!dut.nextMeta[0][24]||!dut.nextMeta[8][24]||dut.nextMeta[0][23]||dut.nextMeta[8][23]||dut.nextMeta[16][23])
            $fatal(1,"FAIL bad-frame bbox visibility or reliable-ID suppression");
        rawDebugWords[2*32+:32]=32'd150001;#1;
        if(dut.nextMeta[0][24]||dut.nextMeta[8][24]||dut.nextMeta[16][23])$fatal(1,"FAIL stale metadata kept ROI/ID");
        rawDebugWords=debugWords;
        sendFrame(640*480,0);
        if(dut.sampleCount[0]!=16||dut.sampleCount[8]!=16||dut.sampleCount[16]!=64)$fatal(1,"FAIL exact ROI sample counts");
        checkRecord(0,192,0,0,0,255,192,1,0);
        checkRecord(8,0,87,184,212,255,184,3,1);
        checkRecord(16,0,87,184,212,255,184,3,1);
        sendFrame(640*480,1);
        if(!dut.heldShowCandidates||!dut.heldShowCentre||dut.displayStatus.activeCfgVersion!=5||dut.displaySampleCount!=8)
            $fatal(1,"FAIL mid-frame switch/status mutation escaped SOP freeze");
        sendFrame(10,0);
        if(dut.publishedRecords[16][79])$fatal(1,"FAIL truncated frame reused a valid centre sample");
        sendFrame(1,0);
        if(dut.displayRecords[16][79]||dut.heldShowCentre||dut.heldShowCandidates)$fatal(1,"FAIL invalid samples or switch disable did not latch");
        if(read!=written||outValid)$fatal(1,"FAIL stream did not drain");
        $display("PASS memberBVgaDiagnostics_tb: %0d pixels, exact 4x4/8x8 RGB/HSV, association, status/switch freeze, partial-frame rejection, backpressure",read);
        $finish;
    end
    initial begin #20000000;$fatal(1,"FAIL diagnostic timeout");end
endmodule
