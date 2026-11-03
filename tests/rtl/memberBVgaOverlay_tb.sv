`timescale 1ns/1ps
module memberBVgaOverlay_tb;
    logic clk=0;
    always #20 clk=~clk;
    logic reset=1;
    logic showCandidates=0,showCentre=0;
    logic [perception_pkg::DEBUG_WORD_COUNT*32-1:0] debugWords=0;
    logic [29:0] inData=30'h20080200,outData;
    logic inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=0;
    logic expectedDraw=0,expectedBlue=1,expectedReference=0;
    integer inputX=0,inputY=0,writeCount=0,readCount=0,readyCycles=0;
    logic [31:0] expectedQueue[0:80000];
    logic priorStall=0;
    logic [31:0] expectedFrames[0:99];
    integer frameWritten=0,frameRead=0;
    logic [31:0] priorPayload;
    memberBVgaOverlay #(.MAX_HOLD_FRAMES(3),.ENABLE_DIAGNOSTICS(0),.BLUE_HUE_UPPER(250),.DEFAULT_BLUE_MINIMUM(32)) dut(.*);

    // Independent display-pixel oracle: multiple disjoint blue regions, a
    // diagonal red region, an orange non-target and an unlabelled reference bar.
    function automatic logic [1:0] rawClass(input integer x,y);
        begin
            rawClass=0;
            if((x>=155&&x<=171&&y<15)||(x>=300&&x<310&&y>=3&&y<9)||
               (x>=330&&x<340&&y>=3&&y<9))rawClass=2;
            if(x>=400+y&&x<404+y&&y<15)rawClass=1;
        end
    endfunction
    function automatic logic [29:0] rawPixel(input integer x,y);
        begin
            case(rawClass(x,y))
                1:rawPixel={10'd768,10'd0,10'd0};
                2:rawPixel={10'd0,10'd348,10'd736};
                default:rawPixel={10'd512,10'd512,10'd512};
            endcase
            if(x>=450&&x<460)rawPixel={10'd816,10'd408,10'd0}; // orange H30
        end
    endfunction
    function automatic logic [29:0] expectedPixel(input integer x,y,input logic draw,blue,isReference);
        integer gx,gy;
        logic [1:0] here,left,above,edgeClass;
        logic hEdge,vEdge,ink;
        begin
            here=rawClass(x,y);left=x==0?2'd0:rawClass(x-1,y);above=y==0?2'd0:rawClass(x,y-1);
            hEdge=here!=left;vEdge=here!=above;edgeClass=0;
            if(hEdge||vEdge||((x==639||y==479)&&here!=0))begin
                if(here!=0)edgeClass=here;
                else if(hEdge&&left!=0)edgeClass=left;
                else edgeClass=above;
            end
            expectedPixel=rawPixel(x,y);
            if(edgeClass==1)expectedPixel={10'h3ff,10'd0,10'd0};
            if(edgeClass==2)expectedPixel={10'd0,10'd0,10'h3ff};
            gx=x-158;gy=y-3;
            if(draw && x>=140 && x<500 && gx>=0 && gx<16 && gy>=0 && gy<12)begin
                ink=(gx==15&&((gy>=1&&gy<=4)||(gy>=6&&gy<=10)))||
                    (isReference&&((gy==11&&gx>=9&&gx<=14)||(gx==8&&gy>=6&&gy<=10)))||
                    (gx==0&&gy>=1&&gy<=10)||((gy==0||gy==5)&&gx>=0&&gx<=4)||(gx==5&&gy>=1&&gy<=4);
                if(blue)ink=ink||(gy==11&&gx>=0&&gx<=4)||(gx==5&&gy>=6&&gy<=10);
                else ink=ink||(gy>=6&&gy<=10&&gx==gy-5);
                expectedPixel=ink?{10'h3ff,10'h3ff,10'h3ff}:
                    blue?{10'd0,10'd128,10'd512}:{10'd512,10'd0,10'd0};
            end
        end
    endfunction
    always @(negedge clk)begin
        readyCycles=readyCycles+1;
        outReady=!reset && readyCycles%5!=0 && readyCycles%7!=0;
    end
    always @(posedge clk)begin
        if(reset)begin priorStall=0;end
        else begin
            if(priorStall && (!outValid || {outSop,outEop,outData}!==priorPayload))
                $fatal(1,"Avalon-ST payload changed while stalled");
            priorStall=outValid&&!outReady;
            priorPayload={outSop,outEop,outData};
            if(inValid && inReady)begin
                if(inSop)begin expectedFrames[frameWritten]=debugWords[3*32+:32];frameWritten=frameWritten+1;end
                expectedQueue[writeCount]={inSop,inEop,expectedPixel(inputX,inputY,expectedDraw,expectedBlue,expectedReference)};
                writeCount=writeCount+1;
            end
            if(dut.contourValid && dut.contourReady && dut.contourSop)begin
                if(dut.frameDebug[3*32+:32]!==expectedFrames[frameRead])$fatal(1,"SOP debug metadata changed in flight");
                frameRead=frameRead+1;
            end
            if(outValid && outReady)begin
                if(readCount>=writeCount)$fatal(1,"Output without input");
                if({outSop,outEop,outData}!==expectedQueue[readCount])
                    $fatal(1,"Overlay mismatch output=%0d expected=%08x actual=%08x",readCount,expectedQueue[readCount],{outSop,outEop,outData});
                readCount=readCount+1;
            end
        end
    end
    task automatic metadata(input integer frameId,input logic good,input integer age,input logic blue);
        begin
            debugWords=0;
            debugWords[31:0]=32'h45425031;debugWords[1*32+:32]={16'(perception_pkg::DEBUG_SCHEMA_VERSION),16'd2};
            debugWords[2*32+:32]=32'd200000;
            debugWords[3*32+:32]=frameId;
            debugWords[4*32+:32]=32'd200000-age;
            debugWords[(perception_pkg::DEBUG_TAIL_BASE+3)*32]=good;
            debugWords[24*32+:32]={1'b1,blue,2'd0,4'd1,8'd255,8'd0,1'd0,7'b0000110};
            debugWords[25*32+:32]={7'd0,9'd310,7'd0,9'd319};
            debugWords[26*32+:32]={8'd0,8'd10,8'd0,8'd20};
        end
    endtask
    task automatic referenceMetadata(input integer frameId,input logic validPair,input logic good,input integer age,input integer schema);
        begin
            metadata(frameId,good,age,1);
            debugWords[31:0]=32'h45425031;debugWords[1*32+:32]={16'(schema),16'd2};
            debugWords[84*32+:32]=32'h4f000000;
            debugWords[85*32+:32]=debugWords[25*32+:32];
            debugWords[86*32+:32]=debugWords[26*32+:32];
            debugWords[24*32+:32]=0;
            debugWords[(perception_pkg::DEBUG_TAIL_BASE+2)*32+3]=validPair;debugWords[(perception_pkg::DEBUG_TAIL_BASE+2)*32+4+:4]=15;
        end
    endtask
    task automatic sendPixels(input integer count,input logic draw,input logic blue,input logic mutateMidFrame);
        begin
            for(int index=0;index<count;index++)begin
                @(negedge clk);#1;
                inputX=index%640;inputY=index/640;inData=rawPixel(inputX,inputY);
                inValid=1;inSop=index==0;inEop=index==count-1;
                expectedDraw=draw;expectedBlue=blue;
                if(mutateMidFrame && index==100) debugWords='0;
                @(posedge clk);
                while(!inReady)@(posedge clk);
                // Keep the accepted source stable until the next falling edge.
            end
            @(negedge clk);#1;inValid=0;inSop=0;inEop=0;
            repeat(5)@(negedge clk);
        end
    endtask
    initial begin
        repeat(4)@(negedge clk);reset=0;
        metadata(1,1,100,1);sendPixels(9600,1,1,1);
        // Bad-frame metadata removes previous labels at the next accepted SOP.
        metadata(2,0,100,1);sendPixels(200,0,1,0);
        metadata(3,1,100,0);sendPixels(200,1,0,0);
        metadata(3,1,100,0);sendPixels(200,1,0,0);
        metadata(3,1,100,0);sendPixels(200,1,0,0);
        metadata(3,1,100,0);sendPixels(200,0,0,0);
        metadata(4,1,150001,1);sendPixels(200,0,1,0);
        metadata(5,1,-1,1);sendPixels(200,0,1,0);
        metadata(6,1,100,1);sendPixels(200,1,1,0);
        // BJ is a separately proven blue reference. Rejected blue pixels alone
        // must never invent this label, and older schemas have no such proof.
        expectedReference=1;
        referenceMetadata(7,1,1,100,7);sendPixels(9600,1,1,0);
        referenceMetadata(8,0,1,100,7);sendPixels(9600,0,1,0);
        referenceMetadata(9,1,0,100,7);sendPixels(9600,0,1,0);
        referenceMetadata(10,1,1,150001,7);sendPixels(9600,0,1,0);
        referenceMetadata(11,1,1,100,4);sendPixels(9600,0,1,0);
        expectedReference=0;
        // Consecutive one-pixel/truncated packets must retain their own metadata.
        for(int f=0;f<8;f++)begin
            @(negedge clk);#1;metadata(100+f,1,100,1);
            inputX=0;inputY=0;inData=rawPixel(0,0);expectedDraw=1;expectedBlue=1;
            inValid=1;inSop=1;inEop=1;
            @(posedge clk);while(!inReady)@(posedge clk);
        end
        @(negedge clk);#1;inValid=0;inSop=0;inEop=0;
        repeat(10)@(negedge clk);
        if(readCount!=writeCount || outValid)$fatal(1,"Stream did not drain");
        reset=1;@(negedge clk);
        if(outValid || outData!=0)$fatal(1,"Reset did not clear the output slot");
        $display("PASS memberBVgaOverlay_tb: %0d pixels, raw contours, accepted digits only, no boxes, stale/bad frames, stalls",readCount);
        $finish;
    end
    initial begin #5000000;$fatal(1,"Global timeout");end
endmodule
