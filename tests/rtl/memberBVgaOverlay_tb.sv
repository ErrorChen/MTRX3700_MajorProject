`timescale 1ns/1ps
module memberBVgaOverlay_tb;
    logic clk=0;
    always #20 clk=~clk;
    logic reset=1;
    logic [3071:0] debugWords=0;
    logic [29:0] inData=30'h1234567,outData;
    logic inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=0;
    logic expectedDraw=0,expectedBlue=1;
    integer inputX=0,inputY=0,writeCount=0,readCount=0,readyCycles=0;
    logic [31:0] expectedQueue[0:20000];
    logic priorStall=0;
    logic [31:0] priorPayload;
    memberBVgaOverlay #(.MAX_HOLD_FRAMES(3)) dut(.*);

    function automatic logic [29:0] expectedPixel(input integer x,y,input logic draw,blue);
        integer u,v,gx,gy;
        logic border,ink;
        begin
            expectedPixel=30'h1234567;
            u=((x-140)*2)/3;v=(y*2)/3;gx=x-158;gy=y-3;
            if(draw && x>=140 && x<500)begin
                if(gx>=0 && gx<8 && gy>=0 && gy<12)begin
                    ink=gx==7 && ((gy>=1&&gy<=4)||(gy>=6&&gy<=10));
                    expectedPixel=ink?{10'h3ff,10'h3ff,10'h3ff}:30'd0;
                end
                border=u>=10&&u<=20&&v>=0&&v<=9&&(u==10||u==20||v==0||v==9);
                if(border)expectedPixel=blue?{10'd0,10'h3ff,10'd0}:{10'h3ff,10'h3ff,10'd0};
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
                expectedQueue[writeCount]={inSop,inEop,expectedPixel(inputX,inputY,expectedDraw,expectedBlue)};
                writeCount=writeCount+1;
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
            debugWords[2*32+:32]=32'd200000;
            debugWords[3*32+:32]=frameId;
            debugWords[4*32+:32]=32'd200000-age;
            debugWords[91*32]=good;
            debugWords[24*32+:32]={1'b1,blue,2'd0,4'd1,8'd255,8'd0,1'd0,7'b0000110};
            debugWords[25*32+:32]={7'd0,9'd310,7'd0,9'd319};
            debugWords[26*32+:32]={8'd0,8'd10,8'd0,8'd20};
        end
    endtask
    task automatic sendPixels(input integer count,input logic draw,input logic blue,input logic mutateMidFrame);
        begin
            for(int index=0;index<count;index++)begin
                @(negedge clk);#1;
                inputX=index%640;inputY=index/640;
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
        // Bad-frame metadata removes previous boxes at the next accepted SOP.
        metadata(2,0,100,1);sendPixels(200,0,1,0);
        metadata(3,1,100,0);sendPixels(200,1,0,0);
        metadata(3,1,100,0);sendPixels(200,1,0,0);
        metadata(3,1,100,0);sendPixels(200,1,0,0);
        metadata(3,1,100,0);sendPixels(200,0,0,0);
        metadata(4,1,150001,1);sendPixels(200,0,1,0);
        metadata(5,1,-1,1);sendPixels(200,0,1,0);
        metadata(6,1,100,1);sendPixels(200,1,1,0);
        repeat(10)@(negedge clk);
        if(readCount!=writeCount || outValid)$fatal(1,"Stream did not drain");
        reset=1;@(negedge clk);
        if(outValid || outData!=0)$fatal(1,"Reset did not clear the output slot");
        $display("PASS memberBVgaOverlay_tb: %0d pixels, held metadata, boxes/digits, stale/bad frames, stalls",readCount);
        $finish;
    end
    initial begin #5000000;$fatal(1,"Global timeout");end
endmodule
