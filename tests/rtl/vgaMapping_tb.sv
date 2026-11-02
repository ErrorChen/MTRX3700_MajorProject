`timescale 1ns/1ps
// Portable full-raster verification of the production display mapping.
// The address oracle deliberately uses integer division, independently of the
// proposed reciprocal multiplication. Every 640x480 address is visited, with
// stalls and a changing RAM response to exercise the existing hold semantics.
module vgaMapping_tb;
    logic clk=0;
    always #20 clk=~clk;
    logic reset=1;
    logic [3071:0] debugWords=0;
    logic [8:0] newX;
    logic [7:0] newY;
    logic [15:0] ramPixel=0;
    logic [29:0] newInput,newOutput;
    logic newSop,newEop,newValid,newReady;
    logic newOutSop,newOutEop,newOutValid;
    logic sinkReady=0;
    integer cycleCount=0,pixelCount=0,outputCount=0,stallCount=0;
    integer modelX=0,modelY=0,fetchX,fetchY,nextX,nextY,expectedX,expectedY;
    logic previousStall=0;
    logic [31:0] previousPayload;

    camera_display #(.ROTATE_CCW_90(1)) cameraNew(
        .clk(clk),.reset(reset),.hold_enable(1'b1),.rd_x(newX),.rd_y(newY),.rd_pixel(ramPixel),
        .data(newInput),.startofpacket(newSop),.endofpacket(newEop),.valid(newValid),.ready(newReady));
    memberBVgaOverlay overlayNew(.clk(clk),.reset(reset),.debugWords(debugWords),
        .inData(newInput),.inSop(newSop),.inEop(newEop),.inValid(newValid),.inReady(newReady),
        .outData(newOutput),.outSop(newOutSop),.outEop(newOutEop),.outValid(newOutValid),.outReady(sinkReady));

    always @(negedge clk) begin
        cycleCount=cycleCount+1;
        sinkReady=!reset && cycleCount%5!=0 && cycleCount%7!=0 && cycleCount%19!=0;
        #1;
        if(!reset)begin
            if(newSop !== (modelX==0 && modelY==0) || newEop !== (modelX==639 && modelY==479))
                $fatal(1,"Packet boundary differs from the independent raster oracle");
            nextX=modelX==639?0:modelX+1;
            nextY=modelX==639?(modelY==479?0:modelY+1):modelY;
            fetchX=newValid&&newReady?nextX:modelX;
            fetchY=newValid&&newReady?nextY:modelY;
            expectedX=0;expectedY=0;
            if(fetchX>=140 && fetchX<500)begin
                expectedX=319-(fetchY*2)/3;
                expectedY=((fetchX-140)*2)/3;
            end
            if(newX!==9'(expectedX) || newY!==8'(expectedY))
                $fatal(1,"Address oracle failed x%0d y%0d: got%0d,%0d expected%0d,%0d",
                    fetchX,fetchY,newX,newY,expectedX,expectedY);
            if(cameraNew.twoThirds(9'(modelY)) !== 9'((modelY*2)/3))
                $fatal(1,"Display vertical coordinate mismatch");
            if(modelX>=140 && modelX<500 &&
               cameraNew.twoThirds(9'(modelX-140)) !== 9'(((modelX-140)*2)/3))
                $fatal(1,"Display horizontal coordinate mismatch");
        end
    end
    always @(posedge clk)begin
        ramPixel <= {newX[7:0],newY} ^ 16'(cycleCount);
        if(reset)begin modelX=0;modelY=0;previousStall=0;end
        else begin
            if(previousStall && {newOutValid,newOutSop,newOutEop,newOutput} !== {1'b1,previousPayload})
                $fatal(1,"Output changed during stall");
            previousStall=newOutValid&&!sinkReady;
            previousPayload={newOutSop,newOutEop,newOutput};
            if(previousStall)stallCount=stallCount+1;
            if(newValid&&newReady)begin
                pixelCount=pixelCount+1;
                if(modelX==639)begin modelX=0;modelY=modelY==479?0:modelY+1;end
                else modelX=modelX+1;
            end
            if(newOutValid&&sinkReady)begin
                outputCount=outputCount+1;
                if(newOutEop)begin
                    if(outputCount!=640*480 || stallCount<10000)$fatal(1,"Coverage incomplete");
                    $display("PASS vgaMapping_tb pixels=%0d stalls=%0d cycles=%0d",outputCount,stallCount,cycleCount);
                    $finish;
                end
            end
        end
    end
    initial begin
        for(int n=0;n<512;n++)begin
            if(cameraNew.twoThirds(9'(n)) !== 9'((n*2)/3))
                $fatal(1,"Exact reciprocal mismatch %0d",n);
        end
        debugWords[2*32+:32]=200000;debugWords[3*32+:32]=1;
        debugWords[4*32+:32]=199900;debugWords[91*32]=1;
        for(int i=0;i<16;i++)begin
            debugWords[(24+i*4)*32+:32]={1'b1,1'(i%2),2'd0,4'(1+i%6),8'd255,8'd0,1'b0,7'b0};
            debugWords[(25+i*4)*32+:32]={7'd0,9'(10+(i%4)*75),7'd0,9'(60+(i%4)*75)};
            debugWords[(26+i*4)*32+:32]={8'd0,8'(5+(i/4)*55),8'd0,8'(45+(i/4)*55)};
        end
        repeat(5)@(negedge clk);#2;reset=0;
    end
    initial begin #30000000;$fatal(1,"Timeout");end
endmodule
